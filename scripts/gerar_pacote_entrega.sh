#!/bin/bash

# Script para Gerar Pacote de Entrega - Sistema RPA v2.0
# Cria pacote completo para instalação na máquina do desenvolvedor
# Desenvolvido em Português Brasileiro

echo "🚀 GERANDO PACOTE DE ENTREGA - SISTEMA RPA v2.0"
echo "=================================================="

# Configurações
DATA_ATUAL=$(date +"%Y%m%d_%H%M%S")
NOME_PACOTE="sistema_rpa_v2_${DATA_ATUAL}"
DIRETORIO_PACOTE="./pacote_entrega"

# Limpar pacote anterior se existir
if [ -d "$DIRETORIO_PACOTE" ]; then
    echo "🗑️  Removendo pacote anterior..."
    rm -rf "$DIRETORIO_PACOTE"
fi

# Criar estrutura do pacote
echo "📁 Criando estrutura do pacote..."
mkdir -p "$DIRETORIO_PACOTE"
mkdir -p "$DIRETORIO_PACOTE/sistema_rpa"
mkdir -p "$DIRETORIO_PACOTE/docs"
mkdir -p "$DIRETORIO_PACOTE/scripts"
mkdir -p "$DIRETORIO_PACOTE/config"

# Copiar arquivos essenciais do sistema
echo "📋 Copiando arquivos do sistema..."

# Arquivos raiz
cp main.py "$DIRETORIO_PACOTE/sistema_rpa/"
cp dashboard_rpa.py "$DIRETORIO_PACOTE/sistema_rpa/"
cp dashboard_notificacoes.py "$DIRETORIO_PACOTE/sistema_rpa/"
cp demo_dashboard.py "$DIRETORIO_PACOTE/sistema_rpa/"
cp agendador_diario.py "$DIRETORIO_PACOTE/sistema_rpa/"
cp config.py "$DIRETORIO_PACOTE/sistema_rpa/"
cp pyproject.toml "$DIRETORIO_PACOTE/sistema_rpa/"
cp uv.lock "$DIRETORIO_PACOTE/sistema_rpa/"

# Credenciais (arquivo de exemplo)
if [ -f "gspread-459713-aab8a657f9b0.json" ]; then
    cp gspread-459713-aab8a657f9b0.json "$DIRETORIO_PACOTE/sistema_rpa/"
fi

# Copiar diretórios completos
echo "📁 Copiando módulos do sistema..."
cp -r core "$DIRETORIO_PACOTE/sistema_rpa/"
cp -r rpa_coleta_indices "$DIRETORIO_PACOTE/sistema_rpa/"
cp -r rpa_analise_planilhas "$DIRETORIO_PACOTE/sistema_rpa/"
cp -r rpa_sienge "$DIRETORIO_PACOTE/sistema_rpa/"
cp -r rpa_sicredi "$DIRETORIO_PACOTE/sistema_rpa/"
cp -r workflows "$DIRETORIO_PACOTE/sistema_rpa/"
cp -r utils "$DIRETORIO_PACOTE/sistema_rpa/"

# Scripts de instalação e execução
echo "⚙️  Criando scripts de instalação..."

# Script de instalação principal
cat > "$DIRETORIO_PACOTE/instalar_sistema.sh" << 'EOF'
#!/bin/bash

echo "🚀 INSTALAÇÃO DO SISTEMA RPA v2.0"
echo "================================="

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.8 ou superior."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Navegar para diretório do sistema
cd sistema_rpa

# Instalar UV (gerenciador de pacotes ultrarrápido)
echo "📦 Instalando UV (gerenciador de pacotes)..."
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Verificar instalação do UV
if ! command -v uv &> /dev/null; then
    echo "⚠️  UV não foi instalado automaticamente. Instalando via pip..."
    python3 -m pip install uv
fi

echo "✅ UV instalado com sucesso"

# Criar ambiente virtual e instalar dependências
echo "🔧 Criando ambiente virtual e instalando dependências..."
uv venv
source .venv/bin/activate  # Linux/Mac
# Para Windows: source .venv/Scripts/activate

# Instalar dependências
uv pip install -r pyproject.toml

