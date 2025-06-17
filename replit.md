# Sistema RPA de Reparcelamento - Replit

## Visão Geral do Projeto
Sistema completo de RPA (Robotic Process Automation) para automatizar reparcelamentos financeiros em 4 sistemas: Coleta de Índices, Análise de Planilhas, Sienge e Sicredi.

## Estado Atual (Junho 2025)
- ✅ **RPA 1 (Coleta Índices)**: Implementado e funcionando
- ✅ **RPA 2 (Análise Planilhas)**: Implementado e funcionando
- 🔄 **RPA 3 (Sienge)**: Em implementação - processamento completo, webscraping em andamento
- ⏳ **RPA 4 (Sicredi)**: Aguardando finalização do RPA 3

## Progresso Atual - RPA Sienge
**O que está pronto:**
- Estrutura completa do código com documentação
- Processamento de planilhas Excel do Sienge
- Validação de inadimplência conforme regras PDD
- Cálculos de reparcelamento (IGP-M, juros 8%)
- Sistema de auditoria e logs

**O que precisa ser implementado:**
- Métodos de webscraping para navegação no Sienge
- Login automático no sistema
- Extração de relatórios financeiros
- Preenchimento de formulários de reparcelamento

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
- **17/06/2025**: Continuidade na implementação RPA Sienge - análise de documentação e código atual