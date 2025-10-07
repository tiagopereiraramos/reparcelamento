"""
Anotações sobre o refatoramento do reparcelamento para uso do JSONRPAFramework.
"""

- 2025-10-06: iniciado trabalho de criação de classe autonoma `RPAReparcelamentoSienge` no módulo `rpa_sienge_reparcelamento.py` seguindo modelo de `rpa_sienge_extracao.py`.
- Nova entrada `scripts/main_reparcelamento_sienge.py` criada, CLI dedicada para acionar reparcelamento com contratos extraídos do repositório JSON.
- Notas: manter compatibilidade com `RPASienge._executar_etapa_reparcelamento`, reuso de métodos privados por enquanto (`pylint disable`).
- Atualizado `RPAReparcelamentoSienge` para herdar de `RPASienge` e executar consulta + webscraping integrados, garantindo retorno single-session com dados completos.

