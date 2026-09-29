$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$unity = 'D:\UnityEngine\6000.4.9f1\Editor\Unity.exe'
$project = Join-Path $root 'agent/modules/04-Unity视觉/SRP-Weather-Visual'
$evidence = Join-Path $root 'agent/tasks/U-02/evidence/runtime/demo'
$player = Join-Path $root '.artifacts-local/task-normalization/U-02/demo-player'
$frames = Join-Path $evidence 'frames'
$ffmpeg = Join-Path $root '.tools/ffmpeg/9.0.1/ffmpeg-9.0.1-essentials_build/bin/ffmpeg.exe'
$ffprobe = Join-Path $root '.tools/ffmpeg/9.0.1/ffmpeg-9.0.1-essentials_build/bin/ffprobe.exe'
New-Item -ItemType Directory -Path $evidence,$player,$frames -Force | Out-Null
$expectedFrames = [IO.Path]::GetFullPath((Join-Path $root 'agent/tasks/U-02/evidence/runtime/demo/frames'))
if ((Resolve-Path -LiteralPath $frames).Path -ne $expectedFrames) { throw 'U02_DEMO_OUTPUT_PATH' }
Get-ChildItem -LiteralPath $frames -Filter 'frame_*.png' -File | ForEach-Object { Remove-Item -LiteralPath $_.FullName }

function Invoke-Editor([string]$method, [string]$logName, [string[]]$extra) {
    $arguments = @('-batchmode','-nographics','-quit','-projectPath',$project,
                   '-executeMethod',$method,'-logFile',(Join-Path $evidence $logName)) + $extra
    $process = Start-Process -FilePath $unity -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "$method failed: $($process.ExitCode)" }
}
Invoke-Editor 'SRP.V03.DevTools.V03DemoBuild.CreateScene' 'scene.log' @()
Invoke-Editor 'SRP.V03.DevTools.V03DemoBuild.BuildPlayer' 'build.log' @("--v03-out=$player")
$arguments = @("--v03-capture=$frames",'--v03-auto-quit','-force-d3d11','-screen-width','960','-screen-height','600',
               '-screen-fullscreen','0','-logFile',(Join-Path $evidence 'player.log'))
$process = Start-Process -FilePath (Join-Path $player 'V03DegradationDemo.exe') -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "demo failed: $($process.ExitCode)" }
if ((Get-ChildItem -LiteralPath $frames -Filter 'frame_*.png').Count -ne 120) { throw 'U02_DEMO_FRAME_COUNT' }
& 'C:\Users\fujunye\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' (Join-Path $PSScriptRoot 'verify_demo.py')
if ($LASTEXITCODE -ne 0) { throw 'U02_DEMO_PIXEL_CHECK_FAILED' }
& $ffmpeg -hide_banner -loglevel error -y -framerate 12 -i (Join-Path $frames 'frame_%04d.png') -c:v libx264 -pix_fmt yuv420p -r 12 (Join-Path $evidence 'degradation-demo.mp4')
if ($LASTEXITCODE -ne 0) { throw 'U02_DEMO_ENCODING_FAILED' }
$probe = & $ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=width,height,r_frame_rate,nb_read_frames -of json (Join-Path $evidence 'degradation-demo.mp4')
if ($LASTEXITCODE -ne 0) { throw 'U02_DEMO_DECODE_FAILED' }
$parsed = $probe | ConvertFrom-Json
if ($parsed.streams[0].nb_read_frames -ne '120' -or $parsed.streams[0].width -ne 960 -or $parsed.streams[0].height -ne 600) { throw 'U02_DEMO_VIDEO_MISMATCH' }
$probe | Set-Content -LiteralPath (Join-Path $evidence 'video-probe.json') -Encoding utf8
Write-Output 'PASS U02 development demo: 120 frames, 960x600, 12 fps'
