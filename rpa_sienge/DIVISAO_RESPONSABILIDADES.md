
# 📋 DIVISÃO DE RESPONSABILIDADES - RPA SIENGE

## 🎯 RESUMO EXECUTIVO

| **RESPONSABILIDADE** | **QUEM** | **O QUE INCLUI** |
|---------------------|----------|------------------|
| 🔍 **WEBSCRAPING** | **USUÁRIO** | Navegação, cliques, preenchimento, extração de dados |
| 🤖 **PROCESSAMENTO** | **ASSISTENTE** | Análise, validações, cálculos, regras PDD |

---

## 🔍 RESPONSABILIDADES DO USUÁRIO (WEBSCRAPING)

### ✅ **MÉTODOS A IMPLEMENTAR**
```python
async def _fazer_login_sienge(self)
async def _consultar_relatorios_financeiros(self, contrato)
async def _navegar_reparcelamento_inclusao(self)
async def _consultar_titulo_reparcelamento(self, numero_titulo)
async def _selecionar_documentos_reparcelamento(self, dados_financeiros)
async def _configurar_detalhes_reparcelamento(self, contrato, indices, dados_financeiros)
async def _confirmar_salvar_reparcelamento(self)
async def _gerar_carne_sienge(self, contrato)
```

### 📋 **AÇÕES DE WEBSCRAPING**
- ✅ Login no Sienge
- ✅ Navegação entre menus
- ✅ Preenchimento de formulários
- ✅ Cliques em botões
- ✅ Seleção/deseleção de checkboxes
- ✅ Download de planilhas
- ✅ Upload de arquivos
- ✅ Captura de dados das telas

---

## 🤖 RESPONSABILIDADES DO ASSISTENTE (PROCESSAMENTO)

### ✅ **MÉTODOS JÁ IMPLEMENTADOS**
```python
async def _processar_planilha_baixada(self, cliente, numero_titulo)
async def _aplicar_regras_pdd_planilha(self, df, cliente, numero_titulo)
async def _validar_contrato_reparcelamento(self, dados_financeiros)
def calcular_valores_reparcelamento(self, contrato, indices, dados_financeiros)
def determinar_parcelas_para_desmarcar(self, dados_financeiros)
async def _aplicar_regras_negocio_pdd(self, dados_financeiros, contrato)
```

### 📊 **AÇÕES DE PROCESSAMENTO**
- ✅ Leitura e análise de planilhas Excel
- ✅ Aplicação das regras PDD
- ✅ Validação de inadimplência
- ✅ Cálculo de valores corrigidos
- ✅ Determinação de parcelas a desmarcar
- ✅ Geração de relatórios de auditoria
- ✅ Atualização da planilha base de cálculo

---

## 🔄 FLUXO DE INTEGRAÇÃO

### **ETAPA 1: CONSULTA DE RELATÓRIOS**
1. **USUÁRIO**: Faz login e navega para relatórios → `_consultar_relatorios_financeiros()`
2. **USUÁRIO**: Executa consulta e baixa planilha Excel
3. **ASSISTENTE**: Processa planilha baixada → `_processar_planilha_baixada()`
4. **ASSISTENTE**: Aplica regras PDD → `_aplicar_regras_pdd_planilha()`

### **ETAPA 2: VALIDAÇÃO E CÁLCULOS**
1. **ASSISTENTE**: Valida se pode reparcelar → `_validar_contrato_reparcelamento()`
2. **ASSISTENTE**: Calcula valores → `calcular_valores_reparcelamento()`
3. **ASSISTENTE**: Determina parcelas a desmarcar → `determinar_parcelas_para_desmarcar()`

### **ETAPA 3: REPARCELAMENTO**
1. **USUÁRIO**: Navega para reparcelamento → `_navegar_reparcelamento_inclusao()`
2. **USUÁRIO**: Consulta título → `_consultar_titulo_reparcelamento()`
3. **USUÁRIO**: Seleciona documentos → `_selecionar_documentos_reparcelamento()`
4. **USUÁRIO**: Desmarca parcelas (usando lista do ASSISTENTE)
5. **USUÁRIO**: Preenche valores (usando cálculos do ASSISTENTE)
6. **USUÁRIO**: Confirma e salva → `_confirmar_salvar_reparcelamento()`

---

## 🔧 INTERFACE DE COMUNICAÇÃO

### **DADOS QUE O ASSISTENTE FORNECE PARA O USUÁRIO**
```python
# Valores calculados para preenchimento
valores_sienge = {
    "detalhamento": "CORREÇÃO 06/25",
    "tipo_condicao": "PM", 
    "valor_total": 150389.45,
    "quantidade_parcelas": 48,
    "data_primeiro_vencimento": "15/07/2025",
    "indexador": "1 IGP-M",
    "tipo_juros": "Fixo",
    "percentual_juros": 8.0
}

# Parcelas para desmarcar
parcelas_desmarcar = [
    {"documento": "CT-001", "data_vencimento": "15/05/2025"},
    {"documento": "CT-002", "data_vencimento": "15/06/2025"}
]
```

### **DADOS QUE O USUÁRIO RETORNA PARA O ASSISTENTE**
```python
# Status do webscraping
resultado_webscraping = {
    "sucesso": True,
    "novo_titulo_gerado": "REPAC_20250617_143022", 
    "erro": None,
    "tempo_execucao": 45.2
}
```

---

## ⚠️ PONTOS DE ATENÇÃO

### **PARA O USUÁRIO (WEBSCRAPING)**
1. **SEMPRE aguardar carregamento** das páginas antes de interagir
2. **SEMPRE validar** que chegou na tela correta após navegação
3. **SEMPRE capturar erros** do Sienge (mensagens de validação)
4. **USAR dados calculados** pelo ASSISTENTE (não calcular manualmente)

### **PARA O ASSISTENTE (PROCESSAMENTO)**
1. **SEMPRE aplicar regras PDD** rigorosamente
2. **SEMPRE usar IGP-M** (nunca IPCA)
3. **SEMPRE validar inadimplência** antes de autorizar
4. **SEMPRE salvar dados** para auditoria

---

## 🧪 TESTES SUGERIDOS

### **TESTE DO USUÁRIO**
```bash
python rpa_sienge/teste_sienge.py webscraping
```

### **TESTE DO ASSISTENTE**
```bash
python rpa_sienge/teste_sienge.py processamento
```

### **TESTE INTEGRADO**
```bash
python rpa_sienge/teste_sienge.py completo
```
