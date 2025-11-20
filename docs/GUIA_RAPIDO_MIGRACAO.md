# Guia Rápido de Migração

## Checklist Rápido

### Pré-Migração

- [ ] Python 3.11+ instalado
- [ ] Chrome e Firefox instalados
- [ ] Acesso ao repositório do projeto
- [ ] Credenciais disponíveis (Google, Sienge, Sicredi, SendGrid)

### Migração

1. **Clone o repositório:**
```bash
git clone <repositorio>
cd reparcelamento
```

2. **Execute setup completo:**
```bash
python scripts/setup_completo.py
```

3. **Configure credenciais:**
```bash
python scripts/configurar_ambiente.py
```

4. **Valide credenciais:**
```bash
python scripts/validar_credenciais.py
```

5. **Teste instalação:**
```bash
python scripts/testar_instalacao.py
```

6. **Configure agendamento:**
```bash
python scripts/configurar_agendamento.py
```

## Comandos Essenciais

### Verificação

```bash
# Verificar pré-requisitos
python scripts/verificar_pre_requisitos.py

# Validar credenciais
python scripts/validar_credenciais.py

# Testar instalação
python scripts/testar_instalacao.py
```

### Setup

```bash
# Setup completo
python scripts/setup_completo.py

# Apenas UV
python scripts/setup_uv.py

# Apenas dependências
python scripts/instalar_dependencias.py

# Configurar drivers
python scripts/configurar_chrome_driver.py
```

### Configuração

```bash
# Configurar ambiente interativo
python scripts/configurar_ambiente.py

# Configurar agendamento
python scripts/configurar_agendamento.py
```

### Execução Manual

```bash
# Usando uv (recomendado)
uv run python scripts/main_coleta_indices.py

# Usando ambiente virtual
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
python scripts/main_coleta_indices.py
```

## Solução de Problemas Comuns

### Problema: "Python não encontrado"

**Solução:**
```bash
# Verificar instalação
python3 --version
# ou
python --version

# Instalar Python 3.11+
# Linux: sudo apt-get install python3.11
# macOS: brew install python@3.11
# Windows: Baixar de python.org
```

### Problema: "uv não encontrado"

**Solução:**
```bash
# Instalar uv
python scripts/setup_uv.py
# ou manualmente
pip install uv
```

### Problema: "Chrome/Firefox não encontrado"

**Solução:**
- **Linux**: `sudo apt-get install google-chrome-stable firefox`
- **macOS**: Instalar via Homebrew ou download direto
- **Windows**: Baixar e instalar dos sites oficiais

### Problema: "Drivers não funcionam"

**Solução:**
```bash
# Configurar drivers
python scripts/configurar_chrome_driver.py

# Verificar versão do Chrome
google-chrome --version  # Linux/macOS
# Windows: Verificar em Settings > About
```

### Problema: "Credenciais inválidas"

**Solução:**
```bash
# Reconfigurar
python scripts/configurar_ambiente.py

# Validar
python scripts/validar_credenciais.py
```

### Problema: "Agendamento não funciona"

**Solução:**
```bash
# Testar agendamento
python scripts/testar_agendamento.py

# Reconfigurar
python scripts/configurar_agendamento.py
```

## Estrutura de Diretórios

```
reparcelamento/
├── .env                    # Credenciais (NÃO commitar!)
├── .venv/                  # Ambiente virtual
├── credentials/            # Credenciais Google
├── scripts/               # Scripts principais
├── core/                  # Módulos core
├── rpa_*/                 # Módulos RPA
├── data/                  # Dados de processamento
├── logs/                  # Logs de execução
└── outputs/               # Arquivos gerados
```

## Diferenças por Sistema Operacional

### Linux/macOS

- Ambiente virtual: `.venv/bin/activate`
- Agendamento: `crontab -e`
- Permissões: `chmod +x scripts/*.py`

### Windows

- Ambiente virtual: `.venv\Scripts\activate`
- Agendamento: Task Scheduler
- Execução: `python scripts\script.py`

## Próximos Passos Após Migração

1. **Testar execução manual:**
```bash
uv run python scripts/main_coleta_indices.py --teste
```

2. **Verificar logs:**
```bash
ls -la logs/
tail -f logs/cron.log  # Linux/macOS
```

3. **Configurar notificações:**
- Verificar configuração do SendGrid
- Testar envio de e-mails

4. **Documentar alterações:**
- Anotar diferenças de configuração
- Documentar problemas encontrados

## Contatos de Suporte

Para problemas durante a migração:

1. Consulte `docs/MIGRACAO_CLIENTE.md` para guia completo
2. Consulte `docs/AGENDAMENTO.md` para problemas de agendamento
3. Consulte `docs/SEGURANCA_CREDENCIAIS.md` para problemas de credenciais
4. Verifique logs em `logs/`

## Referências Rápidas

- **Documentação completa**: `docs/MANUAL_COMPLETO_PROJETO.md`
- **Migração detalhada**: `docs/MIGRACAO_CLIENTE.md`
- **Agendamento**: `docs/AGENDAMENTO.md`
- **Segurança**: `docs/SEGURANCA_CREDENCIAIS.md`

