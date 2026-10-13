# Third-party package license evidence

Evidence review date: 2026-08-12.

## G-02 project source

`Assets/Scripts/Editor/FormalBuildGate.cs` is introduced by the G-02 implementation branch and is recorded as `PROJECT_ORIGINAL`. Its review and publication trail is the Git history for `codex/g-02-data-governance`.

## Unity packages

- Source: `Packages/manifest.json` and `Packages/packages-lock.json`.
- Publisher: Unity Technologies.
- License evidence: https://unity.com/legal/licenses/unity-companion-license
- Use boundary: only with a valid and eligible Unity engine license. Any package-level third-party notice remains authoritative.

## CoplayDev Unity MCP

- Locked commit: `78ee5418415953b79c358bfe6355fcc3fde7912b`.
- Source: https://github.com/CoplayDev/unity-mcp
- License at locked commit: https://raw.githubusercontent.com/CoplayDev/unity-mcp/78ee5418415953b79c358bfe6355fcc3fde7912b/LICENSE
- License: MIT; retain the copyright and permission notice in substantial distributions.

## KlakSpout

- Locked commit: `849e7bca3c167839ed697796153e1749acf0c53f`.
- Source: https://github.com/keijiro/KlakSpout
- License at locked commit: https://raw.githubusercontent.com/keijiro/KlakSpout/849e7bca3c167839ed697796153e1749acf0c53f/LICENSE
- License: Unlicense at the locked commit.

The current target architecture does not require Spout at runtime. Its license is recorded because it remains a direct dependency until a later Unity package cleanup task removes it.
