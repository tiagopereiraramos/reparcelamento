#!/bin/bash

echo "🔧 Instalando Google Chrome 137.0.7151.122 para Mac ARM64..."

# URL do Chrome 137 (usando um mirror confiável)
CHROME_URL="https://dl.google.com/chrome/mac/universal/stable/GGRO/googlechrome-137.0.7151.122.dmg"
CHROME_DMG="googlechrome-137.0.7151.122.dmg"

# Verificar se o Chrome já está instalado
if [ -d "/Applications/Google Chrome.app" ]; then
    echo "⚠️  Chrome já está instalado. Removendo versão atual..."
    sudo rm -rf "/Applications/Google Chrome.app"
fi

# Baixar o Chrome 137
echo "📥 Baixando Chrome 137..."
curl -L -o "$CHROME_DMG" "$CHROME_URL"

if [ $? -ne 0 ]; then
    echo "❌ Falha ao baixar Chrome. Tentando URL alternativa..."
    # URL alternativa
    CHROME_URL="https://dl.google.com/chrome/mac/universal/stable/GGRO/googlechrome-137.0.7151.122.dmg"
    curl -L -o "$CHROME_DMG" "$CHROME_URL"
fi

if [ ! -f "$CHROME_DMG" ]; then
    echo "❌ Não foi possível baixar o Chrome 137"
    echo "💡 Alternativa: Baixe manualmente de:"
    echo "   https://google-chrome.en.uptodown.com/mac/download/4284567"
    echo "   Procure por '137.0.7151.104' ou '137.0.7151.69'"
    exit 1
fi

# Montar o DMG
echo "🔧 Montando DMG..."
hdiutil attach "$CHROME_DMG"

# Instalar o Chrome
echo "📦 Instalando Chrome..."
sudo cp -R "/Volumes/Google Chrome/Google Chrome.app" "/Applications/"

# Desmontar o DMG
echo "🔧 Desmontando DMG..."
hdiutil detach "/Volumes/Google Chrome"

# Limpar arquivo temporário
rm "$CHROME_DMG"

# Definir permissões
echo "🔐 Definindo permissões..."
sudo chown -R root:wheel "/Applications/Google Chrome.app"
sudo chmod -R 755 "/Applications/Google Chrome.app"

# Verificar instalação
if [ -d "/Applications/Google Chrome.app" ]; then
    echo "✅ Chrome 137 instalado com sucesso!"
    echo "📍 Localização: /Applications/Google Chrome.app"
    
    # Verificar versão
    CHROME_VERSION=$(defaults read "/Applications/Google Chrome.app/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null)
    echo "📋 Versão instalada: $CHROME_VERSION"
    
    # Bloquear atualizações automáticas
    echo "🔒 Bloqueando atualizações automáticas..."
    
    # Remover Google Software Update se existir
    if [ -d "/Library/Google/GoogleSoftwareUpdate" ]; then
        sudo rm -rf "/Library/Google/GoogleSoftwareUpdate"
    fi
    
    # Desabilitar atualizações automáticas
    defaults write com.google.Keystone.Agent checkInterval 0 2>/dev/null || true
    
    # Adicionar ao hosts para bloquear atualizações
    echo "127.0.0.1 tools.google.com" | sudo tee -a /etc/hosts > /dev/null
    echo "127.0.0.1 dl.google.com" | sudo tee -a /etc/hosts > /dev/null
    
    echo "✅ Chrome 137 instalado e atualizações bloqueadas!"
    echo "🚀 Agora você pode executar o RPA novamente."
else
    echo "❌ Falha na instalação do Chrome"
    exit 1
fi 