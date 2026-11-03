# Export the poster to PDF (and a PNG preview) with Microsoft PowerPoint COM automation (Abin Shaji Thomas).
# Usage (repo root):  powershell -ExecutionPolicy Bypass -File poster\export_pdf.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pptx = Join-Path $here "Accident_Poster_A3.pptx"
$pdf = Join-Path $here "Accident_Poster_A3.pdf"
$png = Join-Path $env:TEMP "Accident_Poster_A3_preview.png"
$app = New-Object -ComObject PowerPoint.Application
try {
    $pres = $app.Presentations.Open($pptx, $true, $false, $false)   # read-only, no window
    $pres.SaveAs($pdf, 32)                                          # 32 = ppSaveAsPDF
    $pres.Slides(1).Export($png, "PNG", 1400, 1980)
    "{0} x {1} pt" -f $pres.PageSetup.SlideWidth, $pres.PageSetup.SlideHeight
    $pres.Close()
} finally { $app.Quit() }
"PDF: $pdf"
"Preview: $png"
