#!/bin/bash
echo "🔍 Verificando versão do Chrome..."
CHROME_VERSION=$(/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version 2>/dev/null)
echo "Versão atual: $CHROME_VERSION"

if [[ $CHROME_VERSION == *"136.0.7103.93"* ]]; then
    echo "✅ Chrome está na versão correta (136.0.7103.93)"
else
    echo "❌ Chrome não está na versão correta"
fi

echo ""
echo "🔍 Verificando bloqueios de atualização..."
if grep -q "Chrome Update Block" /etc/hosts; then
    echo "✅ Bloqueio no /etc/hosts ativo"
else
    echo "❌ Bloqueio no /etc/hosts não encontrado"
fi

if [ -f "$HOME/Library/Application Support/Google/Chrome/disable_auto_updates.json" ]; then
    echo "✅ Configuração de bloqueio de atualizações ativa"
else
    echo "❌ Configuração de bloqueio não encontrada"
fi
