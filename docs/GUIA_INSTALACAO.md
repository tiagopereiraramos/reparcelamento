# 🚀 Guia de Instalação - Sistema RPA v2.0

**Instalação simplificada para todas as plataformas**

---

## 📋 Pré-requisitos

### Sistema Operacional
- **Windows**: 10 ou 11 (64-bit)
- **macOS**: 10.15 (Catalina) ou superior
- **Linux**: Ubuntu 18.04+ / CentOS 8+ / Debian 10+

### Software Necessário
- **Python**: 3.8, 3.9, 3.10 ou 3.11
- **Google Chrome**: Instalado e atualizado
- **Conexão Internet**: Para download de dependências

### Recursos do Sistema
- **RAM**: Mínimo 4GB, recomendado 8GB
- **Disco**: 2GB de espaço livre
- **Processador**: Dual-core 2GHz ou superior

---

## 🎯 Escolha Sua Versão

### 📦 **Versão Produção** (Cliente Final)
- Sistema completo e otimizado
- Instalação automática
- Pronto para uso imediato

### 🛠️ **Versão Desenvolvedor** (Mac/Linux)
- Configurações VSCode incluídas
- Debug individual de RPAs
- Modo homologação para testes

---

## 🍎 Instalação no macOS

### Versão Desenvolvedor (Recomendada)

```bash
# 1. Extrair pacote
tar -xzf sistema_rpa_dev_*.tar.gz
cd sistema_rpa_dev_*

# 2. Executar instalação automática
./instalar_dev.sh

# 3. Abrir no VSCode
code .
```

### Versão Produção

```bash
# 1. Extrair pacote
tar -xzf sistema_rpa_v2_*.tar.gz
cd sistema_rpa

# 2. Instalar sistema
./instalar_sistema.sh

# 3. Iniciar
./iniciar_sistema.sh
```

### Instalação Manual (se necessário)

```bash
# 1. Instalar UV (gerenciador ultrarrápido)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Recarregar terminal
source ~/.zshrc

# 3. Criar ambiente virtual
uv venv

# 4. Ativar ambiente
source .venv/bin/activate

# 5. Instalar dependências
uv pip install -r pyproject.toml

# 6. Testar instalação
python teste_sistema_refatorado.py
```

---

## 🐧 Instalação no Linux

### Ubuntu/Debian

```bash
# 1. Atualizar sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar Python e dependências
sudo apt install python3 python3-pip python3-venv curl -y

# 3. Instalar Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable -y

# 4. Extrair e instalar RPA
tar -xzf sistema_rpa_v2_*.tar.gz
cd sistema_rpa
./instalar_sistema.sh
```

### CentOS/RHEL

```bash
# 1. Instalar dependências
sudo yum install python3 python3-pip curl -y

# 2. Instalar Google Chrome
sudo yum install -y wget
wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
sudo yum localinstall google-chrome-stable_current_x86_64.rpm -y

# 3. Continuar com instalação padrão
tar -xzf sistema_rpa_v2_*.tar.gz
cd sistema_rpa
./instalar_sistema.sh
```

---

## 🪟 Instalação no Windows

### Usando WSL (Recomendado)

```powershell
# 1. Instalar WSL
wsl --install

# 2. Reiniciar e configurar Ubuntu
# 3. Seguir instruções do Linux acima
```

### Instalação Nativa (PowerShell)

```powershell
# 1. Instalar Python (se não instalado)
# Baixar de python.org e instalar

# 2. Verificar instalação
python --version

# 3. Extrair pacote (usar 7-Zip ou similar)
# 4. Abrir PowerShell na pasta do sistema

# 5. Criar ambiente virtual
python -m venv .venv

# 6. Ativar ambiente
.\.venv\Scripts\activate

# 7. Instalar UV
pip install uv

# 8. Instalar dependências
uv pip install -r pyproject.toml

# 9. Testar
python teste_sistema_refatorado.py
```

---

## 🔑 Configuração de Credenciais

### 1. Google Sheets API

#### Passo a Passo
1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um novo projeto ou selecione existente
3. Vá para **APIs & Services** → **Library**
4. Busque e ative **Google Sheets API**
5. Vá para **APIs & Services** → **Credentials**
6. Clique **Create Credentials** → **Service Account**
7. Preencha nome e descrição
8. Baixe o arquivo JSON
9. Renomeie para `gspread-credentials.json`
10. Coloque na pasta raiz do sistema

