Set-Location 'C:\Users\bisha\.gemini\antigravity\scratch\Mark-LVI'
$proc = Start-Process -FilePath 'C:\Users\bisha\AppData\Local\Programs\Python\Python312\pythonw.exe' -ArgumentList 'main.py' -WorkingDirectory 'C:\Users\bisha\.gemini\antigravity\scratch\Mark-LVI' -PassThru
Start-Sleep -Seconds 3
Get-Process -Id $proc.Id | Select-Object Id, ProcessName, Responding
