# Documento de Definição de Processo (PDD) - Correlacionado com Estrutura

> **Documento de Definição de Processo (PDD)**
>
> **Cliente:** J M
>
> **Processos:**
>
> **1 = >** Reparcelamento de Contratos dentro do Sistema Sienge
>
> **2 = >** Emissão de Boletos
>
> **Analista Responsável:** Patricia Sena
>
> **Data da última atualização:** 12/03/2025
>
> **Versão Correlacionada:** PDD adaptado para estrutura RPA implementada

---

## 1. Objetivo

O presente Plano de Desenvolvimento Detalhado (PDD) visa documentar e otimizar o processo de Reparcelamento de Contratos dentro do Sistema Sienge e Emissão de Boletos, garantindo a padronização do fluxo de trabalho, a precisão nas informações e a eficiência operacional.

### 1.1 - Objetivo do Documento de Definição de Processo

O objetivo deste documento é servir como guia para o desenvolvimento, garantindo o pleno entendimento das etapas e do fluxo do processo e consequentemente a efetividade da automação.

**✅ CORRELAÇÃO COM ESTRUTURA:** Este PDD foi adaptado para correlacionar com a estrutura RPA implementada, onde cada RPA tem responsabilidades específicas e bem definidas.

---

## 2. Acessos e Recursos Necessários

### 2.1 Portais Externos
- **Portal IBGE** - Verificação de última atualização do IPCA
- **Portal FGV** - Verificação de última atualização do IGPM

### 2.2 Planilhas Google Sheets
- **BASE DE CÁLCULO REPARCELAMENTO 2025.xlsx** - Planilha principal de cálculo
- **Base de apoio** - Editada pelo analista financeiro JM com:
  - Novos contratos
  - Consulta mensal de pendência de IPTU

### 2.3 Sistemas
- **ERP Sienge** - Link: https://jmservicos.sienge.com.br/sienge/
- **Conta bancária Sicredi** - Link: https://www.sicredi.com.br/home/
- **Conta de e-mail** - robo@rorato.adm.br

**✅ CORRELAÇÃO COM ESTRUTURA:** 
- `rpa_coleta_indices.py` - Acessa IBGE e FGV
- `rpa_analise_planilhas.py` - Processa planilhas Google Sheets
- `rpa_sienge.py` - Acessa sistema Sienge
- `rpa_sicredi.py` - Acessa banco Sicredi

---

## 3. Escopo

O escopo do projeto consiste na automação do processo de reparcelamento de contratos dos empreendimentos negociados pelas unidades indicadas.

O processo abrange desde a validação dos índices de indexação IPCA e IGP-M nos portais do IBGE e da FGV, até a emissão dos boletos atualizados de cada empresa no banco Sicredi.

**✅ CORRELAÇÃO COM ESTRUTURA:** O processo é dividido em 4 RPAs principais, cada um com responsabilidades específicas conforme implementado.

---

## 4. Equipe Envolvida

- **Sponsor:** Marcely
- **Donas do Processo:** Marcely e Tatiane
- **Analista Responsável:** Patricia Sena

**✅ CORRELAÇÃO COM ESTRUTURA:** A equipe trabalha em conjunto com os RPAs automatizados, onde cada RPA tem funções específicas e bem definidas.

---

## 5. Indicação de Melhorias no Processo

### 5.1 Unificação de Dados
- Unificação dos dados na planilha BASE DE CÁLCULO REPARCELAMENTO 2025.xlsx
- Disponibilização de planilha Base de apoio atualizada pela JM

### 5.2 Definição de Aplicação
- Tipo de juros com a opção "Nenhum"

**✅ CORRELAÇÃO COM ESTRUTURA:** As melhorias foram implementadas nos RPAs correspondentes, com validações e processamentos automatizados.

---

## 6. Descrição Detalhada do Processo

### 6.1 Recorrência de execução

A execução do processo ocorre mensalmente com duas etapas de execução:

1. **1° Etapa** - Ocorre no 11° dia do mês
   - Abrange desde verificação dos índices até o envio de cópia da planilha base de cálculo para validação

