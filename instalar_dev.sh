#!/bin/bash

echo "🍎 INSTALAÇÃO DESENVOLVEDOR - SISTEMA RPA v2.0 (Mac/Linux)"
echo "========================================================="

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.8+ primeiro."
    exit 1
fi

echo "📦 Instalando UV (gerenciador de pacotes ultrarrápido)..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# Adicionar UV ao PATH da sessão atual
export PATH="$HOME/.cargo/bin:$PATH"

echo "🐍 Criando ambiente virtual..."
uv venv

echo "📚 Instalando dependências..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    source .venv/bin/activate
else
    # Linux
    source .venv/bin/activate
fi

uv pip install -r pyproject.toml

echo "📄 Configurando arquivo .env..."
if [ ! -f .env ]; then
    cp .env.exemplo .env
    echo "✅ Arquivo .env criado. Configure suas credenciais!"
else
    echo "⚠️  Arquivo .env já existe. Verifique se precisa atualizar."
fi

echo ""
echo "🎉 INSTALAÇÃO CONCLUÍDA!"
echo "======================="
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Configure suas credenciais no arquivo .env"
echo "2. Coloque suas credenciais Google no arquivo gspread-credentials.json"
echo "3. Abra o VSCode nesta pasta"
echo "4. Use F5 para debugar os RPAs individuais"
echo ""
echo "🚀 COMANDOS ÚTEIS:"
echo "• Abrir VSCode: code ."
echo "• Dashboard: streamlit run dashboard_rpa.py --server.port=5000"
echo "• Dashboard Notificações: streamlit run dashboard_notificacoes.py --server.port=8502"
echo "• API: python main.py"
echo "• Teste completo: python teste_sistema_refatorado.py"
echo ""
echo "💡 DICA: Se der erro de porta em uso:"
echo "• pkill -f streamlit (parar todos os streamlit)"
echo "• lsof -ti:5000 | xargs kill -9 (liberar porta 5000)"
echo ""
echo "🐛 DEBUG NO VSCODE:"
echo "• Pressione F5 e escolha qual RPA debugar"
echo "• Cada RPA tem configuração individual"
echo "• Modo homologação disponível para testes"
