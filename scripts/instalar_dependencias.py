#!/usr/bin/env python3
"""
Script de Instalação de Dependências
Instala todas as dependências do projeto usando uv

Suporta: Linux, Windows, macOS
"""

import sys
import subprocess
import platform
from pathlib import Path

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

def verificar_uv():
    """Verifica se uv está instalado"""
    try:
        result = subprocess.run(
            ['uv', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

def instalar_dependencias(projeto_raiz: Path) -> bool:
    """Instala dependências usando uv sync"""
    color_print("Instalando dependências com uv sync...", "blue")
    
    try:
        result = subprocess.run(
            ['uv', 'sync'],
            cwd=projeto_raiz,
            check=True,
            timeout=600
        )
        color_print("✅ Dependências instaladas com sucesso", "green")
        return True
    except subprocess.CalledProcessError as e:
        color_print(f"❌ Erro ao instalar dependências: {e}", "red")
        return False
    except Exception as e:
        color_print(f"❌ Erro inesperado: {e}", "red")
        return False

def verificar_pacotes_criticos(projeto_raiz: Path) -> bool:
    """Verifica se pacotes críticos foram instalados"""
    color_print("Verificando pacotes críticos...", "blue")
    
    pacotes = [
        'selenium',
        'undetected_chromedriver',
        'gspread',
        'pandas',
        'openpyxl',
        'python-dotenv',
    ]
    
    sistema = platform.system()
    if sistema == "Windows":
        python_path = projeto_raiz / '.venv' / 'Scripts' / 'python.exe'
    else:
        python_path = projeto_raiz / '.venv' / 'bin' / 'python'
    
    if not python_path.exists():
        color_print("❌ Ambiente virtual não encontrado", "red")
        return False
    
    falhas = []
    for pacote in pacotes:
        try:
            # Normalizar nome do pacote para importação
            import_name = pacote.replace('-', '_')
            result = subprocess.run(
                [str(python_path), '-c', f'import {import_name}'],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                color_print(f"✅ {pacote}", "green")
            else:
                falhas.append(pacote)
                color_print(f"❌ {pacote} não encontrado", "red")
        except Exception as e:
            falhas.append(pacote)
            color_print(f"❌ Erro ao verificar {pacote}: {e}", "red")
    
    if falhas:
        color_print(f"⚠️  {len(falhas)} pacote(s) com problemas", "yellow")
        return False
    else:
        color_print("✅ Todos os pacotes críticos instalados", "green")
        return True

def main():
    """Função principal"""
    print("=" * 80)
    color_print("INSTALAÇÃO DE DEPENDÊNCIAS", "bold")
    print("=" * 80)
    print()
    
    if not verificar_uv():
        color_print("❌ uv não está instalado", "red")
        color_print("Execute primeiro: python scripts/setup_uv.py", "yellow")
        return 1
    
    projeto_raiz = Path(__file__).parent.parent
    
    if not instalar_dependencias(projeto_raiz):
        return 1
    
    print()
    
    if not verificar_pacotes_criticos(projeto_raiz):
        color_print("⚠️  Alguns pacotes podem ter problemas", "yellow")
        color_print("Tente executar 'uv sync' novamente", "yellow")
        return 1
    
    print()
    print("=" * 80)
    color_print("✅ INSTALAÇÃO CONCLUÍDA", "green" + "bold")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

