param(
    [string]$TdBin = 'D:\TouchDesigner\bin',
    [string]$Scratch = 'D:\Agent\03-SRP\tmp\td-cleanup-candidate'
)
$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'T01_TelemetryPanel.toe'
$scratchPath = [IO.Path]::GetFullPath($Scratch)
if (Test-Path -LiteralPath $scratchPath) { throw 'Scratch must be a new directory' }
New-Item -ItemType Directory -Path $scratchPath | Out-Null
$candidate = Join-Path $scratchPath 'clean.toe'
Copy-Item -LiteralPath $source -Destination $candidate
& (Join-Path $TdBin 'toeexpand.exe') $candidate | Out-Host
$expanded = "$candidate.dir"
$toc = "$candidate.toc"
if (-not (Test-Path -LiteralPath $toc)) { throw 'Expansion did not produce a TOC' }
$entries = [IO.File]::ReadAllLines($toc)
$coreEntries = @($entries | Where-Object { $_ -match '^project1/T01_TelemetryPanel(?:[./])' })
$before = @{}
foreach ($entry in $coreEntries) { $before[$entry] = (Get-FileHash -LiteralPath (Join-Path $expanded $entry)).Hash }
$demo = 'geo1|noise1|chopto1|displace1|moviefilein1|out1'
$removed = @($entries | Where-Object { $_ -match "^project1/($demo)(?:[./])" })
if ($removed.Count -eq 0) { throw 'No default demo entries found; refusing a redundant rewrite' }
$rootPrefix = [IO.Path]::GetFullPath($expanded) + [IO.Path]::DirectorySeparatorChar
foreach ($entry in $removed) {
    $target = [IO.Path]::GetFullPath((Join-Path $expanded $entry))
    if (-not $target.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Out-of-scope path' }
    Remove-Item -LiteralPath $target
}
$utf8 = [Text.UTF8Encoding]::new($false)
# toecollapse treats CR in a CRLF TOC as part of the filename.
[IO.File]::WriteAllText($toc, ((@($entries | Where-Object { $_ -notin $removed }) -join "`n") + "`n"), $utf8)
$parm = Join-Path $expanded 'project1.parm'
$lines = [IO.File]::ReadAllLines($parm)
if (@($lines | Where-Object { $_ -eq 'top 0 ./out1' }).Count -ne 1) { throw 'Unexpected project display binding' }
[IO.File]::WriteAllText($parm, ((@($lines | ForEach-Object {
    if ($_ -eq 'top 0 ./out1') { 'top 0 ./T01_TelemetryPanel/Output/display_out' } else { $_ }
}) -join "`n") + "`n"), $utf8)
& (Join-Path $TdBin 'toecollapse.exe') $candidate | Out-Host
$verification = Join-Path $scratchPath 'verified.toe'
Copy-Item -LiteralPath $candidate -Destination $verification
& (Join-Path $TdBin 'toeexpand.exe') $verification | Out-Host
$afterEntries = [IO.File]::ReadAllLines("$verification.toc")
if (@($afterEntries | Where-Object { $_ -match "^project1/($demo)(?:[./])" }).Count) { throw 'Demo entries survived' }
foreach ($entry in $coreEntries) {
    if ((Get-FileHash -LiteralPath (Join-Path "$verification.dir" $entry)).Hash -ne $before[$entry]) {
        throw "T01 content changed: $entry"
    }
}
if (-not ([IO.File]::ReadAllLines((Join-Path "$verification.dir" 'project1.parm')) -contains 'top 0 ./T01_TelemetryPanel/Output/display_out')) {
    throw 'Display binding verification failed'
}
$report = [ordered]@{
    scope = 'OFFLINE_TOE_CLEANUP_NOT_RUNTIME_ACCEPTANCE'
    source_sha256 = (Get-FileHash -LiteralPath $source).Hash
    candidate_sha256 = (Get-FileHash -LiteralPath $candidate).Hash
    removed_nodes = @('/project1/geo1', '/project1/noise1', '/project1/chopto1', '/project1/displace1', '/project1/moviefilein1', '/project1/out1')
    removed_entries = $removed
    preserved_core_files = $coreEntries.Count
    core_byte_identity = 'PASS'
    display_binding = './T01_TelemetryPanel/Output/display_out'
    candidate = $candidate
}
[IO.File]::WriteAllText((Join-Path $scratchPath 'cleanup-report.json'), ($report | ConvertTo-Json -Depth 5), $utf8)
$report | ConvertTo-Json -Depth 5
