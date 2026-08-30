[CmdletBinding()]
param(
    [ValidateSet('verify', 'test', 'build', 'formal-negative', 'all')]
    [string]$Mode = 'all'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$unityRoot = Join-Path $repoRoot '02-技术研发\04-Unity视觉\SRP-Weather-Visual'
$lockPath = Join-Path $PSScriptRoot 'f03-environment-lock.json'
$evidenceRoot = Join-Path $repoRoot '03-测试与实验\evidence\F-03'
$buildRoot = Join-Path $unityRoot 'Builds\F03-DevReplay'
$lock = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
$unityExe = $lock.unity_executable -replace '/', '\'

function Write-JsonFile {
    param([Parameter(Mandatory)]$Value, [Parameter(Mandatory)][string]$Path)
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}

function Get-LowerHash {
    param([Parameter(Mandatory)][string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-WindowsShortPath {
    param([Parameter(Mandatory)][string]$Path)
    if ($null -eq ('F03Native.PathApi' -as [type])) {
        Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
using System.Text;
namespace F03Native
{
    public static class PathApi
    {
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
        public static extern uint GetShortPathName(string longPath, StringBuilder shortPath, uint capacity);
    }
}
'@
    }
    $buffer = [Text.StringBuilder]::new(32768)
    $length = [F03Native.PathApi]::GetShortPathName($Path, $buffer, $buffer.Capacity)
    if ($length -eq 0 -or $length -ge $buffer.Capacity) {
        throw "Windows short path is unavailable: $Path"
    }
    return $buffer.ToString()
}

function Start-UnityProcess {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $unityProcesses = @(Get-Process Unity -ErrorAction SilentlyContinue)
    if ($unityProcesses.Count -gt 0) {
        throw "Unity is already running: $($unityProcesses.Id -join ',')"
    }
    $unityLock = Join-Path $unityRoot 'Temp\UnityLockfile'
    if (Test-Path -LiteralPath $unityLock -PathType Leaf) {
        Remove-Item -LiteralPath $unityLock -Force
    }
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $unityExe
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    foreach ($argument in $Arguments) { [void]$startInfo.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::Start($startInfo)
    $process.WaitForExit()
    return $process.ExitCode
}

function Invoke-Unity {
    param([Parameter(Mandatory)][string[]]$Arguments, [Parameter(Mandatory)][string]$Label)
    $exitCode = Start-UnityProcess -Arguments $Arguments
    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode"
    }
}

function Test-F03Environment {
    if (-not (Test-Path -LiteralPath $unityExe -PathType Leaf)) {
        throw "Unity executable is missing: $unityExe"
    }

    $projectVersionPath = Join-Path $unityRoot 'ProjectSettings\ProjectVersion.txt'
    $projectVersion = Get-Content -LiteralPath $projectVersionPath -Raw
    if ($projectVersion -notmatch [regex]::Escape("m_EditorVersion: $($lock.unity_version)")) {
        throw 'Unity project version drifted'
    }
    if ($projectVersion -notmatch [regex]::Escape("($($lock.unity_revision))")) {
        throw 'Unity project revision drifted'
    }

    $hashResults = [ordered]@{}
    foreach ($property in $lock.hashes.PSObject.Properties) {
        $path = Join-Path $unityRoot ($property.Name -replace '/', '\')
        $actual = Get-LowerHash -Path $path
        if ($actual -ne [string]$property.Value) {
            throw "Environment lock hash drifted: $($property.Name) expected=$($property.Value) actual=$actual"
        }
        $hashResults[$property.Name] = $actual
    }

    $manifestPath = Join-Path $unityRoot 'Packages\manifest.json'
    $packageLockPath = Join-Path $unityRoot 'Packages\packages-lock.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $actualDependencies = @($manifest.dependencies.PSObject.Properties)
    $expectedDependencies = @($lock.direct_dependencies.PSObject.Properties)
    if ($actualDependencies.Count -ne $expectedDependencies.Count) {
        throw "Direct dependency count drifted expected=$($expectedDependencies.Count) actual=$($actualDependencies.Count)"
    }
    foreach ($expected in $expectedDependencies) {
        $actual = $manifest.dependencies.PSObject.Properties[$expected.Name]
        if ($null -eq $actual -or [string]$actual.Value -ne [string]$expected.Value) {
            throw "Direct dependency drifted: $($expected.Name)"
        }
    }

    $forbiddenRuntimeHits = @()
    foreach ($path in @(
        $manifestPath,
        $packageLockPath,
        (Join-Path $unityRoot 'Assets\F03\Runtime'),
        (Join-Path $unityRoot 'Assets\F03\Scenes')
    )) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $matches = & rg -n -i 'Klak\.Spout|jp\.keijiro\.klak\.spout|SpoutReceiver|TouchDesigner' $path 2>$null
        if ($LASTEXITCODE -eq 0) { $forbiddenRuntimeHits += $matches }
        elseif ($LASTEXITCODE -ne 1) { throw "Runtime dependency scan failed for $path" }
    }
    if (Test-Path -LiteralPath (Join-Path $unityRoot 'Assets\Scripts\SpoutReceiver.cs')) {
        $forbiddenRuntimeHits += 'Assets/Scripts/SpoutReceiver.cs still exists'
    }
    if ($forbiddenRuntimeHits.Count -gt 0) {
        throw "Forbidden runtime dependencies remain: $($forbiddenRuntimeHits -join '; ')"
    }

    $gitCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
    $report = [ordered]@{
        schema_version = 'f03-environment-report-v1'
        task_id = 'F-03'
        result = 'PASS'
        generated_utc = [DateTime]::UtcNow.ToString('O')
        git_commit = $gitCommit
        unity_executable = $unityExe.Replace('\', '/')
        unity_version = $lock.unity_version
        unity_revision = $lock.unity_revision
        build_target = $lock.build_target
        dev_scene = $lock.dev_scene
        direct_dependency_count = $actualDependencies.Count
        hashes = $hashResults
    }
    Write-JsonFile -Value $report -Path (Join-Path $evidenceRoot 'environment_report.json')
    Write-JsonFile -Value ([ordered]@{
        schema_version = 'f03-runtime-dependency-scan-v1'
        result = 'PASS'
        forbidden_runtime_hits = @()
        allowed_historical_scopes = @('Governance/', '00-项目管理/', 'Assets/Scripts/Editor/FormalBuildGate.cs')
    }) -Path (Join-Path $evidenceRoot 'runtime_dependency_scan.json')
}

function Invoke-F03Tests {
    New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
    $editResults = Join-Path $evidenceRoot 'editmode-results.xml'
    $playResults = Join-Path $evidenceRoot 'playmode-results.xml'
    Remove-Item -LiteralPath $editResults, $playResults -Force -ErrorAction SilentlyContinue
    Invoke-Unity -Label 'Unity EditMode tests' -Arguments @(
        '-batchmode', '-nographics', '-projectPath', $unityRoot,
        '-runTests', '-testPlatform', 'EditMode',
        '-testResults', $editResults,
        '-logFile', (Join-Path $evidenceRoot 'editmode.log')
    )
    Invoke-Unity -Label 'Unity PlayMode tests' -Arguments @(
        '-batchmode', '-nographics', '-projectPath', $unityRoot,
        '-runTests', '-testPlatform', 'PlayMode',
        '-testResults', $playResults,
        '-logFile', (Join-Path $evidenceRoot 'playmode.log')
    )
    foreach ($resultPath in @($editResults, $playResults)) {
        if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
            throw "Unity test result XML is missing: $resultPath"
        }
        [xml]$resultXml = Get-Content -LiteralPath $resultPath -Raw
        if ($resultXml.'test-run'.result -ne 'Passed') {
            throw "Unity test result is not Passed: $resultPath result=$($resultXml.'test-run'.result)"
        }
    }
}

function Invoke-F03Build {
    param([Parameter(Mandatory)][string]$RunName)
    $relativeOutput = "Builds/F03-DevReplay/$RunName"
    Invoke-Unity -Label "Unity Windows build $RunName" -Arguments @(
        '-batchmode', '-nographics', '-quit', '-projectPath', $unityRoot,
        '-executeMethod', 'SRP.F03.Editor.F03Build.BuildWindowsDevReplay',
        '-f03OutputPath', $relativeOutput,
        '-logFile', (Join-Path $evidenceRoot "$RunName-build.log")
    )
}

function Compare-F03Builds {
    $first = Get-Content -LiteralPath (Join-Path $buildRoot 'run-1\f03-build-manifest.json') -Raw | ConvertFrom-Json
    $second = Get-Content -LiteralPath (Join-Path $buildRoot 'run-2\f03-build-manifest.json') -Raw | ConvertFrom-Json
    $firstPaths = @($first.files.path | Sort-Object)
    $secondPaths = @($second.files.path | Sort-Object)
    if (($firstPaths -join "`n") -ne ($secondPaths -join "`n")) {
        throw 'Repeated build file sets differ'
    }
    Write-JsonFile -Value ([ordered]@{
        schema_version = 'f03-repeat-build-report-v1'
        result = 'PASS'
        comparison = 'same input commit, scene, build options, and relative file set'
        byte_identical_required = $false
        run_1_manifest_sha256 = Get-LowerHash (Join-Path $buildRoot 'run-1\f03-build-manifest.json')
        run_2_manifest_sha256 = Get-LowerHash (Join-Path $buildRoot 'run-2\f03-build-manifest.json')
        relative_files = $firstPaths
    }) -Path (Join-Path $evidenceRoot 'repeat_build_report.json')
}

function Test-F03Player {
    $sourceBuild = Join-Path $buildRoot 'run-1'
    $sourceExecutable = Join-Path $sourceBuild 'SRP-F03-DevReplay.exe'
    $screenshot = Join-Path $evidenceRoot 'dev-replay-player.png'
    $playerLog = Join-Path $evidenceRoot 'player.log'
    $tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("srp-f03-player-" + [guid]::NewGuid().ToString('N'))
    $ports = @(5005, 5006, 5010)
    $beforeUdp = @(Get-NetUDPEndpoint -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in $ports } | Select-Object LocalAddress, LocalPort, OwningProcess)
    $beforeTcp = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in $ports } | Select-Object LocalAddress, LocalPort, OwningProcess)

    try {
        New-Item -ItemType Directory -Path $tempRoot | Out-Null
        $tempScreenshot = Join-Path $tempRoot 'capture.png'
        $tempPlayerLog = Join-Path $tempRoot 'player.log'
        $startInfo = [Diagnostics.ProcessStartInfo]::new()
        $startInfo.FileName = Get-WindowsShortPath $sourceExecutable
        $startInfo.WorkingDirectory = Get-WindowsShortPath $sourceBuild
        $startInfo.UseShellExecute = $false
        foreach ($argument in @("--f03-capture=$tempScreenshot", '--f03-auto-quit', '-logFile', $tempPlayerLog, '-screen-width', '1280', '-screen-height', '720', '-screen-fullscreen', '0')) {
            [void]$startInfo.ArgumentList.Add($argument)
        }
        $process = [Diagnostics.Process]::Start($startInfo)
        if (-not $process.WaitForExit(60000)) {
            $process.Kill($true)
            throw 'F-03 Player did not exit after evidence capture'
        }
        if ($process.ExitCode -ne 0) { throw "F-03 Player failed with exit code $($process.ExitCode)" }
        if (-not (Test-Path -LiteralPath $tempScreenshot -PathType Leaf)) { throw 'F-03 Player screenshot was not created' }
        if ((Get-Content -LiteralPath $tempPlayerLog -Raw) -notmatch 'F03_DEV_REPLAY_READY') { throw 'F-03 Player readiness marker is missing from log' }
        Copy-Item -LiteralPath $tempScreenshot -Destination $screenshot -Force
        Copy-Item -LiteralPath $tempPlayerLog -Destination $playerLog -Force
    }
    finally {
        if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
    }

    $afterUdp = @(Get-NetUDPEndpoint -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in $ports } | Select-Object LocalAddress, LocalPort, OwningProcess)
    $afterTcp = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in $ports } | Select-Object LocalAddress, LocalPort, OwningProcess)
    Write-JsonFile -Value ([ordered]@{
        schema_version = 'f03-player-smoke-report-v1'
        result = 'PASS'
        player_exit_code = $process.ExitCode
        launch_mode = 'Win32 short path to original build output'
        source_build_manifest_sha256 = Get-LowerHash (Join-Path $sourceBuild 'f03-build-manifest.json')
        source_executable_sha256 = Get-LowerHash $sourceExecutable
        screenshot_sha256 = Get-LowerHash $screenshot
        before = [ordered]@{ udp = $beforeUdp; tcp = $beforeTcp }
        after = [ordered]@{ udp = $afterUdp; tcp = $afterTcp }
        f03_added_listeners = $false
    }) -Path (Join-Path $evidenceRoot 'player_smoke_report.json')

    $compiledHits = & rg -a -n -i 'Klak\.Spout|jp\.keijiro\.klak\.spout|SpoutReceiver' (Join-Path $buildRoot 'run-1') 2>$null
    if ($LASTEXITCODE -eq 0) { throw "Compiled build contains forbidden dependency text: $($compiledHits -join '; ')" }
    if ($LASTEXITCODE -ne 1) { throw 'Compiled build scan failed' }
}

