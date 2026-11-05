# Run every QA tool on one .blend:  .\tools\qa\qa.ps1 output\ref\survivor\x.blend -Budget 3000 -Height 1.78
#   -Measure output\ref\survivor   reference measured by tools/blender/ref_measure.py (skips E2 when empty)
#   -Compare old.blend             previous version, drawn under the new one in the sheet
#   -Ref picture.webp              reference picture, top row of the sheet
# Results: output\qa\<name>_eval.json, _iou.json/.png, _sheet.png, .glb
param(
    [Parameter(Mandatory = $true)][string]$Blend,
    [int]$Budget = 0,
    [double]$Height = 0,
    [string]$Measure = "",
    [string]$Compare = "",
    [string]$Ref = "",
    [switch]$Asym
)
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$qa = Join-Path $PSScriptRoot ""
$ev = @("--export")
if ($Budget) { $ev += @("--budget", $Budget) }
if ($Height) { $ev += @("--height", $Height) }
if ($Asym) { $ev += "--asym" }
& $blender -b $Blend --factory-startup -P (Join-Path $qa "eval_model.py") -- @ev 2>&1 | Select-String "^QA"
if ($Measure) {
    & $blender -b $Blend --factory-startup -P (Join-Path $qa "silhouette_iou.py") -- --measure $Measure 2>&1 | Select-String "^QA"
}
$sh = @()
if ($Compare) { $sh += @("--compare", $Compare) }
if ($Ref) { $sh += @("--ref", $Ref) }
& $blender -b $Blend --factory-startup -P (Join-Path $qa "sheet.py") -- @sh 2>&1 | Select-String "^QA"
