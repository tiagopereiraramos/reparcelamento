#!/bin/bash
set -e

CHROMEDRIVER_VERSION="138.0.7204.50"
CHROMEDRIVER_DIR="drivers/chromedriver-mac-arm64"
CHROMEDRIVER_BIN="$CHROMEDRIVER_DIR/chromedriver"

mkdir -p "$CHROMEDRIVER_DIR"

URL="https://storage.googleapis.com/chrome-for-testing-public/$CHROMEDRIVER_VERSION/mac-arm64/chromedriver-mac-arm64.zip"
echo "Baixando ChromeDriver $CHROMEDRIVER_VERSION para Mac ARM64..."
curl -L "$URL" -o "$CHROMEDRIVER_DIR/chromedriver.zip"

unzip -o "$CHROMEDRIVER_DIR/chromedriver.zip" -d "$CHROMEDRIVER_DIR"
# Move o binário para o local correto
mv "$CHROMEDRIVER_DIR/chromedriver-mac-arm64/chromedriver" "$CHROMEDRIVER_BIN"
chmod +x "$CHROMEDRIVER_BIN"
rm -rf "$CHROMEDRIVER_DIR/chromedriver.zip" "$CHROMEDRIVER_DIR/chromedriver-mac-arm64"
echo "✅ ChromeDriver fixo salvo em $CHROMEDRIVER_BIN" 