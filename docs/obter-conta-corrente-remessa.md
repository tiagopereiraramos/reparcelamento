# Obter Conta Corrente de Remessa
## Visão Geral
- Função utilitária em `core/utils_sienge.py` que consome `docs/empresas_contas_correntes.csv` para retornar a coluna `CONTA CORRENTE REMESSA` vinculada ao nome de uma empresa.
- Cache em memória garante leitura única do CSV durante a execução, viabilizando múltiplas chamadas eficientes.
- Normalização remove acentos e aplica `lower()` para evitar falhas de correspondência por diferenças de grafia.

## Requisitos Acionáveis
- Validar `nome_empresa`, lançando `ValueError` quando vazio ou composto apenas por espaços.
- Lançar `FileNotFoundError` se o CSV estiver ausente; lançar `ValueError` quando o cabeçalho não possuir as colunas esperadas ou o registro não existir.
- Normalizar nomes com `unicodedata.normalize` e `lower()` antes do lookup.
- Reaproveitar o cache `_CACHE_CONTAS_CORRENTES` como fonte única de dados carregados.

## Exemplos
- **DO**:

```86:108:core/utils_sienge.py
    if not nome_empresa or not nome_empresa.strip():
        raise ValueError(
            "Nome da empresa é obrigatório para obter a conta corrente de remessa."
        )
    contas = _carregar_contas_correntes()
    chave = _normalizar_empresa(nome_empresa)
    conta = contas.get(chave)
    if conta is None:
        raise ValueError(
            f"Empresa '{nome_empresa}' não localizada no mapeamento de contas corrente."
        )
```

- **DON'T**: Abrir o CSV a cada chamada ou comparar nomes sem remover acentos (`"INCORPORADORA DE IMÓVEIS OLIVEIRA LTDA"`) — isso gera falhas de correspondência.

## Referências Cruzadas
- `docs/empresas_contas_correntes.csv`: base de dados.
- `core/utils_sienge.py`: implementação do utilitário e demais funções correlatas.