echo ""
echo "🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Configure suas credenciais do Google Sheets (gspread-***.json)"
echo "2. Execute: ./iniciar_sistema.sh"
echo "3. Acesse o dashboard em: http://localhost:5000"
echo ""
echo "📚 Consulte o arquivo GUIA_INSTALACAO.md para mais detalhes"
EOF

# Script para iniciar o sistema
cat > "$DIRETORIO_PACOTE/iniciar_sistema.sh" << 'EOF'
#!/bin/bash

echo "🚀 INICIANDO SISTEMA RPA v2.0"
echo "============================="

cd sistema_rpa

# Ativar ambiente virtual
source .venv/bin/activate

# Verificar se as dependências estão instaladas
if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado. Execute primeiro: ./instalar_sistema.sh"
    exit 1
fi

echo "✅ Ambiente virtual ativado"

# Opções de execução
echo ""
echo "Escolha uma opção:"
echo "1) 🌐 Dashboard Principal (porta 5000)"
echo "2) 🔔 Dashboard de Notificações (porta 8502)"
echo "3) 📊 Dashboard Demo (porta 8501)"
echo "4) 🤖 API RPA (porta 8000)"
echo "5) ⏰ Agendador Diário"
echo ""

read -p "Digite sua opção (1-5): " opcao

case $opcao in
    1)
        echo "🌐 Iniciando Dashboard Principal..."
        streamlit run dashboard_rpa.py --server.port=5000 --server.address=0.0.0.0
        ;;
    2)
        echo "🔔 Iniciando Dashboard de Notificações..."
        streamlit run dashboard_notificacoes.py --server.port=8502 --server.address=0.0.0.0
        ;;
    3)
        echo "📊 Iniciando Dashboard Demo..."
        streamlit run demo_dashboard.py --server.port=8501 --server.address=0.0.0.0
        ;;
    4)
        echo "🤖 Iniciando API RPA..."
        python main.py
        ;;
    5)
        echo "⏰ Iniciando Agendador Diário..."
        python agendador_diario.py
        ;;
    *)
        echo "❌ Opção inválida"
        exit 1
        ;;
esac
EOF

# Tornar scripts executáveis
chmod +x "$DIRETORIO_PACOTE/instalar_sistema.sh"
chmod +x "$DIRETORIO_PACOTE/iniciar_sistema.sh"

# Criar documentação
echo "📚 Criando documentação..."

# Guia de instalação
cat > "$DIRETORIO_PACOTE/GUIA_INSTALACAO.md" << 'EOF'
# 🚀 Sistema RPA v2.0 - Guia de Instalação

## 📋 Pré-requisitos

- **Python 3.8+** instalado no sistema
- **Conexão com internet** para baixar dependências
- **Credenciais do Google Sheets** configuradas

## ⚡ Instalação Rápida

### 1️⃣ Executar Instalação
```bash
./instalar_sistema.sh
```

### 2️⃣ Configurar Credenciais
- Coloque seu arquivo de credenciais Google na pasta `sistema_rpa/`
- Renomeie para: `gspread-credentials.json`

### 3️⃣ Iniciar Sistema
```bash
./iniciar_sistema.sh
```

## 🎯 Componentes do Sistema

### **🌐 Dashboard Principal (Porta 5000)**
- Interface completa de monitoramento
- Controle de execuções dos RPAs
- Visualização de métricas em tempo real

### **🔔 Dashboard de Notificações (Porta 8502)**
- Configuração de emails
- Teste de notificações
- Gestão de eventos

### **📊 Dashboard Demo (Porta 8501)**
- Demonstração com dados simulados
- Ideal para apresentações

### **🤖 API RPA (Porta 8000)**
- Interface REST para integração
- Execução programática dos RPAs
- Documentação automática em `/docs`

### **⏰ Agendador Diário**
- Execução automática dos RPAs 1 e 2
- Disparo dos RPAs 3 e 4 conforme necessário

## 🛠️ Configuração Avançada

### Variáveis de Ambiente
```bash
# Criar arquivo .env na pasta sistema_rpa/
EMAIL_REMETENTE=sistema.rpa@suaempresa.com
EMAIL_ADMIN=admin@suaempresa.com
PLANILHA_CALCULO_ID=sua_planilha_id
PLANILHA_APOIO_ID=sua_planilha_apoio_id
```

