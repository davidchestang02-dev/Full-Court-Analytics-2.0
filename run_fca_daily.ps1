param(
  [string]$Sport = "ncaab",
  [string]$Date = (Get-Date).ToString("yyyy-MM-dd")
)

$Repo = "C:\Users\d_che\OneDrive\Documents\GitHub\Full-Court-Analytics-2.0"
Set-Location $Repo
$env:PYTHONPATH = $Repo

$LogDir = Join-Path $Repo "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ("daily_{0}_{1}.log" -f $Sport, $Date)

function Write-Log($msg) {
  $line = "[{0}] {1}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"), $msg
  $line | Tee-Object -FilePath $LogFile -Append
}

function Run-Step($name, $cmd) {
  Write-Log "START $name"
  & $cmd 2>&1 | Tee-Object -FilePath $LogFile -Append
  if ($LASTEXITCODE -ne 0) {
    Write-Log "FAIL  $name (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
  }
  Write-Log "DONE  $name"
}

Write-Log "=== FCA Daily Run (sport=$Sport date=$Date) ==="
Run-Step "teamrankings_cache" { python scraper/teamrankings_cache.py --sport $Sport --date $Date --data-dir data }
Run-Step "scoresandodds_board" { python scraper/scoresandodds_board.py --sport $Sport --date $Date --data-dir data }
Run-Step "model_pipeline" { python pipelines/model_pipeline.py --sport $Sport --date $Date --data-dir data }
Write-Log "=== FCA Daily Run Complete ==="
