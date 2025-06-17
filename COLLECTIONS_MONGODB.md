
# 📊 Collections MongoDB - Sistema RPA Reparcelamento

## Database: `rpa_reparcelamento`

### 1. **execucoes_rpa**
**Descrição**: Registra todas as execuções dos RPAs para auditoria
**Índices**: 
- `nome_rpa` + `timestamp_inicio` (desc)

**Estrutura**:
```javascript
{
  "_id": ObjectId,
  "nome_rpa": "Analise_Planilhas",
  "timestamp_inicio": "2025-01-15T10:30:00Z",
  "timestamp_fim": "2025-01-15T10:31:15Z",
  "parametros_entrada": {
    "planilha_calculo_id": "1abc123...",
    "planilha_apoio_id": "2def456..."
  },
  "resultado": {
    "sucesso": true,
    "mensagem": "Análise concluída",
    "dados": {...}
  },
  "sucesso": true,
  "tempo_execucao_segundos": 75.2,
  "mensagem": "Análise concluída - 5 contratos identificados",
  "erro": null
}
```

---

### 2. **contratos_processados**
**Descrição**: Contratos que foram processados pelos RPAs
**Índices**: 
- `numero_titulo` + `data_processamento` (desc)

**Estrutura**:
```javascript
{
  "_id": ObjectId,
  "numero_titulo": "123456789",
  "cliente": "CLIENTE TESTE LTDA",
  "empreendimento": "LOTEAMENTO ABC",
  "data_processamento": "2025-01-15T10:30:00Z",
  "status_sienge": "processado",
  "status_sicredi": "pendente", 
  "saldo_anterior": 150000.00,
  "saldo_novo": 155000.00,
  "indice_aplicado": 3.33,
  "indexador": "IPCA",
  "dados_completos": {
    // Dados completos do contrato
  }
}
```

---

### 3. **fila_processamento_sienge**
**Descrição**: Fila de contratos para processamento no Sienge
**Índices**: 
- `timestamp_criacao` (desc)
- `contratos.numero_titulo`

**Estrutura**:
```javascript
{
  "_id": ObjectId,
  "timestamp_ultima_atualizacao": "2025-01-15T10:30:00Z",
  "total_contratos": 5,
  "status_geral": "ativo",
  "contratos": [
    {
      "id_fila": "reajuste_123456789_20250115_103000",
      "numero_titulo": "123456789",
      "cliente": "CLIENTE TESTE LTDA",
      "empreendimento": "LOTEAMENTO ABC", 
      "ultimo_reajuste": "15/01/2024",
      "indexador": "IPCA",
      "status_processamento": "pendente",
      "timestamp_identificacao": "2025-01-15T10:30:00Z",
      "processado_em": null,
      "erro_processamento": null,
      "dados_completos": {...}
    }
  ]
}
```

---

### 4. **fila_reparcelamento**
**Descrição**: Fila específica para reparcelamentos
**Índices**: 
- `timestamp_identificacao` (desc)
- `numero_titulo`
- `status_processamento`

**Estrutura**:
```javascript
{
  "_id": ObjectId,
  "numero_titulo": "123456789",
  "cliente": "CLIENTE TESTE LTDA",
  "status_processamento": "pendente", // "pendente", "processado", "erro"
  "timestamp_identificacao": "2025-01-15T10:30:00Z",
  "dados_financeiros": {
    "qtd_ct_vencidas": 2,
    "pode_reparcelar": true,
    "parcelas_pendentes": 48,
    "saldo_devedor": 150000.00
  },
  "parametros_reparcelamento": {
    "indexador": "IPCA",
    "prazo_meses": 48,
    "taxa_fixa": 8.0
  }
}
```

---

### 5. **indices_economicos**
**Descrição**: Índices econômicos coletados (IPCA, IGP-M)
**Índices**: 
- `tipo_indice` + `data_coleta` (desc)

**Estrutura**:
```javascript
{
  "_id": ObjectId,
  "tipo_indice": "IPCA", // "IPCA", "IGPM"
  "valor": 3.33,
  "fonte": "IBGE - Sistema IBGE de Recuperação Automática",
  "data_coleta": "2025-01-15T10:30:00Z",
  "periodo": "acumulado_12_meses",
  "metodo_coleta": "webscraping"
}
```

---

### 6. **planilhas_extraidas**
**Descrição**: Auditoria de planilhas extraídas do Sienge
**Índices**: 
- `numero_titulo` + `data_extracao` (desc)
- `cliente` + `data_extracao` (desc)
- `origem_sistema` + `status_auditoria`

**Estrutura**:
```javascript
{
  "_id": ObjectId,
  "numero_titulo": "123456789",
  "cliente": "CLIENTE TESTE LTDA", 
  "caminho_arquivo": "/dados_extraidos/planilhas_sienge/2025/01/sienge_123456789_20250115_103000.xlsx",
  "data_extracao": "2025-01-15T10:30:00Z",
  "origem_sistema": "sienge",
  "status_auditoria": "ativo", // "ativo", "inativo"
  "hash_arquivo": "d41d8cd98f00b204e9800998ecf8427e",
  "tamanho_arquivo": 45632,
  "metadados": {
    "linhas_processadas": 48,
    "total_saldo_devedor": 150000.00,
    "usuario_extracao": "sistema_rpa",
    "ip_origem": "10.0.0.1"
  }
}
```

---

### 7. **processamentos_sicredi** *(Futuro)*
**Descrição**: Processamentos no sistema Sicredi
**Estrutura**:
```javascript
{
  "_id": ObjectId,
  "numero_titulo": "123456789",
  "data_processamento": "2025-01-15T10:30:00Z",
  "status_emissao": "emitido",
  "dados_boleto": {
    "numero_boleto": "456789123",
    "valor_total": 155000.00,
    "data_vencimento": "2025-02-15"
  }
}
```

---

## 📋 Resumo das Collections

| Collection | Finalidade | Tamanho Esperado | Retenção |
|------------|------------|------------------|----------|
| `execucoes_rpa` | Auditoria execuções | Médio | 6 meses |
| `contratos_processados` | Contratos processados | Grande | Permanente |
| `fila_processamento_sienge` | Fila ativa Sienge | Pequeno | Rotativo |
| `fila_reparcelamento` | Fila reparcelamentos | Pequeno | Rotativo |
| `indices_economicos` | Histórico índices | Pequeno | 2 anos |
| `planilhas_extraidas` | Auditoria planilhas | Grande | 1 ano |

## 🔧 Comandos de Manutenção

### Limpeza de dados antigos:
```javascript
// Remover execuções antigas (6+ meses)
db.execucoes_rpa.deleteMany({
  "timestamp_inicio": {
    "$lt": new Date(Date.now() - 6*30*24*60*60*1000)
  }
})

// Marcar planilhas antigas como inativas
db.planilhas_extraidas.updateMany({
  "data_extracao": {
    "$lt": new Date(Date.now() - 365*24*60*60*1000)
  }
}, {
  "$set": {"status_auditoria": "inativo"}
})
```

### Estatísticas rápidas:
```javascript
// Total de execuções por RPA
db.execucoes_rpa.aggregate([
  {"$group": {"_id": "$nome_rpa", "total": {"$sum": 1}}},
  {"$sort": {"total": -1}}
])

// Contratos processados por mês
db.contratos_processados.aggregate([
  {"$group": {
    "_id": {"$dateToString": {"format": "%Y-%m", "date": "$data_processamento"}},
    "total": {"$sum": 1}
  }}
])
```
