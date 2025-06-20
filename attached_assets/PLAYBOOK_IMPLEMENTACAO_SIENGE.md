# 📋 PLAYBOOK DE IMPLEMENTAÇÃO - RPA SIENGE

## 🎯 OBJETIVO
Guia completo para implementação do RPA Sienge baseado no **PDD_Reparcelamento_Sienge.pdf** e análise da planilha real **saldo_devedor_presente-20250610-093716.xlsx**.

---

## 📚 TRECHOS CRÍTICOS DO PDD - REFERÊNCIAS DIRETAS

### 🚨 **SEÇÃO 7.3.1 - CONSULTA RELATÓRIO SALDO DEVEDOR**
> **PDD Página 15, Seção 7.3.1:**
> *"O RPA deve acessar o relatório 'Saldo Devedor Presente' no Sienge através do caminho: Financeiro > Contas a Receber > Relatórios > Saldo Devedor Presente. Este relatório deve ser filtrado pelo número do título específico do contrato em processamento."*

**Implementação obrigatória:**
- Navegação exata: `Financeiro → Contas a Receber → Relatórios → Saldo Devedor Presente`
- Filtro obrigatório: Campo "Número Título" 
- Exportação: Planilha Excel para análise

### 🔍 **SEÇÃO 7.3.2 - REGRA CRÍTICA DE INADIMPLÊNCIA**
> **PDD Página 16, Seção 7.3.2:**
> *"REGRA FUNDAMENTAL: Cliente com 3 (três) ou mais parcelas do tipo CT (Contrato) vencidas será considerado INADIMPLENTE e NÃO poderá ter seu contrato reparcelado. Esta é uma regra rígida e não admite exceções."*

> **PDD Página 16, Continuação:**
> *"Parcelas dos tipos REC (Recebimento) e FAT (Faturamento) vencidas NÃO impedem o reparcelamento, sendo consideradas apenas pendências administrativas que não caracterizam inadimplência contratual."*

**Validação obrigatória:**
```python
# REGRA RIGOROSA PDD - SEM EXCEÇÕES
if qtd_parcelas_ct_vencidas >= 3:
    status = "INADIMPLENTE" 
    pode_reparcelar = False
    # BLOQUEAR IMEDIATAMENTE - SEM PROCESSAMENTO
```

### 💰 **SEÇÃO 7.3.3 - CÁLCULO CORREÇÃO MONETÁRIA**
> **PDD Página 17, Seção 7.3.3:**
> *"O cálculo do novo saldo deve OBRIGATORIAMENTE utilizar o índice IGP-M (Índice Geral de Preços do Mercado), aplicando a fórmula: Novo Saldo = Saldo Atual × (1 + IGP-M/100). O uso de IPCA ou qualquer outro índice é VEDADO para reparcelamentos."*

> **PDD Página 17, Parâmetros Fixos:**
> *"Configurações obrigatórias no Sienge:*
> - *Tipo Condição: PM (Pagamento Mensal)*
> - *Indexador: IGP-M*  
> - *Tipo de Juros: Fixo*
> - *Percentual Juros: 8,0% (oito por cento)*
> - *Estas configurações são IMUTÁVEIS conforme política da empresa."*

### 🔄 **SEÇÃO 7.3.4 - PROCESSAMENTO SIENGE**
> **PDD Página 18, Seção 7.3.4:**
> *"Navegação obrigatória: Financeiro > Contas a receber > Reparcelamento > Inclusão. O sistema deve consultar o título, selecionar TODOS os documentos e posteriormente DESMARCAR apenas as parcelas vencidas até o mês atual, conforme estratégia de reparcelamento."*

> **PDD Página 18, Detalhamento:**
> *"O campo 'Detalhamento' deve ser preenchido automaticamente com 'CORREÇÃO MM/AA' onde MM/AA representa o mês e ano atual do processamento."*

### 📋 **SEÇÃO 7.3.5 - GERAÇÃO DE CARNÊ**
> **PDD Página 19, Seção 7.3.5:**
> *"Após confirmação do reparcelamento, deve ser gerado novo carnê através do caminho: Financeiro > Contas a Receber > Cobrança Escritural > Geração de Arquivos de remessa."*

---

## 📊 ANÁLISE DA PLANILHA REAL

### 🔍 Estrutura Identificada
```
Arquivo: saldo_devedor_presente-20250610-093716.xlsx
Total de registros: 26 linhas
Total de colunas: 39 campos
```

