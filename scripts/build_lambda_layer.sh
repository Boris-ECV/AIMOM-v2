#!/usr/bin/env bash
# 建置 Lambda Layer（相依套件），供 infra/lambda.tf 的 aws_lambda_layer_version 使用（TASK-014）
# 供 CloudShell / Linux / macOS 環境使用（Windows 請用 scripts/build_lambda_layer.ps1）
#
# 用法：
#   bash scripts/build_lambda_layer.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ_FILE="$ROOT_DIR/src/requirements-lambda.txt"
LAYER_DIR="$ROOT_DIR/infra/layer/python"

echo "清除舊的 layer 目錄..."
rm -rf "$ROOT_DIR/infra/layer"
mkdir -p "$LAYER_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "使用 $PYTHON_BIN 安裝 Lambda 相依套件（目標平台：manylinux2014_x86_64, Python 3.12）..."
"$PYTHON_BIN" -m pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target "$LAYER_DIR" \
  -r "$REQ_FILE"

echo "清除快取/測試檔案以縮小 layer 體積..."
find "$LAYER_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

SIZE_MB=$(du -sm "$LAYER_DIR" | cut -f1)
echo "完成。infra/layer/python 未壓縮大小：約 ${SIZE_MB} MB"

echo "打包成 infra/build/aimom-lambda-layer.zip（terraform 直接讀取此 zip，不再用
archive_file 動態壓縮，避免磁碟空間有限的環境如 CloudShell 同時存放原始檔+zip 爆容量）..."
BUILD_DIR="$ROOT_DIR/infra/build"
mkdir -p "$BUILD_DIR"
rm -f "$BUILD_DIR/aimom-lambda-layer.zip"
(cd "$ROOT_DIR/infra/layer" && zip -q -r "$BUILD_DIR/aimom-lambda-layer.zip" python)
echo "完成：infra/build/aimom-lambda-layer.zip"
echo "接下來執行 terraform plan/apply 即可"
