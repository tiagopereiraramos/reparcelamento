# Atualizar Último Reajuste

## Visão Geral
- Script CLI dedicado a retroalimentar a coluna `Último reajuste` na planilha base do Sienge.
- Fluxo inspirado em `rpa_sienge/atualizar_planilha_extracao_resultados.py`, mas sem leitura de CSV intermediário.
- Opera com parâmetros explícitos (`código`, `título`, `data`) fornecidos pelo usuário para localizar e atualizar o contrato alvo.

## Requisitos Acionáveis
- Validar `--data-reajuste` aceitando `DD/MM/AAAA`, `DD/MM/AA`, `MM/AAAA` ou `MM/AA`, normalizando a saída.
- Garantir que `--codigo-cliente` e `--titulo` correspondam à mesma linha antes de atualizar a célula.
- Localizar automaticamente a aba padrão quando `--aba` não for informado, replicando a lógica do script original.
- Registrar logs em português padronizados com o prefixo `[ÚLTIMO REAJUSTE]` para todas as etapas críticas.
- Lançar `ValueError` com mensagens claras quando a planilha não contiver colunas obrigatórias ou o contrato não for localizado.

## Exemplos
- **DO** (uso recomendado):

```63:87:rpa_sienge/atualizar_ultimo_reajuste.py
def validar_data(data_reajuste: str) -> str:
    """Valida o formato e normaliza a data do último reajuste.

    Args:
        data_reajuste: Valor textual informado pelo usuário.

    Returns:
        Data normalizada no formato "DD/MM/AAAA" ou "MM/AAAA" conforme entrada.

    Raises:
        ValueError: Caso o valor fornecido não corresponda a nenhum formato
            suportado.
    """
    formatos_suportados = ("%d/%m/%Y", "%d/%m/%y", "%m/%Y", "%m/%y")
    for formato in formatos_suportados:
        try:
            data = datetime.strptime(data_reajuste, formato)
            if len(formato) == 5:  # Formatos MM/AA ou MM/AAAA
                return data.strftime("%m/%Y")
            return data.strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError(
        "Data de reajuste inválida. Informe no formato DD/MM/AAAA ou MM/AAAA.")
```

- **DON'T** (evitar): ignorar a validação de colunas obrigatórias ao localizar o contrato; referenciar diretamente índices fixos sem verificar cabeçalho quebra a execução quando a planilha muda.

## Referências Cruzadas
- Consulte também `rpa_sienge/atualizar_planilha_extracao_resultados.py` para padrões de autenticação e logging consistentes neste domínio.

