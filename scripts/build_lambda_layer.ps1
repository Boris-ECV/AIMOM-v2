# 建置 Lambda Layer（相依套件），供 infra/lambda.tf 的 aws_lambda_layer_version 使用（TASK-014）
#
# 用途：修正原本 Lambda 只打包 src/ 原始碼、完全沒有 fastapi/mangum/boto3 等相依套件
# 導致每次呼叫都 500 的問題。相依套件與應用程式碼分開打包成 Layer，方便版本控管與重複使用。
#
# 使用方式（本機需有 Python 3.12venv 或任何 Python + pip，跨平台下載不需本機也是 3.12/Linux）：
#   powershell -File scripts/build_lambda_layer.ps1
#
# 產出：infra/layer/python/ 底下會有所有相依套件，之後 `terraform apply` 時
# archive_file 會自動把 infra/layer/ 打包成 layer zip 上傳。

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$reqFile = Join-Path $root "src\requirements-lambda.txt"
$layerDir = Join-Path $root "infra\layer\python"

Write-Host "清除舊的 layer 目錄..."
Remove-Item -Recurse -Force (Join-Path $root "infra\layer") -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $layerDir -Force | Out-Null

# 優先使用 src/venv（若存在），否則退回系統 python
$venvPython = Join-Path $root "src\venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "使用 $python 安裝 Lambda 相依套件（目標平台：manylinux2014_x86_64, Python 3.12）..."
& $python -m pip install `
  --platform manylinux2014_x86_64 `
  --implementation cp `
  --python-version 3.12 `
  --only-binary=:all: `
  --target $layerDir `
  -r $reqFile

Write-Host "清除快取/測試檔案以縮小 layer 體積..."
Get-ChildItem $layerDir -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force
Get-ChildItem $layerDir -Directory -Recurse -Filter "tests" -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$sizeMb = (Get-ChildItem $layerDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ("Done. infra/layer/python raw size: {0:N1} MB" -f $sizeMb)

Write-Host "Zipping into infra/build/aimom-lambda-layer.zip (terraform reads this zip directly, no longer via archive_file, to avoid disk space issues on constrained environments like CloudShell)..."
$buildDir = Join-Path $root "infra\build"
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
$zipPath = Join-Path $buildDir "aimom-lambda-layer.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $layerDir -DestinationPath $zipPath -Force
Write-Host "Done: infra/build/aimom-lambda-layer.zip"
Write-Host "Next: terraform plan/apply"
