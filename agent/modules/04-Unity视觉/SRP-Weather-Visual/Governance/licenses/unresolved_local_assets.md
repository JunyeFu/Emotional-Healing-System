# Unresolved local asset provenance

Evidence review date: 2026-08-12.

## Local sprite group

Git history shows that the current PNG set entered the repository in commit `cbb811d`, but the repository contains no author declaration, source receipt, generation record, or redistribution permission. This group is therefore `REPLACE`, not `PROJECT_ORIGINAL`.

- Responsible role: Unity visual lead.
- Deadline: 2026-08-19.
- Exclusion plan: remove every unresolved PNG from candidate scenes, Resources, Addressables, and build settings, or replace it with an asset whose authorship and allowed use are recorded before the Z-01 candidate build.

## Roslyn binary group

Git history shows that the five DLLs entered the repository in commit `e37f577`, and file metadata identifies Roslyn 4.12.0 plus .NET support assemblies. The exact acquisition artifact and accompanying third-party notice were not retained. General upstream MIT terms do not establish the provenance of these exact binary files.

- Responsible role: Unity technical lead.
- Deadline: 2026-08-19.
- Exclusion plan: remove `Assets/Plugins/Roslyn` from the candidate build or reacquire pinned binaries from an approved package with its license and third-party notices archived.

## Existing project file group

The tracked scenes, animations, scripts, Unity settings, input actions, and derived JSON files predate G-02. Repository history alone does not establish authorship or reuse permission.

- Responsible role: Unity technical lead.
- Deadline: 2026-08-19.
- Exclusion plan: confirm project authorship or replace/exclude every affected file before a candidate build.

All three groups remain release blockers even though the replacement plans are complete.
