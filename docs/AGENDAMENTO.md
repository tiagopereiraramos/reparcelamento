# Guia de Agendamento

## Visão Geral

Este projeto utiliza agendamento para executar scripts automaticamente em horários específicos. O sistema de agendamento varia conforme o sistema operacional:

- **Linux/macOS**: Usa **cron**
- **Windows**: Usa **Task Scheduler**

## Scripts Agendados

### Etapa 1 (11º dia do mês)

1. **Coleta de Índices** (`scripts/main_coleta_indices.py`)
   - Horário: 9h00
   - Descrição: Coleta índices IPCA e IGPM

2. **Análise de Planilhas** (`scripts/main_analise_planilhas.py`)
   - Horário: 10h00
   - Descrição: Análise de planilhas e geração de fila

### Etapa 2 (16º dia do mês)

3. **Extração Sienge** (`scripts/main_extracao_relatorio_sienge.py`)
   - Horário: 9h00
   - Descrição: Extração de relatórios do Sienge

4. **Reparcelamento Sienge** (`scripts/main_reparcelamento_sienge.py`)
   - Horário: 10h00
   - Descrição: Execução de reparcelamentos

5. **Sicredi** (`scripts/main_sicredi.py`)
   - Horário: 11h00
   - Descrição: Importação de arquivos no Sicredi

## Configuração no Linux/macOS (Cron)

### Método Automático

Execute o script de configuração:

```bash
python scripts/configurar_agendamento.py
```

Este script irá:
- Gerar entradas de cron apropriadas
- Adicionar ao crontab do usuário
- Configurar variáveis de ambiente

### Método Manual

1. Edite o crontab:
```bash
crontab -e
```

2. Adicione as entradas (ajuste os caminhos):
```cron
# RPA Reparcelamento - Coleta de Índices (11º dia às 9h)
0 9 11 * * cd /caminho/para/projeto && /usr/bin/python3 scripts/executar_agendado.py scripts/main_coleta_indices.py >> logs/cron.log 2>&1

# RPA Reparcelamento - Análise de Planilhas (11º dia às 10h)
0 10 11 * * cd /caminho/para/projeto && /usr/bin/python3 scripts/executar_agendado.py scripts/main_analise_planilhas.py >> logs/cron.log 2>&1

# RPA Reparcelamento - Extração Sienge (16º dia às 9h)
0 9 16 * * cd /caminho/para/projeto && /usr/bin/python3 scripts/executar_agendado.py scripts/main_extracao_relatorio_sienge.py >> logs/cron.log 2>&1

# RPA Reparcelamento - Reparcelamento Sienge (16º dia às 10h)
0 10 16 * * cd /caminho/para/projeto && /usr/bin/python3 scripts/executar_agendado.py scripts/main_reparcelamento_sienge.py >> logs/cron.log 2>&1

# RPA Reparcelamento - Sicredi (16º dia às 11h)
0 11 16 * * cd /caminho/para/projeto && /usr/bin/python3 scripts/executar_agendado.py scripts/main_sicredi.py >> logs/cron.log 2>&1
```

**Importante**: Use caminhos absolutos para o Python e para o diretório do projeto.

### Usando uv run

Se estiver usando uv, ajuste os comandos:

```cron
0 9 11 * * cd /caminho/para/projeto && uv run python scripts/main_coleta_indices.py >> logs/cron.log 2>&1
```

## Configuração no Windows (Task Scheduler)

### Método Manual (Recomendado)

1. Abra o **Task Scheduler** (`taskschd.msc`)

2. Clique em **Create Basic Task** ou **Create Task**

