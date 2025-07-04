#!/bin/bash
echo "🔧 Restaurando permissões do Chrome..."
sudo chmod 755 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sudo chmod -R 755 "/Applications/Google Chrome.app/Contents/Versions/"
echo "✅ Permissões restauradas"
