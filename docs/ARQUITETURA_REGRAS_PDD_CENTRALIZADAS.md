
# ARQUITETURA DE REGRAS PDD CENTRALIZADAS

## 📋 Resumo da Reestruturação

**Data:** 18/06/2025  
**Objetivo:** Centralizar todas as regras PDD em local compartilhado para facilitar manutenção

## 🏗️ Nova Estrutura

### Antes (Descentralizado)
```
rpa_sienge/
├── processador_regras_pdd.py  # ❌ Isolado no RPA Sienge
└── rpa_sienge.py

rpa_analise_planilhas/
├── rpa_analise_planilhas.py   # ❌ Sem acesso às regras PDD
```

### Depois (Centralizado)
```
core/
├── processador_regras_pdd.py  # ✅ CENTRALIZADO - Acesso por todos RPAs
├── data_manager.py
└── base_rpa.py

rpa_sienge/
├── rpa_sienge.py             # ✅ Importa de core.processador_regras_pdd
└── teste_sienge.py

rpa_analise_planilhas/
├── rpa_analise_planilhas.py  # ✅ Agora pode usar regras PDD
└── teste_analise_planilhas.py # ✅ Teste completo com regras 9.1.1
```

## 🎯 Benefícios da Centralização

### 1. **Manutenibilidade**
- ✅ **Um local único** para todas as regras PDD
- ✅ **Atualizações centralizadas** afetam todos os RPAs
- ✅ **Versionamento consistente** das regras de negócio

### 2. **Reutilização**
- ✅ **Todos os RPAs** podem usar as mesmas regras
- ✅ **Consistência** nas validações entre sistemas
- ✅ **Redução de código duplicado**

### 3. **Testabilidade**
- ✅ **Testes centralizados** das regras de negócio
- ✅ **Cobertura completa** das regras PDD 9.1.1
- ✅ **Validação com dados reais** (CSV do Sienge)

## 📊 Regras PDD 9.1.1 Implementadas

### ✅ **REGRA CRÍTICA - Inadimplência PDD 7.3.2**
```python
# REGRA: >= 3 CT vencidas = INADIMPLENTE
if qtd_ct_vencidas >= 3:
    pode_reparcelar = False
    status = "INADIMPLENTE"
```

### ✅ **REGRA 1 - Dia de Vencimento**
- Identifica dia mais comum nas parcelas CT a vencer
- Base para cálculo do primeiro vencimento

### ✅ **REGRA 2 - Primeiro Vencimento**
- Calcula data do primeiro vencimento do novo carnê
- Considera tipo de reajuste (ANUAL/ANIVERSÁRIO)

### ✅ **REGRA 3 - Valor da Parcela Atual**
- Determina valor base das parcelas CT
- Usado para detectar irregularidades

### ✅ **REGRA 4 - Parcelas Irregulares**
- Identifica parcelas com valores divergentes
- Tolerância de 1% para diferenças

### ✅ **REGRA 5 - Parcelas a Vencer**
- Conta CT e IPTU pendentes
- Calcula valores totais

### ✅ **REGRA 6 - Parcelas Vencidas CT**
- Valida inadimplência (reutiliza regra crítica)
- Lista detalhada de CT vencidas

### ✅ **REGRA 7 - Pendências IPTU**
- Identifica IPTU vencido
- Não impede reparcelamento (conforme PDD)

### ✅ **REGRA 8 - Validação Final**
- Consolidação de todas as regras
- Resultado estruturado para automação

## 🔄 Fluxo de Importação

### Para RPAs:
```python
# Todos os RPAs agora importam do mesmo local
from core.processador_regras_pdd import ProcessadorRegrasNegocio

# Uso consistente
processador = ProcessadorRegrasNegocio()
resultado = processador.processar_dados_cliente_completo(df, cliente, titulo)
```

### Para Testes:
```python
# Testes também usam a versão centralizada
from core.processador_regras_pdd import ProcessadorRegrasNegocio

# Testes com dados reais CSV
df_csv = pd.read_csv("saldo_devedor_presente.csv")
resultado = processador.processar_dados_cliente_completo(df_csv, "CLIENTE", "2239")
```

## 📄 Adaptação para CSV Real do Sienge

### Estrutura de Colunas Suportadas:
```csv
Título,Parcela/Condição,Documento,Cliente,Status da parcela,
Data vencimento,Valor a receber,Valor original,Indexador,Tipo condição
```

### Tipos de Documento Reconhecidos:
- **CT**: Parcelas do contrato (críticas para inadimplência)
- **IPTU**: Impostos (não impedem reparcelamento)
- **REC/FAT**: Recebimentos/Faturamentos (se existirem)

### Status Reconhecidos:
- **Paga/Quitada/Liquidada**: Parcela quitada
- **A vencer**: Parcela pendente
- **Outros**: Tratados como pendentes

## 🧪 Testes Implementados

### 1. **Teste Completo Regras PDD + CSV Real**
```bash
# Executa todas as 8 regras usando dados reais
python rpa_analise_planilhas/teste_analise_planilhas.py
# Opção: 1
```

### 2. **Teste Comparativo (Google Sheets vs CSV)**
```bash
# Compara ambos os métodos
# Opção: 2
```

### 3. **Teste Validação Estrutura CSV**
```bash
# Valida se CSV está no formato correto
# Opção: 3
```

## 📁 Arquivos Afetados

### Criados:
- ✅ `core/processador_regras_pdd.py` - **NOVO** (centralizado)
- ✅ `docs/ARQUITETURA_REGRAS_PDD_CENTRALIZADAS.md` - **NOVA** documentação

### Modificados:
- 🔄 `rpa_analise_planilhas/teste_analise_planilhas.py` - Teste completo com regras PDD
- 🔄 `rpa_sienge/rpa_sienge.py` - Import atualizado para core
- 🔄 `rpa_sienge/teste_sienge.py` - Import atualizado (se necessário)

### Mantidos (Compatibilidade):
- ✅ `rpa_sienge/processador_regras_pdd.py` - Pode ser removido após testes
- ✅ APIs existentes mantidas através de wrappers

## 🚀 Próximos Passos

1. **Testar a nova estrutura:**
   ```bash
   python rpa_analise_planilhas/teste_analise_planilhas.py
   ```

2. **Validar todos os RPAs:**
   - RPA Sienge
   - RPA Análise Planilhas
   - Outros RPAs futuros

3. **Remover arquivo antigo** (após confirmação):
   ```bash
   # Após testes bem-sucedidos
   rm rpa_sienge/processador_regras_pdd.py
   ```

4. **Documentar para desenvolvedores:**
   - Atualizar READMEs
   - Exemplos de uso
   - Guias de migração

## ✅ Conclusão

A centralização das regras PDD na pasta `core/` proporciona:

- 🎯 **Facilidade de manutenção** por desenvolvedores
- 🔄 **Reutilização** entre todos os RPAs
- 📊 **Testes mais robustos** com dados reais
- 🏗️ **Arquitetura mais limpa** e organizada
- 📋 **Documentação centralizada** das regras de negócio

**Recomendação:** Executar testes completos antes de remover arquivos antigos.
