#!/usr/bin/env python3
"""
Script Principal de Setup Completo
Orquestra todo o processo de instalação e configuração

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from typing import List, Tuple

def color_print(text: str, color_code: str = ""):
    """Imprime texto colorido"""
    if platform.system() != 'Windows':
        colors = {
            'green': '\033[92m',
            'red': '\033[91m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'reset': '\033[0m',
            'bold': '\033[1m',
        }
        print(f"{colors.get(color_code, '')}{text}{colors['reset']}")
    else:
        print(text)

def executar_script(nome: str, script_path: Path, projeto_raiz: Path) -> bool:
    """Executa um script e retorna sucesso"""
    color_print(f"\n{'='*80}", "blue")
    color_print(f"Executando: {nome}", "bold" + "blue")
    color_print(f"{'='*80}", "blue")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=projeto_raiz,
            timeout=600
        )
        
        if result.returncode == 0:
            color_print(f"✅ {nome} concluído", "green")
            return True
        else:
            color_print(f"❌ {nome} falhou com código {result.returncode}", "red")
            return False
    except subprocess.TimeoutExpired:
        color_print(f"❌ {nome} excedeu tempo limite", "red")
        return False
    except Exception as e:
        color_print(f"❌ Erro ao executar {nome}: {e}", "red")
        return False

def main():
    """Função principal"""
    print("=" * 80)
    color_print("SETUP COMPLETO DO PROJETO RPA", "bold")
    print("=" * 80)
    print()
    
    sistema = platform.system()
    projeto_raiz = Path(__file__).parent.parent
    
    color_print(f"Sistema Operacional: {sistema}", "blue")
    color_print(f"Diretório do Projeto: {projeto_raiz}", "blue")
    print()
    
    # Etapas do setup
    etapas = [
        ("Verificação de Pré-requisitos", projeto_raiz / 'scripts' / 'verificar_pre_requisitos.py'),
        ("Setup do UV", projeto_raiz / 'scripts' / 'setup_uv.py'),
        ("Instalação de Dependências", projeto_raiz / 'scripts' / 'instalar_dependencias.py'),
        ("Configuração do Chrome Driver", projeto_raiz / 'scripts' / 'configurar_chrome_driver.py'),
    ]
    
    resultados = []
    
    for nome, script_path in etapas:
        if not script_path.exists():
            color_print(f"⚠️  Script não encontrado: {script_path}", "yellow")
            resultados.append((nome, False))
            continue
        
        sucesso = executar_script(nome, script_path, projeto_raiz)
        resultados.append((nome, sucesso))
        
        if not sucesso:
            color_print(f"\n⚠️  Falha em {nome}. Deseja continuar mesmo assim? (s/n): ", "yellow")
            continuar = input().strip().lower()
            if continuar != 's':
                color_print("Setup interrompido pelo usuário", "yellow")
                return 1
    
    # Resumo
    print()
    print("=" * 80)
    color_print("RESUMO DO SETUP", "bold")
    print("=" * 80)
    
    for nome, sucesso in resultados:
        if sucesso:
            color_print(f"✅ {nome}", "green")
        else:
            color_print(f"❌ {nome}", "red")
    
    print()
    
    # Próximos passos
    total = len(resultados)
    aprovados = sum(1 for _, sucesso in resultados if sucesso)
    
    if aprovados == total:
        color_print("✅ SETUP COMPLETO CONCLUÍDO COM SUCESSO", "green" + "bold")
        print()
        color_print("Próximos passos:", "blue")
        color_print("1. Configure as credenciais:", "blue")
        color_print("   python scripts/configurar_ambiente.py", "blue")
        color_print("2. Valide as credenciais:", "blue")
        color_print("   python scripts/validar_credenciais.py", "blue")
        color_print("3. Teste a instalação:", "blue")
        color_print("   python scripts/testar_instalacao.py", "blue")
        print()
        return 0
    else:
        color_print(f"⚠️  SETUP CONCLUÍDO COM AVISOS ({aprovados}/{total} etapas OK)", "yellow" + "bold")
        color_print("\nRevise os erros acima antes de continuar", "yellow")
        return 1

if __name__ == "__main__":
    sys.exit(main())

