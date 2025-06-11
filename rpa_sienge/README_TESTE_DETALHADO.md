
# Teste Replit Detalhado - RPA Sienge

## Visão Geral

O teste detalhado simula o processamento completo do RPA Sienge com logs precisos de cada regra do PDD (Processo de Desenvolvimento de Software).

## Funcionalidades

✅ **Múltiplas fontes de dados**
- Arquivos Excel locais
- Google Sheets (com retroalimentação)

✅ **Logs detalhados**
- Cada regra PDD rastreada
- Timestamps precisos
- Critérios de aprovação/reprovação

✅ **Retroalimentação Google Sheets**
- Conforme PDD seção 7.3
- Atualiza planilha com resultados
- Mantém histórico de processamentos

## Uso

### 1. Arquivo Excel Padrão
```bash
python rpa_sienge/executar_teste_replit.py
```

### 2. Arquivo Excel Específico
```bash
python rpa_sienge/executar_teste_replit.py --arquivo /caminho/para/planilha.xlsx
```

### 3. Google Sheets (Recomendado)
```bash
python rpa_sienge/executar_teste_replit.py --sheets 1ABC123DEF456GHI789JKL012MNO345PQR678STU
```

### 4. Modo Híbrido
```bash
python rpa_sienge/executar_teste_replit.py --arquivo planilha.xlsx --sheets PLANILHA_ID
```

## Configuração Google Sheets

1. Configure credenciais em `gspread-credentials.json`
2. Planilha deve ter aba "Saldo Devedor Presente"
3. Sistema criará aba "Resultados Processamento" automaticamente

## Regras PDD Implementadas

- **ARQUIVO_EXCEL_VALIDO**: Arquivo deve existir e ser legível
- **COLUNAS_OBRIGATORIAS**: Estrutura mínima requerida
- **LIMITE_INADIMPLENCIA_PDD**: < 3 parcelas CT vencidas
- **INDICE_ECONOMICO_PDD**: Sempre IGP-M conforme especificação
- **CALCULO_NOVO_SALDO**: Saldo × (1 + IGP-M/100)
- **PARAMETROS_FIXOS_PDD**: PM, IGP-M, Fixo 8%
- **DATA_PRIMEIRO_VENCIMENTO**: Próximo mês dia 15
- **RETROALIMENTACAO**: Atualização Google Sheets

## Saídas

1. **Console**: Logs em tempo real
2. **Arquivo JSON**: Relatório completo
3. **Arquivo LOG**: Debug detalhado
4. **Google Sheets**: Retroalimentação (se habilitado)

## Estrutura do Relatório

```json
{
  "metadados": {
    "fonte_dados": "Google Sheets",
    "planilha_id": "1ABC...",
    "usar_google_sheets": true,
    "timestamp_teste": "2025-06-10T23:25:23",
    "versao_teste": "2.0.0"
  },
  "resultado": {
    "contrato": "TESTE_REPLIT_001",
    "cliente": "CLIENTE TESTE",
    "status_final": "ADIMPLENTE",
    "pode_reparcelar": true,
    "dados_calculados": {
      "valor_total": 103890.00,
      "quantidade_parcelas": 26,
      "data_primeiro_vencimento": "15/07/2025",
      "indice_aplicado": 3.89
    }
  },
  "logs_detalhados": [...]
}
```
