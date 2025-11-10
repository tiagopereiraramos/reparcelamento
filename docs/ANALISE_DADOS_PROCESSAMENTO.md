# ANÁLISE: USO DA PASTA `dados_processamento`

Este documento lista todos os arquivos do projeto que escrevem arquivos JSON dentro da pasta `dados_processamento`.

---

## RESUMO EXECUTIVO

**Total de arquivos identificados:** 8 arquivos principais  
**Total de arquivos JSON gerados:** 10+ tipos diferentes  
**Principais usos:** Persistência de dados, auditoria, rastreamento e fallback

---

## ARQUIVOS QUE ESCREVEM EM `dados_processamento`

### 1. `core/data_manager.py`

**Arquivos JSON gerados:**

1. **`execucoes_rpa.json`**
   - **Linha:** 36-37
   - **Propósito:** Registro de todas as execuções de RPAs
   - **Estrutura:** Lista de objetos com dados de execução
   - **Quando:** Inicializado na criação do DataManager e atualizado durante execuções

2. **`contratos_processados.json`**
   - **Linha:** 38-39
   - **Propósito:** Contratos que foram processados
   - **Estrutura:** Lista de contratos
   - **Quando:** Inicializado na criação do DataManager

3. **`indices_economicos.json`**
   - **Linha:** 40-41
   - **Propósito:** Índices econômicos coletados (IPCA, IGP-M)
   - **Estrutura:** Lista de índices
   - **Quando:** Inicializado na criação do DataManager

4. **`fila_contratos_sienge.json`**
   - **Linha:** 42-43
   - **Propósito:** Fila de contratos para processamento no Sienge
   - **Estrutura:** Objeto com `timestamp_ultima_atualizacao`, `total_contratos`, `status_geral`, `contratos[]`
   - **Quando:** Inicializado na criação do DataManager

5. **`planilhas_extraidas.json`**
   - **Linha:** 44-45
   - **Propósito:** Registro de planilhas extraídas
   - **Estrutura:** Lista de planilhas
   - **Quando:** Inicializado na criação do DataManager

**Método principal:**
- `_salvar_json_seguro()` (linha 777-784): Salva JSON com tratamento de erros

**Observações:**
- Este é o **gerenciador central** de dados do sistema
- Todos os arquivos são inicializados na criação do DataManager
- Usa sistema híbrido MongoDB + JSON (MongoDB principal, JSON como fallback)

---

### 2. `core/base_rpa.py`

**Arquivos JSON gerados:**

1. **`execucao_fallback_{nome_rpa}_{timestamp}.json`**
   - **Linha:** 391
   - **Propósito:** Arquivo de fallback quando há erro na execução do RPA
   - **Estrutura:** Objeto com `timestamp`, `nome_rpa`, `parametros_entrada`, `resultado`, `fallback: True`
   - **Quando:** Quando ocorre erro durante execução e o sistema precisa salvar dados de fallback

**Código relevante:**
```python
arquivo_fallback = f"dados_processamento/execucao_fallback_{self.nome_rpa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(arquivo_fallback, 'w', encoding='utf-8') as f:
    json.dump(dados_execucao, f, indent=2, ensure_ascii=False, default=str)
```

**Observações:**
- Classe base para **todos os RPAs**
- Gera arquivo único por execução com erro
- Usado como mecanismo de segurança para não perder dados em caso de falha

---

### 3. `rpa_sicredi/rpa_sicredi.py`

**Arquivos JSON gerados:**

1. **`processamentos_sicredi.json`**
   - **Linha:** 551
   - **Propósito:** Registro de todos os processamentos realizados no Sicredi
   - **Estrutura:** Lista de objetos com `timestamp`, `dados_processamento`, `tipo: "processamento_sicredi"`, `status: "processado"`
   - **Quando:** Após cada processamento de arquivo de remessa no Sicredi
   - **Método:** `salvar_dados_localmente()` (linha 545-604)

2. **`processamentos_sicredi_temp_{timestamp}.json`**
   - **Linha:** 596
   - **Propósito:** Arquivo temporário criado quando há erro ao salvar o arquivo principal
   - **Estrutura:** Lista com um único objeto de processamento
   - **Quando:** Em caso de erro ao salvar `processamentos_sicredi.json`

**Características especiais:**
- Implementa validação de JSON após escrita
- Cria backup automático se arquivo principal estiver corrompido
- Sanitiza dados antes de salvar (método `_sanitizar_dados_json()`)

**Observações:**
- Este é o **único RPA que mantém histórico persistente** de processamentos
- Implementa sistema robusto de recuperação de erros

---

### 4. `rpa_analise_planilhas/rpa_analise_planilhas.py`

**Arquivos JSON gerados:**

