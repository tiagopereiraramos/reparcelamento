# Sistema RPA de Reparcelamento - Replit

## Visão Geral do Projeto
Sistema completo de RPA (Robotic Process Automation) para automatizar reparcelamentos financeiros em 4 sistemas: Coleta de Índices, Análise de Planilhas, Sienge e Sicredi.

## Estado Atual (Junho 2025)
- ✅ **RPA 1 (Coleta Índices)**: Implementado e funcionando
- ✅ **RPA 2 (Análise Planilhas)**: Implementado e funcionando
- 🔄 **RPA 3 (Sienge)**: Em implementação - processamento completo, webscraping em andamento
- ⏳ **RPA 4 (Sicredi)**: Aguardando finalização do RPA 3

## Progresso Atual - RPA Sienge
**✅ IMPLEMENTADO (17/06/2025):**
- Estrutura completa do código com documentação
- **ValidadorInadimplenciaPDD**: Regra rigorosa ≥3 CT vencidas = INADIMPLENTE
- **CalculadoraReparcelamentoPDD**: Cálculos IGP-M e juros 8% fixos
- Processamento de planilhas Excel do Sienge
- Sistema de auditoria e logs
- **Todos os testes PDD aprovados**: inadimplente/adimplente, cálculos financeiros, parcelas para desmarcar
- **Webscraping funcional portado**: Login, navegação, consultas e exportação de relatórios
- Arquitetura limpa em `rpa_sienge_clean.py` com código validado integrado

**⚡ PRONTO PARA TESTE:**
- Sistema completo RPA Sienge com webscraping funcional
- Métodos de login automático implementados
- Extração de relatórios financeiros operacional
- Integração completa entre webscraping e processamento PDD

## Responsabilidades Definidas
- **Usuário**: Implementação de webscraping (navegação, cliques, preenchimento)
- **Assistente**: Processamento de dados, validações, cálculos conforme PDD

## Tecnologias
- Python 3.11
- Selenium WebDriver
- Pandas para processamento de planilhas
- FastAPI para endpoints
- Streamlit para dashboard
- MongoDB para auditoria

## Próximos Passos
1. Finalizar implementação dos métodos de webscraping do RPA Sienge
2. Testes integrados com sistema real
3. Implementação do RPA Sicredi
4. Deploy completo do sistema

## Preferências do Usuário
- Comunicação em português brasileiro
- Foco na continuidade do desenvolvimento
- Divisão clara de responsabilidades entre usuário e assistente
- Documentação detalhada conforme PDD oficial

## Alterações Recentes
- **17/06/2025**: Migração para ambiente Replit completada
- **17/06/2025**: RPA Sienge restaurado completamente com código funcional original
- **17/06/2025**: Todos os XPaths de webscraping funcional preservados
- **17/06/2025**: Integração entre webscraping funcional e processamento PDD mantida