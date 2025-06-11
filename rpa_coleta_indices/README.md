# RPA Coleta de Índices Econômicos

## 📋 Visão Geral

Este RPA é responsável pela coleta automática de índices econômicos (IPCA e IGPM) dos sites oficiais do governo brasileiro e atualização das planilhas Google Sheets conforme especificado no PDD.

## 🎯 Funcionalidades

- **Coleta IPCA**: Extrai índice acumulado 12 meses do site oficial do IBGE
- **Coleta IGPM**: Extrai índice acumulado 12 meses do site oficial da FGV  
- **Atualização de Planilhas**: Atualiza automaticamente planilhas Google Sheets
- **Logs Detalhados**: Registra toda execução no MongoDB para auditoria
- **Fallback APIs**: Usa APIs do Banco Central como backup

## 📁 Estrutura de Arquivos

```
rpa_coleta_indices/
├── rpa_coleta_indices.py      # RPA principal
├── teste_coleta_indices.py    # Teste independente  
└── README.md                  # Esta documentação
```

## 🔧 Configuração

### Pré-requisitos

1. **Credenciais Google Sheets**:
   - Arquivo `credentials/google_service_account.json`
   - Service account com permissões de editor na planilha

2. **Planilha Google Sheets**:
   - Deve ter abas "IPCA" e "IGPM"
   - Estrutura: Coluna A (mês), Coluna B (valor %)

3. **Conexão MongoDB**:
   - Para salvar logs de execução

### Parâmetros de Entrada

```python
parametros = {
    "planilha_id": "ID_DA_PLANILHA_GOOGLE_SHEETS",
    "credenciais_google": "caminho/para/credenciais.json"  # Opcional
}
```

## 🚀 Como Usar

### Execução via Orquestração Temporal

```python
from rpa_coleta_indices.rpa_coleta_indices import executar_coleta_indices

# Executa RPA com monitoramento completo
resultado = await executar_coleta_indices(
    planilha_id="1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
)

print(f"Sucesso: {resultado.sucesso}")
print(f"Dados: {resultado.dados}")
```

### Teste Independente (Desenvolvimento)

```bash
# Teste completo
python rpa_coleta_indices/teste_coleta_indices.py completo

# Teste apenas conexão
python rpa_coleta_indices/teste_coleta_indices.py conexao

# Teste apenas APIs
python rpa_coleta_indices/teste_coleta_indices.py apis

# Verificação de saúde
python rpa_coleta_indices/teste_coleta_indices.py saude

# Menu interativo
python rpa_coleta_indices/teste_coleta_indices.py
```

## 📊 Fontes de Dados

### IPCA (Índice Nacional de Preços ao Consumidor Amplo)
- **Fonte Oficial**: IBGE
- **URL**: https://www.ibge.gov.br/explica/inflacao.php
- **Método**: WebScraping com Selenium
- **Backup**: API Banco Central (série 13522)
- **Período**: Acumulado 12 meses

### IGPM (Índice Geral de Preços do Mercado)
- **Fonte Oficial**: FGV (Fundação Getúlio Vargas)
- **URL**: https://portalibre.fgv.br/taxonomy/term/94
- **Método**: WebScraping com Selenium + navegação em PDF
- **Backup**: API Banco Central (série 28655)
- **Período**: Acumulado 12 meses

## 🔍 Implementação WebScraping

### TODO para o Cliente

O RPA está estruturado para usar a **classe Browser fornecida pelo cliente**. As seguintes funções precisam ser implementadas usando Selenium:

#### IPCA - Site IBGE
```python
async def _coletar_ipca_ibge(self) -> Dict[str, Any]:
    # TODO: Implementar usando self.browser
    # 1. Acessar https://www.ibge.gov.br/explica/inflacao.php
    # 2. Localizar seção com dados atuais
    # 3. Extrair valor acumulado 12 meses
    # 4. Usar regex para extrair percentual
    pass
```