1. **`fila_contratos_sienge.json`**
   - **Linha:** 1472-1477
   - **Propósito:** Fila de contratos gerada após análise de planilhas, pronta para processamento no Sienge
   - **Estrutura:** Lista de contratos com dados completos
   - **Quando:** Após análise completa de planilhas e identificação de contratos elegíveis
   - **Método:** `salvar_fila_localmente()` (linha 1470-1483)

**Código relevante:**
```python
arquivo_fila = os.path.join('dados_processamento', "fila_contratos_sienge.json")
with open(str(arquivo_fila), 'w', encoding='utf-8') as f:
    json.dump(fila_processamento, f, indent=2, ensure_ascii=False)
```

**Observações:**
- Este arquivo é **sobrescrito** a cada execução da análise de planilhas
- Contém todos os contratos identificados para processamento no Sienge
- É usado como entrada para o processo de extração de relatórios Sienge

---

### 5. `core/rastreamento_unificado.py`

**Arquivos JSON gerados:**

1. **`{id_execucao}.json`** (dentro de `dados_processamento/auditoria_completa/`)
   - **Linha:** 38, 296
   - **Propósito:** Arquivo de rastreamento individual por execução
   - **Estrutura:** Objeto com `id_execucao`, `timestamp_inicio`, `passos[]`, `ultimo_passo`, `total_passos`
   - **Quando:** Durante toda a execução, cada passo é adicionado ao arquivo
   - **Método:** `_salvar_json_passo()` (linha 290-296)

2. **`CONSOLIDADO_{id_execucao}.json`** (dentro de `dados_processamento/auditoria_completa/`)
   - **Linha:** 326, 329
   - **Propósito:** Documento consolidado final de toda a execução
   - **Estrutura:** Objeto completo com todos os passos e metadados
   - **Quando:** Ao finalizar a execução
   - **Método:** `_salvar_documento_consolidado()` (linha 323-331)

**Características:**
- Sistema de rastreamento completo de execuções
- Cada passo da execução é registrado incrementalmente
- Arquivo consolidado é gerado ao final
- **821 arquivos JSON** já foram gerados (conforme listagem do diretório)

**Observações:**
- Sistema mais completo de auditoria do projeto
- Permite rastreamento detalhado de cada passo de execução
- Útil para debugging e análise de performance

---

### 6. `rpa_sienge/rpa_sienge.py`

**Arquivos JSON gerados:**

1. **`auditoria_{codigo_cliente}_{timestamp}.json`** (dentro de `dados_processamento/auditoria_pdd/`)
   - **Linha:** 839-844
   - **Propósito:** Auditoria PDD para cada cliente processado
   - **Estrutura:** Objeto com dados de auditoria conforme PDD
   - **Quando:** Após processar relatório de cada cliente
   - **Método:** `_salvar_auditoria_pdd()` (linha 835-846)

2. **`dados_{empresa}_{timestamp}.json`** (dentro de `dados_extraidos/metadados_remessa/`)
   - **Linha:** 4965-4970
   - **Propósito:** Metadados de contratos incluídos em arquivo de remessa
   - **Estrutura:** Objeto com `total_contratos_processados`, `empresa`, `arquivo_remessa`, lista de contratos
   - **Quando:** Após gerar arquivo de remessa para uma empresa
   - **Método:** `_salvar_metadados_remessa()` (linha 4960-4974)

**Observações:**
- `rpa_sienge.py` é um arquivo grande com múltiplas funcionalidades
- Gera arquivos de auditoria para cada cliente
- Gera metadados para cada arquivo de remessa criado

---

### 7. `scripts/main_extracao_relatorio_sienge.py`

**Arquivos JSON gerados:**

1. **`resultados_processamento.json`** (não está em `dados_processamento`, mas processa dados relacionados)
   - **Linha:** 358
   - **Propósito:** Resultado do processamento de extração de relatórios
   - **Estrutura:** Depende do resultado do processamento
   - **Quando:** Após processar regras de extração

**Observações:**
- Este arquivo não escreve diretamente em `dados_processamento`
- Mas processa dados que podem ser salvos lá por outros módulos

---

### 8. `rpa_sienge/processar_regras_extracao_inadimplencia.py`

**Arquivos JSON gerados:**

1. **`resultados_processamento.txt`** (não é JSON, mas mencionado)
   - **Linha:** 1884
   - **Propósito:** Resumo textual do processamento (contém JSON dentro do texto)
   - **Estrutura:** Texto com JSON embutido
   - **Quando:** Após processar todas as regras de extração

**Observações:**
- Não escreve diretamente JSON em `dados_processamento`
- Mas gera arquivo que pode ser usado por outros módulos

---

## RESUMO DE ARQUIVOS JSON POR ARQUIVO ORIGEM

### Por Módulo Core