2. **2° Etapa** - Ocorre até o 16º dia do mês
   - Abrange desde a leitura do e-mail de retorno do analista financeiro com ok para lançamentos em sistema, até a conclusão da emissão dos boletos no banco para todas as empresas

**✅ CORRELAÇÃO COM ESTRUTURA:** 
- Etapa 1: `rpa_coleta_indices.py` + `rpa_analise_planilhas.py`
- Etapa 2: `rpa_sienge.py` + `rpa_sicredi.py`

---

## 7. Consulta de índices atualizados

### 7.1 Índice IPCA

**Fonte:** https://www.ibge.gov.br/explica/inflacao.php

**Processo:**
1. Acessar página para extrair publicação do índice atualizado
2. Verificar se foi realizada a publicação do índice referente ao mês anterior
3. Registrar no log o valor "acumulado de 12 meses"
4. Inserir na aba IPCA da planilha de cálculo

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_coleta_indices.py` com:
- Validação de disponibilidade do índice
- Retry automático por 3 dias
- Inserção na planilha Google Sheets
- Logs detalhados

### 7.2 Índice IGPM

**Fonte:** https://portalibre.fgv.br/taxonomy/term/94

**Processo:**
1. Verificar disponibilização de publicação do índice para o mês vigente
2. Acessar documento PDF disponibilizado
3. Registrar no log o índice do IGP-M acumulado de 12 meses
4. Inserir na aba IGPM da planilha base de cálculo

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_coleta_indices.py` com:
- Tratamento de variações de nomenclatura de arquivos
- Extração de dados de PDF
- Validação de formato de dados
- Inserção na planilha Google Sheets

---

## 8. Verificação Base de apoio

### 8.1 - Verificação de novos contratos

**Processo:**
1. Acessar a planilha Base de apoio na aba NOVOS CONTRATOS
2. Copiar linhas onde constarem novo lançamentos
3. Colar na aba Base de cálculo da planilha BASE DE CÁLCULO REPARCELAMENTO 2025.xlsx

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_analise_planilhas.py` com:
- Conexão com Google Sheets
- Validação de dados obrigatórios
- Auditoria completa de contratos
- Logs detalhados linha por linha
- Relatório de contratos aprovados/rejeitados

### 8.2 - Verificação de consulta de IPTU

**Processo:**
1. Acessar aba Consulta IPTU
2. Verificar para cada cliente/Título a atualização data consulta do IPTU
3. Copiar informação da coluna IPTU PENDÊNCIAS PMFI para clientes cuja "Data de consulta" é do mês vigente
4. Colar na coluna correspondente da Base de cálculo

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_analise_planilhas.py` com:
- Validação de data de consulta (mês vigente)
- Identificação de pendências IPTU (NÃO bloqueia contratos)
- Atualização de colunas na planilha
- Relatório de pendências no e-mail
- Logs detalhados de cada atualização

---

## 9. Acesso ao ERP - Sienge

### 9.1 Acesso aos relatórios Saldo devedor Presente - Sienge

**Processo:**
1. Acessar menu Financeiro > Relatório > Extrato > Saldo devedor Presente
2. Informar nome do cliente no campo Cliente
3. Clicar em Consultar > Gerar relatório
4. Selecionar tipo de documento > Exportar
5. Repetir para cada cliente registrado no log

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_sienge.py` com:
- Login automatizado no sistema
- Navegação por menus
- Download de relatórios
- Compilação de arquivos
- Tratamento de erros e timeouts

### 9.1.1 Leitura e extração de dados do relatório

**Dados extraídos:**
- Dia de vencimento das parcelas
- Valor da parcela atual
- Quantidade de parcelas a vencer
- Quantidade de parcelas vencidas
- Verificação de inadimplência (60 dias antes)
- Verificação de pendências (REC/FAT)

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_sienge.py` com:
- Processamento de planilhas baixadas
- Extração de dados específicos
- Validação de pendências SIENGE INAD
- Validação de pendências SIENGE (REC/FAT)
- Aplicação de regras PDD para elegibilidade

### 9.1.2 Atualização dos dados captados em planilha base de cálculo

