#!/usr/bin/env python3
"""
Wrapper para Execução Agendada
Garante que scripts agendados executem com ambiente correto

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from datetime import datetime

def color_print(text: str, color_code: str = ""):
    """Imprime texto colorido"""
    if platform.system() != 'Windows':
        colors = {
            'green': '\033[92m',
            'red': '\033[91m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'reset': '\033[0m',
        }
        print(f"{colors.get(color_code, '')}{text}{colors['reset']}")
    else:
        print(text)

def obter_python_path() -> Path:
    """Obtém caminho do Python do ambiente virtual"""
    projeto_raiz = Path(__file__).parent.parent
    sistema = platform.system()
    
    if sistema == "Windows":
        python_path = projeto_raiz / '.venv' / 'Scripts' / 'python.exe'
    else:
        python_path = projeto_raiz / '.venv' / 'bin' / 'python'
    
    # Se não encontrar, tentar uv run
    if not python_path.exists():
        # Verificar se uv está disponível
        try:
            subprocess.run(['uv', '--version'], capture_output=True, check=True, timeout=5)
            return None  # Usar uv run
        except:
            pass
    
    return python_path if python_path.exists() else None

def executar_com_uv(script: Path, args: list) -> int:
    """Executa script usando uv run"""
    projeto_raiz = Path(__file__).parent.parent
    
    cmd = ['uv', 'run', 'python', str(script)] + args
    
    try:
        result = subprocess.run(
            cmd,
            cwd=projeto_raiz,
            timeout=3600  # 1 hora máximo
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        color_print("❌ Timeout na execução", "red")
        return 1
    except Exception as e:
        color_print(f"❌ Erro na execução: {e}", "red")
        return 1

def executar_com_venv(script: Path, args: list) -> int:
    """Executa script usando ambiente virtual"""
    projeto_raiz = Path(__file__).parent.parent
    python_path = obter_python_path()
    
    if not python_path:
        color_print("❌ Ambiente virtual não encontrado", "red")
        return 1
    
    cmd = [str(python_path), str(script)] + args
    
    try:
        result = subprocess.run(
            cmd,
            cwd=projeto_raiz,
            env=os.environ.copy(),
            timeout=3600  # 1 hora máximo
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        color_print("❌ Timeout na execução", "red")
        return 1
    except Exception as e:
        color_print(f"❌ Erro na execução: {e}", "red")
        return 1

def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python executar_agendado.py <script> [args...]")
        print("Exemplo: python executar_agendado.py scripts/main_coleta_indices.py")
        return 1
    
    script_path = Path(sys.argv[1])
    args = sys.argv[2:]
    
    projeto_raiz = Path(__file__).parent.parent
    
    # Converter caminho relativo para absoluto
    if not script_path.is_absolute():
        script_path = projeto_raiz / script_path
    
    if not script_path.exists():
        color_print(f"❌ Script não encontrado: {script_path}", "red")
        return 1
    
    # Log de início
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color_print(f"[{timestamp}] Iniciando execução agendada: {script_path.name}", "blue")
    
    # Carregar variáveis de ambiente
    env_path = projeto_raiz / '.env'
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        color_print("✅ Variáveis de ambiente carregadas", "green")
    else:
        color_print("⚠️  Arquivo .env não encontrado", "yellow")
    
    # Executar script
    python_path = obter_python_path()
    
    if python_path is None:
        # Usar uv run
        color_print("Usando uv run para execução", "blue")
        return_code = executar_com_uv(script_path, args)
    else:
        # Usar ambiente virtual
        color_print(f"Usando ambiente virtual: {python_path}", "blue")
        return_code = executar_com_venv(script_path, args)
    
    # Log de fim
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if return_code == 0:
        color_print(f"[{timestamp}] ✅ Execução concluída com sucesso", "green")
    else:
        color_print(f"[{timestamp}] ❌ Execução falhou com código {return_code}", "red")
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())

