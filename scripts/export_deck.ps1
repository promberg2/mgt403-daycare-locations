param([string]$pptx, [string]$pdf, [string]$pngdir)
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open($pptx, $true, $false, $false)
if ($pdf) { $pres.SaveAs($pdf, 32) }
if ($pngdir) { New-Item -ItemType Directory -Force $pngdir | Out-Null; $i = 1; foreach ($s in $pres.Slides) { $s.Export("$pngdir\slide_$i.png", "PNG", 1600, 900); $i++ } }
$pres.Close(); $app.Quit()
