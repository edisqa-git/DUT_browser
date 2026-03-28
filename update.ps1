$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TempVenv = Join-Path $RootDir ".venv.update.tmp"
$NpmCache = Join-Path $RootDir ".npm-update-cache"
$Branch = git -C $RootDir rev-parse --abbrev-ref HEAD

if (git -C $RootDir status --porcelain) {
  Write-Host "Update aborted: working tree has local changes. Commit or stash them first."
  exit 1
}

Write-Host "Fetching latest code for branch $Branch..."
git -C $RootDir fetch --tags origin
git -C $RootDir pull --ff-only origin $Branch

Write-Host "Rebuilding Python environment in a temporary virtualenv..."
if (Test-Path $TempVenv) {
  Remove-Item -Recurse -Force $TempVenv
}
python -m venv $TempVenv
& "$TempVenv\Scripts\python.exe" -m pip install --upgrade pip wheel
& "$TempVenv\Scripts\python.exe" -m pip install -r (Join-Path $RootDir "requirements.txt")

Write-Host "Reinstalling Node dependencies..."
New-Item -ItemType Directory -Force -Path $NpmCache | Out-Null
npm install --prefix $RootDir --cache $NpmCache --no-audit --no-fund
npm install --prefix (Join-Path $RootDir "dut-dashboard/frontend") --cache $NpmCache --no-audit --no-fund

$CurrentVenv = Join-Path $RootDir ".venv"
$BackupVenv = Join-Path $RootDir ".venv.previous"

if (Test-Path $BackupVenv) {
  Remove-Item -Recurse -Force $BackupVenv
}
if (Test-Path $CurrentVenv) {
  Move-Item $CurrentVenv $BackupVenv
}
Move-Item $TempVenv $CurrentVenv
if (Test-Path $BackupVenv) {
  Remove-Item -Recurse -Force $BackupVenv
}

$Version = Get-Content (Join-Path $RootDir "VERSION") -Raw
Write-Host "Update complete. Current version: $($Version.Trim())"
