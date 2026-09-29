$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$python = 'D:\MathModelingTools\envs\cumcm\python.exe'
$agentRoot = if ($env:AGENT_ROOT) { $env:AGENT_ROOT } else { 'D:\Agent' }
$builder = Join-Path $agentRoot 'math-modeling\math-modeling\runtime\build_paper.py'
$output = Join-Path $projectRoot 'human\deliverables\pdf'

if (-not (Test-Path -LiteralPath $python)) {
    throw "Canonical math-modeling Python not found: $python"
}
if (-not (Test-Path -LiteralPath $builder)) {
    throw "Math-modeling PDF builder not found: $builder"
}

$sources = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter '02_*.md' -File)
if ($sources.Count -ne 1) {
    throw 'Expected exactly one current task-summary source'
}

foreach ($source in $sources) {
    & $python $builder $source.FullName --output-dir $output
    if ($LASTEXITCODE -ne 0) {
        throw "PDF build failed: $($source.FullName)"
    }
}

& $python (Join-Path $PSScriptRoot 'verify_briefs.py')
if ($LASTEXITCODE -ne 0) {
    throw 'PDF verification failed'
}

Write-Host "WROTE: $output"
