#!/bin/bash

# Script para gerar pacote de desenvolvedor com configurações VSCode
# Desenvolvido em Português Brasileiro

echo "🛠️  GERANDO PACOTE DE DESENVOLVEDOR - SISTEMA RPA v2.0"
echo "====================================================="

# Data atual para versionamento
DATA_ATUAL=$(date +"%Y%m%d_%H%M%S")
NOME_PACOTE="sistema_rpa_dev_${DATA_ATUAL}"

echo "🗑️  Removendo pacote anterior..."
rm -f sistema_rpa_dev_*.tar.gz

echo "📁 Criando estrutura do pacote..."
mkdir -p "${NOME_PACOTE}"

echo "📋 Copiando arquivos principais..."
cp -r core "${NOME_PACOTE}/"
cp -r rpa_* "${NOME_PACOTE}/"
cp -r workflows "${NOME_PACOTE}/"
cp -r scripts "${NOME_PACOTE}/"
cp -r .vscode "${NOME_PACOTE}/"
cp -r docs "${NOME_PACOTE}/"

# Criar arquivos __init__.py para importação correta
echo "📦 Criando arquivos __init__.py..."
echo "# Core Module" > "${NOME_PACOTE}/core/__init__.py"
echo "# Workflows Module" > "${NOME_PACOTE}/workflows/__init__.py"

# Criar __init__.py para cada pasta RPA
for rpa_dir in "${NOME_PACOTE}"/rpa_*; do
    if [ -d "$rpa_dir" ]; then
        echo "# RPA Module" > "${rpa_dir}/__init__.py"
    fi
done

# Corrigir importações nos arquivos de teste
echo "🔧 Corrigindo importações nos testes..."
if [ -f "${NOME_PACOTE}/rpa_coleta_indices/teste_coleta_indices.py" ]; then
    sed -i 's/from rpa_coleta_indices.rpa_coleta_indices/from rpa_coleta_indices/g' "${NOME_PACOTE}/rpa_coleta_indices/teste_coleta_indices.py"
fi

if [ -f "${NOME_PACOTE}/rpa_analise_planilhas/teste_analise_planilhas.py" ]; then
    sed -i 's/from rpa_analise_planilhas.rpa_analise_planilhas/from rpa_analise_planilhas/g' "${NOME_PACOTE}/rpa_analise_planilhas/teste_analise_planilhas.py"
fi

if [ -f "${NOME_PACOTE}/rpa_sienge/teste_sienge.py" ]; then
    sed -i 's/from rpa_sienge.rpa_sienge/from rpa_sienge/g' "${NOME_PACOTE}/rpa_sienge/teste_sienge.py"
fi

if [ -f "${NOME_PACOTE}/rpa_sicredi/teste_sicredi.py" ]; then
    sed -i 's/from rpa_sicredi.rpa_sicredi/from rpa_sicredi/g' "${NOME_PACOTE}/rpa_sicredi/teste_sicredi.py"
fi

# Arquivos principais
cp main.py "${NOME_PACOTE}/"
cp api_rpa.py "${NOME_PACOTE}/"
cp dashboard_rpa.py "${NOME_PACOTE}/"
cp dashboard_notificacoes.py "${NOME_PACOTE}/"
cp demo_dashboard.py "${NOME_PACOTE}/"
cp agendador_diario.py "${NOME_PACOTE}/"
cp teste_sistema_refatorado.py "${NOME_PACOTE}/"
cp temporal_orchestrator.py "${NOME_PACOTE}/"

# Arquivos de configuração
cp pyproject.toml "${NOME_PACOTE}/"
cp .replit "${NOME_PACOTE}/"

echo "⚙️  Criando arquivo .env de exemplo..."
cat > "${NOME_PACOTE}/.env.exemplo" << 'EOF'
# Configurações do Sistema RPA - Desenvolvedor
# Copie este arquivo para .env e configure suas credenciais

# Google Sheets
GOOGLE_CREDENTIALS_PATH=./gspread-credentials.json

# Sienge (opcional - para testes)
SIENGE_URL=https://sua-empresa.sienge.com.br
SIENGE_USERNAME=seu_usuario
SIENGE_PASSWORD=sua_senha

# Sicredi (opcional - para testes)  
SICREDI_URL=https://empresas.sicredi.com.br
SICREDI_USERNAME=seu_usuario
SICREDI_PASSWORD=sua_senha

# Gmail API (para notificações)
GMAIL_CREDENTIALS_PATH=./gmail-credentials.json

# MongoDB (opcional - usa JSON se não configurado)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=sistema_rpa

# Debug
DEBUG_MODE=true
PYTHONPATH=.
EOF