**Colunas atualizadas:**
- PENDÊNCIAS SIENGE INAD
- PENDÊNCIAS SIENGE
- Parcelas a vencer
- Valor da Parcela Base
- Dia de vencimento de parcelas
- 1º vencimento carnê

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_sienge.py` com:
- Atualização de planilha Google Sheets
- Validação de dados antes da inserção
- Logs detalhados de cada atualização
- Tratamento de erros de conexão

---

## 10. Retorno de validação

### 10.1 Registro do reparcelamento no Sistema Sienge

**Processo:**
1. Acessar menu Financeiro > Contas a receber > Reparcelamento > Inclusão
2. Preencher Número do título em reparcelamento > Consultar
3. Selecionar documentos > Próximo
4. Marcar todas as parcelas > Desmarcar parcelas com vencimento <= mês vigente
5. Preencher informações do reparcelamento
6. Salvar reparcelamento

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_sienge.py` com:
- Navegação automatizada no sistema
- Seleção inteligente de parcelas
- Preenchimento de formulários
- Validação de dados antes do salvamento
- Tratamento de mensagens de erro

### 10.2 Emissão de carnê - Sistema Sienge

**Regras de geração:**
- Apenas para clientes com status OK nas colunas de Pendência
- PENDÊNCIAS PMFI: Verificar atualização na planilha de apoio
- PENDÊNCIAS SIENGE INAD: Não gerar se houver inadimplência
- PENDÊNCIAS SIENGE: Não gerar se houver pendências REC/FAT

