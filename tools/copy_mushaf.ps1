# ينسخ ملفات المصحف الأصلية إلى مجلد assets\mushap (بدل الرابط الرمزي)
$ErrorActionPreference = 'Stop'
$src = 'D:\My Projects\Religion\Dad''s Quraan'
$dst = Join-Path $PSScriptRoot '..\assets\mushaf'

if (Test-Path $dst) {
    $item = Get-Item $dst -Force
    if ($item.LinkType -eq 'Junction') {
        Remove-Item $dst -Force
        Write-Host "أُزيل الرابط الرمزي." -ForegroundColor Yellow
    }
}
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$i = 1
Get-ChildItem $src -Filter *.pdf | Sort-Object Name | ForEach-Object {
    $name = 'm {0:D2} Qraan nos .pdf' -f $i
    Copy-Item $_.FullName (Join-Path $dst $name) -Force
    Write-Host "نسخت $name"
    $i++
}
Write-Host "تم نسخ $($i-1) ملفًا إلى $dst" -ForegroundColor Green