$processes = Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe'"
$matches = $processes | Where-Object { $_.CommandLine -like "*assistant.py*" -and $_.CommandLine -like "*browser-assist*" }
foreach ($process in $matches) {
    Stop-Process -Id $process.ProcessId -Force
}
$startup = [Environment]::GetFolderPath("Startup")
$shortcut = Join-Path $startup "Browser Assist.lnk"
if (Test-Path $shortcut) { Remove-Item $shortcut -Force }
Write-Host "Browser Assist stopped and removed from Windows startup."
