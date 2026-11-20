$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$Pythonw = Join-Path $Venv "Scripts\pythonw.exe"
$ModelName = "vosk-model-small-en-us-0.15"
$ModelDir = Join-Path $Root "models\$ModelName"
$ZipPath = Join-Path $env:TEMP "$ModelName.zip"

Write-Host "Setting up Browser Assist Windows background listener..."
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python 3.11 is required. Install it from https://www.python.org/downloads/release/python-3119/ and enable the Python launcher."
}
py -3.11 --version
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 was not found. Install Python 3.11 and retry." }
if (-not (Test-Path $Venv)) { py -3.11 -m venv $Venv }
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")

if (-not (Test-Path $ModelDir)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ModelDir) | Out-Null
    Write-Host "Downloading the small English speech model (about 40-50 MB)..."
    Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/$ModelName.zip" -OutFile $ZipPath
    Expand-Archive -Path $ZipPath -DestinationPath (Split-Path -Parent $ModelDir) -Force
    Remove-Item $ZipPath -Force
}

$Startup = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $Startup "Browser Assist.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Pythonw
$Shortcut.Arguments = '"' + $Root + '\assistant.py' + '"'
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "Browser Assist continuous voice listener"
$Shortcut.Save()

Write-Host "Setup complete. Browser Assist will start automatically when you sign in."
Write-Host "Restart Windows or run .venv\Scripts\python.exe assistant.py to start it now."
Write-Host "Log file: $env:LOCALAPPDATA\BrowserAssist\assistant.log"
