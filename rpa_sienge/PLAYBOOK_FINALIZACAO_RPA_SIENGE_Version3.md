# 🚀 PLAYBOOK ENTERPRISE PARA FINALIZAR `rpa_sienge.py`

---

## 🎯 Objetivo

Finalizar o desenvolvimento do arquivo `rpa_sienge.py` para um RPA robusto, 100% aderente ao PDD e à metodologia enterprise, com divisão clara das responsabilidades:

- **Lógica de negócio PDD, helpers, parsing, validação, cálculo**: já implementados e testados.
- **Webscraping real (navegação, cliques, waits, scraping HTML)**: responsabilidade do usuário (você), sempre marcado com TODO ultra-detalhado, sem código Selenium/Playwright real no corpo do método.

---

## 📌 REFERÊNCIAS E ANÁLISE

- **Arquivo `rpa_sienge.py`**:  
  Lógica principal, regras PDD e estrutura ready, mas métodos de scraping precisam ser TODOs ultra-comentados.
- **README_REGRAS_PDD_IMPLEMENTADAS.md**:  
  Todas as regras e helpers já modelados e testados.
- **Playbooks/Assets**:  
  Detalhamento do fluxo e responsabilidades.

---

## 🏗️ PLANO DE IMPLEMENTAÇÃO

### 1. Refatorar Métodos Webscraping para TODO Ultra-Detalhado

Para cada método de scraping real, substitua o corpo por um TODO com:

- **PASSOS detalhados** (1, 2, 3...)
- **XPATHs/Seletores sugeridos**
- **Validações e resultados esperados**
- **Possíveis erros a tratar**

Exemplo:
```python
async def _navegar_reparcelamento_inclusao(self):
    """
    WEBSCRAPING (RESPONSABILIDADE DO USUÁRIO)
    PASSOS:
    1. Navegar para o menu financeiro na home do Sienge
    2. Clicar em "Contas a Receber"
    3. Clicar em "Reparcelamento"
    4. Clicar em "Inclusão"
    5. Validar que está na tela correta (checar cabeçalho/campo exclusivo)

    XPATHs sugeridos:
    - Menu Financeiro: //a[contains(text(),'Financeiro')]
    - Contas a Receber: //a[contains(text(),'Contas a Receber')]
    - Reparcelamento: //a[contains(text(),'Reparcelamento')]
    - Inclusão: //a[contains(text(),'Inclusão')]

    ERROS:
    - Elemento não encontrado
    - Timeout de carregamento
    """
    # TODO: Implementar scraping conforme passos acima.
    pass
```

### 2. Garantir Lógica de Negócio Pronta e Testada

- Métodos auxiliares e helpers de parsing, validação, cálculo, etc. devem estar prontos e cobertos por testes.
- Parsing de planilha deve ser resiliente a colunas variantes e tipos de valores.

### 3. Checklist dos Métodos Webscraping

**NUNCA** implemente scraping real nesses métodos, apenas TODO ultra-detalhado:

- `_navegar_menu_financeiro`
- `_acessar_relatorio_saldo_devedor`
- `_filtrar_por_titulo`
- `_executar_relatorio`
- `_extrair_dados_tabela_sienge`
- `_navegar_reparcelamento_inclusao`
- `_consultar_titulo_reparcelamento`
- `_selecionar_documentos_reparcelamento`
- `_configurar_detalhes_reparcelamento`
- `_confirmar_salvar_reparcelamento`
- `_navegar_geracao_carne`
- `_configurar_parametros_carne`
- `_executar_geracao_carne`
- `_preencher_campo_sienge`
- `_selecionar_opcao_sienge`
- `_aguardar_carregamento_documentos`
- `_verificar_confirmacao_salvamento`

---

## 🧪 SUGESTÃO DE `teste_sienge.py`: TESTE INTERATIVO ENTERPRISE

Para garantir qualidade, produtividade e facilidade de troubleshooting, **sugira a criação de um arquivo `teste_sienge.py`** com menu interativo (CLI) que permite:

- Escolher qual etapa executar (login, consulta relatório, validação, reparcelamento, geração de carnê, fluxo completo)
- Abrir e controlar o browser real (com Selenium/Playwright)
- Exibir logs e outputs intermediários
- Validar resultados de cada etapa
- Facilitar debugging e acompanhamento de cada passo do RPA

**Exemplo de estrutura do menu:**
```python
def main():
    print("=== TESTE INTERATIVO RPA SIENGE ===")
    print("1 - Login Sienge")
    print("2 - Consulta relatório financeiro")
    print("3 - Validação PDD")
    print("4 - Reparcelamento")
    print("5 - Geração de carnê")
    print("6 - Fluxo completo")
    print("0 - Sair")
    escolha = input("Escolha a opção: ")
    # Chamar cada método correspondente, mostrando logs, resultados e possíveis erros
```
**Dicas enterprise:**
- Use argparse ou click para CLI robusto.
- Sempre abra e feche o browser de forma controlada.
- Faça dump dos resultados de cada etapa em arquivos JSON para auditoria.
- Permita repetir testes sem reiniciar o script.

---

## ✅ CHECKLIST DE FINALIZAÇÃO

| Item                                             | Status |
|--------------------------------------------------|--------|
| Métodos de scraping com TODO detalhado           | [ ]    |
| Métodos de parsing/negócio implementados/testados| [ ]    |
| Documentação de cada método                      | [ ]    |
| Testes unitários das regras                      | [ ]    |
| Teste interativo (`teste_sienge.py`)             | [ ]    |
| Readme/documentação de uso                       | [ ]    |

---

## 🚀 Resumo

- **Implemente toda lógica de negócio e parsing com o assistente**
- **Deixe TODO ultra-detalhado nos métodos de scraping**
- **Implemente scraping real apenas você**
- **Use `teste_sienge.py` para validar cada etapa interativamente**
- **Scraping e lógica nunca se misturam!**

---

*Playbook pronto para garantir padrão enterprise, manutenção fácil, testabilidade máxima e evolução segura do seu RPA Sienge!*