#!/bin/bash
# Script de Configuração Completa para Desenvolvimento - Sistema RPA v2.0
# Prepara ambiente completo com UV, .venv e todas as dependências

set -e

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}⚡ CONFIGURANDO AMBIENTE DE DESENVOLVIMENTO COMPLETO${NC}"
echo "=================================================================="

# Instalar UV se não estiver instalado
if ! command -v uv &> /dev/null; then
    echo -e "${BLUE}📦 Instalando UV (gerenciador de pacotes ultra-rápido)...${NC}"
    pip install uv
    echo -e "${GREEN}✅ UV instalado com sucesso!${NC}"
else
    echo -e "${GREEN}✅ UV já está instalado${NC}"
fi

# Verificar se pyproject.toml existe
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Arquivo pyproject.toml não encontrado!"
    echo "Execute este script na pasta raiz do projeto"
    exit 1
fi

# Remover .venv antigo se existir
if [ -d ".venv" ]; then
    echo -e "${YELLOW}🗑️ Removendo ambiente virtual antigo...${NC}"
    rm -rf .venv
fi

# Criar novo ambiente virtual e instalar dependências
echo -e "${BLUE}🔄 Criando ambiente virtual e instalando dependências...${NC}"
uv venv .venv
uv sync

# Verificar se ambiente foi criado
if [ -d ".venv" ]; then
    echo -e "${GREEN}✅ Ambiente virtual criado em .venv/${NC}"
else
    echo "❌ Falha ao criar ambiente virtual"
    exit 1
fi

# Ativar ambiente e verificar instalação
echo -e "${BLUE}🔍 Verificando instalação das dependências...${NC}"
source .venv/bin/activate

# Verificar pacotes principais
echo "Verificando pacotes principais..."
python -c "import streamlit; print('✅ Streamlit:', streamlit.__version__)"
python -c "import fastapi; print('✅ FastAPI:', fastapi.__version__)"
python -c "import selenium; print('✅ Selenium:', selenium.__version__)"
python -c "import pandas; print('✅ Pandas:', pandas.__version__)"
python -c "import gspread; print('✅ gspread:', gspread.__version__)"

# Criar arquivos de configuração se não existirem
echo -e "${BLUE}📁 Criando estrutura de desenvolvimento...${NC}"

# Criar diretórios necessários
mkdir -p {logs,temp,backup,credentials}

# Copiar arquivo .env se não existir
if [ ! -f ".env" ]; then
    if [ -f "deploy/.env.example" ]; then
        cp deploy/.env.example .env
        echo -e "${YELLOW}⚠️ Arquivo .env criado a partir do exemplo${NC}"
        echo -e "${YELLOW}   Configure suas credenciais antes de executar${NC}"
    fi
fi

# Criar script de ativação rápida
cat > activate_dev.sh << 'EOF'
#!/bin/bash
# Script de ativação rápida do ambiente de desenvolvimento
echo "🚀 Ativando ambiente de desenvolvimento..."
source .venv/bin/activate
echo "✅ Ambiente ativado!"
echo ""
echo "🎯 Comandos disponíveis:"
echo "  • uv run python main.py              - Executar API"
echo "  • uv run streamlit run dashboard_rpa.py - Executar Dashboard"
echo "  • uv run python teste_sistema_refatorado.py - Executar testes"
echo "  • uv add nome-pacote                 - Instalar nova dependência"
echo ""
EOF

chmod +x activate_dev.sh

# Criar script de desenvolvimento rápido
cat > dev_start.sh << 'EOF'
#!/bin/bash
# Script para iniciar desenvolvimento rapidamente
echo "🚀 Iniciando Sistema RPA - Modo Desenvolvimento"
echo "=============================================="

# Ativar ambiente
source .venv/bin/activate

# Verificar configurações
if [ ! -f ".env" ]; then
    echo "⚠️ Arquivo .env não encontrado!"
    echo "Configure suas credenciais primeiro"
    exit 1
fi

echo "🎯 Escolha o que executar:"
echo "1) API REST (main.py)"
echo "2) Dashboard Streamlit"
echo "3) Ambos (API + Dashboard)"
echo "4) Executar testes"
read -p "Digite sua opção (1-4): " opcao

case $opcao in
    1)
        echo "🔗 Executando API REST..."
        uv run python main.py
        ;;
    2)
        echo "📊 Executando Dashboard..."
        uv run streamlit run dashboard_rpa.py --server.port=8501 --server.address=0.0.0.0
        ;;
    3)
        echo "🚀 Executando API + Dashboard..."
        echo "API estará em: http://localhost:5000"
        echo "Dashboard estará em: http://localhost:8501"
        # Executar API em background
        uv run python main.py &
        # Executar Dashboard
        uv run streamlit run dashboard_rpa.py --server.port=8501 --server.address=0.0.0.0
        ;;
    4)
        echo "🧪 Executando testes do sistema..."
        uv run python teste_sistema_refatorado.py
        ;;
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac
EOF

chmod +x dev_start.sh

echo ""
echo "=================================================================="
echo -e "${GREEN}🎉 AMBIENTE DE DESENVOLVIMENTO CONFIGURADO COM SUCESSO!${NC}"
echo ""
echo -e "${BLUE}📁 Estrutura criada:${NC}"
echo "  ✅ Ambiente virtual (.venv/) com todas as dependências"
echo "  ✅ Scripts de desenvolvimento (activate_dev.sh, dev_start.sh)"
echo "  ✅ Diretórios necessários (logs/, temp/, backup/, credentials/)"
echo "  ✅ Arquivo .env (configure suas credenciais)"
echo ""
echo -e "${BLUE}🚀 Para começar a desenvolver:${NC}"
echo "  1. Configure o arquivo .env com suas credenciais"
echo "  2. Execute: ./dev_start.sh"
echo "  3. Ou ative o ambiente: ./activate_dev.sh"
echo ""
echo -e "${BLUE}⚡ Comandos rápidos com UV:${NC}"
echo "  • uv add nome-pacote        - Instalar dependência"
echo "  • uv remove nome-pacote     - Remover dependência"
echo "  • uv sync --upgrade         - Atualizar tudo"
echo "  • uv run python script.py  - Executar script"
echo ""
echo -e "${GREEN}✨ Ambiente pronto para desenvolvimento de alta velocidade!${NC}"