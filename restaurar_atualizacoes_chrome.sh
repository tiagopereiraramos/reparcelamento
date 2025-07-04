#!/bin/bash

echo "🔄 Restaurando atualizações do Chrome..."

# 1. Parar processos do Chrome
echo "🛑 Parando processos do Chrome..."
pkill -f "Google Chrome" 2>/dev/null || true
sleep 2

# 2. Reabilitar atualizações automáticas do Chrome
echo "✅ Reabilitando atualizações automáticas..."
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist checkInterval 43200
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist checkForUpdatesOnLaunch -bool true
sudo defaults write /Library/Preferences/com.google.Keystone.Agent.plist updateCheckEnabled -bool true

# 3. Restaurar permissões de escrita do Chrome
echo "🔓 Restaurando permissões de escrita..."
sudo chmod -R 755 /Applications/Google\ Chrome.app
sudo chown -R $(whoami):staff /Applications/Google\ Chrome.app

# 4. Remover arquivo de controle
echo "🗑️ Removendo controle de versão..."
rm -f /tmp/chrome_version_fixed.txt

echo ""
echo "🎉 Atualizações do Chrome restauradas!"
echo "⚠️ O Chrome pode atualizar automaticamente agora." 