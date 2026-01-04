# run.ps1  (haberyazilimi klasöründe olmalı)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$crawlerPath = Join-Path $root "crawler"

if (!(Test-Path $crawlerPath)) {
    Write-Host "❌ crawler klasörü bulunamadı: $crawlerPath" -ForegroundColor Red
    Write-Host "run.ps1 dosyası haberyazilimi klasöründe olmalı." -ForegroundColor Yellow
    exit 1
}

Set-Location $crawlerPath
$env:PYTHONPATH=".."

python -m pdm run python ..\app\scripts\fetch_top3.py $args[0] $args[1]
