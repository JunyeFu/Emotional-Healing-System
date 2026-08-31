[CmdletBinding()]
param(
    [ValidateSet('test', 'verify', 'all')]
    [string]$Action = 'all',
    [string]$EvidenceDir
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (-not $EvidenceDir) {
    $EvidenceDir = Join-Path $repoRoot '03-测试与实验\evidence\F-05'
}

function Invoke-F05Command {
    param(
        [string]$Name,
        [string[]]$Arguments
    )
    $logPath = Join-Path $EvidenceDir "$Name.log"
    & py -3.14 @Arguments 2>&1 | Tee-Object -FilePath $logPath
    if ($LASTEXITCODE -ne 0) {
        throw "F05_COMMAND_FAILED:$Name"
    }
}

Push-Location $repoRoot
try {
    New-Item -ItemType Directory -Path $EvidenceDir -Force | Out-Null
    if ($Action -in @('test', 'all')) {
        Invoke-F05Command -Name 'contract-tests' -Arguments @('-m', 'pytest', '02-技术研发/05-通信协议/tests/contract', '-q')
        Invoke-F05Command -Name 'p01-tests' -Arguments @('-m', 'pytest', '02-技术研发/tests/session_core', '-q')
        Invoke-F05Command -Name 'p02-tests' -Arguments @('-m', 'pytest', '02-技术研发/tests/session_store', '-q')
    }
    if ($Action -in @('verify', 'all')) {
        Invoke-F05Command -Name 'f05-contract-verifier' -Arguments @('02-技术研发/05-通信协议/contracts/verify_f05_v22.py', '--report', (Join-Path $EvidenceDir 'f05-verification.json'))
        $diffOutput = git diff --check 2>&1
        $diffText = [string]::Join([Environment]::NewLine, @($diffOutput))
        Set-Content -LiteralPath (Join-Path $EvidenceDir 'git-diff-check.log') -Value $diffText -Encoding utf8
        if ($LASTEXITCODE -ne 0) {
            throw 'F05_GIT_DIFF_CHECK_FAILED'
        }
    }
    $files = Get-ChildItem -LiteralPath $EvidenceDir -File | Sort-Object Name
    $hashes = foreach ($file in $files) {
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $($file.Name)"
    }
    $hashes | Set-Content -LiteralPath (Join-Path $EvidenceDir 'evidence_hashes.sha256') -Encoding ascii
    $branchName = (git branch --show-current)
    if ([string]::IsNullOrWhiteSpace($branchName)) {
        $branchName = 'DETACHED'
    }
    else {
        $branchName = $branchName.Trim()
    }
    $manifest = [ordered]@{
        report_version = 'f05-evidence-manifest-v1'
        git_head = (git rev-parse HEAD).Trim()
        branch = $branchName
        files = @(
            Get-ChildItem -LiteralPath $EvidenceDir -File | Sort-Object Name | ForEach-Object {
                [ordered]@{
                    name = $_.Name
                    sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                    size_bytes = $_.Length
                }
            }
        )
    }
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $EvidenceDir 'evidence_manifest.json') -Encoding utf8
}
finally {
    Pop-Location
}
