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
    throw "Python 3.10+ is required. Install it from https://www.python.org/downloads/windows/ and enable the Python launcher."
}
if (-not (Test-Path $Venv)) { py -3 -m venv $Venv }
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
Write-Host "To start it now, run the pythonw.exe command shown in the setup instructions."
Write-Host "Log file: $env:LOCALAPPDATA\BrowserAssist\assistant.log"