### 📝 COLUNAS CRÍTICAS PARA PROCESSAMENTO

#### 🟢 **COLUNAS OBRIGATÓRIAS (Campos-chave)**
1. **`Título`** - Identificador único do contrato
2. **`Cliente`** - Nome do cliente/devedor
3. **`Status da parcela`** - **CAMPO CRÍTICO** para validação de inadimplência
4. **`Data vencimento`** - Para calcular atraso
5. **`Valor original`** - Valor base da parcela
6. **`Valor a receber`** - Valor atual pendente (com correções)

#### 🟡 **COLUNAS DE VALIDAÇÃO PDD**
7. **`Parcela/Condição`** - Tipo da parcela (CT, REC, FAT)
8. **`Tipo condição`** - Condição de pagamento
9. **`Indexador`** - Índice atual (deve ser alterado para IGP-M)
10. **`Juros %`** - Taxa atual (deve ser alterado para 8%)
11. **`Dias de atraso`** - Quantidade de dias em atraso

#### 🔵 **COLUNAS DE CÁLCULO**
12. **`Correção monetária`** - Valor da correção aplicada
13. **`Juros contratuais`** - Juros calculados
14. **`Valor atualizado`** - Valor com correções
15. **`Valor corrigido`** - Valor final corrigido
16. **`Multa %`** - Percentual de multa
17. **`Juros de mora`** - Valor dos juros de mora

---

## ⚖️ REGRAS DO PDD - ANÁLISE DETALHADA COM REFERÊNCIAS

### 🚨 **REGRA 1: VALIDAÇÃO DE INADIMPLÊNCIA**
> **📖 REFERÊNCIA PDD:** Página 16, Seção 7.3.2
> 
> *"REGRA FUNDAMENTAL: Cliente com 3 (três) ou mais parcelas do tipo CT (Contrato) vencidas será considerado INADIMPLENTE e NÃO poderá ter seu contrato reparcelado. Esta é uma regra rígida e não admite exceções."*

```
CRITÉRIO RIGOROSO PDD: Cliente com 3+ parcelas CT vencidas = INADIMPLENTE
LOCALIZAÇÃO: Página 16, Seção 7.3.2 do PDD
STATUS: REGRA RÍGIDA - SEM EXCEÇÕES
```

#### 🔍 **Implementação Conforme PDD:**
1. **Filtrar apenas parcelas tipo "CT"** na coluna `Parcela/Condição`
2. **Verificar `Status da parcela`** != "Quitada" 
3. **Verificar `Data vencimento`** < data atual
4. **Contar parcelas CT vencidas**
5. **SE >= 3 parcelas CT vencidas → BLOQUEAR reparcelamento (PDD Página 16)**

#### 📋 **Exceções Documentadas no PDD:**
> **📖 REFERÊNCIA PDD:** Página 16, Seção 7.3.2
> 
> *"Parcelas dos tipos REC (Recebimento) e FAT (Faturamento) vencidas NÃO impedem o reparcelamento, sendo consideradas apenas pendências administrativas que não caracterizam inadimplência contratual."*

#### 📋 **Código de Validação:**
```python
def validar_inadimplencia_pdd(df_planilha):
    # Filtra apenas parcelas CT
    parcelas_ct = df_planilha[df_planilha['Parcela/Condição'].str.contains('CT', na=False)]

    # Parcelas CT vencidas (não quitadas + vencidas)
    hoje = datetime.now().date()
    parcelas_ct_vencidas = parcelas_ct[
        (parcelas_ct['Status da parcela'] != 'Quitada') &
        (pd.to_datetime(parcelas_ct['Data vencimento']).dt.date < hoje)
    ]

    qtd_ct_vencidas = len(parcelas_ct_vencidas)

    # REGRA PDD: >= 3 = INADIMPLENTE
    pode_reparcelar = qtd_ct_vencidas < 3

    return {
        "pode_reparcelar": pode_reparcelar,
        "qtd_ct_vencidas": qtd_ct_vencidas,
        "status": "ADIMPLENTE" if pode_reparcelar else "INADIMPLENTE"
    }
```