#### IGPM - Site FGV
```python
async def _coletar_igpm_fgv(self) -> Dict[str, Any]:
    # TODO: Implementar usando self.browser conforme PDD
    # 1. Acessar https://portalibre.fgv.br/taxonomy/term/94
    # 2. Clicar em "Ler mais" da publicação mais recente
    # 3. Clicar no PDF (IGP-M_FGV_press release_XXX.pdf)
    # 4. Extrair valor acumulado 12 meses do PDF
    pass
```

### Seletores e Estratégias

**Elementos a procurar**:
- Textos contendo "acumulado" + "12 meses"
- Elementos com padrões `\d+,\d+%`
- Tables com dados econômicos
- Links para PDFs com padrão `IGP-M_FGV_press`

## 📈 Resultado da Execução

### Sucesso
```python
ResultadoRPA(
    sucesso=True,
    mensagem="Índices coletados com sucesso - IPCA: 4.62%, IGPM: 3.89%",
    dados={
        "ipca": {
            "tipo": "IPCA",
            "valor": 4.62,
            "periodo": "acumulado_12_meses",
            "fonte": "IBGE",
            "url": "https://www.ibge.gov.br/explica/inflacao.php",
            "metodo": "webscraping_selenium",
            "timestamp": "2025-05-28T10:30:00"
        },
        "igpm": {
            "tipo": "IGPM", 
            "valor": 3.89,
            "periodo": "acumulado_12_meses",
            "fonte": "FGV",
            "url": "https://portalibre.fgv.br/taxonomy/term/94",
            "metodo": "webscraping_selenium",
            "timestamp": "2025-05-28T10:30:00"
        },
        "planilha_atualizada": "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk",
        "timestamp_coleta": "2025-05-28T10:30:00"
    },
    tempo_execucao=45.2
)
```

### Erro
```python
ResultadoRPA(
    sucesso=False,
    mensagem="Falha na coleta de índices econômicos",
    erro="Erro na conexão com Google Sheets: Invalid credentials",
    tempo_execucao=12.5
)
```

## 🗃️ Persistência MongoDB

Todas as execuções são automaticamente salvas na collection `execucoes_rpa`:

```javascript
{
  "nome_rpa": "Coleta_Indices",
  "timestamp_inicio": "2025-05-28T10:30:00Z",
  "timestamp_fim": "2025-05-28T10:31:15Z", 
  "parametros_entrada": {
    "planilha_id": "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
  },
  "resultado": { /* ResultadoRPA completo */ },
  "sucesso": true,
  "tempo_execucao_segundos": 75.2,
  "mensagem": "Índices coletados com sucesso",
  "erro": null
}
```

## 🔧 Manutenção

### Logs
- Todos os logs são estruturados e incluem contexto
- Logs salvos em `logs/rpa_system.log`
- Integração com MongoDB para auditoria

### Monitoramento
- Status de saúde via `verificar_saude()`
- Métricas de performance no MongoDB
- Alertas automáticos em caso de falha

### Troubleshooting

#### Problema: Erro de conexão Google Sheets
**Solução**: Verificar credenciais e permissões na planilha

#### Problema: WebScraping falhando
**Solução**: APIs do Banco Central como backup automático

#### Problema: Valores incorretos
**Solução**: Verificar seletores CSS/XPath nos sites oficiais

## 🔄 Evolução

### Próximas Implementações
1. ✅ Coleta via APIs (implementado)
2. 🔧 WebScraping IBGE (TODO cliente)
3. 🔧 WebScraping FGV com PDF (TODO cliente)
4. 📊 Dashboard Metabase (planejado)

### Melhorias Futuras
- Cache de resultados para evitar coletas duplas
- Notificações quando índices são atualizados
- Histórico comparativo de variações
- Validação de dados coletados

---

**Desenvolvido em Português Brasileiro**  
**Sistema RPA Empresarial - Self-hosted**