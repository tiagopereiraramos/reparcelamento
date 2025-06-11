
# 📊 ANÁLISE DETALHADA DA PLANILHA REAL

## 📁 Arquivo: `saldo_devedor_presente-20250610-093716.xlsx`
## 📖 Baseado em: **PDD_Reparcelamento_Sienge.pdf**

---

## 📚 CORRELAÇÃO COM PDD

### 🎯 **Relatório Oficial Conforme PDD**
> **📖 REFERÊNCIA PDD:** Página 15, Seção 7.3.1
> 
> *"O RPA deve acessar o relatório 'Saldo Devedor Presente' no Sienge através do caminho: Financeiro > Contas a Receber > Relatórios > Saldo Devedor Presente."*

**✅ CONFIRMAÇÃO:** O arquivo analisado corresponde EXATAMENTE ao relatório especificado no PDD.

---

## 🔍 ESTRUTURA IDENTIFICADA

### 📊 **Informações Gerais**
- **Total de registros:** 26 linhas
- **Total de colunas:** 39 campos
- **Tamanho do arquivo:** 10.224 bytes
- **Formato:** Excel (.xlsx)

### 📋 **Colunas Identificadas** (39 campos)

#### 🟢 **GRUPO 1: IDENTIFICAÇÃO** (Campos-chave)
1. `Título` - Identificador único do contrato
2. `Parcela/Sequencial` - Número sequencial da parcela  
3. `Parcela/Condição` - **CRÍTICO:** Tipo da parcela (CT, REC, FAT)
4. `Documento` - Número do documento
5. `Nº documento` - Número complementar
6. `Cód. cliente` - Código do cliente
7. `Cliente` - Nome completo do cliente

#### 🟡 **GRUPO 2: EMPRESA/CENTRO DE CUSTO**
8. `Cód. empresa` - Código da empresa
9. `Empresa` - Nome da empresa
10. `Cód. centro de custo` - Código do centro de custo
11. `Centro de custo` - Nome do centro de custo

#### 🔴 **GRUPO 3: STATUS E CONDIÇÕES** (Validação PDD)
12. `Status da parcela` - **CRÍTICO:** Status atual (Quitada, Pendente, etc.)
13. `Tipo condição` - Tipo de condição de pagamento
14. `Data vencimento` - **CRÍTICO:** Data de vencimento da parcela
15. `Data base de juros` - Data base para cálculo de juros
16. `Data base correção` - Data base para correção monetária
17. `Data correção` - Data da última correção
18. `Data da baixa` - Data da baixa (se houver)

#### 💰 **GRUPO 4: VALORES FINANCEIROS** (Cálculos)
19. `Valor original` - **CRÍTICO:** Valor original da parcela
20. `Valor atualizado` - Valor com atualizações
21. `Valor corrigido` - Valor com correções aplicadas
22. `Valor a receber` - **CRÍTICO:** Valor atual pendente
23. `Valor da baixa` - Valor baixado (se houver)
24. `Recebimento líquido` - Valor líquido recebido

#### 📈 **GRUPO 5: CORREÇÕES E JUROS**
25. `Indexador` - **CRÍTICO:** Índice usado (deve ser IGP-M)
26. `Correção monetária` - Valor da correção aplicada
27. `Juros contratuais` - Valor dos juros contratuais
28. `Juros %` - **CRÍTICO:** Percentual de juros (deve ser 8%)
29. `Tipo de juros` - **CRÍTICO:** Tipo (deve ser "Fixo")
30. `Juros de mora` - Valor dos juros de mora

#### ⚖️ **GRUPO 6: PENALIDADES E DESCONTOS**
31. `Taxa administrativa` - Taxa administrativa aplicada
32. `Seguro` - Valor do seguro
33. `Multa %` - Percentual de multa
34. `Valor de acréscimo` - Valor de acréscimos
35. `Dias de atraso` - **CRÍTICO:** Quantidade de dias em atraso
36. `Dias para desconto VP` - Dias para desconto valor presente
37. `Juros VP %` - Percentual juros valor presente
38. `Valor presente` - Valor presente calculado
39. `Valor desconto comercial` - Valor do desconto comercial

---