### 💰 **REGRA 2: CÁLCULO DO NOVO SALDO**
> **📖 REFERÊNCIA PDD:** Página 17, Seção 7.3.3
> 
> *"O cálculo do novo saldo deve OBRIGATORIAMENTE utilizar o índice IGP-M (Índice Geral de Preços do Mercado), aplicando a fórmula: Novo Saldo = Saldo Atual × (1 + IGP-M/100). O uso de IPCA ou qualquer outro índice é VEDADO para reparcelamentos."*

```
FÓRMULA PDD: Novo Saldo = Saldo Atual × (1 + IGP-M/100)
LOCALIZAÇÃO: Página 17, Seção 7.3.3 do PDD  
ÍNDICE OBRIGATÓRIO: IGP-M (IPCA é VEDADO)
```

#### 🔍 **Implementação Conforme PDD:**
1. **Somar coluna `Valor a receber`** de todas as parcelas pendentes
2. **Aplicar EXCLUSIVAMENTE índice IGP-M** (PDD Página 17 - IPCA é vedado)
3. **Calcular novo saldo corrigido** usando fórmula oficial do PDD

#### ⚠️ **Restrições Documentadas:**
> **📖 REFERÊNCIA PDD:** Página 17, Seção 7.3.3
> 
> *"O uso de IPCA ou qualquer outro índice é VEDADO para reparcelamentos."*

#### 📋 **Código de Cálculo:**
```python
def calcular_novo_saldo_pdd(df_planilha, indice_igpm):
    # Soma apenas parcelas não quitadas
    parcelas_pendentes = df_planilha[df_planilha['Status da parcela'] != 'Quitada']
    saldo_atual = parcelas_pendentes['Valor a receber'].sum()

    # Aplica correção IGP-M
    fator_correcao = 1 + (indice_igpm / 100)
    novo_saldo = saldo_atual * fator_correcao

    return {
        "saldo_anterior": saldo_atual,
        "indice_igpm": indice_igpm,
        "fator_correcao": fator_correcao,
        "novo_saldo": novo_saldo,
        "diferenca": novo_saldo - saldo_atual
    }
```

### ⚙️ **REGRA 3: CONFIGURAÇÕES FIXAS PDD**
> **📖 REFERÊNCIA PDD:** Página 17, Seção 7.3.3 - Parâmetros Fixos
> 
> *"Configurações obrigatórias no Sienge:*
> - *Tipo Condição: PM (Pagamento Mensal)*
> - *Indexador: IGP-M*  
> - *Tipo de Juros: Fixo*
> - *Percentual Juros: 8,0% (oito por cento)*
> - *Estas configurações são IMUTÁVEIS conforme política da empresa."*

```
PARÂMETROS OBRIGATÓRIOS PDD (IMUTÁVEIS):
LOCALIZAÇÃO: Página 17, Seção 7.3.3 do PDD
- Tipo Condição: "PM" (Pagamento Mensal)
- Indexador: "IGP-M" (EXCLUSIVO)
- Tipo de Juros: "Fixo" (IMUTÁVEL)  
- Percentual Juros: 8.0% (FIXO - política empresa)
```

#### 🚨 **Importante - Política da Empresa:**
> **📖 REFERÊNCIA PDD:** Página 17, Seção 7.3.3
> 
> *"Estas configurações são IMUTÁVEIS conforme política da empresa."*

#### 🔍 **Implementação:**
```python
def obter_configuracao_pdd():
    return {
        "tipo_condicao": "PM",              # FIXO
        "indexador": "IGP-M",               # SEMPRE IGP-M
        "indexador_codigo": "1 IGP-M",      # Código Sienge
        "tipo_juros": "Fixo",               # FIXO
        "percentual_juros": 8.0,            # FIXO 8%
        "data_primeiro_vencimento": calcular_proximo_mes_dia_15()
    }
```

---

## 🔄 FLUXO DE PROCESSAMENTO SIENGE CONFORME PDD

### 📝 **ETAPA 1: COLETA DE DADOS**
> **📖 REFERÊNCIA PDD:** Página 15, Seção 7.3.1
> 
> *"O RPA deve acessar o relatório 'Saldo Devedor Presente' no Sienge através do caminho: Financeiro > Contas a Receber > Relatórios > Saldo Devedor Presente. Este relatório deve ser filtrado pelo número do título específico do contrato em processamento."*

**Navegação Obrigatória PDD:**
1. **Financeiro → Contas a Receber → Relatórios → Saldo Devedor Presente**
2. **Filtrar por "Número Título"** (campo obrigatório)
3. **Extrair dados da tabela** (todas as 39 colunas)
4. **Salvar planilha para auditoria** (vínculo MongoDB)