**Processo:**
1. Acessar Financeiro > Contas a Receber > Cobrança Escritural > Geração de Arquivos de remessa
2. Preencher período (primeiro dia do próximo mês)
3. Selecionar empresa
4. Configurar opções de remessa
5. Gerar arquivo de remessa

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_sienge.py` com:
- Validação rigorosa de pendências antes da geração
- Geração de arquivos de remessa por empresa
- Nomenclatura automática de arquivos
- Logs detalhados de cada geração

### 10.3 - Acesso ao Banco - Importação dos arquivos de remessa

**Processo:**
1. Acessar página do banco Sicredi
2. Login com CNPJ da empresa
3. Acessar aba cobrança > Transferência de Arquivos
4. Selecionar arquivo gerado no Sienge
5. Importar arquivo no sistema bancário
6. Repetir para todas as empresas

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado em `rpa_sicredi.py` com:
- Login automatizado no banco
- Upload de arquivos de remessa
- Validação de importação
- Loop por todas as empresas
- Logs detalhados de cada importação

---

## 11. Considerações Finais

Ao final da execução do reparcelamento do mês vigente o robô enviará o relatório com o registro da execução e o arquivo correspondente para a manutenção do histórico.

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado com:
- Sistema de notificações centralizado
- Relatórios detalhados por RPA
- Histórico de execuções
- Tratamento de exceções

---

## 12. Exceções e Tratamentos de Erros

### 12.1 Situações excepcionais

Será realizado o envio de log de erro sempre que o robô:
- Identificar divergências de informações
- Não encontrar os dados necessários para a execução do processo
- Sofrer alguma quebra

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado com:
- Sistema de logs avançado (`core/logger_avancado.py`)
- Rastreamento unificado (`core/rastreamento_unificado.py`)
- Notificações de erro (`core/notificacoes_simples.py`)
- Tratamento de exceções em cada RPA

---

## 13. Comunicação Centralizada em Projetos

- **Trajetória Consultoria** - +55 41 9265-0701
- **Grupo de WhatsApp** com envolvidos nos processos

**✅ CORRELAÇÃO COM ESTRUTURA:** Implementado com:
- Sistema de notificações integrado
- Relatórios automáticos por e-mail
- Comunicação centralizada via WhatsApp

---

## 14. Estrutura RPA Implementada

### 14.1 RPAs Principais

#### `rpa_coleta_indices.py`
**Responsabilidades:**
- Coleta de índices IPCA do IBGE
- Coleta de índices IGPM da FGV
- Inserção na planilha Google Sheets
- Validação de disponibilidade de dados

#### `rpa_analise_planilhas.py`
**Responsabilidades:**
- Processamento de planilha Base de apoio
- Verificação de novos contratos
- Verificação de pendências IPTU (identifica, não bloqueia)
- Geração de fila para extração no Sienge
- Relatório de pendências no e-mail

#### `rpa_sienge.py`
**Responsabilidades:**
- Login no sistema Sienge
- Download de relatórios financeiros
- Extração de dados dos relatórios
- Validação de pendências SIENGE INAD (60 dias antes)
- Validação de pendências SIENGE (REC/FAT)
- Aplicação de regras PDD para elegibilidade
- Reparcelamento de contratos
- Geração de carnês (apenas para adimplentes)

#### `rpa_sicredi.py`
**Responsabilidades:**
- Login no banco Sicredi
- Importação de arquivos de remessa
- Loop por todas as empresas
- Validação de importação

### 14.2 Componentes de Suporte

#### `core/base_rpa.py`
- Classe base para todos os RPAs
- Sistema de logs unificado
- Tratamento de erros padronizado

#### `core/data_manager.py`
- Gerenciamento de dados MongoDB + JSON
- Persistência de filas de processamento
- Controle de status de contratos

#### `core/notificacoes_simples.py`
- Sistema de notificações por e-mail
- Relatórios automáticos
- Comunicação com analistas

#### `core/rastreamento_unificado.py`
- Rastreamento de execução
- Logs detalhados
- Auditoria de processos

---

## 15. Fluxo de Execução Correlacionado

### 15.1 Etapa 1 (11º dia do mês)

1. **`rpa_coleta_indices.py`**
   - Coleta IPCA do IBGE
   - Coleta IGPM da FGV
   - Insere na planilha Google Sheets

2. **`rpa_analise_planilhas.py`**
   - Processa planilha Base de apoio
   - Identifica novos contratos
   - Verifica pendências IPTU
   - Gera fila para extração
   - Envia relatório por e-mail

### 15.2 Etapa 2 (16º dia do mês)

3. **`rpa_sienge.py`**
   - Processa fila de contratos
   - Extrai relatórios financeiros
   - Valida pendências SIENGE
   - Aplica regras PDD
   - Executa reparcelamentos
   - Gera carnês (apenas adimplentes)

4. **`rpa_sicredi.py`**
   - Importa arquivos de remessa
   - Processa todas as empresas
   - Valida importações

---

## 16. Regras PDD Implementadas

### 16.1 Elegibilidade para Reparcelamento
- **Todos os contratos podem ser reparcelados** (conforme PDD)
- **Carnê apenas para adimplentes** (sem pendências)

### 16.2 Validação de Pendências
- **PENDÊNCIAS PMFI (IPTU):** Identificadas pelo `rpa_analise_planilhas.py`
- **PENDÊNCIAS SIENGE INAD:** Validadas pelo `rpa_sienge.py` (60 dias antes)
- **PENDÊNCIAS SIENGE (REC/FAT):** Validadas pelo `rpa_sienge.py`

### 16.3 Controle de Processamento
- **Status granular:** PENDENTE, EM_PROCESSAMENTO, CONCLUIDO, ERRO
- **Tentativas automáticas:** Máximo 3 tentativas por contrato
- **Fallback:** Sistema híbrido MongoDB + JSON

---

## 17. Monitoramento e Relatórios

### 17.1 Logs Detalhados
- Logs linha por linha de cada atualização
- Rastreamento de cada contrato processado
- Relatórios de pendências identificadas

### 17.2 Notificações Automáticas
- E-mail de sucesso com relatório completo
- E-mail de erro com detalhes do problema
- Relatório de pendências IPTU

### 17.3 Auditoria Completa
- Histórico de todas as execuções
- Status de cada contrato processado
- Estatísticas de processamento

---

**✅ CORRELAÇÃO TOTAL IMPLEMENTADA**

Este PDD foi completamente correlacionado com a estrutura RPA implementada, garantindo que cada responsabilidade esteja claramente definida e implementada no RPA correto, com logs detalhados, validações rigorosas e conformidade total com as regras do PDD original. 