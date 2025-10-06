#!/bin/bash

# Script para atualizar ChromeDriver quando o Chrome for atualizado
# Execute este script sempre que o Chrome for atualizado

echo "🔄 Atualizando ChromeDriver para versão compatível..."

# Verificar versão do Chrome
CHROME_VERSION=$(/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version | cut -d' ' -f3 | cut -d'.' -f1-3)
echo "📱 Versão do Chrome detectada: $CHROME_VERSION"

# Atualizar ChromeDriver via Homebrew
echo "📥 Atualizando ChromeDriver..."
brew upgrade chromedriver

# Verificar versão do ChromeDriver
CHROMEDRIVER_VERSION=$(chromedriver --version | head -n1 | cut -d' ' -f2)
echo "🚗 Versão do ChromeDriver: $CHROMEDRIVER_VERSION"

# Verificar compatibilidade
if [[ "$CHROMEDRIVER_VERSION" == "$CHROME_VERSION"* ]]; then
    echo "✅ ChromeDriver compatível com Chrome $CHROME_VERSION"
else
    echo "⚠️  Versões podem não ser compatíveis"
    echo "   Chrome: $CHROME_VERSION"
    echo "   ChromeDriver: $CHROMEDRIVER_VERSION"
fi

echo "🧪 Testando UC..."
uv run python scripts/teste_uc_chrome.py

echo "✅ Atualização concluída!"
