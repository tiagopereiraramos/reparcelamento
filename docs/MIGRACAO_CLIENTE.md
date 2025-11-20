# Guia de Migração para Máquina do Cliente

## Visão Geral

Este documento fornece instruções completas para migrar o projeto RPA de reparcelamento para a máquina do cliente, suportando **Linux**, **Windows** e **macOS**.

## Requisitos do Sistema

### Requisitos Mínimos por Sistema Operacional

#### Linux
- **Sistema Operacional**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / RHEL 8+
- **Python**: 3.11 ou superior
- **Espaço em Disco**: Mínimo 2GB livres
- **RAM**: Mínimo 4GB
- **Navegadores**: 
  - Google Chrome (versão mais recente)
  - Firefox (versão mais recente)
- **Dependências do Sistema**:
  ```bash
  # Ubuntu/Debian
  sudo apt-get update
  sudo apt-get install -y python3.11 python3.11-venv python3-pip curl wget
  
  # CentOS/RHEL
  sudo yum install -y python3.11 python3-pip curl wget
  ```

#### Windows
- **Sistema Operacional**: Windows 10/11 (64-bit)
- **Python**: 3.11 ou superior
- **Espaço em Disco**: Mínimo 2GB livres
- **RAM**: Mínimo 4GB
- **Navegadores**: 
  - Google Chrome (versão mais recente)
  - Firefox (versão mais recente)
- **Dependências do Sistema**:
  - PowerShell 5.1+ (já incluído no Windows 10/11)
  - Visual C++ Redistributable (geralmente já instalado)

#### macOS
- **Sistema Operacional**: macOS 11 (Big Sur) ou superior
- **Python**: 3.11 ou superior
- **Espaço em Disco**: Mínimo 2GB livres
- **RAM**: Mínimo 4GB
- **Navegadores**: 
  - Google Chrome (versão mais recente)
  - Firefox (versão mais recente)
- **Dependências do Sistema**:
  ```bash
  # Homebrew (recomendado)
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  brew install python@3.11
  ```

### Versões Necessárias

- **Python**: 3.11 ou superior
- **Chrome**: Versão mais recente (compatível com undetected-chromedriver)
- **Firefox**: Versão mais recente
- **uv**: Versão mais recente (será instalado automaticamente)

### Dependências de Drivers

#### GeckoDriver (Firefox)
- **Linux**: `geckodriver-vX.X.X-linux64.tar.gz`
- **Windows**: `geckodriver-vX.X.X-win64.zip`
- **macOS Intel**: `geckodriver-vX.X.X-macos.tar.gz`
- **macOS ARM (Apple Silicon)**: `geckodriver-vX.X.X-macos-aarch64.tar.gz`

#### ChromeDriver
- Gerenciado automaticamente pelo `undetected-chromedriver`
- Versão compatível detectada automaticamente

### Permissões Necessárias

#### Linux/macOS
- Permissão de escrita no diretório do projeto
- Permissão de execução para scripts
- Permissão para criar arquivos em diretórios de downloads

#### Windows
- Permissões de administrador podem ser necessárias para:
  - Instalar drivers
  - Configurar Task Scheduler
  - Criar variáveis de ambiente do sistema

## Processo de Migração

### Passo 1: Verificação de Pré-requisitos

Execute o script de verificação:

```bash
# Linux/macOS
python3 scripts/verificar_pre_requisitos.py

# Windows
python scripts\verificar_pre_requisitos.py
```

Este script verifica:
- Versão do Python
- Instalação do uv
- Navegadores instalados
- Permissões de diretórios
- Conectividade de rede

### Passo 2: Instalação de Dependências

Execute o script de setup completo:

```bash
# Linux/macOS
bash scripts/setup_completo.sh

# Windows
scripts\setup_completo.bat

# Ou usando Python (recomendado - multiplataforma)
python scripts/setup_completo.py
```

Este script:
- Instala o uv (se necessário)
- Cria ambiente virtual
- Instala todas as dependências
- Configura drivers
- Configura ambiente

### Passo 3: Configuração de Credenciais

