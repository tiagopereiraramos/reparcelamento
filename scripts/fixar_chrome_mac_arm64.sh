#!/bin/bash

echo "🔒 Fixando Google Chrome na versão 136.0.7103.93..."

# Verificar se o Chrome 136 está instalado
if [ ! -d "/Applications/Google Chrome.app" ]; then
    echo "❌ Chrome não está instalado. Execute primeiro o script de instalação."
    exit 1
fi

CHROME_VERSION=$(/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version 2>/dev/null)
if [[ $CHROME_VERSION != *"136.0.7103.93"* ]]; then
    echo "❌ Chrome 136.0.7103.93 não está instalado. Versão atual: $CHROME_VERSION"
    exit 1
fi

echo "✅ Chrome 136.0.7103.93 detectado"

# 1. Remover Google Software Update (se existir)
echo "🔧 Removendo Google Software Update..."
if [ -d "/Library/Google/GoogleSoftwareUpdate" ]; then
    sudo rm -rf "/Library/Google/GoogleSoftwareUpdate"
    echo "✅ Google Software Update removido"
fi

if [ -d "$HOME/Library/Google/GoogleSoftwareUpdate" ]; then
    rm -rf "$HOME/Library/Google/GoogleSoftwareUpdate"
    echo "✅ Google Software Update do usuário removido"
fi

# 2. Desabilitar o agente de atualização do Chrome
echo "🔧 Desabilitando agente de atualização do Chrome..."
sudo launchctl unload -w /Library/LaunchDaemons/com.google.keystone.daemon.plist 2>/dev/null || true
sudo launchctl unload -w /Library/LaunchAgents/com.google.keystone.agent.plist 2>/dev/null || true

# 3. Remover arquivos de keystone (sistema de atualização do Google)
echo "🔧 Removendo sistema de atualização Keystone..."
sudo rm -rf "/Library/Google/GoogleSoftwareUpdate"
sudo rm -rf "/Library/Google/GoogleSoftwareUpdate.bundle"
sudo rm -rf "/Library/Google/GoogleSoftwareUpdateAgent.app"
sudo rm -rf "/Library/Google/GoogleSoftwareUpdateAgent.bundle"

# 4. Bloquear atualizações via hosts
echo "🔧 Bloqueando atualizações via /etc/hosts..."
HOSTS_BLOCK="# Chrome Update Block - Adicionado $(date)
127.0.0.1 tools.google.com
127.0.0.1 dl.google.com
127.0.0.1 dl-ssl.google.com
127.0.0.1 update.googleapis.com
127.0.0.1 omahaproxy.appspot.com
127.0.0.1 chromedriver.storage.googleapis.com
127.0.0.1 chrome-update.google.com
127.0.0.1 chrome.google.com
127.0.0.1 www.google.com/chrome
127.0.0.1 www.google.com/chrome/eula.html
127.0.0.1 www.google.com/chrome/privacy/eula_text.html"

# Verificar se já existe o bloqueio
if ! grep -q "Chrome Update Block" /etc/hosts; then
    echo "$HOSTS_BLOCK" | sudo tee -a /etc/hosts > /dev/null
    echo "✅ Bloqueio adicionado ao /etc/hosts"
else
    echo "✅ Bloqueio já existe no /etc/hosts"
fi

# 5. Desabilitar atualizações automáticas do macOS para o Chrome
echo "🔧 Desabilitando atualizações automáticas do macOS..."
defaults write com.apple.SoftwareUpdate AutomaticCheckEnabled -bool false
defaults write com.apple.commerce AutoUpdate -bool false
echo "✅ Atualizações automáticas do macOS desabilitadas"

# 6. Criar arquivo de configuração para impedir atualizações
echo "🔧 Criando configuração para impedir atualizações..."
CHROME_CONFIG_DIR="$HOME/Library/Application Support/Google/Chrome"
mkdir -p "$CHROME_CONFIG_DIR"

cat > "$CHROME_CONFIG_DIR/disable_auto_updates.json" << 'EOF'
{
  "update_disabled": true,
  "auto_update_enabled": false,
  "update_check_disabled": true
}
EOF

echo "✅ Configuração de atualizações criada"

# 7. Definir permissões para impedir modificação
echo "🔧 Definindo permissões para impedir modificação..."
sudo chmod 444 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sudo chmod -R 444 "/Applications/Google Chrome.app/Contents/Versions/"
echo "✅ Permissões definidas (somente leitura)"

# 8. Criar script de verificação
echo "🔧 Criando script de verificação..."
cat > "verificar_chrome.sh" << 'EOF'
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
EOF

chmod +x "verificar_chrome.sh"
echo "✅ Script de verificação criado: ./verificar_chrome.sh"

# 9. Criar script para restaurar permissões (se necessário)
echo "🔧 Criando script para restaurar permissões..."
cat > "restaurar_permissoes_chrome.sh" << 'EOF'
#!/bin/bash
echo "🔧 Restaurando permissões do Chrome..."
sudo chmod 755 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sudo chmod -R 755 "/Applications/Google Chrome.app/Contents/Versions/"
echo "✅ Permissões restauradas"
EOF

chmod +x "restaurar_permissoes_chrome.sh"
echo "✅ Script de restauração criado: ./restaurar_permissoes_chrome.sh"

echo ""
echo "🎉 Chrome 136.0.7103.93 foi fixado com sucesso!"
echo ""
echo "📋 O que foi feito:"
echo "   ✅ Removido Google Software Update"
echo "   ✅ Desabilitado agente de atualização"
echo "   ✅ Bloqueado domínios de atualização no /etc/hosts"
echo "   ✅ Desabilitado atualizações automáticas do macOS"
echo "   ✅ Criada configuração para impedir atualizações"
echo "   ✅ Definidas permissões somente leitura"
echo ""
echo "🔍 Para verificar o status: ./verificar_chrome.sh"
echo "🔧 Para restaurar permissões: ./restaurar_permissoes_chrome.sh"
echo ""
echo "⚠️  IMPORTANTE: Se precisar atualizar o Chrome no futuro, execute:"
echo "   ./restaurar_permissoes_chrome.sh"
echo "   E remova as linhas de bloqueio do /etc/hosts"