#!/bin/bash

# Script para limpar repositório do Sistema RPA
# Remove arquivos desnecessários e organiza estrutura

echo "🧹 LIMPANDO REPOSITÓRIO - SISTEMA RPA v2.0"
echo "=========================================="

echo "🗑️  Removendo pacotes antigos..."
rm -f sistema_rpa_*.tar.gz
rm -f sistema-rpa-*.tar.gz

echo "📁 Removendo pastas temporárias..."
rm -rf pacote_entrega/
rm -rf deploy/
rm -rf ci-cd/

echo "📄 Removendo documentações duplicadas..."
rm -f ENTREGA_FINAL_SISTEMA_RPA.md
rm -f ESTRUTURA_PROJETO_FINAL.md
rm -f GUIA_RAPIDO.md
rm -f MANUAL_COMPLETO_SISTEMA_RPA.md
rm -f MANUAL_COMPORTAMENTOS_SISTEMA.md
rm -f PACOTE_DESENVOLVIMENTO_COMPLETO.md
rm -f README_DEPLOY.md
rm -f README_INSTALACAO_UV.md

echo "🔧 Removendo arquivos de configuração obsoletos..."
rm -f Dockerfile
rm -f docker-compose.yml
rm -f start_dashboard.py

echo "📂 Limpando logs antigos..."
rm -rf logs/*

echo "🔍 Verificando arquivos principais..."
echo "✅ Mantendo arquivos essenciais:"
echo "   • core/ (módulos principais)"
echo "   • rpa_*/ (4 RPAs)"
echo "   • scripts/ (utilitários)"
echo "   • workflows/ (orquestração)"
echo "   • .vscode/ (configurações debug)"
echo "   • main.py, dashboard_*.py (interfaces)"
echo "   • pyproject.toml (dependências)"

echo ""
echo "✨ LIMPEZA CONCLUÍDA!"
echo "==================="
echo "📁 Repositório organizado e limpo"
echo "🚀 Pronto para desenvolvimento"
echo ""
echo "📋 ESTRUTURA FINAL:"
echo "├── .vscode/              # Configurações VSCode"
echo "├── core/                 # Módulos principais"
echo "├── rpa_*/                # 4 RPAs individuais"
echo "├── scripts/              # Scripts utilitários"
echo "├── workflows/            # Orquestração Temporal"
echo "├── main.py              # API principal"
echo "├── dashboard_*.py       # Interfaces web"
echo "├── teste_*.py           # Scripts de teste"
echo "└── pyproject.toml       # Dependências"