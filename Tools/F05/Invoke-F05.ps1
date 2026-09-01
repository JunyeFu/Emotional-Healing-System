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
    $sealFiles = @('evidence_hashes.sha256', 'evidence_manifest.json')
    $leafFiles = @('contract-tests.log', 'p01-tests.log', 'p02-tests.log', 'f05-contract-verifier.log', 'f05-verification.json', 'git-diff-check.log')
    $clearFiles = if ($Action -eq 'all') { $leafFiles + $sealFiles } else { $sealFiles }
    foreach ($name in $clearFiles) {
        Remove-Item -LiteralPath (Join-Path $EvidenceDir $name) -Force -ErrorAction SilentlyContinue
    }
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
    if ($Action -eq 'all') {
        & py -3.14 'Tools/F05/f05_evidence.py' seal --evidence-dir $EvidenceDir --tested-git-commit (git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0) { throw 'F05_EVIDENCE_SEAL_FAILED' }
        & py -3.14 'Tools/F05/f05_evidence.py' verify --evidence-dir $EvidenceDir
        if ($LASTEXITCODE -ne 0) { throw 'F05_EVIDENCE_VERIFY_FAILED' }
    }
}
finally {
    Pop-Location
}