## 🎯 CAMPOS CRÍTICOS PARA REGRAS PDD

### 🚨 **INADIMPLÊNCIA (Regra Principal PDD)**
> **📖 REFERÊNCIA PDD:** Página 16, Seção 7.3.2
> 
> *"REGRA FUNDAMENTAL: Cliente com 3 (três) ou mais parcelas do tipo CT (Contrato) vencidas será considerado INADIMPLENTE e NÃO poderá ter seu contrato reparcelado."*

```sql
-- Lógica de validação CONFORME PDD Página 16:
WHERE "Parcela/Condição" LIKE '%CT%'  -- Apenas parcelas CT (PDD)
  AND "Status da parcela" != 'Quitada'  -- Não quitadas
  AND "Data vencimento" < TODAY()       -- Vencidas
-- SE COUNT >= 3 → INADIMPLENTE (PDD Regra Rígida)
```

**Campos utilizados CONFORME PDD:**
- `Parcela/Condição` → Filtrar tipo "CT" (PDD Página 16)
- `Status da parcela` → Excluir "Quitadas"  
- `Data vencimento` → Comparar com data atual
- **LIMITE:** 3 parcelas CT = INADIMPLENTE (PDD Página 16)

### 💰 **CÁLCULO SALDO (Correção IGP-M CONFORME PDD)**
> **📖 REFERÊNCIA PDD:** Página 17, Seção 7.3.3
> 
> *"O cálculo do novo saldo deve OBRIGATORIAMENTE utilizar o índice IGP-M (Índice Geral de Preços do Mercado), aplicando a fórmula: Novo Saldo = Saldo Atual × (1 + IGP-M/100). O uso de IPCA ou qualquer outro índice é VEDADO para reparcelamentos."*

```sql
-- Soma do saldo atual:
SUM("Valor a receber") WHERE "Status da parcela" != 'Quitada'

-- Aplicar correção CONFORME PDD Página 17:
Novo_Saldo = Saldo_Atual × (1 + IGP-M/100)  -- FÓRMULA OFICIAL PDD
-- IMPORTANTE: IPCA é VEDADO (PDD Página 17)
```

**Campos utilizados CONFORME PDD:**
- `Valor a receber` → Saldo atual pendente
- `Status da parcela` → Filtrar pendentes
- **ÍNDICE OBRIGATÓRIO:** IGP-M (PDD Página 17)
- **ÍNDICE VEDADO:** IPCA (PDD Página 17)

### ⚙️ **CONFIGURAÇÃO SIENGE (Parâmetros IMUTÁVEIS PDD)**
> **📖 REFERÊNCIA PDD:** Página 17, Seção 7.3.3 - Parâmetros Fixos
> 
> *"Configurações obrigatórias no Sienge: Tipo Condição: PM (Pagamento Mensal), Indexador: IGP-M, Tipo de Juros: Fixo, Percentual Juros: 8,0% (oito por cento). Estas configurações são IMUTÁVEIS conforme política da empresa."*

**Campos que devem ser alterados CONFORME PDD:**
- `Indexador` → Trocar para "IGP-M" (OBRIGATÓRIO PDD Página 17)
- `Juros %` → Trocar para "8.0" (FIXO PDD Página 17)
- `Tipo de juros` → Trocar para "Fixo" (IMUTÁVEL PDD Página 17)
- `Tipo condição` → Trocar para "PM" (Pagamento Mensal PDD Página 17)

### 🚨 **ATENÇÃO - Política da Empresa:**
> **📖 REFERÊNCIA PDD:** Página 17, Seção 7.3.3
> 
> *"Estas configurações são IMUTÁVEIS conforme política da empresa."*

---

## 📊 ANÁLISE DOS DADOS REAIS

### 🔍 **Análise do Arquivo Carregado:**
```
✅ REGRA CARREGAMENTO: ARQUIVO_EXCEL_VALIDO
   📋 Critério: Arquivo deve existir e ser legível
   📊 Valor avaliado: saldo_devedor_presente-20250610-093716.xlsx
   🎯 Resultado: Carregado com sucesso - 26 registros
```

