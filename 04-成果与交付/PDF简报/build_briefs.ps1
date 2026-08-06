$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = 'D:\MathModelingTools\envs\cumcm\python.exe'
$builder = 'D:\Agent\01-math-modeling\math-modeling\runtime\build_paper.py'
$output = Join-Path $projectRoot 'output\pdf'

if (-not (Test-Path -LiteralPath $python)) {
    throw "Canonical math-modeling Python not found: $python"
}
if (-not (Test-Path -LiteralPath $builder)) {
    throw "Math-modeling PDF builder not found: $builder"
}

& $python (Join-Path $PSScriptRoot 'generate_brief_figures.py')

$sources = Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.md' -File |
    Where-Object { $_.Name -ne 'README.md' } |
    Sort-Object Name

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
