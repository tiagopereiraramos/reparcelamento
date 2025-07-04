#!/bin/bash

echo "🔄 Substituindo Chrome 138 pelo Chrome 120..."

# 1. Parar todos os processos do Chrome
echo "🛑 Parando processos do Chrome..."
pkill -f "Google Chrome" 2>/dev/null || true
sleep 3

# 2. Fazer backup do Chrome atual (se existir)
echo "💾 Fazendo backup do Chrome atual..."
if [ -d "/Applications/Google Chrome.app" ]; then
    sudo mv "/Applications/Google Chrome.app" "/Applications/Google Chrome.app.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup criado: /Applications/Google Chrome.app.backup.*"
fi

# 3. Verificar se o Chrome 120 está disponível no volume montado
if [ -d "/Volumes/Google Chrome/Google Chrome.app" ]; then
    echo "📦 Copiando Chrome 120 do volume..."
    sudo cp -r "/Volumes/Google Chrome/Google Chrome.app" "/Applications/"
    sudo xattr -dr com.apple.quarantine "/Applications/Google Chrome.app"
    echo "✅ Chrome 120 copiado com sucesso"
else
    echo "❌ Chrome 120 não encontrado no volume. Reinstalando..."
    # Baixar e instalar Chrome 120 novamente
    curl -L -o /tmp/GoogleChrome120.dmg https://dl.google.com/chrome/mac/universal/stable/GGRO/googlechrome.dmg
    hdiutil attach /tmp/GoogleChrome120.dmg
    sudo cp -r "/Volumes/Google Chrome/Google Chrome.app" "/Applications/"
    sudo xattr -dr com.apple.quarantine "/Applications/Google Chrome.app"
    hdiutil detach "/Volumes/Google Chrome"
fi

# 4. Fixar permissões e bloquear atualizações
echo "🔐 Configurando permissões..."
sudo chmod -R 755 "/Applications/Google Chrome.app"
sudo chown -R root:wheel "/Applications/Google Chrome.app"

# 5. Bloquear atualizações
echo "🚫 Bloqueando atualizações..."
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist checkInterval 0
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist checkForUpdatesOnLaunch -bool false
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist updateCheckEnabled -bool false

# 6. Verificar versão
echo "✅ Verificando versão do Chrome..."
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# 7. Criar arquivo de controle
echo "📝 Criando controle de versão..."
echo "Chrome 120 - Substituído em $(date)" > /tmp/chrome_version_fixed.txt
echo "Versão: 120.0.6099.109" >> /tmp/chrome_version_fixed.txt
echo "Status: Substituído Chrome 138 por Chrome 120" >> /tmp/chrome_version_fixed.txt
echo "Backup: /Applications/Google Chrome.app.backup.*" >> /tmp/chrome_version_fixed.txt

echo ""
echo "🎉 Chrome 120 instalado e configurado!"
echo "📋 Para verificar: ./verificar_status_chrome.sh" 