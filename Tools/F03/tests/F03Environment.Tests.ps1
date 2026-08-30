$modulePath = Join-Path $PSScriptRoot '..\F03Environment.psm1'
Import-Module $modulePath -Force

Describe 'F-03 environment evidence helpers' {
    It 'uses the package canonical hash policy across LF and CRLF checkouts' {
        $lfPath = Join-Path $TestDrive 'lf.txt'
        $crlfPath = Join-Path $TestDrive 'crlf.txt'
        [IO.File]::WriteAllBytes($lfPath, [Text.Encoding]::UTF8.GetBytes("alpha  `nbeta`t`n"))
        [IO.File]::WriteAllBytes($crlfPath, [Text.Encoding]::UTF8.GetBytes("alpha  `r`nbeta`t`r`n"))

        Get-F03CanonicalTextHash $lfPath | Should Be (Get-F03CanonicalTextHash $crlfPath)
    }

    It 'changes the canonical hash when file content changes' {
        $firstPath = Join-Path $TestDrive 'first.txt'
        $secondPath = Join-Path $TestDrive 'second.txt'
        [IO.File]::WriteAllBytes($firstPath, [Text.Encoding]::UTF8.GetBytes("alpha`n"))
        [IO.File]::WriteAllBytes($secondPath, [Text.Encoding]::UTF8.GetBytes("beta`n"))

        Get-F03CanonicalTextHash $firstPath | Should Not Be (Get-F03CanonicalTextHash $secondPath)
    }

    It 'rejects a non-empty pre-run Git status' {
        $failure = $null
        try { Assert-F03CleanStatus -Status @(' M tracked.txt') }
        catch { $failure = $_ }
        $failure.Exception.Message | Should Match 'F03_PRE_RUN_WORKTREE_NOT_CLEAN'

        Assert-F03CleanStatus -Status @()
    }

    It 'binds the environment lock to canonical project file hashes' {
        $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
        $unityRoot = Join-Path $repoRoot '02-技术研发\04-Unity视觉\SRP-Weather-Visual'
        $lock = Get-Content (Join-Path $PSScriptRoot '..\f03-environment-lock.json') -Raw | ConvertFrom-Json

        $lock.hash_policy | Should Be 'sha256_lf_no_trailing_ws_text_v1'
        foreach ($property in $lock.hashes.PSObject.Properties) {
            Get-F03CanonicalTextHash (Join-Path $unityRoot ($property.Name -replace '/', '\')) |
                Should Be ([string]$property.Value)
        }
    }

    It 'creates a stable hash for the committed implementation tree' {
        $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
        $paths = @('Tools/F03', '02-技术研发/04-Unity视觉/SRP-Weather-Visual')
        $first = Get-F03ImplementationTreeHash -RepoRoot $repoRoot -RelativePaths $paths
        $second = Get-F03ImplementationTreeHash -RepoRoot $repoRoot -RelativePaths $paths

        $first | Should Match '^[0-9a-f]{64}$'
        $first | Should Be $second
    }

    It 'checks out Unity serialized text with LF line endings' {
        $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
        $samples = @(
            '02-技术研发/04-Unity视觉/SRP-Weather-Visual/Assets/F03/Scenes/F03DevReplay.unity',
            '02-技术研发/04-Unity视觉/SRP-Weather-Visual/Assets/DefaultVolumeProfile.asset',
            '02-技术研发/04-Unity视觉/SRP-Weather-Visual/Assets/F03/Runtime/DevReplayBanner.cs.meta',
            '02-技术研发/04-Unity视觉/SRP-Weather-Visual/ProjectSettings/Packages/com.unity.probuilder/Settings.json'
        )
        $attributes = @(& git -C $repoRoot check-attr eol -- $samples)

        $LASTEXITCODE | Should Be 0
        @($attributes | Where-Object { $_ -notmatch 'eol: lf$' }).Count | Should Be 0
    }
}