echo "📝 Criando script de instalação para Mac/Linux..."
cat > "${NOME_PACOTE}/instalar_dev.sh" << 'EOF'
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
EOF

chmod +x "${NOME_PACOTE}/instalar_dev.sh"

echo "📚 Criando README específico para desenvolvedor..."
cat > "${NOME_PACOTE}/README_DEV.md" << 'EOF'
# 🛠️ Sistema RPA - Versão Desenvolvedor

Versão otimizada para desenvolvimento com configurações VSCode completas.

## 🚀 Instalação Rápida (Mac/Linux)

```bash
# 1. Extrair pacote
tar -xzf sistema_rpa_dev_*.tar.gz
cd sistema_rpa_dev_*

# 2. Instalar (automaticamente)
./instalar_dev.sh

# 3. Configurar credenciais
# Edite o arquivo .env com suas configurações
# Coloque suas credenciais Google em gspread-credentials.json

# 4. Abrir no VSCode
code .
```

## 🐛 Debug no VSCode

O projeto inclui configurações completas para debug:

### Dashboards
- **🌐 Dashboard Principal**: Streamlit na porta 5000
- **🔔 Dashboard Notificações**: Streamlit na porta 8502  
- **📊 Dashboard Demo**: Streamlit na porta 8501

### RPAs Individuais (Modo Homologação)
- **📊 RPA 1 - Coleta Índices**: Teste individual
- **📋 RPA 2 - Análise Planilhas**: Teste individual
- **🏢 RPA 3 - Sienge**: Teste individual
- **🏦 RPA 4 - Sicredi**: Teste individual

### Utilitários
- **🤖 API REST**: FastAPI com hot reload
- **🧪 Teste Sistema Completo**: Execução de todos os RPAs
- **📧 Teste Notificações**: Sistema de emails
- **⏰ Agendador**: Execução automática

## ⌨️ Comandos de Teclado

- **F5**: Iniciar debug (escolha a configuração)
- **Ctrl+Shift+P**: Palette de comandos
- **Ctrl+`**: Terminal integrado

## 📁 Estrutura do Projeto

```
sistema_rpa/
├── .vscode/           # Configurações VSCode
├── core/             # Módulos principais
├── rpa_*/            # RPAs individuais
├── scripts/          # Scripts utilitários
├── dashboard_*.py    # Interfaces web
├── main.py          # API principal
└── .env             # Configurações (você cria)
```

## 🔧 Configuração de Credenciais

### Google Sheets
1. Vá para Google Cloud Console
2. Crie um projeto e ative Google Sheets API
3. Baixe as credenciais JSON
4. Salve como `gspread-credentials.json`

### Variáveis de Ambiente
Configure no arquivo `.env`:
```env
GOOGLE_CREDENTIALS_PATH=./gspread-credentials.json
SIENGE_URL=https://sua-empresa.sienge.com.br
SICREDI_URL=https://empresas.sicredi.com.br
DEBUG_MODE=true
```

## 🎯 Modo Homologação

Cada RPA pode ser executado individualmente para testes:

1. Configure breakpoints no código
2. Pressione F5
3. Escolha o RPA que quer debugar
4. Acompanhe execução passo a passo

Perfect for development and testing! 🇧🇷
EOF

echo "📦 Compactando pacote..."
tar -czf "${NOME_PACOTE}.tar.gz" "${NOME_PACOTE}"
rm -rf "${NOME_PACOTE}"

# Obter informações do pacote
TAMANHO=$(du -h "${NOME_PACOTE}.tar.gz" | cut -f1)
ARQUIVOS=$(tar -tzf "${NOME_PACOTE}.tar.gz" | wc -l)

echo ""
echo "🎉 PACOTE DE DESENVOLVEDOR CRIADO COM SUCESSO!"
echo "=============================================="
echo "📁 Pacote: ${NOME_PACOTE}.tar.gz"
echo "📏 Tamanho: ${TAMANHO}"
echo "📋 Arquivos: ${ARQUIVOS}"
echo ""
echo "📋 CONTEÚDO DO PACOTE:"
echo "✅ Sistema RPA completo (4 RPAs)"
echo "✅ Configurações VSCode para debug"
echo "✅ Scripts de teste individuais"
echo "✅ Dashboard com modo desenvolvedor"
echo "✅ Instalação automática Mac/Linux"
echo "✅ Documentação específica"
echo "✅ Modo homologação para testes"
echo ""
echo "🚀 PARA INSTALAR:"
echo "1. tar -xzf ${NOME_PACOTE}.tar.gz"
echo "2. cd sistema_rpa_dev_*"
echo "3. ./instalar_dev.sh"
echo "4. code . (abrir no VSCode)"
echo ""
echo "🐛 Perfect for development! 🇧🇷"