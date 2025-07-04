#!/bin/bash

echo "🔍 Verificando status do Chrome..."

# Verificar versão atual
echo "📋 Versão atual do Chrome:"
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

echo ""
echo "🔧 Configurações de atualização:"
echo "Check Interval: $(sudo defaults read /Library/Preferences/com.google.Keystone.Agent.plist checkInterval 2>/dev/null || echo 'Não configurado')"
echo "Check on Launch: $(sudo defaults read /Library/Preferences/com.google.Keystone.Agent.plist checkForUpdatesOnLaunch 2>/dev/null || echo 'Não configurado')"
echo "Update Enabled: $(sudo defaults read /Library/Preferences/com.google.Keystone.Agent.plist updateCheckEnabled 2>/dev/null || echo 'Não configurado')"

echo ""
echo "📁 Permissões do Chrome:"
ls -la /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome

echo ""
if [ -f "/tmp/chrome_version_fixed.txt" ]; then
    echo "🔒 Status: Chrome FIXADO (atualizações bloqueadas)"
    echo "📝 Detalhes:"
    cat /tmp/chrome_version_fixed.txt
else
    echo "🔄 Status: Chrome NORMAL (atualizações habilitadas)"
fi

echo ""
echo "💡 Comandos úteis:"
echo "  ./fixar_chrome_120.sh     - Fixar Chrome na versão 120"
echo "  ./restaurar_atualizacoes_chrome.sh - Restaurar atualizações"
echo "  ./verificar_status_chrome.sh       - Verificar status (este script)" 