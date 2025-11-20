#!/usr/bin/env python3
"""
Script de Setup do UV
Instala e configura o uv para gerenciamento de dependências

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional

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

def verificar_uv_instalado() -> Tuple[bool, Optional[str]]:
    """Verifica se uv está instalado"""
    try:
        result = subprocess.run(
            ['uv', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, None
    except FileNotFoundError:
        return False, None
    except Exception:
        return False, None

def instalar_uv() -> bool:
    """Instala o uv"""
    sistema = platform.system()
    
    color_print("Instalando uv...", "blue")
    
    try:
        if sistema == "Windows":
            # Windows: usar pip ou curl
            try:
                # Tentar com pip primeiro
                subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', 'uv'],
                    check=True,
                    timeout=120
                )
                color_print("✅ uv instalado via pip", "green")
                return True
            except:
                # Tentar com PowerShell
                try:
                    ps_script = """
                    $ProgressPreference = 'SilentlyContinue'
                    Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing | Invoke-Expression
                    """
                    subprocess.run(
                        ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                        check=True,
                        timeout=120
                    )
                    color_print("✅ uv instalado via script oficial", "green")
                    return True
                except Exception as e:
                    color_print(f"❌ Erro ao instalar uv: {e}", "red")
                    return False
        else:
            # Linux/macOS: usar curl
            try:
                subprocess.run(
                    ['curl', '-LsSf', 'https://astral.sh/uv/install.sh', '|', 'sh'],
                    shell=True,
                    check=True,
                    timeout=120
                )
                color_print("✅ uv instalado via script oficial", "green")
                return True
            except Exception as e:
                # Fallback: pip
                try:
                    subprocess.run(
                        [sys.executable, '-m', 'pip', 'install', 'uv'],
                        check=True,
                        timeout=120
                    )
                    color_print("✅ uv instalado via pip", "green")
                    return True
                except Exception as e2:
                    color_print(f"❌ Erro ao instalar uv: {e2}", "red")
                    return False
    except Exception as e:
        color_print(f"❌ Erro ao instalar uv: {e}", "red")
        return False

def criar_ambiente_virtual(projeto_raiz: Path) -> bool:
    """Cria ambiente virtual com uv"""
    color_print("Criando ambiente virtual com uv...", "blue")
    
    try:
        # Usar uv para criar ambiente virtual
        subprocess.run(
            ['uv', 'venv'],
            cwd=projeto_raiz,
            check=True,
            timeout=60
        )
        color_print("✅ Ambiente virtual criado", "green")
        return True
    except subprocess.CalledProcessError as e:
        color_print(f"❌ Erro ao criar ambiente virtual: {e}", "red")
        return False
    except Exception as e:
        color_print(f"❌ Erro inesperado: {e}", "red")
        return False

def instalar_dependencias(projeto_raiz: Path) -> bool:
    """Instala dependências do projeto"""
    color_print("Instalando dependências do projeto...", "blue")
    
    try:
        # Usar uv sync para instalar todas as dependências
        subprocess.run(
            ['uv', 'sync'],
            cwd=projeto_raiz,
            check=True,
            timeout=600  # 10 minutos
        )
        color_print("✅ Dependências instaladas", "green")
        return True
    except subprocess.CalledProcessError as e:
        color_print(f"❌ Erro ao instalar dependências: {e}", "red")
        return False
    except Exception as e:
        color_print(f"❌ Erro inesperado: {e}", "red")
        return False

def validar_instalacao(projeto_raiz: Path) -> bool:
    """Valida instalação testando importações"""
    color_print("Validando instalação...", "blue")
    
    pacotes_criticos = [
        'selenium',
        'undetected_chromedriver',
        'gspread',
        'pandas',
        'openpyxl',
    ]
    
    # Ativar ambiente virtual e testar importações
    sistema = platform.system()
    if sistema == "Windows":
        python_path = projeto_raiz / '.venv' / 'Scripts' / 'python.exe'
    else:
        python_path = projeto_raiz / '.venv' / 'bin' / 'python'
    
    if not python_path.exists():
        color_print("❌ Ambiente virtual não encontrado", "red")
        return False
    
    falhas = []
    for pacote in pacotes_criticos:
        try:
            result = subprocess.run(
                [str(python_path), '-c', f'import {pacote}'],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                color_print(f"✅ {pacote} importado com sucesso", "green")
            else:
                falhas.append(pacote)
                color_print(f"❌ {pacote} não pôde ser importado", "red")
        except Exception as e:
            falhas.append(pacote)
            color_print(f"❌ Erro ao testar {pacote}: {e}", "red")
    
    if falhas:
        color_print(f"⚠️  {len(falhas)} pacote(s) com problemas", "yellow")
        return False
    else:
        color_print("✅ Todas as importações OK", "green")
        return True

def main():
    """Função principal"""
    print("=" * 80)
    color_print("SETUP DO UV - Gerenciamento de Dependências", "bold")
    print("=" * 80)
    print()
    
    projeto_raiz = Path(__file__).parent.parent
    
    # Verificar se uv está instalado
    color_print("Verificando instalação do uv...", "blue")
    instalado, versao = verificar_uv_instalado()
    
    if instalado:
        color_print(f"✅ uv já está instalado: {versao}", "green")
    else:
        color_print("⚠️  uv não encontrado, instalando...", "yellow")
        if not instalar_uv():
            color_print("❌ Falha ao instalar uv", "red")
            return 1
        
        # Verificar novamente
        instalado, versao = verificar_uv_instalado()
        if not instalado:
            color_print("❌ uv não foi instalado corretamente", "red")
            color_print("Tente instalar manualmente: pip install uv", "yellow")
            return 1
    
    print()
    
    # Criar ambiente virtual
    if not criar_ambiente_virtual(projeto_raiz):
        return 1
    
    print()
    
    # Instalar dependências
    if not instalar_dependencias(projeto_raiz):
        return 1
    
    print()
    
    # Validar instalação
    if not validar_instalacao(projeto_raiz):
        color_print("⚠️  Alguns pacotes podem ter problemas", "yellow")
        color_print("Execute 'uv sync' novamente se necessário", "yellow")
        return 1
    
    print()
    print("=" * 80)
    color_print("✅ SETUP DO UV CONCLUÍDO COM SUCESSO", "green" + "bold")
    print("=" * 80)
    print()
    color_print("Próximos passos:", "blue")
    color_print("1. Execute: python scripts/configurar_ambiente.py", "blue")
    color_print("2. Execute: python scripts/validar_credenciais.py", "blue")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