#### Permissões Necessárias
- Compartilhe suas planilhas Google com o email da conta de serviço
- Permissão de **Editor** é necessária

### 2. Arquivo .env

Crie arquivo `.env` na pasta raiz:

```env
# Google Sheets (obrigatório)
GOOGLE_CREDENTIALS_PATH=./gspread-credentials.json

# Sienge ERP (configure conforme sua empresa)
SIENGE_URL=https://sua-empresa.sienge.com.br
SIENGE_USERNAME=seu_usuario_sienge
SIENGE_PASSWORD=sua_senha_sienge

# Sicredi (configure com suas credenciais)
SICREDI_URL=https://empresas.sicredi.com.br
SICREDI_USERNAME=seu_usuario_sicredi
SICREDI_PASSWORD=sua_senha_sicredi

# Notificações Gmail (opcional)
GMAIL_CREDENTIALS_PATH=./gmail-credentials.json

# MongoDB (opcional - sistema funciona sem)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=sistema_rpa

# Configurações gerais
DEBUG_MODE=false
PYTHONPATH=.
```

### 3. Gmail API (Opcional - para notificações)

#### Se quiser usar Gmail para enviar emails:
1. No Google Cloud Console, ative **Gmail API**
2. Configure OAuth 2.0 credentials
3. Baixe como `gmail-credentials.json`
4. Configure no dashboard de notificações

---

## ✅ Verificação da Instalação

### Testes Básicos

```bash
# 1. Testar sistema completo
python teste_sistema_refatorado.py

# 2. Testar conexão Google Sheets
python -c "import gspread; print('Google Sheets OK')"

# 3. Testar Selenium
python -c "from selenium import webdriver; print('Selenium OK')"

# 4. Iniciar dashboard
streamlit run dashboard_rpa.py --server.port=5000
```

### Verificar URLs

Após iniciar, verifique se consegue acessar:
- **Dashboard Principal**: http://localhost:5000
- **Dashboard Notificações**: http://localhost:8502
- **API REST**: http://localhost:8000/docs

### Logs de Instalação

Em caso de problemas, verifique:
- **Logs gerais**: `logs/sistema_rpa.log`
- **Erros Python**: Mensagens no terminal
- **Chrome/Selenium**: `logs/browser.log`

---

## 🔧 Solução de Problemas

### Erro: "Python não encontrado"
```bash
# Verificar instalação
python --version
python3 --version

# Instalar se necessário (Ubuntu)
sudo apt install python3 python3-pip
```

### Erro: "Google Chrome não encontrado"
```bash
# Verificar instalação
google-chrome --version

# Instalar se necessário
# Ver seções específicas por OS acima
```

### Erro: "Permissão negada" (Linux/Mac)
```bash
# Dar permissão aos scripts
chmod +x instalar_sistema.sh
chmod +x iniciar_sistema.sh
chmod +x scripts/*.sh
```

### Erro: "UV não encontrado"
```bash
# Instalar UV manualmente
pip install uv

# Ou via curl (Linux/Mac)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Erro: "Porta em uso"
```bash
# Verificar portas ocupadas
lsof -i :5000  # Dashboard
lsof -i :8000  # API
lsof -i :8502  # Notificações

# Parar processos se necessário
kill -9 <PID>
```

---

## 🚀 Próximos Passos

Após instalação bem-sucedida:

1. **Configure credenciais** (Google Sheets obrigatório)
2. **Teste sistema** com `python teste_sistema_refatorado.py`
3. **Acesse dashboard** em http://localhost:5000
4. **Configure notificações** em http://localhost:8502
5. **Leia o manual** em `docs/MANUAL_SISTEMA_RPA.md`

---

## 📞 Ajuda

### Arquivos de Configuração
- **pyproject.toml**: Dependências Python
- **.env**: Configurações do sistema
- **gspread-credentials.json**: Credenciais Google

### Logs Importantes
- **logs/**: Todos os logs do sistema
- **Terminal**: Mensagens de erro em tempo real

### Comandos Úteis
```bash
# Reinstalar dependências
uv pip install --force-reinstall -r pyproject.toml

# Limpar cache
./scripts/clean_system.sh

# Backup configurações
cp .env .env.backup
cp gspread-credentials.json gspread-credentials.json.backup
```

---

**🎯 Instalação concluída! Sistema RPA pronto para automação.**