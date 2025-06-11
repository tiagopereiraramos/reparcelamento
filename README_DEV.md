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