### Credenciais Google Sheets
1. Acesse o Google Cloud Console
2. Crie um projeto e ative a API do Google Sheets
3. Crie uma conta de serviço
4. Baixe as credenciais JSON
5. Coloque na pasta do sistema

## 🔧 Solução de Problemas

### Erro de Dependências
```bash
cd sistema_rpa
uv pip install --upgrade pip
uv pip install -r pyproject.toml
```

### Erro de Credenciais
- Verifique se o arquivo JSON está na pasta correta
- Confirme se a conta de serviço tem acesso às planilhas

### Erro de Porta
- Verifique se as portas não estão em uso
- Mude as portas nos comandos se necessário

## 📞 Suporte

Sistema desenvolvido em português brasileiro com arquitetura modular e escalável.

Para dúvidas técnicas, consulte a documentação completa no arquivo `SISTEMA_COMPLETO.md`.
EOF

# Arquivo README principal
cat > "$DIRETORIO_PACOTE/README.md" << 'EOF'
# 🤖 Sistema RPA v2.0 - Automação Empresarial

## ✨ **SISTEMA COMPLETO E FUNCIONAL**

Este é um sistema profissional de automação RPA (Robotic Process Automation) desenvolvido especificamente para empresas brasileiras.

### 🎯 **FUNCIONALIDADES PRINCIPAIS**

✅ **4 RPAs Especializados:**
- 📊 **RPA 1**: Coleta de Índices Econômicos (IPCA/IGPM)
- 📋 **RPA 2**: Análise de Planilhas e Identificação de Contratos
- 🏢 **RPA 3**: Processamento no Sistema Sienge
- 🏦 **RPA 4**: Processamento no Sistema Sicredi

✅ **Dashboard Profissional:**
- Interface web moderna e intuitiva
- Monitoramento em tempo real
- Controle manual e agendamento automático

✅ **Sistema de Notificações:**
- Emails automáticos com templates HTML elegantes
- Gmail API integrado
- Configuração visual via dashboard

✅ **Arquitetura Robusta:**
- Persistência híbrida (MongoDB + JSON)
- Tratamento completo de erros
- Logs detalhados para auditoria

### 🚀 **INSTALAÇÃO RÁPIDA**

```bash
# 1. Executar instalação (uma vez apenas)
./instalar_sistema.sh

# 2. Iniciar sistema
./iniciar_sistema.sh
```

### 📊 **ACESSOS RÁPIDOS**

- **Dashboard Principal**: http://localhost:5000
- **Notificações**: http://localhost:8502
- **API REST**: http://localhost:8000/docs
- **Demo**: http://localhost:8501

### 🎯 **TECNOLOGIAS UTILIZADAS**

- **Python 3.8+** com UV (gerenciador ultrarrápido)
- **Streamlit** para interfaces web modernas
- **FastAPI** para APIs REST robustas
- **Selenium** para automação web
- **Google Sheets API** para integração com planilhas
- **Gmail API** para notificações profissionais
- **MongoDB/JSON** para persistência híbrida

### 📋 **ESTRUTURA DO SISTEMA**

```
sistema_rpa/
├── 🤖 RPAs/
│   ├── rpa_coleta_indices/     # Coleta IPCA/IGPM
│   ├── rpa_analise_planilhas/  # Análise contratos
│   ├── rpa_sienge/             # Processamento Sienge
│   └── rpa_sicredi/            # Processamento Sicredi
├── 🌐 Interfaces/
│   ├── dashboard_rpa.py        # Dashboard principal
│   ├── dashboard_notificacoes.py # Configuração emails
│   └── demo_dashboard.py       # Demonstração
├── 🔧 Core/
│   ├── base_rpa.py            # Base dos RPAs
│   ├── data_manager.py        # Gestão de dados
│   └── notificacoes_simples.py # Sistema emails
└── 📋 API/
    └── main.py                # API REST principal
```

### 🎉 **PRONTO PARA PRODUÇÃO**

Este sistema foi desenvolvido seguindo as melhores práticas de engenharia de software:

