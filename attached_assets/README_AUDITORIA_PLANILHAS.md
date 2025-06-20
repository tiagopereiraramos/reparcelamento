
# Sistema de Auditoria de Planilhas - RPA Sienge

## Visão Geral

O RPA Sienge agora possui um sistema completo de auditoria que armazena todas as planilhas extraídas do sistema Sienge, vinculando-as aos clientes consultados. Isso permite rastreabilidade completa para auditorias e verificações futuras.

## Funcionalidades

### 1. Armazenamento Estruturado
- **Pasta organizada**: `dados_extraidos/planilhas_sienge/YYYY/MM/`
- **Nomenclatura**: `saldo_devedor_{numero_titulo}_{timestamp}.xlsx`
- **Estrutura por ano/mês**: Facilita localização e manutenção

### 2. Vínculo com Cliente
- **MongoDB**: Cada planilha é registrada no banco de dados
- **Metadados completos**: Cliente, título, data, hash do arquivo
- **Dados de auditoria**: IP, usuário, sistema origem

### 3. Integridade dos Dados
- **Hash MD5**: Verificação de integridade do arquivo
- **Metadados Excel**: Aba dedicada com informações de auditoria
- **Status tracking**: Controle de planilhas ativas/inativas

## Estrutura do Arquivo Excel

Cada planilha salva contém:

### Aba "Dados_Sienge"
- Dados extraídos do relatório do Sienge
- Formato original preservado

### Aba "Metadados_Auditoria"
- `numero_titulo`: Número do título consultado
- `cliente`: Nome do cliente
- `data_extracao`: Timestamp da extração
- `usuario_rpa`: Usuário que executou o RPA
- `versao_rpa`: Versão do sistema
- `origem_dados`: Sistema fonte (Sienge)
- `total_parcelas`: Quantidade de parcelas
- `saldo_total`: Valor total do saldo
- `status_cliente`: Status de elegibilidade

## Consultas de Auditoria

### Consultar por Cliente
```bash
python scripts/consultar_planilhas_auditoria.py --cliente "NOME DO CLIENTE"
```

### Consultar por Título
```bash
python scripts/consultar_planilhas_auditoria.py --titulo "123456789"
```

### Estatísticas Gerais
```bash
python scripts/consultar_planilhas_auditoria.py --estatisticas
```

### Limitar Resultados
```bash
python scripts/consultar_planilhas_auditoria.py --cliente "CLIENTE" --limite 5
```

## Estrutura MongoDB

### Collection: `planilhas_extraidas`

```javascript
{
  "_id": ObjectId,
  "numero_titulo": "123456789",
  "cliente": "NOME DO CLIENTE",
  "caminho_arquivo": "/path/to/file.xlsx",
  "nome_arquivo": "saldo_devedor_123456789_20250610_143022.xlsx",
  "data_extracao": ISODate,
  "origem_sistema": "Sienge",
  "tipo_relatorio": "Saldo Devedor Presente",
  "dados_extracao": {
    "saldo_total": 150000.00,
    "total_parcelas": 24,
    "parcelas_vencidas": 2,
    "parcelas_ct_vencidas": 0,
    "status_cliente": "ADIMPLENTE"
  },
  "hash_arquivo": "abc123def456...",
  "tamanho_arquivo_bytes": 10240,
  "usuario_sistema": "sistema_rpa",
  "ip_origem": "192.168.1.100",
  "status_auditoria": "ativo"
}
```

## Índices MongoDB

- `numero_titulo + data_extracao`: Busca por título
- `cliente + data_extracao`: Busca por cliente
- `origem_sistema + status_auditoria`: Relatórios por sistema

## Benefícios para Auditoria

### 1. Rastreabilidade Completa
- **Quem**: Usuário que executou
- **Quando**: Timestamp preciso
- **O quê**: Dados extraídos
- **Onde**: Sistema origem e IP
- **Como**: Versão do RPA

### 2. Integridade dos Dados
- **Hash MD5**: Detecção de alterações
- **Verificação de existência**: Arquivo ainda existe?
- **Metadados preservados**: Informações originais

### 3. Facilidade de Consulta
- **Scripts prontos**: Consultas rápidas por cliente/título
- **Interface MongoDB**: Consultas complexas quando necessário
- **Estatísticas**: Visão geral do sistema

## Manutenção

### Limpeza de Arquivos Antigos
```python
# Marcar planilha como inativa
await mongodb_manager.marcar_planilha_inativa("planilha_id")
```

### Verificação de Integridade
```python
# Verificar se arquivo ainda existe e hash corresponde
planilhas = await mongodb_manager.obter_planilhas_cliente()
for planilha in planilhas:
    if planilha['arquivo_existe']:
        # Arquivo existe, verificar hash se necessário
        pass
```

## Exemplo de Uso

```python
from rpa_sienge.rpa_sienge import RPASienge

# RPA automaticamente salva planilha e registra no MongoDB
rpa = RPASienge()
resultado = await rpa.executar(contrato, credenciais_sienge)

# Planilha salva em: dados_extraidos/planilhas_sienge/2025/06/
# Vínculo registrado no MongoDB para auditoria
```

## Integração com Dashboard

O sistema pode ser integrado ao dashboard para mostrar:
- Últimas planilhas extraídas
- Estatísticas de extração
- Status de integridade dos arquivos
- Alertas de problemas de auditoria

## Considerações de Segurança

- **Acesso restrito**: Pasta `dados_extraidos` deve ter permissões adequadas
- **Backup regular**: MongoDB e arquivos devem ser backupeados
- **Retenção**: Definir política de retenção de arquivos antigos
- **Logs de acesso**: Monitorar acessos às planilhas sensíveis
