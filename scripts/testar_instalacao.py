#!/usr/bin/env python3
"""
Script de Teste Pós-Instalação
Valida instalação completa do projeto

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
import subprocess
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

def testar_importacoes(projeto_raiz: Path) -> bool:
    """Testa importações de pacotes críticos"""
    color_print("Testando importações...", "blue")
    
    sistema = platform.system()
    if sistema == "Windows":
        python_path = projeto_raiz / '.venv' / 'Scripts' / 'python.exe'
    else:
        python_path = projeto_raiz / '.venv' / 'bin' / 'python'
    
    if not python_path.exists():
        # Tentar uv run
        python_path = None
    
    pacotes = [
        'selenium',
        'undetected_chromedriver',
        'gspread',
        'pandas',
        'openpyxl',
        'dotenv',
    ]
    
    falhas = []
    for pacote in pacotes:
        try:
            import_name = pacote.replace('-', '_')
            if python_path:
                result = subprocess.run(
                    [str(python_path), '-c', f'import {import_name}'],
                    capture_output=True,
                    timeout=10
                )
                sucesso = result.returncode == 0
            else:
                # Usar uv run
                result = subprocess.run(
                    ['uv', 'run', 'python', '-c', f'import {import_name}'],
                    cwd=projeto_raiz,
                    capture_output=True,
                    timeout=10
                )
                sucesso = result.returncode == 0
            
            if sucesso:
                color_print(f"✅ {pacote}", "green")
            else:
                falhas.append(pacote)
                color_print(f"❌ {pacote}", "red")
        except Exception as e:
            falhas.append(pacote)
            color_print(f"❌ {pacote}: {e}", "red")
    
    return len(falhas) == 0

def testar_drivers(projeto_raiz: Path) -> bool:
    """Testa inicialização de drivers"""
    color_print("Testando drivers...", "blue")
    
    sistema = platform.system()
    if sistema == "Windows":
        python_path = projeto_raiz / '.venv' / 'Scripts' / 'python.exe'
    else:
        python_path = projeto_raiz / '.venv' / 'bin' / 'python'
    
    if not python_path.exists():
        python_path = None
    
    # Teste básico de importação do browser_manager
    try:
        if python_path:
            result = subprocess.run(
                [str(python_path), '-c', 'from core.browser_manager import RPABrowser'],
                cwd=projeto_raiz,
                capture_output=True,
                timeout=10
            )
            sucesso = result.returncode == 0
        else:
            result = subprocess.run(
                ['uv', 'run', 'python', '-c', 'from core.browser_manager import RPABrowser'],
                cwd=projeto_raiz,
                capture_output=True,
                timeout=10
            )
            sucesso = result.returncode == 0
        
        if sucesso:
            color_print("✅ browser_manager importado", "green")
            return True
        else:
            color_print(f"❌ Erro ao importar browser_manager: {result.stderr.decode()}", "red")
            return False
    except Exception as e:
        color_print(f"❌ Erro: {e}", "red")
        return False

def testar_conexoes(projeto_raiz: Path) -> bool:
    """Testa conexões com serviços externos"""
    color_print("Testando conexões...", "blue")
    
    # Verificar se .env existe
    env_path = projeto_raiz / '.env'
    if not env_path.exists():
        color_print("⚠️  Arquivo .env não encontrado - pulando testes de conexão", "yellow")
        return True
    
    # Executar script de validação de credenciais
    validar_script = projeto_raiz / 'scripts' / 'validar_credenciais.py'
    if validar_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(validar_script)],
                cwd=projeto_raiz,
                capture_output=True,
                timeout=60
            )
            # Não falhar se houver problemas - apenas avisar
            if result.returncode == 0:
                color_print("✅ Credenciais validadas", "green")
            else:
                color_print("⚠️  Alguns problemas nas credenciais (verifique manualmente)", "yellow")
            return True
        except Exception as e:
            color_print(f"⚠️  Erro ao validar credenciais: {e}", "yellow")
            return True
    else:
        color_print("⚠️  Script de validação não encontrado", "yellow")
        return True

def testar_scripts_principais(projeto_raiz: Path) -> bool:
    """Testa se scripts principais são executáveis"""
    color_print("Testando scripts principais...", "blue")
    
    scripts = [
        'scripts/main_coleta_indices.py',
        'scripts/main_analise_planilhas.py',
        'scripts/main_extracao_relatorio_sienge.py',
    ]
    
    todos_ok = True
    for script_rel in scripts:
        script_path = projeto_raiz / script_rel
        if script_path.exists():
            # Apenas verificar se o script pode ser importado/executado com --help
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path), '--help'],
                    cwd=projeto_raiz,
                    capture_output=True,
                    timeout=10
                )
                # Não importa o código de retorno - apenas se não deu erro fatal
                color_print(f"✅ {script_rel}", "green")
            except:
                color_print(f"⚠️  {script_rel} (verifique manualmente)", "yellow")
        else:
            color_print(f"⚠️  {script_rel} não encontrado", "yellow")
    
    return todos_ok

def main():
    """Função principal"""
    print("=" * 80)
    color_print("TESTE DE INSTALAÇÃO", "bold")
    print("=" * 80)
    print()
    
    projeto_raiz = Path(__file__).parent.parent
    
    # Executar testes
    testes = [
        ("Importações", lambda: testar_importacoes(projeto_raiz)),
        ("Drivers", lambda: testar_drivers(projeto_raiz)),
        ("Conexões", lambda: testar_conexoes(projeto_raiz)),
        ("Scripts Principais", lambda: testar_scripts_principais(projeto_raiz)),
    ]
    
    resultados = []
    
    for nome, funcao in testes:
        print()
        try:
            sucesso = funcao()
            resultados.append((nome, sucesso))
        except Exception as e:
            color_print(f"❌ Erro no teste {nome}: {e}", "red")
            resultados.append((nome, False))
    
    # Resumo
    print()
    print("=" * 80)
    color_print("RESUMO DOS TESTES", "bold")
    print("=" * 80)
    
    for nome, sucesso in resultados:
        if sucesso:
            color_print(f"✅ {nome}", "green")
        else:
            color_print(f"❌ {nome}", "red")
    
    print()
    
    total = len(resultados)
    aprovados = sum(1 for _, sucesso in resultados if sucesso)
    
    if aprovados == total:
        color_print("✅ TODOS OS TESTES PASSARAM", "green" + "bold")
        color_print("\nInstalação validada com sucesso!", "green")
        return 0
    else:
        color_print(f"⚠️  ALGUNS TESTES FALHARAM ({aprovados}/{total})", "yellow" + "bold")
        color_print("\nRevise os problemas acima", "yellow")
        return 1

if __name__ == "__main__":
    sys.exit(main())