### ✅ **ETAPA 2: VALIDAÇÃO CONFORME PDD**
1. **Aplicar REGRA 1** (inadimplência - PDD Página 16)
2. **Verificar estrutura da planilha**
3. **Validar dados obrigatórios**
4. **Aplicar REGRA 2** (cálculo IGP-M - PDD Página 17)

### 💻 **ETAPA 3: NAVEGAÇÃO SIENGE CORRIGIDA**

> **📖 REFERÊNCIA PDD:** Página 18, Seção 7.3.4
> 
> *"Navegação obrigatória: Financeiro > Contas a receber > Reparcelamento > Inclusão. O sistema deve consultar o título, selecionar TODOS os documentos e posteriormente DESMARCAR apenas as parcelas vencidas até o mês atual, conforme estratégia de reparcelamento."*

```
✅ CAMINHO CORRETO CONFORME PDD:
Financeiro → Contas a receber → Reparcelamento → Inclusão

❌ NÃO É: Financeiro → Contas a Receber → Relatórios → Saldo Devedor Presente
LOCALIZAÇÃO: Página 18, Seção 7.3.4 do PDD
```

**🔧 CORREÇÃO IMPLEMENTADA:**
- O relatório "Saldo Devedor Presente" é usado apenas para CONSULTA de dados
- O PROCESSAMENTO do reparcelamento é feito em "Reparcelamento > Inclusão"

#### 🎯 **Ações no Sienge Conforme PDD:**
> **📖 REFERÊNCIA PDD:** Página 18, Seção 7.3.4

1. **Consultar título** pelo número (PDD Página 18)
2. **Selecionar TODOS os documentos** (obrigatório PDD)
3. **DESMARCAR parcelas vencidas** até mês atual (estratégia PDD)
4. **Configurar detalhes:** PM, IGP-M, Fixo 8% (PDD Página 17)
5. **Preencher detalhamento automático** (PDD Página 18)
6. **Confirmar e salvar**

#### 📋 **Detalhamento Automático PDD:**
> **📖 REFERÊNCIA PDD:** Página 18, Seção 7.3.4
> 
> *"O campo 'Detalhamento' deve ser preenchido automaticamente com 'CORREÇÃO MM/AA' onde MM/AA representa o mês e ano atual do processamento."*

```python
# Exemplo: Se processamento em junho/2025
detalhamento = "CORREÇÃO 06/25"
```

### 📊 **ETAPA 4: CONFIGURAÇÃO DETALHES**
```python
def configurar_detalhes_sienge(dados_calculo):
    return {
        # Campos obrigatórios Sienge
        "detalhamento": f"CORREÇÃO {datetime.now().strftime('%m/%y')}",
        "tipo_condicao": "PM",
        "valor_total": dados_calculo["novo_saldo"],
        "quantidade_parcelas": dados_calculo["parcelas_pendentes"],
        "data_primeiro_vencimento": "15/07/2025",  # Próximo mês
        "indexador": "IGP-M",
        "indexador_codigo": "1 IGP-M",
        "tipo_juros": "Fixo",
        "percentual_juros": 8.0
    }
```

---

## 🎯 IMPLEMENTAÇÃO NO CÓDIGO ATUAL

### 🔧 **MÉTODOS A IMPLEMENTAR/CORRIGIR**

#### 1. **`_processar_dados_relatorio_sienge()`**
```python
def _processar_dados_relatorio_sienge(self, dados_relatorio, contrato):
    """IMPLEMENTAR: Processamento real dos dados do Sienge"""
    try:
        # Converter dados HTML para DataFrame
        df = self._converter_tabela_sienge_para_dataframe(dados_relatorio)

        # Aplicar validações PDD
        validacao_inadimplencia = self._validar_inadimplencia_pdd(df)

        # Calcular novos valores
        calculo_saldo = self._calcular_novo_saldo_pdd(df, self.indices_igpm)

        # Retornar dados estruturados
        return {
            "sucesso": True,
            "dados_brutos": df,
            "validacao_inadimplencia": validacao_inadimplencia,
            "calculo_saldo": calculo_saldo,
            "parcelas_ct_vencidas": self._extrair_parcelas_ct_vencidas(df),
            "parcelas_rec_fat": self._extrair_parcelas_rec_fat(df),
            "saldo_total": calculo_saldo["saldo_anterior"],
            "cliente": contrato.get("cliente", "")
        }
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
```

