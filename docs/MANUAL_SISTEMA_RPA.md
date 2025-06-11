# 📖 Manual Completo - Sistema RPA v2.0

**Guia definitivo para operação do Sistema RPA de Reparcelamento**

---

## 📋 Índice

1. [Visão Geral do Sistema](#-visão-geral-do-sistema)
2. [Instalação e Configuração](#-instalação-e-configuração)
3. [Operação dos RPAs](#-operação-dos-rpas)
4. [Dashboard e Monitoramento](#-dashboard-e-monitoramento)
5. [Sistema de Notificações](#-sistema-de-notificações)
6. [Troubleshooting](#-troubleshooting)
7. [Manutenção](#-manutenção)

---

## 🎯 Visão Geral do Sistema

### Objetivo
O Sistema RPA v2.0 automatiza o processo completo de reparcelamento financeiro, desde a coleta de índices econômicos até a atualização de carnês bancários.

### Fluxo de Trabalho
```
RPA 1: Coleta Índices (IPCA/IGPM)
    ↓
RPA 2: Análise de Planilhas → Identifica contratos
    ↓ (Se houver contratos)
RPA 3: Processamento Sienge → Calcula reparcelamento
    ↓
RPA 4: Atualização Sicredi → Gera novos carnês
```

### Componentes Principais
- **4 RPAs Automatizados**: Cada um com função específica
- **Dashboard Web**: Interface de monitoramento e controle
- **API REST**: Para integrações externas
- **Sistema de Notificações**: Alertas automáticos por email
- **Persistência Híbrida**: MongoDB + JSON (funciona offline)

---

## 🚀 Instalação e Configuração

### Requisitos do Sistema
- **Sistema Operacional**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Python**: 3.8 ou superior
- **Navegador**: Google Chrome (instalado automaticamente)
- **Memória RAM**: Mínimo 4GB, recomendado 8GB
- **Espaço em Disco**: 2GB livres

### Instalação Automática

#### Para Produção (Cliente Final)
```bash
# 1. Extrair pacote
tar -xzf sistema_rpa_v2_*.tar.gz
cd sistema_rpa

# 2. Executar instalação automática
./instalar_sistema.sh

# 3. Configurar credenciais (ver seção abaixo)

# 4. Iniciar sistema
./iniciar_sistema.sh
```

#### Para Desenvolvimento (Mac/Linux)
```bash
# 1. Extrair pacote desenvolvedor
tar -xzf sistema_rpa_dev_*.tar.gz
cd sistema_rpa_dev_*

# 2. Instalar dependências
./instalar_dev.sh

# 3. Abrir no VSCode
code .
# Pressione F5 para debugar RPAs individuais
```

### Configuração de Credenciais

#### Google Sheets API
1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um projeto ou selecione existente
3. Ative a **Google Sheets API**
4. Crie credenciais de **Conta de Serviço**
5. Baixe o arquivo JSON
6. Salve como `gspread-credentials.json` na pasta do sistema

#### Variáveis de Ambiente
Crie arquivo `.env` na raiz do projeto:
```env
# Google Sheets
GOOGLE_CREDENTIALS_PATH=./gspread-credentials.json

# Sienge (ERP)
SIENGE_URL=https://sua-empresa.sienge.com.br
SIENGE_USERNAME=seu_usuario
SIENGE_PASSWORD=sua_senha

# Sicredi (Banco)
SICREDI_URL=https://empresas.sicredi.com.br
SICREDI_USERNAME=seu_usuario
SICREDI_PASSWORD=sua_senha

# Notificações Gmail (opcional)
GMAIL_CREDENTIALS_PATH=./gmail-credentials.json

# MongoDB (opcional - usa JSON se não configurado)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=sistema_rpa
```

---

## 🤖 Operação dos RPAs

### RPA 1 - Coleta de Índices Econômicos

**Função**: Coleta valores atualizados de IPCA e IGPM de fontes oficiais

**Execução**: 
- **Automática**: Diariamente às 9:00
- **Manual**: Via dashboard ou API

**Fontes de Dados**:
- IPCA: Portal do IBGE
- IGPM: Portal da FGV

**Resultado**: Planilha Google Sheets atualizada com índices

**Tempo Médio**: 5-10 minutos

#### Operação Manual
```bash
# Via linha de comando
python rpa_coleta_indices/teste_coleta_indices.py

# Via API REST
curl -X POST "http://localhost:8000/rpa/coleta-indices" \
  -H "Content-Type: application/json" \
  -d '{"planilha_id": "1abc123..."}'
```

### RPA 2 - Análise de Planilhas

**Função**: Analisa planilhas e identifica contratos que precisam de reparcelamento

**Entrada**: 
- Planilha "BASE DE CÁLCULO REPARCELAMENTO"
- Planilha "Base de apoio"

**Processo**:
1. Lê dados das planilhas Google Sheets
2. Aplica regras de negócio para identificar contratos
3. Calcula valores de reparcelamento
4. Gera fila de processamento

**Resultado**: Lista de contratos para processamento

**Tempo Médio**: 10-15 minutos

#### Critérios de Identificação
- Contratos com atraso > 90 dias
- Valor em aberto > R$ 1.000,00
- Cliente não em processo judicial
- Última tentativa de cobrança > 30 dias

### RPA 3 - Processamento Sienge

**Função**: Processa reparcelamentos no sistema ERP Sienge

**Entrada**: Lista de contratos do RPA 2

**Processo**:
1. Faz login no sistema Sienge
2. Para cada contrato:
   - Localiza o contrato no sistema
   - Aplica índices de correção (IPCA/IGPM)
   - Calcula novo valor parcelado
   - Gera arquivo de remessa bancária
3. Salva dados para próxima etapa

**Resultado**: Arquivo de remessa para o banco

**Tempo Médio**: 20-30 minutos (depende da quantidade)

#### Configurações Importantes
- **Timeout de login**: 30 segundos
- **Intervalo entre contratos**: 5 segundos
- **Máximo de tentativas**: 3 por contrato

### RPA 4 - Processamento Sicredi

**Função**: Atualiza carnês bancários no sistema Sicredi

**Entrada**: Arquivo de remessa do RPA 3

**Processo**:
1. Faz login no portal Sicredi
2. Envia arquivo de remessa
3. Confirma processamento
4. Baixa comprovantes
5. Atualiza status dos contratos

**Resultado**: Carnês atualizados e comprovantes salvos

**Tempo Médio**: 15-25 minutos

---

## 💻 Dashboard e Monitoramento

### Dashboard Principal
**URL**: `http://localhost:5000`

#### Abas Disponíveis

##### 🏠 Visão Geral
- Status atual dos 4 RPAs
- Última execução de cada RPA
- Métricas de performance
- Alertas e notificações

##### ⏰ Agendamentos
- Configuração de horários automáticos
- Ativação/desativação de RPAs
- Histórico de agendamentos

##### ▶️ Execuções Ativas
- RPAs em execução no momento
- Progresso em tempo real
- Logs de execução
- Opção de parar execuções

##### 📊 Histórico
- Todas as execuções passadas
- Filtros por data, RPA, status
- Detalhes de cada execução
- Download de relatórios

##### 🔔 Notificações
- Configuração de emails
- Tipos de alertas
- Teste de envio
- Histórico de notificações

### API REST
**URL**: `http://localhost:8000`

#### Endpoints Principais
```bash
# Status geral
GET /health

# Executar workflow completo
POST /workflow/reparcelamento

# Executar RPA individual
POST /rpa/coleta-indices
POST /rpa/analise-planilhas  
POST /rpa/sienge
POST /rpa/sicredi

# Consultar execuções
GET /execucoes
GET /execucoes/{id}

# Limpar execuções
DELETE /execucoes
DELETE /execucoes/{id}
```

#### Documentação Automática
Acesse `http://localhost:8000/docs` para ver a documentação interativa da API.

---

## 📧 Sistema de Notificações

### Configuração de Emails

#### Dashboard de Notificações
**URL**: `http://localhost:8502`

1. **Configurar Emails**: Adicione destinatários para cada tipo de evento
2. **Tipos de Evento**:
   - RPA concluído com sucesso
   - RPA com erro
   - Workflow completo finalizado
   - Índices econômicos atualizados
   - Contratos identificados para reparcelamento

3. **Testar Envios**: Função para validar configuração

#### Tipos de Notificação

##### ✅ Sucesso de RPA
- Enviado quando RPA termina sem erros
- Inclui tempo de execução e resultados
- Template HTML profissional

##### ❌ Erro de RPA  
- Enviado quando ocorre falha
- Inclui detalhes do erro e logs
- Sugestões de solução

##### 🔄 Workflow Completo
- Enviado ao final dos 4 RPAs
- Resumo completo da execução
- Estatísticas consolidadas

##### 📊 Índices Atualizados
- Notifica sobre novos valores IPCA/IGPM
- Comparação com valores anteriores

##### 📋 Contratos Identificados
- Lista contratos encontrados para reparcelamento
- Valores e prazos envolvidos

### Configuração Gmail API (Opcional)

Para usar Gmail como servidor de email:

1. Vá para [Google Cloud Console](https://console.cloud.google.com)
2. Ative a **Gmail API**
3. Configure OAuth 2.0
4. Baixe credenciais como `gmail-credentials.json`
5. Configure no dashboard de notificações

---

## 🔧 Troubleshooting

### Problemas Comuns

#### ❌ "Credenciais Google inválidas"
**Solução**:
1. Verifique se arquivo `gspread-credentials.json` existe
2. Confirme se a API está ativada no Google Cloud
3. Verifique permissões da conta de serviço
4. Teste com planilha compartilhada

#### ❌ "Erro de conexão com Sienge/Sicredi"
**Solução**:
1. Verifique credenciais no arquivo `.env`
2. Teste login manual nos sistemas
3. Confirme se URLs estão corretas
4. Verifique firewall e proxy

#### ❌ "Browser não inicializa"
**Solução**:
1. Instale Google Chrome
2. Execute: `python -c "from selenium import webdriver; webdriver.Chrome()"`
3. Verifique permissões do sistema
4. Em servidores, use modo headless

#### ❌ "MongoDB não conecta"
**Solução**:
- Sistema funciona sem MongoDB (usa JSON)
- Para usar MongoDB: instale e configure conexão
- Verifique string de conexão no `.env`

#### ❌ "Notificações não enviam"
**Solução**:
1. Teste configuração no dashboard
2. Verifique credenciais Gmail
3. Confirme configuração de SMTP
4. Verifique logs de erro

### Logs do Sistema

#### Localização
- **Logs gerais**: `logs/sistema_rpa.log`
- **Logs por RPA**: `logs/rpa_[nome].log`
- **Logs de notificação**: `logs/notificacoes.log`

#### Níveis de Log
- **INFO**: Operações normais
- **WARNING**: Situações que merecem atenção
- **ERROR**: Erros que impedem funcionamento
- **DEBUG**: Detalhes técnicos (modo desenvolvimento)

### Comandos de Diagnóstico

```bash
# Testar sistema completo
python teste_sistema_refatorado.py

# Testar RPA individual
python rpa_coleta_indices/teste_coleta_indices.py

# Testar notificações
python scripts/testar_notificacoes.py

# Limpar logs antigos
./scripts/clean_system.sh
```

---

## 🛠️ Manutenção

### Manutenção Preventiva

#### Diária
- ✅ Verificar execução automática dos RPAs 1 e 2
- ✅ Revisar logs de erro
- ✅ Confirmar recebimento de notificações

#### Semanal  
- ✅ Limpar logs antigos (`./scripts/clean_system.sh`)
- ✅ Verificar espaço em disco
- ✅ Testar backup das configurações
- ✅ Atualizar credenciais se necessário

#### Mensal
- ✅ Revisar performance dos RPAs
- ✅ Atualizar dependências Python (`uv pip install --upgrade`)
- ✅ Verificar atualizações do Chrome
- ✅ Backup completo do sistema

### Backup e Restauração

#### Arquivos Importantes para Backup
```bash
# Credenciais
gspread-credentials.json
gmail-credentials.json
.env

# Configurações
logs/
dados/
core/configuracoes.json

# Dados históricos (se usando JSON)
dados/execucoes/
dados/historico/
```

#### Script de Backup
```bash
# Criar backup completo
tar -czf backup_sistema_rpa_$(date +%Y%m%d).tar.gz \
  gspread-credentials.json \
  gmail-credentials.json \
  .env \
  logs/ \
  dados/
```

### Atualizações do Sistema

#### Processo de Atualização
1. **Backup completo** dos dados atuais
2. **Parar execuções** ativas
3. **Baixar nova versão** do sistema
4. **Migrar configurações** e credenciais
5. **Testar** em ambiente controlado
6. **Ativar** nova versão

#### Versionamento
- **Major** (v2.0 → v3.0): Mudanças importantes na arquitetura
- **Minor** (v2.0 → v2.1): Novas funcionalidades
- **Patch** (v2.0.1 → v2.0.2): Correções de bugs

### Monitoramento de Performance

#### Métricas Importantes
- **Tempo de execução** de cada RPA
- **Taxa de sucesso** das automações
- **Uso de memória** durante execução
- **Número de contratos** processados
- **Tempo de resposta** dos sistemas externos

#### Alertas Automáticos
- RPA executando há mais de 1 hora
- Taxa de erro acima de 10%
- Falha em 3 execuções consecutivas
- Sistemas externos indisponíveis

---

## 📞 Suporte

### Informações do Sistema
- **Versão**: v2.0
- **Desenvolvido em**: Python 3.8+
- **Arquitetura**: Modular com orquestração Temporal.io
- **Linguagem**: Português Brasileiro

### Contatos
- **Documentação**: Este manual e arquivos em `/docs`
- **Logs**: Pasta `/logs` para análise técnica
- **Configurações**: Arquivo `.env` e credenciais JSON

---

**🎯 Sistema RPA v2.0 - Automação profissional para reparcelamento financeiro**

*Desenvolvido com foco em simplicidade, robustez e manutenção.*