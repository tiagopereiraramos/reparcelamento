#!/usr/bin/env python3
"""
Script de Configuração do Chrome Driver
Detecta versão do Chrome e configura undetected-chromedriver

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
import subprocess
import re
from pathlib import Path
from typing import Optional, Tuple

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

def encontrar_chrome() -> Optional[str]:
    """Encontra caminho do Chrome"""
    sistema = platform.system()
    
    caminhos = {
        'Linux': [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
        ],
        'Windows': [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe'),
        ],
        'Darwin': [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ]
    }
    
    for caminho in caminhos.get(sistema, []):
        if os.path.exists(caminho):
            return caminho
    
    return None

def obter_versao_chrome(caminho: str) -> Optional[int]:
    """Obtém versão principal do Chrome"""
    try:
        sistema = platform.system()
        
        if sistema == 'Windows':
            # Windows: usar --version ou verificar arquivo
            result = subprocess.run(
                [caminho, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout or result.stderr
        else:
            # Linux/macOS
            result = subprocess.run(
                [caminho, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout or result.stderr
        
        # Extrair versão (ex: "Google Chrome 120.0.6099.109")
        match = re.search(r'(\d+)\.\d+\.\d+', output)
        if match:
            return int(match.group(1))
    except Exception as e:
        color_print(f"⚠️  Erro ao obter versão: {e}", "yellow")
    
    return None

def detectar_arquitetura() -> str:
    """Detecta arquitetura do sistema"""
    machine = platform.machine().lower()
    
    if 'arm' in machine or 'aarch64' in machine:
        return 'arm64'
    elif 'x86_64' in machine or 'amd64' in machine:
        return 'x86_64'
    elif 'i386' in machine or 'i686' in machine:
        return 'i386'
    else:
        return 'unknown'

def testar_undetected_chromedriver(versao: Optional[int]) -> bool:
    """Testa se undetected-chromedriver funciona"""
    color_print("Testando undetected-chromedriver...", "blue")
    
    try:
        projeto_raiz = Path(__file__).parent.parent
        sistema = platform.system()
        
        if sistema == "Windows":
            python_path = projeto_raiz / '.venv' / 'Scripts' / 'python.exe'
        else:
            python_path = projeto_raiz / '.venv' / 'bin' / 'python'
        
        if not python_path.exists():
            color_print("⚠️  Ambiente virtual não encontrado", "yellow")
            return False
        
        # Script de teste
        script_teste = f"""
import undetected_chromedriver as uc
import sys

try:
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options, version_main={versao if versao else 'None'})
    driver.get('https://www.google.com')
    print('SUCCESS')
    driver.quit()
    sys.exit(0)
except Exception as e:
    print(f'ERROR: {{e}}')
    sys.exit(1)
"""
        
        result = subprocess.run(
            [str(python_path), '-c', script_teste],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if 'SUCCESS' in result.stdout:
            color_print("✅ undetected-chromedriver funcionando", "green")
            return True
        else:
            color_print(f"❌ Erro no teste: {result.stdout}", "red")
            return False
            
    except Exception as e:
        color_print(f"❌ Erro ao testar: {e}", "red")
        return False

def main():
    """Função principal"""
    print("=" * 80)
    color_print("CONFIGURAÇÃO DO CHROME DRIVER", "bold")
    print("=" * 80)
    print()
    
    # Detectar sistema
    sistema = platform.system()
    arquitetura = detectar_arquitetura()
    
    color_print(f"Sistema: {sistema}", "blue")
    color_print(f"Arquitetura: {arquitetura}", "blue")
    print()
    
    # Encontrar Chrome
    color_print("Procurando Google Chrome...", "blue")
    caminho_chrome = encontrar_chrome()
    
    if not caminho_chrome:
        color_print("❌ Google Chrome não encontrado", "red")
        color_print("Instale o Google Chrome antes de continuar", "yellow")
        return 1
    
    color_print(f"✅ Chrome encontrado: {caminho_chrome}", "green")
    
    # Obter versão
    color_print("Obtendo versão do Chrome...", "blue")
    versao = obter_versao_chrome(caminho_chrome)
    
    if versao:
        color_print(f"✅ Versão do Chrome: {versao}", "green")
    else:
        color_print("⚠️  Não foi possível detectar versão", "yellow")
        versao = None
    
    print()
    
    # Testar undetected-chromedriver
    if testar_undetected_chromedriver(versao):
        print()
        print("=" * 80)
        color_print("✅ CHROME DRIVER CONFIGURADO COM SUCESSO", "green" + "bold")
        print("=" * 80)
        return 0
    else:
        print()
        color_print("⚠️  Problemas detectados com o driver", "yellow")
        color_print("O undetected-chromedriver tentará baixar a versão correta automaticamente", "yellow")
        return 1

if __name__ == "__main__":
    sys.exit(main())

