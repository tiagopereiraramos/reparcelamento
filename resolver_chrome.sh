#!/bin/bash

echo "🔧 Resolvendo problema do Chrome..."

# 1. Matar todos os processos do Chrome
echo "🔧 Matando processos do Chrome..."
pkill -f "Google Chrome" 2>/dev/null || true
sleep 2

# 2. Limpar cache e dados
echo "🔧 Limpando cache..."
rm -rf "$HOME/Library/Application Support/Google/Chrome/Default/Cache"
rm -rf "$HOME/Library/Application Support/Google/Chrome/Default/Code Cache"
rm -rf "$HOME/Library/Caches/Google/Chrome"

# 3. Tentar abrir com flags especiais
echo "🚀 Tentando abrir Chrome..."
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --no-sandbox --disable-gpu-sandbox --disable-dev-shm-usage --disable-web-security --user-data-dir=/tmp/chrome_temp &

echo "✅ Chrome deve estar abrindo agora..." 