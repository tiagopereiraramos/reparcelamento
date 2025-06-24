# Scripts de Execução dos RPAs (Produção)

Este diretório contém os pontos de entrada (main) para execução dos RPAs em ambiente de produção.

## Padrão de Organização
- Cada RPA possui um arquivo `main_<nome_do_rpa>.py` responsável por executar o respectivo robô de forma padronizada, robusta e pronta para integração com agendadores, CI/CD ou execução manual.
- Os scripts **não** contêm lógica de teste, debug interativo ou prints desnecessários. Apenas logs claros e código de saída apropriado.

## Como Usar

1. **Configure as variáveis de ambiente necessárias:**
   - Exemplo para o RPA de Coleta de Índices:
     - `PLANILHA_CALCULO_ID` — ID da planilha Google Sheets de produção
     - `GOOGLE_CREDENTIALS_PATH` — Caminho para o arquivo de credenciais do Google (opcional, padrão: `./gspread-credentials.json`)

2. **Execute o script desejado:**
   ```bash
   export PLANILHA_CALCULO_ID="<ID_DA_PLANILHA>"
   export GOOGLE_CREDENTIALS_PATH="./gspread-credentials.json"
   python scripts/main_coleta_indices.py
   ```
   - O script irá logar início, sucesso ou falha, e retornar código de saída 0 (sucesso) ou 1 (falha).

## Boas Práticas para Novos RPAs
- Crie um arquivo `main_<nome_do_rpa>.py` neste diretório para cada novo RPA.
- Use variáveis de ambiente para parâmetros sensíveis ou de ambiente.
- Importe e utilize a função de execução principal do RPA (ex: `executar_<nome_do_rpa>()`).
- Não inclua lógica de teste, apenas execução de produção.
- Use logs claros e código de saída apropriado.

## Exemplo de Estrutura
```
scripts/
  main_coleta_indices.py
  main_sienge.py
  main_sicredi.py
  README.md
```

---

Dúvidas? Consulte o time de desenvolvimento ou o README principal do projeto. 