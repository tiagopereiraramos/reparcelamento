#!/bin/bash
# Script de Limpeza do Sistema RPA v2.0
# Remove arquivos obsoletos e prepara ambiente limpo

echo "🧹 Limpando Sistema RPA v2.0..."

# Remover arquivos Python temporários
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remover logs antigos (manter estrutura)
rm -rf logs/*.log 2>/dev/null || true
rm -rf temp/* 2>/dev/null || true

# Remover arquivos de ambiente de desenvolvimento
rm -f .env 2>/dev/null || true

# Limpar cache
rm -rf .cache 2>/dev/null || true

# Arquivos obsoletos específicos identificados
echo "📋 Removendo arquivos obsoletos:"

# Arquivos de teste antigos
rm -f webscraping_pdd_correto.py 2>/dev/null && echo "✅ webscraping_pdd_correto.py removido"
rm -f webscraping_pdd_firefox.py 2>/dev/null && echo "✅ webscraping_pdd_firefox.py removido"
rm -f webscraping_pdd_simples.py 2>/dev/null && echo "✅ webscraping_pdd_simples.py removido"
rm -f workflow_final_corrigido.py 2>/dev/null && echo "✅ workflow_final_corrigido.py removido"
rm -f workflow_planilha_nativa.py 2>/dev/null && echo "✅ workflow_planilha_nativa.py removido"

# Testes antigos
rm -f test_final_workflow.py 2>/dev/null && echo "✅ test_final_workflow.py removido"
rm -f test_google_sheets_workflow.py 2>/dev/null && echo "✅ test_google_sheets_workflow.py removido"
rm -f test_sheets_access.py 2>/dev/null && echo "✅ test_sheets_access.py removido"
rm -f test_simple_sheets.py 2>/dev/null && echo "✅ test_simple_sheets.py removido"

# Scripts antigos
rm -f execute_reparcelamento_workflow.py 2>/dev/null && echo "✅ execute_reparcelamento_workflow.py removido"
rm -f start-services.sh 2>/dev/null && echo "✅ start-services.sh removido"
rm -f test-api.sh 2>/dev/null && echo "✅ test-api.sh removido"

# Arquivos Docker antigos
rm -f Dockerfile.dev 2>/dev/null && echo "✅ Dockerfile.dev removido"
rm -f docker-compose.yml 2>/dev/null && echo "✅ docker-compose.yml antigo removido"

# Arquivos de documentação obsoletos
rm -f ARQUITETURA_NOVA.md 2>/dev/null && echo "✅ ARQUITETURA_NOVA.md removido"

# Arquivos de credenciais de exemplo/teste
rm -f gspread-459713-aab8a657f9b0.json 2>/dev/null && echo "✅ Credenciais de teste removidas"

echo ""
echo "✅ Limpeza concluída!"
echo "📦 Sistema pronto para empacotamento"