using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using Process = System.Diagnostics.Process;
using ProcessStartInfo = System.Diagnostics.ProcessStartInfo;

namespace SRP.F03.Editor
{
    public static class F03Build
    {
        private const string GeneratedScenePath = "Assets/F03/Generated/F03DevReplayBuild.unity";

        [MenuItem("SRP/F-03/Build Windows DEV-REPLAY")]
        public static void BuildWindowsDevReplay()
        {
            var unityRoot = Directory.GetParent(Application.dataPath)?.FullName
                ?? throw new BuildFailedException("F03_UNITY_ROOT_UNAVAILABLE");
            var outputDirectory = ResolveOutputDirectory(unityRoot, ReadArgument("-f03OutputPath"));
            var executablePath = Path.Combine(outputDirectory, "SRP-F03-DevReplay.exe");
            PrepareOutputDirectory(unityRoot, outputDirectory);

            var commit = ReadGitCommit(unityRoot);
            var implementationTreeHash = ReadImplementationTreeHash();
            var buildUtc = DateTime.UtcNow.ToString("O");
            var revision = File.ReadAllText(Path.Combine(unityRoot, "ProjectSettings", "ProjectVersion.txt")).Trim();

            Directory.CreateDirectory(Path.GetDirectoryName(GeneratedScenePath) ?? "Assets/F03/Generated");
            try
            {
                CreateGeneratedBuildScene(commit, buildUtc, revision);
                using (F03BuildAuthorization.Begin())
                {
                    var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                    {
                        scenes = new[] { GeneratedScenePath },
                        locationPathName = executablePath,
                        target = BuildTarget.StandaloneWindows64,
                        options = BuildOptions.Development | BuildOptions.StrictMode | BuildOptions.CleanBuildCache
                    });
                    if (report.summary.result != BuildResult.Succeeded)
                    {
                        throw new BuildFailedException($"F03_DEV_BUILD_FAILED result={report.summary.result}");
                    }
                }

                WriteBuildManifest(unityRoot, outputDirectory, commit, implementationTreeHash, buildUtc, revision);
                Debug.Log($"F03_DEV_BUILD_SUCCEEDED output={executablePath}");
            }
            finally
            {
                AssetDatabase.DeleteAsset(GeneratedScenePath);
                AssetDatabase.DeleteAsset("Assets/F03/Generated");
            }
        }