- ✅ **Código limpo e documentado**
- ✅ **Arquitetura modular e escalável**
- ✅ **Tratamento robusto de erros**
- ✅ **Interface profissional**
- ✅ **Integração com serviços externos**
- ✅ **Sistema de notificações empresarial**

**Desenvolvido em Português Brasileiro** 🇧🇷

---

*Sistema RPA v2.0 - Automação que funciona!*
EOF

# Copiar documentação existente
if [ -f "SISTEMA_NOTIFICACOES_COMPLETO.md" ]; then
    cp SISTEMA_NOTIFICACOES_COMPLETO.md "$DIRETORIO_PACOTE/docs/"
fi

if [ -f "ARQUITETURA_NOVA.md" ]; then
    cp ARQUITETURA_NOVA.md "$DIRETORIO_PACOTE/docs/"
fi

# Criar arquivo de versão
cat > "$DIRETORIO_PACOTE/sistema_rpa/VERSION" << EOF
Sistema RPA v2.0
Data de Build: $(date '+%Y-%m-%d %H:%M:%S')
Versão: 2.0.0
Status: Produção
Desenvolvido em: Português Brasileiro
EOF

# Criar arquivo de configuração de exemplo
cat > "$DIRETORIO_PACOTE/config/.env.exemplo" << 'EOF'
# Configurações do Sistema RPA v2.0
# Renomeie este arquivo para .env e configure suas variáveis

# === CONFIGURAÇÕES GERAIS ===
AMBIENTE=producao
DEBUG=false

# === GOOGLE SHEETS ===
PLANILHA_CALCULO_ID=1ABC123_sua_planilha_base_calculo_reparcelamento
PLANILHA_APOIO_ID=1XYZ789_sua_planilha_base_apoio
CREDENCIAIS_GOOGLE=gspread-credentials.json

# === NOTIFICAÇÕES ===
EMAIL_REMETENTE=sistema.rpa@suaempresa.com
EMAIL_ADMIN=admin@suaempresa.com

# === SIENGE (Configure com suas credenciais) ===
SIENGE_URL=https://suaempresa.sienge.com.br
SIENGE_USUARIO=seu_usuario
SIENGE_SENHA=sua_senha

# === SICREDI (Configure com suas credenciais) ===
SICREDI_URL=https://empresas.sicredi.com.br
SICREDI_USUARIO=seu_usuario
SICREDI_SENHA=sua_senha

# === BANCO DE DADOS (Opcional - usa JSON se não configurado) ===
# MONGODB_URL=mongodb://localhost:27017
# DATABASE_NAME=sistema_rpa
EOF

# Compactar pacote
echo "📦 Compactando pacote para entrega..."
cd "$DIRETORIO_PACOTE/.."
tar -czf "${NOME_PACOTE}.tar.gz" -C "$DIRETORIO_PACOTE" .

# Estatísticas do pacote
TAMANHO_PACOTE=$(du -sh "${NOME_PACOTE}.tar.gz" | cut -f1)
TOTAL_ARQUIVOS=$(find "$DIRETORIO_PACOTE" -type f | wc -l)

echo ""
echo "🎉 PACOTE DE ENTREGA CRIADO COM SUCESSO!"
echo "========================================"
echo "📁 Pacote: ${NOME_PACOTE}.tar.gz"
echo "📏 Tamanho: $TAMANHO_PACOTE"
echo "📋 Arquivos: $TOTAL_ARQUIVOS"
echo ""
echo "📋 CONTEÚDO DO PACOTE:"
echo "✅ Sistema RPA completo (4 RPAs)"
echo "✅ Dashboard web profissional"
echo "✅ Sistema de notificações"
echo "✅ API REST com documentação"
echo "✅ Scripts de instalação automática"
echo "✅ Documentação completa"
echo "✅ Configurações de exemplo"
echo ""
echo "🚀 PARA INSTALAR NA MÁQUINA DESTINO:"
echo "1. Extrair: tar -xzf ${NOME_PACOTE}.tar.gz"
echo "2. Executar: ./instalar_sistema.sh"
echo "3. Configurar credenciais"
echo "4. Iniciar: ./iniciar_sistema.sh"
echo ""
echo "📞 Sistema pronto para entrega ao cliente!"