3. Para cada script, configure:

   **General Tab:**
   - Name: `RPA - Coleta de Índices` (ou nome apropriado)
   - Description: Descrição do script
   - Run whether user is logged on or not: ✅
   - Run with highest privileges: ✅ (se necessário)

   **Triggers Tab:**
   - New Trigger
   - Begin the task: `On a schedule`
   - Settings: `Monthly`
   - Months: `All months`
   - Days: `11` (ou `16` conforme o script)
   - Time: `09:00:00` (ajuste conforme necessário)
   - Enabled: ✅

   **Actions Tab:**
   - Action: `Start a program`
   - Program/script: `C:\caminho\para\python.exe` (ou `uv.exe`)
   - Add arguments: `scripts\executar_agendado.py scripts\main_coleta_indices.py`
   - Start in: `C:\caminho\para\projeto`

   **Conditions Tab:**
   - Start the task only if the computer is on AC power: ❌ (desmarque se necessário)
   - Wake the computer to run this task: ❌

   **Settings Tab:**
   - Allow task to be run on demand: ✅
   - Run task as soon as possible after a scheduled start is missed: ✅
   - If the task fails, restart every: `10 minutes`
   - Attempt to restart up to: `3 times`

4. Repita para todos os scripts

### Variáveis de Ambiente no Windows

Para garantir que as variáveis de ambiente sejam carregadas:

1. Na aba **Actions**, adicione no campo **Add arguments**:
```
scripts\executar_agendado.py scripts\main_coleta_indices.py
```

2. O script `executar_agendado.py` carrega automaticamente o arquivo `.env`

3. Alternativamente, configure variáveis de ambiente do sistema:
   - Abra **System Properties** > **Environment Variables**
   - Adicione as variáveis necessárias

## Wrapper de Execução

O script `scripts/executar_agendado.py` é um wrapper que:

- Carrega variáveis de ambiente do arquivo `.env`
- Ativa o ambiente virtual automaticamente
- Executa o script solicitado
- Registra logs
- Trata erros

**Uso:**
```bash
python scripts/executar_agendado.py <script> [args...]
```

**Exemplo:**
```bash
python scripts/executar_agendado.py scripts/main_coleta_indices.py
```

## Testando Agendamento

Execute o script de teste:

```bash
python scripts/testar_agendamento.py
```

Este script valida:
- Variáveis de ambiente
- Caminhos
- Executabilidade dos scripts

## Troubleshooting

### Problema: Script não executa no cron

**Soluções:**
1. Verifique se o caminho do Python está correto: `which python3`
2. Use caminhos absolutos no crontab
3. Verifique permissões de execução: `chmod +x scripts/*.py`
4. Verifique logs em `logs/cron.log`

### Problema: Variáveis de ambiente não carregadas

**Soluções:**
1. Use o wrapper `executar_agendado.py` que carrega `.env` automaticamente
2. Configure variáveis no próprio crontab:
```cron
0 9 11 * * export VAR=valor && cd /caminho && python script.py
```

### Problema: Task Scheduler não executa

**Soluções:**
1. Verifique se a tarefa está habilitada
2. Verifique o histórico de execução no Task Scheduler
3. Execute manualmente para testar
4. Verifique permissões do usuário
5. Verifique se o Python está no PATH do sistema

### Problema: Scripts falham silenciosamente

**Soluções:**
1. Redirecione saída para arquivo de log:
```cron
>> logs/cron.log 2>&1
```

2. Adicione logging no script
3. Execute manualmente para ver erros

## Manutenção

### Atualizar Agendamentos

Para atualizar agendamentos:

1. **Linux/macOS**: Edite crontab (`crontab -e`)
2. **Windows**: Edite tarefas no Task Scheduler

### Remover Agendamentos

1. **Linux/macOS**: Remova linhas do crontab
2. **Windows**: Delete tarefas no Task Scheduler

### Verificar Status

1. **Linux/macOS**: `crontab -l` para listar
2. **Windows**: Abra Task Scheduler e veja tarefas ativas

## Logs

Os logs de execução agendada são salvos em:
- `logs/cron.log` (Linux/macOS)
- Logs individuais em `logs/` (Windows)

Verifique regularmente os logs para identificar problemas.