        public static void BuildUnauthorizedDevelopmentProbe()
        {
            Environment.SetEnvironmentVariable(F03BuildAuthorization.EnvironmentVariable, null);
            var unityRoot = Directory.GetParent(Application.dataPath)?.FullName
                ?? throw new BuildFailedException("F03_UNITY_ROOT_UNAVAILABLE");
            var outputDirectory = Path.Combine(unityRoot, "Builds", "F03-DevReplay", "unauthorized-probe");
            PrepareOutputDirectory(unityRoot, outputDirectory);
            BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { F03SceneContract.SourceScenePath },
                locationPathName = Path.Combine(outputDirectory, "unauthorized.exe"),
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.Development | BuildOptions.StrictMode
            });
            throw new BuildFailedException("UNAUTHORIZED_DEVELOPMENT_BUILD_UNEXPECTEDLY_COMPLETED");
        }

        private static void CreateGeneratedBuildScene(string commit, string buildUtc, string revision)
        {
            var scene = EditorSceneManager.OpenScene(F03SceneContract.SourceScenePath, OpenSceneMode.Single);
            var inspection = F03SceneContract.Inspect(scene);
            if (!inspection.IsValid)
            {
                throw new BuildFailedException(inspection.Error);
            }

            if (!EditorSceneManager.SaveScene(scene, GeneratedScenePath, true))
            {
                throw new BuildFailedException("F03_GENERATED_SCENE_SAVE_FAILED");
            }

            var generatedScene = EditorSceneManager.OpenScene(GeneratedScenePath, OpenSceneMode.Single);
            var banner = generatedScene.GetRootGameObjects()
                .SelectMany(root => root.GetComponentsInChildren<DevReplayBanner>(true))
                .Single();
            banner.ConfigureBuildEvidence(commit, buildUtc, revision.Replace("m_EditorVersion: ", string.Empty).Replace("m_EditorVersionWithRevision: ", string.Empty).Replace("\r", " | ").Replace("\n", " | "));
            EditorUtility.SetDirty(banner);
            EditorSceneManager.SaveScene(generatedScene);
        }

        private static string ResolveOutputDirectory(string unityRoot, string requested)
        {
            var buildsRoot = Path.GetFullPath(Path.Combine(unityRoot, "Builds", "F03-DevReplay"));
            var output = string.IsNullOrWhiteSpace(requested)
                ? Path.Combine(buildsRoot, "run")
                : (Path.IsPathRooted(requested) ? requested : Path.Combine(unityRoot, requested));
            output = Path.GetFullPath(output);
            var prefix = buildsRoot.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!output.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                throw new BuildFailedException($"F03_OUTPUT_OUTSIDE_ALLOWED_ROOT output={output}");
            }
            return output;
        }

        private static void PrepareOutputDirectory(string unityRoot, string outputDirectory)
        {
            var buildsRoot = Path.GetFullPath(Path.Combine(unityRoot, "Builds", "F03-DevReplay"));
            if (Directory.Exists(outputDirectory))
            {
                var resolved = Path.GetFullPath(outputDirectory);
                if (string.Equals(resolved, buildsRoot, StringComparison.OrdinalIgnoreCase))
                {
                    throw new BuildFailedException("F03_REFUSE_DELETE_BUILDS_ROOT");
                }
                Directory.Delete(resolved, true);
            }
            Directory.CreateDirectory(outputDirectory);
        }

        private static string ReadGitCommit(string unityRoot)
        {
            var repoRoot = Directory.GetParent(Directory.GetParent(Directory.GetParent(unityRoot)?.FullName ?? string.Empty)?.FullName ?? string.Empty)?.FullName;
            if (string.IsNullOrWhiteSpace(repoRoot))
            {
                throw new BuildFailedException("F03_REPO_ROOT_UNAVAILABLE");
            }

            using var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "git",
                    Arguments = $"-C \"{repoRoot}\" rev-parse HEAD",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                }
            };
            process.Start();
            var output = process.StandardOutput.ReadToEnd().Trim();
            var error = process.StandardError.ReadToEnd().Trim();
            process.WaitForExit();
            if (process.ExitCode != 0 || output.Length != 40)
            {
                throw new BuildFailedException($"F03_GIT_COMMIT_UNAVAILABLE {error}");
            }
            return output;
        }

        private static string ReadImplementationTreeHash()
        {
            var value = Environment.GetEnvironmentVariable("SRP_F03_IMPLEMENTATION_TREE_SHA256");
            if (string.IsNullOrWhiteSpace(value) || value.Length != 64 || value.Any(character => !Uri.IsHexDigit(character)))
            {
                throw new BuildFailedException("F03_IMPLEMENTATION_TREE_HASH_UNAVAILABLE");
            }
            return value.ToLowerInvariant();
        }

        private static void WriteBuildManifest(string unityRoot, string outputDirectory, string commit, string implementationTreeHash, string buildUtc, string revision)
        {
            var files = Directory.GetFiles(outputDirectory, "*", SearchOption.AllDirectories)
                .Where(path => !path.EndsWith("f03-build-manifest.json", StringComparison.OrdinalIgnoreCase))
                .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                .Select(path => new BuildFileEntry
                {
                    path = Path.GetRelativePath(outputDirectory, path).Replace('\\', '/'),
                    bytes = new FileInfo(path).Length,
                    sha256 = Sha256(path)
                })
                .ToArray();
            var manifest = new BuildManifest
            {
                schema_version = "f03-build-manifest-v1",
                task_id = "F-03",
                build_mode = "DEV-REPLAY",
                formal_use_allowed = false,
                implementation_commit = commit,
                implementation_tree_sha256 = implementationTreeHash,
                build_utc = buildUtc,
                unity_revision = revision,
                environment_hash_policy = "sha256_lf_no_trailing_ws_text_v1",
                project_version_sha256 = CanonicalTextSha256(Path.Combine(unityRoot, "ProjectSettings", "ProjectVersion.txt")),
                package_manifest_sha256 = CanonicalTextSha256(Path.Combine(unityRoot, "Packages", "manifest.json")),
                package_lock_sha256 = CanonicalTextSha256(Path.Combine(unityRoot, "Packages", "packages-lock.json")),
                source_scene = F03SceneContract.SourceScenePath,
                files = files
            };
            File.WriteAllText(
                Path.Combine(outputDirectory, "f03-build-manifest.json"),
                JsonUtility.ToJson(manifest, true) + Environment.NewLine);
        }

        private static string Sha256(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha256 = SHA256.Create();
            return BitConverter.ToString(sha256.ComputeHash(stream)).Replace("-", string.Empty).ToLowerInvariant();
        }

        private static string CanonicalTextSha256(string path)
        {
            var content = File.ReadAllBytes(path);
            using var canonical = new MemoryStream(content.Length);
            var lineStart = 0;
            for (var index = 0; index < content.Length; index++)
            {
                if (content[index] != 10)
                {
                    continue;
                }
                var lineEnd = index;
                if (lineEnd > lineStart && content[lineEnd - 1] == 13)
                {
                    lineEnd--;
                }
                while (lineEnd > lineStart && (content[lineEnd - 1] == 9 || content[lineEnd - 1] == 32))
                {
                    lineEnd--;
                }
                canonical.Write(content, lineStart, lineEnd - lineStart);
                canonical.WriteByte(10);
                lineStart = index + 1;
            }
            if (lineStart < content.Length)
            {
                var lineEnd = content.Length;
                while (lineEnd > lineStart && (content[lineEnd - 1] == 9 || content[lineEnd - 1] == 32))
                {
                    lineEnd--;
                }
                canonical.Write(content, lineStart, lineEnd - lineStart);
            }
            using var sha256 = SHA256.Create();
            return BitConverter.ToString(sha256.ComputeHash(canonical.ToArray())).Replace("-", string.Empty).ToLowerInvariant();
        }

        private static string ReadArgument(string name)
        {
            var args = Environment.GetCommandLineArgs();
            for (var index = 0; index < args.Length - 1; index++)
            {
                if (string.Equals(args[index], name, StringComparison.Ordinal))
                {
                    return args[index + 1];
                }
            }
            return null;
        }

        [Serializable]
        private sealed class BuildManifest
        {
            public string schema_version;
            public string task_id;
            public string build_mode;
            public bool formal_use_allowed;
            public string implementation_commit;
            public string implementation_tree_sha256;
            public string build_utc;
            public string unity_revision;
            public string environment_hash_policy;
            public string project_version_sha256;
            public string package_manifest_sha256;
            public string package_lock_sha256;
            public string source_scene;
            public BuildFileEntry[] files;
        }

        [Serializable]
        private sealed class BuildFileEntry
        {
            public string path;
            public long bytes;
            public string sha256;
        }
    }
}
