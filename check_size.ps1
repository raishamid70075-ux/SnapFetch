$base = "d:\downloader"
$total = (Get-ChildItem $base -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
Write-Host "=== Total Project Size: $([math]::Round($total/1MB, 2)) MB ==="
Write-Host ""
Write-Host "--- Top-Level Folders ---"
Get-ChildItem $base -Directory | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-Host ("{0,-30} {1,10} MB" -f $_.Name, [math]::Round($s/1MB, 2))
}
Write-Host ""
Write-Host "--- Largest Files (Top 30) ---"
Get-ChildItem $base -Recurse -File -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 30 | ForEach-Object {
    $rel = $_.FullName.Replace("$base\", "")
    Write-Host ("{0,-70} {1,10} MB" -f $rel, [math]::Round($_.Length/1MB, 2))
}
Write-Host ""
Write-Host "--- File Type Summary ---"
Get-ChildItem $base -Recurse -File -ErrorAction SilentlyContinue | Group-Object Extension | ForEach-Object {
    $s = ($_.Group | Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{Extension=$_.Name; Count=$_.Count; SizeMB=[math]::Round($s/1MB,2)}
} | Sort-Object SizeMB -Descending | Select-Object -First 20 | Format-Table -AutoSize
