#!/bin/bash

echo "🔓 Desbloqueando Chrome temporariamente..."

# 1. Remover bloqueios do /etc/hosts
echo "🔧 Removendo bloqueios do /etc/hosts..."
sudo sed -i '' '/Chrome Update Block/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 tools.google.com/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 dl.google.com/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 dl-ssl.google.com/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 update.googleapis.com/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 omahaproxy.appspot.com/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 chromedriver.storage.googleapis.com/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 chrome-update.google.com/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 chrome.google.com/d' /etc/hosts
sudo sed -i '' '/127.0.0.1 www.google.com\/chrome/d' /etc/hosts
echo "✅ Bloqueios removidos do /etc/hosts"

# 2. Remover arquivo de configuração de bloqueio
echo "🔧 Removendo configuração de bloqueio..."
rm -f "$HOME/Library/Application Support/Google/Chrome/disable_auto_updates.json"
echo "✅ Configuração de bloqueio removida"

# 3. Restaurar permissões completas
echo "🔧 Restaurando permissões..."
sudo chmod 755 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sudo chmod -R 755 "/Applications/Google Chrome.app/Contents/Versions/"
sudo chown -R root:wheel "/Applications/Google Chrome.app"
echo "✅ Permissões restauradas"

# 4. Limpar cache do Chrome
echo "🔧 Limpando cache do Chrome..."
rm -rf "$HOME/Library/Application Support/Google/Chrome/Default/Cache"
rm -rf "$HOME/Library/Application Support/Google/Chrome/Default/Code Cache"
rm -rf "$HOME/Library/Caches/Google/Chrome"
echo "✅ Cache limpo"

# 5. Reabilitar atualizações automáticas do macOS
echo "🔧 Reabilitando atualizações automáticas do macOS..."
defaults write com.apple.SoftwareUpdate AutomaticCheckEnabled -bool true
defaults write com.apple.commerce AutoUpdate -bool true
echo "✅ Atualizações automáticas reabilitadas"

echo ""
echo "🎉 Chrome foi desbloqueado temporariamente!"
echo ""
echo "📋 O que foi feito:"
echo "   ✅ Removidos bloqueios do /etc/hosts"
echo "   ✅ Removida configuração de bloqueio"
echo "   ✅ Restauradas permissões"
echo "   ✅ Limpo cache do Chrome"
echo "   ✅ Reabilitadas atualizações automáticas"
echo ""
echo "🚀 Tente abrir o Chrome agora:"
echo "   open -a 'Google Chrome'"
echo ""
echo "⚠️  IMPORTANTE: Para reativar os bloqueios depois, execute:"
echo "   ./scripts/fixar_chrome_mac_arm64.sh" 