Execute o script interativo de configuração:

```bash
python scripts/configurar_ambiente.py
```

Este script guia você através da:
- Criação do arquivo `.env`
- Configuração de variáveis de ambiente
- Validação de credenciais
- Cópia de arquivos de credenciais

### Passo 4: Validação de Instalação

Execute o script de teste:

```bash
python scripts/testar_instalacao.py
```

Este script valida:
- Instalação de dependências
- Configuração de drivers
- Conexões com serviços externos
- Execução de scripts principais

### Passo 5: Configuração de Agendamento

Execute o script de configuração de agendamento:

```bash
# Linux/macOS (cron)
bash scripts/configurar_cron.sh

# Windows (Task Scheduler)
powershell -ExecutionPolicy Bypass -File scripts\configurar_taskscheduler.ps1

# Ou usando Python (recomendado - detecta SO automaticamente)
python scripts/configurar_agendamento.py
```

## Diferenças entre Plataformas

### Caminhos de Arquivos

#### Linux/macOS
- Ambiente virtual: `.venv/bin/activate`
- Downloads: `~/Downloads/RPA_DOWNLOADS`
- Scripts: `scripts/nome_script.sh`

#### Windows
- Ambiente virtual: `.venv\Scripts\activate`
- Downloads: `C:\Users\<usuario>\Downloads\RPA_DOWNLOADS`
- Scripts: `scripts\nome_script.bat`

### Agendamento

#### Linux/macOS
- Usa **cron** para agendamento
- Arquivo de cron: `/etc/crontab` ou `crontab -e`
- Variáveis de ambiente configuradas no próprio cron

#### Windows
- Usa **Task Scheduler** para agendamento
- Interface gráfica ou PowerShell
- Variáveis de ambiente configuradas nas propriedades da tarefa

### Execução de Scripts

#### Linux/macOS
```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Executar script
python scripts/main_coleta_indices.py
```

#### Windows
```cmd
# Ativar ambiente virtual
.venv\Scripts\activate

# Executar script
python scripts\main_coleta_indices.py
```

#### Usando uv (multiplataforma)
```bash
# Não precisa ativar ambiente virtual
uv run python scripts/main_coleta_indices.py
```

## Troubleshooting

### Problemas Comuns

#### 1. Driver não encontrado
**Solução**: Execute `python scripts/configurar_chrome_driver.py` para configurar drivers automaticamente.

#### 2. Variáveis de ambiente não carregadas
**Solução**: Verifique se o arquivo `.env` existe na raiz do projeto e execute `python scripts/validar_credenciais.py`.

#### 3. Agendamento não funciona
**Solução**: 
- Linux/macOS: Verifique permissões do cron e caminhos absolutos
- Windows: Verifique se a tarefa está habilitada no Task Scheduler

#### 4. Erro de permissões
**Solução**: 
- Linux/macOS: `chmod +x scripts/*.sh`
- Windows: Execute como administrador se necessário

### Logs e Diagnóstico

Os logs são salvos em:
- `logs/` - Logs de execução
- `outputs/` - Arquivos gerados
- `dados_processamento/` - Dados de processamento

Para diagnóstico detalhado:
```bash
python scripts/verificar_pre_requisitos.py --verbose
python scripts/testar_instalacao.py --verbose
```

## Checklist de Migração

- [ ] Pré-requisitos verificados
- [ ] Python 3.11+ instalado
- [ ] Chrome e Firefox instalados
- [ ] Dependências instaladas com uv
- [ ] Drivers configurados (Firefox e Chrome)
- [ ] Arquivo `.env` criado e configurado
- [ ] Credenciais validadas
- [ ] Agendamento configurado
- [ ] Testes de instalação passaram
- [ ] Scripts principais executáveis
- [ ] Documentação revisada

## Suporte

Para problemas durante a migração:
1. Consulte `docs/GUIA_RAPIDO_MIGRACAO.md`
2. Execute scripts de diagnóstico
3. Verifique logs em `logs/`
4. Consulte `docs/AGENDAMENTO.md` para problemas de agendamento