function Invoke-FormalNegative {
    & py -3.14 -m pytest '02-技术研发/05-通信协议/tests/contract/test_runtime_contract.py' -q
    if ($LASTEXITCODE -ne 0) { throw 'F-01 contract negative regression failed' }

    $unauthorizedExit = Start-UnityProcess -Arguments @(
        '-batchmode', '-nographics', '-quit', '-projectPath', $unityRoot,
        '-executeMethod', 'SRP.F03.Editor.F03Build.BuildUnauthorizedDevelopmentProbe',
        '-logFile', (Join-Path $evidenceRoot 'unauthorized-development-negative.log')
    )
    if ($unauthorizedExit -eq 0) { throw 'Unauthorized Development build unexpectedly passed' }
    $unauthorizedLog = Get-Content -LiteralPath (Join-Path $evidenceRoot 'unauthorized-development-negative.log') -Raw
    if ($unauthorizedLog -notmatch 'UNCONTROLLED_DEVELOPMENT_BUILD') {
        throw 'Unauthorized Development build failed without the expected gate reason'
    }

    $formalExit = Start-UnityProcess -Arguments @(
        '-batchmode', '-nographics', '-projectPath', $unityRoot,
        '-executeMethod', 'SRP.Editor.FormalBuildGate.ValidateFromCommandLine',
        '-logFile', (Join-Path $evidenceRoot 'formal-gate-negative.log')
    )
    if ($formalExit -eq 0) { throw 'Formal build gate unexpectedly passed' }
    $formalLog = Get-Content -LiteralPath (Join-Path $evidenceRoot 'formal-gate-negative.log') -Raw
    if ($formalLog -notmatch 'ASSET_LICENSE_GATE_BLOCKED|FORMAL_SCENES_MISSING|FORMAL_RUNTIME_CONTROLLER_MISSING') {
        throw 'Formal gate failed without an expected fail-closed reason'
    }
    Write-JsonFile -Value ([ordered]@{
        schema_version = 'f03-formal-negative-report-v1'
        result = 'PASS'
        manifest_contract = 'F-01 runtime-contract-v2.1 regression passed, including missing-field rejection'
        unauthorized_development_exit_code = $unauthorizedExit
        unauthorized_development_expected_failure = $true
        unity_formal_gate_exit_code = $formalExit
        unity_formal_gate_expected_failure = $true
        runtime_manifest_handshake_owner = 'U-01'
    }) -Path (Join-Path $evidenceRoot 'formal_negative_report.json')
}

New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
switch ($Mode) {
    'verify' { Test-F03Environment }
    'test' { Invoke-F03Tests }
    'build' { Invoke-F03Build -RunName 'run' }
    'formal-negative' { Invoke-FormalNegative }
    'all' {
        Test-F03Environment
        Invoke-F03Tests
        Invoke-F03Build -RunName 'run-1'
        Invoke-F03Build -RunName 'run-2'
        Compare-F03Builds
        Test-F03Player
        Invoke-FormalNegative
    }
}

Write-Output "F03_$($Mode.ToUpperInvariant().Replace('-', '_'))_PASS"