### ✅ **Validação Estrutural:**
```
✅ REGRA VALIDACAO_ESTRUTURA: COLUNAS_OBRIGATORIAS
   📋 Critério: Arquivo deve conter colunas essenciais
   📊 Valor avaliado: ['Parcela/Sequencial', 'Cód. centro de custo', 'Valor original', 'Documento', 'Status da parcela']
   🎯 Resultado: Encontradas 5/5 colunas obrigatórias
```

### 🎯 **Validação Inadimplência:**
```
✅ REGRA VALIDACAO_ELEGIBILIDADE: LIMITE_INADIMPLENCIA_PDD
   📋 Critério: Cliente com 3 ou mais parcelas CT vencidas = INADIMPLENTE
   📊 Valor avaliado: 0 parcelas CT vencidas
   🎯 Resultado: PODE reparcelar (cliente ADIMPLENTE)
```

### 💰 **Análise Financeira:**
```
❌ REGRA CALCULO_FINANCEIRO: SALDO_TOTAL
   📋 Critério: Soma de todos os valores pendentes
   📊 Valor avaliado: R$ 0.00
   🎯 Resultado: Saldo zerado (possível problema nos dados)
```

---

## ⚠️ PROBLEMAS IDENTIFICADOS

### 🚨 **PROBLEMA 1: Saldo Zerado**
- **Situação:** Todas as parcelas podem estar quitadas
- **Impacto:** Não há valor para reparcelar
- **Solução:** Verificar campo `Status da parcela`

### 🔍 **PROBLEMA 2: Dados de Teste**
- **Situação:** Arquivo pode conter dados fictícios/zerados
- **Impacto:** Teste não reflete cenário real
- **Solução:** Validar com dados reais do Sienge

---

## 🎯 RECOMENDAÇÕES IMPLEMENTAÇÃO

### 📋 **1. Validação de Dados**
```python
def validar_dados_planilha(df):
    """Validar integridade dos dados antes de processar"""
    
    # Verificar se há dados válidos
    if df['Valor a receber'].sum() == 0:
        return {"valido": False, "motivo": "Saldo total zerado"}
    
    # Verificar colunas críticas
    colunas_criticas = ['Parcela/Condição', 'Status da parcela', 'Data vencimento']
    for coluna in colunas_criticas:
        if df[coluna].isna().all():
            return {"valido": False, "motivo": f"Coluna {coluna} vazia"}
    
    return {"valido": True}
```

### 📊 **2. Processamento Específico**
```python
def processar_planilha_sienge(df):
    """Processar dados específicos do Sienge"""
    
    # Converter datas
    df['Data vencimento'] = pd.to_datetime(df['Data vencimento'])
    
    # Filtrar parcelas CT
    parcelas_ct = df[df['Parcela/Condição'].str.contains('CT', na=False)]
    
    # Identificar vencidas
    hoje = datetime.now().date()
    ct_vencidas = parcelas_ct[
        (parcelas_ct['Status da parcela'] != 'Quitada') &
        (parcelas_ct['Data vencimento'].dt.date < hoje)
    ]
    
    return {
        "total_parcelas": len(df),
        "parcelas_ct": len(parcelas_ct),
        "ct_vencidas": len(ct_vencidas),
        "saldo_pendente": df[df['Status da parcela'] != 'Quitada']['Valor a receber'].sum()
    }
```

### 🎯 **3. Mapeamento Sienge**
```python
# Mapeamento de campos Sienge para processamento
CAMPOS_SIENGE = {
    "identificacao": {
        "titulo": "Título",
        "cliente": "Cliente", 
        "documento": "Documento"
    },
    "validacao_pdd": {
        "tipo_parcela": "Parcela/Condição",
        "status": "Status da parcela",
        "data_vencimento": "Data vencimento"
    },
    "calculo_financeiro": {
        "valor_original": "Valor original",
        "valor_atual": "Valor a receber",
        "dias_atraso": "Dias de atraso"
    },
    "configuracao_atual": {
        "indexador": "Indexador",
        "juros_percentual": "Juros %", 
        "tipo_juros": "Tipo de juros"
    }
}
```

---

*Esta análise serve como base para a implementação completa do RPA Sienge conforme as regras do PDD.*