#### 2. **`_selecionar_documentos_reparcelamento()`**
```python
def _selecionar_documentos_reparcelamento(self, dados_financeiros):
    """IMPLEMENTAR: Seleção específica conforme PDD"""
    try:
        # 1. Selecionar TODOS os documentos primeiro
        checkbox_todos = await self.browser.find_element(By.NAME, "select_all")
        await checkbox_todos.click()

        # 2. DESMARCAR parcelas vencidas até mês atual
        parcelas_vencidas = dados_financeiros.get("parcelas_vencidas", [])
        for parcela in parcelas_vencidas:
            if self._eh_vencida_ate_mes_atual(parcela["data_vencimento"]):
                checkbox_parcela = await self.browser.find_element(
                    By.XPATH, f"//input[@value='{parcela['id']}']"
                )
                await checkbox_parcela.click()  # Desmarca

        self.log_progresso(f"Documentos selecionados conforme PDD")

    except Exception as e:
        self.log_erro("Erro na seleção de documentos", e)
```

#### 3. **`_confirmar_salvar_reparcelamento()`**
```python
def _confirmar_salvar_reparcelamento(self):
    """IMPLEMENTAR: Confirmação real no Sienge"""
    try:
        # Botão confirmar
        btn_confirmar = await self.browser.find_element(By.XPATH, "//input[@value='Confirmar']")
        await btn_confirmar.click()

        # Aguardar processamento
        await asyncio.sleep(5)

        # Capturar número do novo título gerado
        elemento_titulo = await self.browser.find_element(By.ID, "novo_titulo_gerado")
        novo_titulo = elemento_titulo.text

        # Salvar confirmação
        btn_salvar = await self.browser.find_element(By.XPATH, "//input[@value='Salvar']")
        await btn_salvar.click()

        self.log_progresso(f"✅ Reparcelamento salvo - Novo título: {novo_titulo}")
        return novo_titulo

    except Exception as e:
        self.log_erro("Erro ao confirmar reparcelamento", e)
        return f"ERRO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
```

---

## 🧪 TESTES E VALIDAÇÃO

### 📋 **CENÁRIOS DE TESTE**

#### ✅ **TESTE 1: Cliente Adimplente**
```
Entrada: 0-2 parcelas CT vencidas
Resultado Esperado: PODE reparcelar
```

#### ❌ **TESTE 2: Cliente Inadimplente**
```
Entrada: 3+ parcelas CT vencidas  
Resultado Esperado: NÃO PODE reparcelar
```

#### 🔄 **TESTE 3: Cálculo Correção**
```
Entrada: Saldo R$ 1.000,00 + IGP-M 3,89%
Resultado Esperado: Novo saldo R$ 1.038,90
```

### 🎯 **COMANDO DE TESTE**
```bash
python rpa_sienge/teste_replit_detalhado.py --planilha=saldo_devedor_presente-20250610-093716.xlsx
```

---

## 🚨 PONTOS CRÍTICOS DE ATENÇÃO

### ⚠️ **VALIDAÇÕES OBRIGATÓRIAS**
1. **SEMPRE verificar inadimplência** antes de processar
2. **SEMPRE usar IGP-M** (nunca IPCA)
3. **SEMPRE configurar juros fixos 8%**
4. **SEMPRE salvar planilha para auditoria**

### 🔒 **SEGURANÇA**
1. **Backup automático** de planilhas extraídas
2. **Log detalhado** de cada operação
3. **Vínculo no MongoDB** para auditoria
4. **Validação de integridade** dos dados

### 📊 **MONITORAMENTO**
1. **Logs precisos** de cada regra aplicada
2. **Métricas de processamento**
3. **Alertas em caso de erro**
4. **Relatórios de auditoria**

---

## 🎯 PRÓXIMOS PASSOS

1. **Implementar métodos TODO** no `rpa_sienge.py`
2. **Testar com planilha real** fornecida
3. **Validar integração MongoDB** para auditoria
4. **Configurar logs detalhados** conforme PDD
5. **Homologar em ambiente Sienge** real

---

*Este playbook serve como guia definitivo para implementação do RPA Sienge seguindo rigorosamente as regras do PDD e baseado na análise da planilha real fornecida.*