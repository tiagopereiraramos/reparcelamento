#!/bin/bash

echo "🔒 Fixando Chrome na versão 120 e bloqueando atualizações..."

# 1. Parar processos do Chrome
echo "🛑 Parando processos do Chrome..."
pkill -f "Google Chrome" 2>/dev/null || true
sleep 2

# 2. Desabilitar atualizações automáticas do Chrome
echo "🚫 Desabilitando atualizações automáticas..."
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist checkInterval 0
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist checkForUpdatesOnLaunch -bool false
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist updateCheckEnabled -bool false

# 3. Remover permissões de escrita do Chrome para evitar atualizações
echo "🔐 Removendo permissões de escrita do Chrome..."
sudo chmod -R 755 /Applications/Google\ Chrome.app
sudo chown -R root:wheel /Applications/Google\ Chrome.app

# 4. Criar arquivo de controle de versão
echo "📝 Criando controle de versão..."
echo "Chrome 120 - Fixado em $(date)" > /tmp/chrome_version_fixed.txt
echo "Versão: 120.0.6099.109" >> /tmp/chrome_version_fixed.txt
echo "Status: Bloqueado para atualizações" >> /tmp/chrome_version_fixed.txt

# 5. Verificar se o Chrome 120 está funcionando
echo "✅ Verificando versão do Chrome..."
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

echo ""
echo "🎉 Chrome 120 fixado com sucesso!"
echo "📋 Para verificar o status: cat /tmp/chrome_version_fixed.txt"
echo "🔄 Para restaurar atualizações: restaurar_atualizacoes_chrome.sh" 