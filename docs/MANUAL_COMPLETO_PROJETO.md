# MANUAL COMPLETO DO PROJETO
## Sistema de Automação de Reparcelamento de Contratos

**Cliente:** J M  
**Versão:** 1.1  
**Data:** Outubro 2025  
**Baseado em:** PDD Original Reescrito (12/03/2025)  
**Última atualização:** Outubro 2025 - Sistema de Auditoria Completa implementado

---

## ÍNDICE

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Mapeamento PDD → Implementação](#2-mapeamento-pdd--implementação)
3. [Arquitetura do Sistema](#3-arquitetura-do-sistema)
4. [Guia de Uso - Etapa 1](#4-guia-de-uso---etapa-1)
5. [Guia de Uso - Etapa 2](#5-guia-de-uso---etapa-2)
6. [Componentes Técnicos Detalhados](#6-componentes-técnicos-detalhados)
7. [Configuração e Instalação](#7-configuração-e-instalação)
8. [Status e Fluxo de Contratos](#8-status-e-fluxo-de-contratos)
9. [Relatórios e Notificações](#9-relatórios-e-notificações)
10. [Sistema de Auditoria Completa](#10-sistema-de-auditoria-completa)
11. [Troubleshooting e Manutenção](#11-troubleshooting-e-manutenção)
12. [Anexos Técnicos](#12-anexos-técnicos)

---

## 1. VISÃO GERAL DO PROJETO

### 1.1 Objetivo

Este sistema automatiza o processo completo de **Reparcelamento de Contratos** dentro do Sistema Sienge e **Emissão de Boletos** no banco Sicredi, garantindo:

- **Padronização** do fluxo de trabalho
- **Precisão** nas informações processadas
- **Eficiência operacional** com redução de erros manuais
- **Rastreabilidade** completa do processo

### 1.2 Escopo

O sistema abrange desde a **validação dos índices de indexação** (IPCA e IGP-M) nos portais do IBGE e FGV, até a **emissão dos boletos atualizados** de cada empresa no banco Sicredi.

### 1.3 Recorrência de Execução

O processo é executado **mensalmente** em duas etapas:

**1° Etapa:**
- Coleta de índices econômicos (IPCA e IGP-M)
- Análise de planilhas e identificação de contratos
- Extração de relatórios do Sienge
- Envio de planilha para validação do analista financeiro

**2° Etapa:**
- Verificação de autorização via planilha Google Sheets
- Execução de reparcelamentos no Sienge
- Geração de carnês
- Importação de arquivos de remessa no Sicredi

### 1.4 Tecnologias Utilizadas

- **Python 3.11+** - Linguagem principal
- **Selenium/ChromeDriver** - Automação web
- **Google Sheets API** - Integração com planilhas
- **MongoDB + JSON** - Persistência híbrida de dados
- **Pandas/OpenPyXL** - Processamento de planilhas
- **SendGrid** - Envio de e-mails

---

## 2. MAPEAMENTO PDD → IMPLEMENTAÇÃO

### 2.1 Tabela de Correlação Completa

| **Seção PDD** | **Descrição** | **Implementação** | **Arquivo Principal** |
|---------------|---------------|-------------------|----------------------|
| **7.1** | Consulta Índice IPCA | Coleta automática do IBGE | `rpa_coleta_indices/rpa_coleta_indices.py` |
| **7.2** | Consulta Índice IGPM | Coleta automática da FGV | `rpa_coleta_indices/rpa_coleta_indices.py` |
| **8.1** | Verificação Novos Contratos | Cópia de planilha Base de Apoio | `rpa_analise_planilhas/rpa_analise_planilhas.py` |
| **8.2** | Verificação Consulta IPTU | Atualização de pendências IPTU | `rpa_analise_planilhas/rpa_analise_planilhas.py` |
| **9.1** | Acesso Relatório Saldo Devedor | Extração de relatórios Sienge | `rpa_sienge/rpa_sienge_extracao.py` |
| **9.1.1** | Leitura e Extração de Dados | Processamento de relatórios | `rpa_sienge/processar_regras_extracao_inadimplencia.py` |
| **9.1.2** | Atualização Planilha Base | Retroalimentação Google Sheets | `rpa_sienge/atualizar_planilha_extracao_resultados.py` |
| **10.1** | Registro Reparcelamento Sienge | Execução de reparcelamentos | `rpa_sienge/rpa_sienge_reparcelamento.py` |
| **10.2** | Emissão de Carnê Sienge | Geração de arquivos de remessa | `rpa_sienge/rpa_sienge_emissao_carne.py` |
| **10.3** | Acesso Banco Sicredi | Login e navegação | `rpa_sicredi/rpa_sicredi.py` |
| **10.4** | Importação Arquivos Remessa | Upload de arquivos | `rpa_sicredi/rpa_sicredi.py` |

### 2.2 Fluxo Detalhado por Etapa

#### Etapa 1 - Mapeamento PDD

```
PDD 7.1 + 7.2 → main_coleta_indices.py
  └─> Coleta IPCA (IBGE)
  └─> Coleta IGPM (FGV)
  └─> Atualiza planilha Google Sheets

PDD 8.1 + 8.2 → main_analise_planilhas.py
  └─> Processa Base de Apoio
  └─> Identifica novos contratos
  └─> Verifica pendências IPTU
  └─> Gera fila de processamento

PDD 9.1 + 9.1.1 → main_extracao_relatorio_sienge.py
  └─> Extrai relatórios Sienge
  └─> Processa dados financeiros
  └─> Aplica regras PDD

PDD 9.1.2 → atualizar_planilha_extracao_resultados.py
  └─> Retroalimenta planilha base
  └─> Envia e-mail com relatório para conhecimento
```

#### Etapa 2 - Mapeamento PDD

```
PDD 10 → autorizador_reparcelamentos.py
  └─> Verifica autorização via planilha Google Sheets

PDD 10.1 → main_reparcelamento_sienge.py
  └─> Executa reparcelamentos no Sienge

PDD 10.2 → main_sienge_emissao_carnes.py
  └─> Gera carnês e arquivos de remessa

PDD 10.3 + 10.4 → main_sicredi.py
  └─> Importa arquivos no Sicredi
  └─> Processa todas as empresas
```

---

## 3. ARQUITETURA DO SISTEMA

### 3.1 Estrutura de Diretórios

```
reparcelamento/
├── core/                          # Módulos centrais reutilizáveis
│   ├── base_rpa.py               # Classe base para todos os RPAs
│   ├── browser_manager.py        # Gerenciamento de navegadores
│   ├── data_manager.py           # Gerenciamento de dados
│   ├── notificacoes_simples.py   # Sistema de notificações
│   ├── relatorio_rpa.py          # Sistema de relatórios genérico
│   ├── repositorio_contratos_arquivo.py  # Repositório JSON
│   ├── repositorio_indices_arquivo.py   # Repositório de índices
│   └── status_enum.py            # Enum de status de contratos
│
├── rpa_coleta_indices/           # RPA de coleta de índices
│   ├── rpa_coleta_indices.py
│   └── teste_coleta_indices.py
│
├── rpa_analise_planilhas/        # RPA de análise de planilhas
│   ├── rpa_analise_planilhas.py
│   └── teste_analise_planilhas.py
│
├── rpa_sienge/                   # RPAs do sistema Sienge
│   ├── rpa_sienge_extracao.py
│   ├── rpa_sienge_reparcelamento.py
│   ├── rpa_sienge_emissao_carne.py
│   ├── atualizar_planilha_extracao_resultados.py
│   ├── atualizar_ultimo_reajuste.py
│   ├── autorizador_reparcelamentos.py
│   └── processar_regras_extracao_inadimplencia.py
│
├── rpa_sicredi/                  # RPA do banco Sicredi
│   ├── rpa_sicredi.py
│   └── teste_sicredi.py
│
├── scripts/                      # Scripts principais de execução
│   ├── main_coleta_indices.py
│   ├── main_analise_planilhas.py
│   ├── main_extracao_relatorio_sienge.py
│   ├── main_reparcelamento_sienge.py
│   ├── main_sienge_emissao_carnes.py
│   └── main_sicredi.py
│
├── data/                        # Dados persistentes
│   ├── fila_contratos.json      # Fila principal de contratos
│   └── indices_economicos.json # Índices coletados
│
├── outputs/                     # Saídas do sistema
│   ├── remessas/               # Arquivos de remessa gerados
│   ├── carnes/                # Carnês gerados
│   └── relatorios/            # Relatórios Excel
│
└── credentials/                 # Credenciais e configurações
    └── gspread-*.json          # Credenciais Google Sheets
```

### 3.2 Componentes Principais

#### 3.2.1 Core (Módulos Centrais)

**BaseRPA** (`core/base_rpa.py`)
- Classe base para todos os RPAs
- Gerencia logs, navegadores e tratamento de erros
- Implementa padrões comuns de automação

**RepositorioContratosArquivo** (`core/repositorio_contratos_arquivo.py`)
- Gerencia persistência de contratos em JSON
- Implementa transações atômicas
- Garante integridade dos dados

**RelatorioRPA** (`core/relatorio_rpa.py`)
- Sistema unificado de relatórios
- Gera relatórios JSON e TXT
- Categoriza sucessos/erros

**NotificacoesSimples** (`core/notificacoes_simples.py`)
- Envio de e-mails via SendGrid
- Suporte a anexos
- Templates de notificação

#### 3.2.2 RPAs Especializados

**RPA Coleta Índices** (`rpa_coleta_indices/`)
- Coleta IPCA do IBGE
- Coleta IGPM da FGV
- Atualiza planilha Google Sheets

**RPA Análise Planilhas** (`rpa_analise_planilhas/`)
- Processa planilha Base de Apoio
- Identifica novos contratos
- Verifica pendências IPTU

**RPA Sienge** (`rpa_sienge/`)
- Extração de relatórios
- Reparcelamento de contratos
- Emissão de carnês

**RPA Sicredi** (`rpa_sicredi/`)
- Importação de arquivos de remessa
- Processamento por empresa/CNPJ

---

## 4. GUIA DE USO - ETAPA 1

### 4.1 Coleta de Índices Econômicos

**PDD Referência:** Seções 7.1 e 7.2

#### Visão do Usuário

**O que faz:**
- Coleta automaticamente os índices IPCA e IGP-M dos portais oficiais
- Atualiza a planilha Google Sheets com os valores coletados
- Registra logs detalhados da execução

**Como executar:**

```bash
cd /caminho/para/reparcelamento
python scripts/main_coleta_indices.py
```

**Modo teste (opcional):**
```bash
python scripts/main_coleta_indices.py --teste
```

**O que esperar:**
- ✅ E-mail de sucesso com relatório em anexo
- 📊 Índices atualizados na planilha Google Sheets
- 📝 Logs salvos em `logs/`

#### Visão Técnica

**Arquivo:** `scripts/main_coleta_indices.py`

**Fluxo de execução:**
1. Inicializa relatório RPA
2. Carrega credenciais Google Sheets
3. Chama `executar_coleta_indices()` do RPA
4. Processa resultado e atualiza relatório
5. Salva relatórios JSON/TXT
6. Envia notificação por e-mail

**Arquivo RPA:** `rpa_coleta_indices/rpa_coleta_indices.py`

**Funcionalidades principais:**
- `coletar_ipca_ibge()` - Acessa IBGE e extrai IPCA acumulado 12 meses
- `coletar_igpm_fgv()` - Acessa FGV e extrai IGP-M acumulado 12 meses
- `atualizar_planilha_indices()` - Atualiza abas IPCA/IGPM na planilha

**Rastreamento:**
- Todos os passos são registrados em `dados_processamento/auditoria_completa/`
- Arquivo individual: `RPA_Coleta_Indices_{timestamp}.json`
- Arquivo consolidado: `CONSOLIDADO_RPA_Coleta_Indices_{timestamp}.json`

**Dependências:**
- Variável de ambiente: `PLANILHA_CALCULO_ID`
- Credenciais Google: `GOOGLE_CREDENTIALS_PATH`
- Portal IBGE: https://www.ibge.gov.br/explica/inflacao.php
- Portal FGV: https://portalibre.fgv.br/taxonomy/term/94

### 4.2 Análise de Planilhas

**PDD Referência:** Seções 8.1 e 8.2

#### Visão do Usuário

**O que faz:**
- Processa planilha Base de Apoio para identificar novos contratos
- Verifica atualização de consultas IPTU
- Copia novos contratos para planilha Base de Cálculo
- Atualiza pendências IPTU na planilha
- Gera fila de contratos para processamento

**Como executar:**

```bash
python scripts/main_analise_planilhas.py
```

**O que esperar:**
- ✅ E-mail com relatório executivo
- 📊 Planilha Base de Cálculo atualizada
- 📋 Fila de contratos gerada em `data/fila_contratos.json`
- 📄 Arquivo Excel `resumo_executivo_*.xlsx` gerado

#### Visão Técnica

**Arquivo:** `scripts/main_analise_planilhas.py`

**Fluxo de execução:**
1. Carrega planilhas (Base de Cálculo e Base de Apoio)
2. Chama `executar_analise_planilhas()` do RPA
3. Processa resultados e métricas
4. Gera relatórios e anexa Excel
5. Envia notificação por e-mail

**Arquivo RPA:** `rpa_analise_planilhas/rpa_analise_planilhas.py`

**Funcionalidades principais:**
- `processar_novos_contratos()` - Copia novos contratos da Base de Apoio
- `verificar_consulta_iptu()` - Atualiza pendências IPTU
- `filtrar_contratos_reajuste()` - Identifica contratos elegíveis
- `atualizar_data_ultimo_reajuste()` - Atualiza coluna "Último reajuste"

**Rastreamento:**
- Todos os passos são registrados em `dados_processamento/auditoria_completa/`
- Arquivo individual: `RPA_Analise_Planilhas_{timestamp}.json`
- Arquivo consolidado: `CONSOLIDADO_RPA_Analise_Planilhas_{timestamp}.json`

**Dependências:**
- Variáveis de ambiente:
  - `PLANILHA_CALCULO_ID`
  - `PLANILHA_APOIO_ID`
  - `GOOGLE_CREDENTIALS_PATH`

### 4.3 Extração de Relatórios Sienge

**PDD Referência:** Seções 9.1 e 9.1.1

#### Visão do Usuário

**O que faz:**
- Acessa sistema Sienge automaticamente
- Baixa relatórios "Saldo Devedor Presente" para cada contrato
- Extrai dados financeiros (parcelas, valores, pendências)
- Aplica regras PDD para validação
- Gera arquivos `resultados_processamento.csv` e `.txt`

**Como executar:**

```bash
python scripts/main_extracao_relatorio_sienge.py
```

**Opções disponíveis:**
```bash
# Executar apenas extração
python scripts/main_extracao_relatorio_sienge.py --extrair

# Executar apenas processamento
python scripts/main_extracao_relatorio_sienge.py --processar

# Executar apenas retroalimentação
python scripts/main_extracao_relatorio_sienge.py --retroalimentar

# Executar tudo (padrão)
python scripts/main_extracao_relatorio_sienge.py --extrair --processar --retroalimentar
```

**O que esperar:**
- ✅ E-mail com relatório e anexos (para conhecimento)
- 📊 Arquivos `resultados_processamento.csv` e `.txt` gerados
- 📋 Planilha Base de Cálculo retroalimentada
- 📝 Logs detalhados em `logs/`
- 📋 Auditoria completa em `dados_processamento/auditoria_completa/`

#### Visão Técnica

**Arquivo:** `scripts/main_extracao_relatorio_sienge.py`

**Fluxo de execução:**
1. **Fase 1 - Extração:** `RPAExtracaoRelatorioSienge`
   - Login no Sienge
   - Download de relatórios por contrato
   - Salva relatórios em `dados_extraidos/planilhas_sienge/`

2. **Fase 2 - Processamento:** `processar_regras_extracao_inadimplencia.py`
   - Lê relatórios baixados
   - Aplica regras PDD (PDD 9.1.1)
   - Extrai: dia vencimento, valor parcela, parcelas a vencer/vencidas, pendências
   - Gera CSV e TXT

3. **Fase 3 - Retroalimentação:** `atualizar_planilha_extracao_resultados.py`
   - Atualiza planilha Google Sheets com dados extraídos
   - Retroalimenta colunas conforme PDD 9.1.2

**Arquivos RPA:**
- `rpa_sienge/rpa_sienge_extracao.py` - Extração via Selenium
- `rpa_sienge/processar_regras_extracao_inadimplencia.py` - Processamento de regras
- `rpa_sienge/atualizar_planilha_extracao_resultados.py` - Retroalimentação

**Rastreamento:**
- Todos os passos são registrados em `dados_processamento/auditoria_completa/`
- Arquivo individual: `RPA_Sienge_Extracao_{timestamp}.json`
- Arquivo consolidado: `CONSOLIDADO_RPA_Sienge_Extracao_{timestamp}.json`

**Regras PDD Implementadas (9.1.1):**

1. **Dia de vencimento das parcelas:**
   - Filtra por "Status da parcela" = "A vencer"
   - Identifica dia na coluna "Data vencimento"
   - Calcula 1º vencimento conforme tipo de reparcelamento

2. **Valor da parcela atual:**
   - Verifica coluna "original ou corrigido" na planilha
   - Extrai de "Valor original" ou "Valor Corrigido"

3. **Parcelas a vencer:**
   - Filtra por "Status da parcela" = "A vencer" e "Documento" = "CT"
   - **REGRA CORRIGIDA:** Conta parcelas a partir do mês de reparcelamento

4. **Pendências SIENGE INAD:**
   - Identifica parcelas vencidas 60 dias antes do 1º vencimento do novo carnê
   - Documento tipo "CT"

5. **Pendências SIENGE:**
   - Identifica parcelas vencidas tipo "REC" ou "FAT"

**Dependências:**
- Variáveis de ambiente:
  - `SIENGE_USUARIO`
  - `SIENGE_SENHA`
  - `PLANILHA_CALCULO_ID`
  - `GOOGLE_CREDENTIALS_PATH`

---

## 5. GUIA DE USO - ETAPA 2

### 5.1 Verificação de Autorização

**PDD Referência:** Seção 10

#### Visão do Usuário

**O que faz:**
- Verifica autorização de reparcelamentos na planilha Google Sheets
- Lê a aba "LANÇAMENTO DE REPARCELAMENTOS AUTORIZADO"
- Atualiza status de contratos de `AGUARDANDO_APROVACAO` para `APROVACAO_REALIZADA`

**⚠️ IMPORTANTE:** A autorização é feita **exclusivamente via planilha Google Sheets**, não por e-mail.

**Como o analista autoriza:**
1. Acessa a planilha Base de Cálculo
2. Vai para a aba "LANÇAMENTO DE REPARCELAMENTOS AUTORIZADO"
3. Preenche as colunas:
   - **Coluna A (Ano):** Ano do mês de reparcelamento (ex: 2025)
   - **Coluna B (Mês):** Mês do reparcelamento (ex: 11)
   - **Coluna C (Autorização):** "SIM" para autorizar
4. O sistema verifica automaticamente esta aba

**Como executar:**

```bash
python scripts/main_reparcelamento_sienge.py --verificar-autorizacao
```

**O que esperar:**
- ✅ Logs indicando autorização encontrada na planilha
- 📋 Contratos atualizados para `APROVACAO_REALIZADA`

#### Visão Técnica

**Arquivo:** `rpa_sienge/autorizador_reparcelamentos.py`

**Funcionalidades:**
- Lê aba "LANÇAMENTO DE REPARCELAMENTOS AUTORIZADO" da planilha Base de Cálculo
- Verifica colunas A (ano), B (mês), C (autorização "SIM")
- Busca pelo mês seguinte ao atual
- Atualiza contratos no repositório JSON de `AGUARDANDO_APROVACAO` para `APROVACAO_REALIZADA`

### 5.2 Execução de Reparcelamentos

**PDD Referência:** Seção 10.1

#### Visão do Usuário

**O que faz:**
- Executa reparcelamentos no sistema Sienge para contratos aprovados
- Preenche formulários conforme PDD 10.1
- Atualiza status dos contratos

**Como executar:**

```bash
python scripts/main_reparcelamento_sienge.py
```

**O que esperar:**
- ✅ Contratos reparcelados com sucesso
- 📋 Status atualizado para `REPARCELADO`
- 📝 Logs detalhados de cada operação
- 📋 Auditoria completa em `dados_processamento/auditoria_completa/`

#### Visão Técnica

**Arquivo:** `scripts/main_reparcelamento_sienge.py`

**Fluxo de execução:**
1. Verifica autorização (se necessário)
2. Carrega índices econômicos da planilha
3. Busca contratos com status `APROVACAO_REALIZADA`
4. Chama `RPAReparcelamentoSienge` para cada contrato
5. Atualiza status dos contratos

**Arquivo RPA:** `rpa_sienge/rpa_sienge_reparcelamento.py`

**Funcionalidades principais:**
- `executar_reparcelamento()` - Executa reparcelamento completo
- Preenche formulário conforme PDD 10.1:
  - Número do título
  - Tipo condição: PM
  - Valor total: Saldo devedor NOVO
  - Quantidade de parcelas
  - Data do 1º vencimento
  - Indexador: IGP-M
  - Tipo de juros: Nenhum

**Rastreamento:**
- Todos os passos são registrados em `dados_processamento/auditoria_completa/`
- Arquivo individual: `RPA_Sienge_Reparcelamento_{timestamp}.json`
- Arquivo consolidado: `CONSOLIDADO_RPA_Sienge_Reparcelamento_{timestamp}.json`

**Dependências:**
- Variáveis de ambiente:
  - `SIENGE_USUARIO`
  - `SIENGE_SENHA`
  - `PLANILHA_CALCULO_ID`

### 5.3 Emissão de Carnês

**PDD Referência:** Seção 10.2

#### Visão do Usuário

**O que faz:**
- Gera carnês de reparcelamento no Sienge
- Cria arquivos de remessa para cada empresa
- Vincula arquivos gerados aos contratos no repositório

**Como executar:**

```bash
python scripts/main_sienge_emissao_carnes.py
```

**Modo teste:**
```bash
python scripts/main_sienge_emissao_carnes.py --teste
```

**O que esperar:**
- ✅ Arquivos de remessa gerados em `outputs/remessas/`
- 📋 Contratos atualizados para `CARNE_GERADO`
- 📝 Logs detalhados de cada empresa processada
- 📋 Auditoria completa em `dados_processamento/auditoria_completa/`

#### Visão Técnica

**Arquivo:** `scripts/main_sienge_emissao_carnes.py`

**Fluxo de execução:**
1. Busca contratos com status `REPARCELADO`
2. Carrega dados da planilha base de cálculo
3. Verifica pendências IPTU e inadimplência
4. Filtra contratos aptos (sem pendências)
5. Chama `RPAEmissaoCarneSienge` para gerar carnês
6. Vincula arquivos gerados aos contratos

**Arquivo RPA:** `rpa_sienge/rpa_sienge_emissao_carne.py`

**Funcionalidades principais:**
- `gerar_carnes_empresa()` - Gera carnês para uma empresa
- Preenche formulário conforme PDD 10.2:
  - Data inicial: 1º vencimento carnê
  - Data final: mesma data mês anterior ano seguinte
  - Nome da empresa (seleciona via lupa)
  - Conta corrente (seleciona via lupa)
  - Nome arquivo: primeiros 5 dígitos conta + mês + dia + sequencial
  - Mensagens de remessa e boletos
  - Opções de geração

**Regras especiais:**
- **Rio Almada:** Usa dígito `06300` no início do nome do arquivo
- **SPE RESIDENCIAL PARQUE DA LAGOA:** Usa dígito `01870` no início do nome do arquivo

**Rastreamento:**
- Todos os passos são registrados em `dados_processamento/auditoria_completa/`
- Arquivo individual: `RPA_Sienge_EmissaoCarne_{timestamp}.json`
- Arquivo consolidado: `CONSOLIDADO_RPA_Sienge_EmissaoCarne_{timestamp}.json`

**Dependências:**
- Variáveis de ambiente:
  - `SIENGE_USUARIO`
  - `SIENGE_SENHA`
  - `PLANILHA_CALCULO_ID`

### 5.4 Importação no Sicredi

**PDD Referência:** Seções 10.3 e 10.4

#### Visão do Usuário

**O que faz:**
- Importa arquivos de remessa gerados no Sienge para o banco Sicredi
- Processa todas as empresas/CNPJs configurados
- Valida importações e atualiza status dos contratos

**Como executar:**

```bash
python scripts/main_sicredi.py
```

**O que esperar:**
- ✅ E-mail com relatório detalhado
- 📊 Arquivos de remessa importados com sucesso
- 📋 Contratos atualizados para `PROCESSADO_SICREDI`
- 📝 Logs detalhados por empresa
- 📋 Auditoria completa em `dados_processamento/auditoria_completa/`

#### Visão Técnica

**Arquivo:** `scripts/main_sicredi.py`

**Fluxo de execução:**
1. Diagnostica arquivos de remessa disponíveis
2. Agrupa arquivos por empresa/CNPJ
3. Para cada empresa:
   - Login no Sicredi
   - Importa arquivos de remessa
   - Valida importação
   - Atualiza status dos contratos
4. Gera relatório final

**Arquivo RPA:** `rpa_sicredi/rpa_sicredi.py`

**Funcionalidades principais:**
- `fazer_login()` - Login no Sicredi com CNPJ
- `importar_arquivo_remessa()` - Upload de arquivo de remessa
- `validar_importacao()` - Verifica sucesso da importação

**Dependências:**
- Variáveis de ambiente:
  - `SICREDI_CNPJ_*` (um para cada empresa)
  - `SICREDI_USUARIO_*` (um para cada empresa)
  - `SICREDI_SENHA_*` (um para cada empresa)

**Tabela de CNPJs:**
- Configurada em variáveis de ambiente
- Cada empresa tem seu próprio CNPJ/usuário/senha

**Rastreamento:**
- Todos os passos são registrados em `dados_processamento/auditoria_completa/`
- Arquivo individual: `RPA_Sicredi_{timestamp}.json`
- Arquivo consolidado: `CONSOLIDADO_RPA_Sicredi_{timestamp}.json`

---

## 6. COMPONENTES TÉCNICOS DETALHADOS

### 6.1 Sistema de Status de Contratos

**PDD Referência:** Implícito em todas as seções

#### Visão Técnica

O sistema utiliza um enum de status definido em `core/status_enum.py`:

```python
class StatusContrato(Enum):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    APROVACAO_REALIZADA = "APROVACAO_REALIZADA"
    REPARCELADO = "REPARCELADO"
    CARNE_GERADO = "CARNE_GERADO"
    PROCESSADO_SICREDI = "PROCESSADO_SICREDI"
    ERRO = "ERRO"
    CANCELADO = "CANCELADO"
    IGNORADO = "IGNORADO"
    REJEITADO = "REJEITADO"
    FINALIZADO = "FINALIZADO"
```

**Fluxo de status típico:**

```
PENDENTE → PROCESSANDO → AGUARDANDO_APROVACAO → 
APROVACAO_REALIZADA → REPARCELADO → CARNE_GERADO → 
PROCESSADO_SICREDI → FINALIZADO
```

### 6.2 Repositório de Contratos

**Arquivo:** `core/repositorio_contratos_arquivo.py`

#### Visão Técnica

**Funcionalidades:**
- Persistência em JSON com transações atômicas
- Métodos principais:
  - `find()` - Busca contratos
  - `update()` - Atualiza contrato
  - `insert()` - Insere novo contrato
  - `delete()` - Remove contrato

**Estrutura de dados:**

```json
{
  "_id": "uuid",
  "Titulo": "123456",
  "Empresa": "Nome da Empresa",
  "status": "PENDENTE",
  "arquivo_remessa": "outputs/remessas/arquivo.rem",
  "timestamp_ultima_atualizacao": "2025-10-30T14:00:00"
}
```

### 6.3 Sistema de Relatórios

**Arquivo:** `core/relatorio_rpa.py`

#### Visão Técnica

**Classe:** `RelatorioRPA`

**Funcionalidades:**
- Rastreamento de tempo de execução
- Categorização de sucessos/erros
- Geração de relatórios JSON e TXT
- Métricas personalizadas

**Métodos principais:**
- `iniciar_execucao()` - Inicia rastreamento
- `adicionar_sucesso()` - Registra sucesso
- `adicionar_erro()` - Registra erro
- `finalizar_execucao()` - Finaliza rastreamento
- `salvar_relatorio_json()` - Salva JSON
- `salvar_relatorio_txt()` - Salva TXT

### 6.4 Sistema de Notificações

**Arquivo:** `core/notificacoes_simples.py`

#### Visão Técnica

**Funcionalidades:**
- Envio de e-mails via SendGrid
- Suporte a anexos (TXT, CSV, Excel, etc.)
- Templates de notificação
- Destinatários configuráveis

**Métodos principais:**
- `enviar_email()` - Envia e-mail genérico
- `notificar_sucesso()` - Notifica sucesso
- `notificar_erro()` - Notifica erro
- `notificar_inicio()` - Notifica início

**Configuração:**
- Arquivo: `config/notificacoes.json`
- Variáveis de ambiente: `SENDGRID_API_KEY`

---

## 7. CONFIGURAÇÃO E INSTALAÇÃO

### 7.1 Pré-requisitos

**Software:**
- Python 3.11 ou superior
- Google Chrome instalado
- ChromeDriver (gerenciado automaticamente)

**Contas e Acessos:**
- Conta Google com acesso à planilha
- Conta SendGrid para envio de e-mails
- Acesso ao sistema Sienge
- Acesso ao banco Sicredi (todas as empresas)

### 7.2 Instalação

**1. Clone o repositório:**
```bash
git clone <repositorio>
cd reparcelamento
```

**2. Crie ambiente virtual:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

**3. Instale dependências:**
```bash
pip install -r requirements.txt
```

**4. Configure variáveis de ambiente:**

Crie arquivo `.env` na raiz do projeto:

```env
# Google Sheets
PLANILHA_CALCULO_ID=seu_id_da_planilha
PLANILHA_APOIO_ID=seu_id_da_planilha_apoio
GOOGLE_CREDENTIALS_PATH=./credentials/gspread-459713-aab8a657f9b0.json

# Sienge
SIENGE_USUARIO=tc@trajetoriaconsultoria.com.br
SIENGE_SENHA=sua_senha

# Sicredi (uma linha para cada empresa)
SICREDI_CNPJ_1=12345678000190
SICREDI_USUARIO_1=Isabella
SICREDI_SENHA_1=senha_empresa_1

# SendGrid
SENDGRID_API_KEY=sua_chave_sendgrid

# Modo headless (opcional)
HEADLESS=1
```

**5. Configure credenciais Google:**

Coloque o arquivo JSON de credenciais em:
```
credentials/gspread-459713-aab8a657f9b0.json
```

### 7.3 Estrutura de Planilhas Google Sheets

**Planilha Base de Cálculo:**
- Abas: "Base de cálculo", "IPCA", "IGPM"
- Colunas principais na aba "Base de cálculo":
  - Título
  - Empresa
  - Cliente
  - Índice
  - Mês reajuste
  - Último reajuste
  - PENDÊNCIAS IPTU
  - PENDÊNCIAS SIENGE INAD
  - PENDÊNCIAS SIENGE
  - Parcelas a vencer
  - Valor da Parcela Base
  - Dia de vencimento
  - 1º vencimento carnê

**Planilha Base de Apoio:**
- Aba "NOVOS CONTRATOS"
- Aba "Consulta IPTU"

### 7.4 Teste de Instalação

**Teste básico:**
```bash
python scripts/main_coleta_indices.py --teste
```

**Verificar logs:**
```bash
ls -la logs/
```

---

## 8. STATUS E FLUXO DE CONTRATOS

### 8.1 Fluxo Completo de Status

```
┌─────────────┐
│  PENDENTE   │ ← Contrato identificado na análise de planilhas
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PROCESSANDO │ ← Durante extração de relatórios
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ AGUARDANDO_APROVACAO │ ← Após análise, aguardando autorização
└──────┬───────────────┘
       │
       ▼ (autorização)
┌──────────────────────┐
│ APROVACAO_REALIZADA  │ ← Após verificação de autorização
└──────┬───────────────┘
       │
       ▼
┌──────────────┐
│ REPARCELADO  │ ← Após reparcelamento no Sienge
└──────┬───────┘
       │
       ▼
┌──────────────┐
│CARNE_GERADO  │ ← Após geração de carnês
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ PROCESSADO_SICREDI   │ ← Após importação no Sicredi
└──────┬───────────────┘
       │
       ▼
┌──────────────┐
│  FINALIZADO  │ ← Processo completo
└──────────────┘
```

### 8.2 Status de Erro

```
┌─────────────┐
│    ERRO     │ ← Em qualquer etapa, se ocorrer erro
└─────────────┘

┌─────────────┐
│  CANCELADO  │ ← Cancelado manualmente
└─────────────┘

┌─────────────┐
│  IGNORADO   │ ← Contrato não elegível (pendências)
└─────────────┘

┌─────────────┐
│  REJEITADO  │ ← Rejeitado na análise
└─────────────┘
```

### 8.3 Consulta de Status

**Via código:**
```python
from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo

contratos = repositorio_contratos_arquivo.framework.find({"status": "PENDENTE"})
```

**Via arquivo JSON:**
```bash
cat data/fila_contratos.json | jq '.[] | select(.status == "PENDENTE")'
```

---

## 9. RELATÓRIOS E NOTIFICAÇÕES

### 9.1 Tipos de Relatórios

**1. Relatório JSON:**
- Estrutura: `relatorio_YYYYMMDD_HHMMSS.json`
- Localização: `outputs/relatorios/`
- Formato estruturado para processamento automático

**2. Relatório TXT:**
- Estrutura: `relatorio_YYYYMMDD_HHMMSS.txt`
- Localização: `outputs/relatorios/`
- Formato legível para humanos
- Enviado como anexo nos e-mails

**3. Relatório Excel:**
- Gerado em alguns processos (ex: análise de planilhas)
- Localização: `outputs/relatorios/`
- Nome: `resumo_executivo_YYYYMMDD_HHMMSS.xlsx`

### 9.2 Notificações por E-mail

**Destinatários configurados:**
- `tiagopereiraramos@gmail.com`
- `patriciasena@trajetoriaconsultoria.com.br`
- `comercial@rorato.adm.br`

**Tipos de notificação:**
- **Sucesso:** Quando processo completa com sucesso
- **Erro:** Quando ocorre erro crítico
- **Início:** Quando processo inicia (opcional)

**Anexos incluídos:**
- Relatório TXT
- Arquivos CSV/TXT de processamento (quando aplicável)
- Arquivos Excel de resumo (quando aplicável)

### 9.3 Estrutura de Relatórios

**Relatório JSON:**
```json
{
  "nome_rpa": "Nome do RPA",
  "inicio_execucao": "2025-10-30T14:00:00",
  "fim_execucao": "2025-10-30T14:30:00",
  "tempo_execucao_segundos": 1800,
  "status": "SUCESSO_COMPLETO",
  "sucessos": [...],
  "erros": [...],
  "metricas": {...}
}
```

**Relatório TXT:**
```
========================================
RELATÓRIO DE EXECUÇÃO - Nome do RPA
========================================

Data/Hora: 30/10/2025 14:00:00
Tempo de Execução: 30 minutos

STATUS: SUCESSO COMPLETO

SUCESSOS:
- Item 1: Descrição
- Item 2: Descrição

ERROS:
(Nenhum)

MÉTRICAS:
- Total processado: 100
- Taxa de sucesso: 100%
```

---

## 10. SISTEMA DE AUDITORIA COMPLETA

### 10.1 Visão Geral

O sistema possui um **sistema de auditoria completa** que registra **cada passo** de cada execução de RPA, criando um histórico detalhado para:

- **Debugging avançado** - Saber exatamente o que aconteceu em cada execução
- **Recuperação de dados** - Poder reconstruir o que foi feito mesmo se houver falha
- **Compliance e auditoria** - Provar o que foi executado e como
- **Análise de performance** - Entender tempos de execução e gargalos

### 10.2 Localização dos Arquivos

**Pasta:** `dados_processamento/auditoria_completa/`

**Estrutura:**
```
dados_processamento/auditoria_completa/
├── RPA_Sienge_20250830_085035_7471.json        # Execução individual
├── RPA_Sicredi_20251015_143022_1234.json       # Execução individual
├── RPA_Coleta_Indices_20251014_070859_5114.json # Execução individual
├── CONSOLIDADO_RPA_Sienge_20250830_085035_7471.json  # Consolidado final
└── ... (821+ arquivos)
```

### 10.3 RPAs que Utilizam Auditoria

**Todos os RPAs principais** utilizam o sistema de auditoria:

1. ✅ **RPA Coleta de Índices** - `rpa_coleta_indices/rpa_coleta_indices.py`
2. ✅ **RPA Análise de Planilhas** - `rpa_analise_planilhas/rpa_analise_planilhas.py`
3. ✅ **RPA Sienge (Principal)** - `rpa_sienge/rpa_sienge.py`
4. ✅ **RPA Sicredi** - `rpa_sicredi/rpa_sicredi.py`
5. ✅ **RPA Sienge - Emissão de Carnês** - `rpa_sienge/rpa_sienge_emissao_carne.py`
6. ✅ **RPA Sienge - Reparcelamento** - `rpa_sienge/rpa_sienge_reparcelamento.py`
7. ✅ **RPA Sienge - Extração** - `rpa_sienge/rpa_sienge_extracao.py`

### 10.4 O que é Registrado

Cada passo da execução registra:

- **Timestamp preciso** - Quando ocorreu
- **Nome do passo** - Ex: "LOGIN_SIENGE", "PROCESSAR_REPARCELAMENTO_123456"
- **Categoria** - INICIO, OPERACAO, ERRO, SUCESSO
- **Dados completos** - Parâmetros, resultados, contexto
- **Criticidade** - INFO, WARNING, ERROR, CRITICAL

### 10.5 Tipos de Arquivos

**1. Arquivo Individual (`{id_execucao}.json`):**
- Criado durante a execução
- Atualizado incrementalmente a cada passo
- Contém todos os passos registrados até o momento

**2. Arquivo Consolidado (`CONSOLIDADO_{id_execucao}.json`):**
- Criado ao finalizar a execução
- Contém todos os passos + estatísticas finais
- Documento completo da execução

### 10.6 Exemplo de Uso

**Consultar execução específica:**
```bash
cat dados_processamento/auditoria_completa/RPA_Sienge_20250830_085035_7471.json | jq '.'
```

**Verificar passos de erro:**
```bash
cat dados_processamento/auditoria_completa/RPA_Sienge_20250830_085035_7471.json | jq '.passos[] | select(.categoria == "ERRO")'
```

**Analisar tempo de execução:**
```bash
cat dados_processamento/auditoria_completa/CONSOLIDADO_RPA_Sienge_20250830_085035_7471.json | jq '.estatisticas_finais'
```

### 10.7 Benefícios

**Para Debugging:**
- Identificar exatamente onde ocorreu um erro
- Ver contexto completo do erro
- Verificar sequência de passos antes do erro

**Para Compliance:**
- Histórico imutável de todas as execuções
- Timestamps precisos de cada ação
- Rastreabilidade completa

**Para Performance:**
- Identificar gargalos (passos que demoram muito)
- Analisar tempos entre passos
- Estatísticas de sucesso/erro

### 10.8 Manutenção

**Limpeza de Arquivos Antigos:**
- Arquivos antigos (>30 dias) podem ser arquivados
- Recomendação: Manter últimos 90 dias ativos
- Arquivos consolidados podem ser mantidos por mais tempo

**Tamanho:**
- Arquivos individuais: ~50-200KB cada
- Total atual: ~50-150MB (821+ arquivos)
- Impacto mínimo no desempenho

---

## 11. TROUBLESHOOTING E MANUTENÇÃO

### 11.1 Problemas Comuns

#### Erro: "ChromeDriver não encontrado"

**Solução:**
```bash
python scripts/atualizar_chromedriver.sh
```

#### Erro: "APIError: [429] Quota exceeded" (Google Sheets)

**Causa:** Limite de requisições da API do Google Sheets excedido

**Solução:**
- O sistema implementa retry automático com backoff exponencial
- Aguardar alguns minutos e tentar novamente
- Considerar reduzir frequência de execuções

#### Erro: "Login falhou no Sienge"

**Causas possíveis:**
- Credenciais incorretas
- Captcha ou verificação de segurança
- Sistema Sienge em manutenção

**Solução:**
- Verificar variáveis de ambiente `SIENGE_USUARIO` e `SIENGE_SENHA`
- Executar manualmente para verificar se há captcha
- Aguardar e tentar novamente

#### Erro: "Contrato não encontrado no repositório"

**Causa:** Contrato não foi inserido na fila ou foi removido

**Solução:**
- Verificar `data/fila_contratos.json`
- Re-executar análise de planilhas se necessário

### 11.1 Logs e Debugging

**Localização dos logs:**
```
logs/
├── emissao_carnes_YYYYMMDD_HHMMSS.log
├── coleta_indices_YYYYMMDD_HHMMSS.log
└── ...
```

**Visualizar logs:**
```bash
tail -f logs/emissao_carnes_*.log
```

**Modo debug:**
- Remover `HEADLESS=1` do `.env` para ver navegador
- Executar com `--teste` para usar planilhas de teste

### 11.2 Manutenção Preventiva

**Tarefas mensais:**
1. Verificar espaço em disco
2. Limpar logs antigos (manter últimos 30 dias)
3. Arquivar arquivos de auditoria antigos (>90 dias)
4. Verificar atualizações de dependências
5. Validar credenciais Google Sheets
6. Testar conexões (Sienge, Sicredi)

**Tarefas trimestrais:**
1. Atualizar ChromeDriver
2. Atualizar dependências Python
3. Revisar configurações de notificações
4. Backup de `data/fila_contratos.json`
5. Backup de arquivos consolidados de auditoria

### 11.3 Backup e Recuperação

**Arquivos críticos para backup:**
- `data/fila_contratos.json`
- `data/indices_economicos.json`
- `credentials/gspread-*.json`
- `.env` (sem commit no Git)
- `dados_processamento/auditoria_completa/` (arquivos consolidados)

**Script de backup:**
```bash
# Criar backup manual
cp data/fila_contratos.json data/fila_contratos.json.backup_$(date +%Y%m%d_%H%M%S)
```

---

## 12. MIGRAÇÃO PARA MÁQUINA DO CLIENTE

### 12.1 Visão Geral

Este projeto foi preparado para migração fácil entre ambientes (Linux, Windows, macOS) com suporte completo a:
- Gerenciamento de dependências com **uv**
- Detecção automática de drivers (Firefox e Chrome)
- Configuração segura de credenciais
- Agendamento multiplataforma (cron/Task Scheduler)

### 12.2 Processo de Migração Rápido

**Passo 1: Verificar Pré-requisitos**
```bash
python scripts/verificar_pre_requisitos.py
```

**Passo 2: Setup Completo**
```bash
python scripts/setup_completo.py
```

**Passo 3: Configurar Credenciais**
```bash
python scripts/configurar_ambiente.py
```

**Passo 4: Validar Instalação**
```bash
python scripts/validar_credenciais.py
python scripts/testar_instalacao.py
```

**Passo 5: Configurar Agendamento**
```bash
python scripts/configurar_agendamento.py
```

### 12.3 Documentação de Migração

Para guias detalhados, consulte:

- **`docs/MIGRACAO_CLIENTE.md`**: Guia completo de migração
- **`docs/AGENDAMENTO.md`**: Configuração de agendamento
- **`docs/SEGURANCA_CREDENCIAIS.md`**: Boas práticas de segurança
- **`docs/GUIA_RAPIDO_MIGRACAO.md`**: Referência rápida

### 12.4 Scripts de Migração Disponíveis

| Script | Descrição |
|--------|-----------|
| `scripts/verificar_pre_requisitos.py` | Verifica pré-requisitos do sistema |
| `scripts/setup_uv.py` | Instala e configura uv |
| `scripts/instalar_dependencias.py` | Instala dependências do projeto |
| `scripts/configurar_chrome_driver.py` | Configura Chrome driver |
| `scripts/configurar_ambiente.py` | Configuração interativa de .env |
| `scripts/validar_credenciais.py` | Valida credenciais configuradas |
| `scripts/configurar_agendamento.py` | Configura agendamento (cron/Task Scheduler) |
| `scripts/executar_agendado.py` | Wrapper para execução agendada |
| `scripts/testar_agendamento.py` | Testa configuração de agendamento |
| `scripts/setup_completo.py` | Orquestra todo o processo de setup |
| `scripts/testar_instalacao.py` | Valida instalação completa |

### 12.5 Suporte Multiplataforma

O projeto suporta automaticamente:

- **Linux**: Ubuntu 20.04+, Debian 11+, CentOS 8+
- **Windows**: Windows 10/11 (64-bit)
- **macOS**: macOS 11 (Big Sur) ou superior

Todos os scripts detectam automaticamente o sistema operacional e ajustam comportamentos conforme necessário.

### 12.6 Troubleshooting de Migração

**Problema: Drivers não funcionam**
```bash
python scripts/configurar_chrome_driver.py
```

**Problema: Credenciais inválidas**
```bash
python scripts/validar_credenciais.py
```

**Problema: Agendamento não executa**
```bash
python scripts/testar_agendamento.py
python scripts/configurar_agendamento.py
```

Para mais detalhes, consulte `docs/GUIA_RAPIDO_MIGRACAO.md`.

---

## 13. ANEXOS TÉCNICOS

### 13.1 Variáveis de Ambiente Completas

```env
# ============================================
# GOOGLE SHEETS
# ============================================
PLANILHA_CALCULO_ID=seu_id_aqui
PLANILHA_APOIO_ID=seu_id_aqui
PLANILHA_TESTE_HOM=seu_id_teste
GOOGLE_CREDENTIALS_PATH=./credentials/gspread-459713-aab8a657f9b0.json

# ============================================
# SIENGE
# ============================================
SIENGE_USUARIO=tc@trajetoriaconsultoria.com.br
SIENGE_SENHA=sua_senha_aqui

# ============================================
# SICREDI (configurar para cada empresa)
# ============================================
SICREDI_CNPJ_1=12345678000190
SICREDI_USUARIO_1=Isabella
SICREDI_SENHA_1=senha_empresa_1

SICREDI_CNPJ_2=98765432000110
SICREDI_USUARIO_2=Usuario
SICREDI_SENHA_2=senha_empresa_2

# ... (adicionar mais empresas conforme necessário)

# ============================================
# SENDGRID
# ============================================
SENDGRID_API_KEY=sua_chave_aqui

# ============================================
# MODO DE EXECUÇÃO
# ============================================
HEADLESS=1  # 1 = headless, 0 = com navegador visível
```

### 13.2 Estrutura de Dados - Fila de Contratos

```json
[
  {
    "_id": "uuid-gerado-automaticamente",
    "Titulo": "123456",
    "Empresa": "Nome da Empresa",
    "Cliente": "Nome do Cliente",
    "status": "PENDENTE",
    "arquivo_remessa": "outputs/remessas/24053312.2231",
    "timestamp_criacao": "2025-10-30T14:00:00",
    "timestamp_ultima_atualizacao": "2025-10-30T14:00:00",
    "dados_planilha": {
      "indice": "IPCA",
      "mes_reajuste": "2025-11-01",
      "ultimo_reajuste": "2025-10-15",
      "pendencias_iptu": "OK",
      "pendencias_sienge_inad": "OK",
      "pendencias_sienge": "OK"
    }
  }
]
```

### 13.3 Comandos Úteis

**Executar todos os processos da Etapa 1:**
```bash
python scripts/main_coleta_indices.py
python scripts/main_analise_planilhas.py
python scripts/main_extracao_relatorio_sienge.py
```

**Executar todos os processos da Etapa 2:**
```bash
python scripts/main_reparcelamento_sienge.py
python scripts/main_sienge_emissao_carnes.py
python scripts/main_sicredi.py
```

**Verificar status de contratos:**
```bash
python -c "from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo; import json; print(json.dumps([c for c in repositorio_contratos_arquivo.framework.find_all() if c.get('status') == 'PENDENTE'], indent=2, default=str))"
```

**Atualizar último reajuste (processo auxiliar):**
```bash
python rpa_sienge/atualizar_ultimo_reajuste.py \
  --planilha-id "$PLANILHA_CALCULO_ID" \
  --credenciais "./credentials/gspread-459713-aab8a657f9b0.json" \
  --aba "Base de cálculo" \
  --lote-mes-reajuste "nov.-25" \
  --notificar true
```

**Consultar auditoria de execução:**
```bash
# Listar arquivos de auditoria recentes
ls -lt dados_processamento/auditoria_completa/*.json | head -10

# Ver execução específica
cat dados_processamento/auditoria_completa/RPA_Sienge_20250830_085035_7471.json | jq '.'

# Ver apenas passos de erro
cat dados_processamento/auditoria_completa/RPA_Sienge_20250830_085035_7471.json | jq '.passos[] | select(.categoria == "ERRO")'

# Ver estatísticas de execução consolidada
cat dados_processamento/auditoria_completa/CONSOLIDADO_RPA_Sienge_20250830_085035_7471.json | jq '.estatisticas_finais'
```

### 12.4 Referências PDD

**Todas as seções do PDD foram implementadas:**

- ✅ **Seção 7:** Consulta de índices atualizados (IPCA e IGP-M)
- ✅ **Seção 8:** Verificação Base de Apoio (novos contratos e IPTU)
- ✅ **Seção 9:** Acesso ao ERP Sienge e extração de relatórios
- ✅ **Seção 10:** Registro de reparcelamento, emissão de carnês e importação no Sicredi

**Regras PDD implementadas:**
- ✅ Fórmulas de cálculo de reajuste
- ✅ Regras de elegibilidade (pendências)
- ✅ Regras de contagem de parcelas (anual vs aniversário)
- ✅ Validação de inadimplência (60 dias)
- ✅ Nomenclatura de arquivos de remessa
- ✅ Processo completo de autorização via planilha Google Sheets

**Sistema de Auditoria:**
- ✅ Todos os 7 RPAs principais registram auditoria completa
- ✅ Rastreamento de cada passo de execução
- ✅ Histórico imutável para compliance
- ✅ Ferramenta poderosa para debugging e análise de performance

---

## GLOSSÁRIO

- **RPA:** Robotic Process Automation (Automação de Processos Robóticos)
- **PDD:** Plano de Desenvolvimento Detalhado
- **IPCA:** Índice Nacional de Preços ao Consumidor Amplo
- **IGP-M:** Índice Geral de Preços do Mercado
- **IBGE:** Instituto Brasileiro de Geografia e Estatística
- **FGV:** Fundação Getulio Vargas
- **Sienge:** Sistema ERP utilizado pela empresa
- **Sicredi:** Banco cooperativo utilizado
- **Reparcelamento:** Processo de renegociação de parcelas com correção monetária
- **Carnê:** Documento de cobrança de parcelas
- **Remessa:** Arquivo de cobrança para importação no banco

---

**Fim do Manual**

*Documento gerado em: Outubro 2025*  
*Versão: 1.0*  
*Baseado em: PDD Original Reescrito (12/03/2025)*