| Arquivo | Arquivos JSON Gerados | Quantidade |
|---------|----------------------|------------|
| `core/data_manager.py` | 5 arquivos principais | 5 |
| `core/base_rpa.py` | 1 arquivo de fallback | 1 (por execução com erro) |
| `core/rastreamento_unificado.py` | 2 tipos (individual + consolidado) | 821+ arquivos |

### Por RPA

| Arquivo | Arquivos JSON Gerados | Quantidade |
|---------|----------------------|------------|
| `rpa_sicredi/rpa_sicredi.py` | 2 tipos (principal + temp) | 1-2 por execução |
| `rpa_analise_planilhas/rpa_analise_planilhas.py` | 1 arquivo (fila) | 1 por execução |
| `rpa_sienge/rpa_sienge.py` | 2 tipos (auditoria + metadados) | Múltiplos por execução |

---

## ESTRUTURA DE DIRETÓRIOS

```
dados_processamento/
├── execucoes_rpa.json                    # DataManager
├── contratos_processados.json            # DataManager
├── indices_economicos.json              # DataManager
├── fila_contratos_sienge.json           # DataManager + RPA Análise
├── planilhas_extraidas.json              # DataManager
├── processamentos_sicredi.json          # RPA Sicredi
├── processamentos_sicredi.json.backup_corrupted  # Backup RPA Sicredi
├── auditoria_completa/                   # Rastreamento Unificado
│   ├── {id_execucao}.json               # 821 arquivos
│   └── CONSOLIDADO_{id_execucao}.json   # Arquivos consolidados
└── execucao_fallback_{rpa}_{ts}.json    # BaseRPA (quando há erro)
```

---

## PADRÕES IDENTIFICADOS

### 1. **Inicialização de Arquivos Base**
- `data_manager.py` inicializa 5 arquivos base na criação
- Todos começam como estruturas vazias ou com valores padrão

### 2. **Sistema de Fallback**
- `base_rpa.py` cria arquivos de fallback em caso de erro
- `rpa_sicredi.py` cria arquivos temporários em caso de erro

### 3. **Rastreamento Detalhado**
- `rastreamento_unificado.py` mantém histórico completo de execuções
- Cada passo é registrado incrementalmente

### 4. **Persistência de Processamentos**
- `rpa_sicredi.py` mantém histórico persistente de processamentos
- Cada processamento é adicionado a uma lista

### 5. **Sobrescrita vs Append**
- **Sobrescrita:** `fila_contratos_sienge.json` (análise de planilhas)
- **Append:** `processamentos_sicredi.json` (RPA Sicredi)
- **Individual:** Arquivos de auditoria e fallback (um por execução)

---

## RECOMENDAÇÕES

### 1. **Consolidação**
- Considerar consolidar alguns arquivos similares
- `fila_contratos_sienge.json` é usado por múltiplos módulos

### 2. **Limpeza**
- Implementar rotina de limpeza para arquivos antigos de auditoria
- Considerar arquivamento de arquivos de fallback antigos

### 3. **Documentação**
- Documentar estrutura de cada arquivo JSON
- Criar schema de validação para arquivos críticos

### 4. **Monitoramento**
- Monitorar tamanho dos arquivos JSON
- Implementar alertas para arquivos muito grandes

### 5. **Backup**
- Implementar backup automático de arquivos críticos
- Considerar backup incremental para `processamentos_sicredi.json`

---

## ARQUIVOS CRÍTICOS

### Alta Prioridade (Não perder dados)
1. **`fila_contratos_sienge.json`** - Fila principal de processamento
2. **`processamentos_sicredi.json`** - Histórico de processamentos
3. **`execucoes_rpa.json`** - Registro de execuções

### Média Prioridade (Auditoria)
4. **`auditoria_completa/{id_execucao}.json`** - Rastreamento detalhado
5. **`auditoria_pdd/auditoria_{cliente}_{timestamp}.json`** - Auditoria PDD

### Baixa Prioridade (Fallback/Temporário)
6. **`execucao_fallback_{rpa}_{timestamp}.json`** - Arquivos de fallback
7. **`processamentos_sicredi_temp_{timestamp}.json`** - Arquivos temporários

---

## CONCLUSÃO

A pasta `dados_processamento` é usada por **8 módulos principais** para:
- Persistência de dados de processamento
- Auditoria e rastreamento
- Fallback em caso de erros
- Histórico de execuções

O sistema implementa múltiplas camadas de segurança:
- Fallback automático em caso de erro
- Validação de JSON após escrita
- Backup automático de arquivos corrompidos
- Sistema híbrido MongoDB + JSON

**Total de arquivos JSON gerados:** 10+ tipos diferentes  
**Total de arquivos na pasta:** 821+ arquivos (principalmente em `auditoria_completa/`)

---

**Documento gerado em:** Outubro 2025  
**Baseado em:** Análise completa do código-fonte

