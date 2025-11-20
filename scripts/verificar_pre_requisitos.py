#!/usr/bin/env python3
"""
Script de Verificação de Pré-requisitos
Verifica se o ambiente está pronto para executar o projeto RPA

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Cores para output (funciona em Linux/macOS, ignorado no Windows)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def color_print(text: str, color: str = Colors.RESET):
    """Imprime texto colorido (se suportado)"""
    if platform.system() == 'Windows':
        print(text)
    else:
        print(f"{color}{text}{Colors.RESET}")

def verificar_python() -> Tuple[bool, str]:
    """Verifica versão do Python"""
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 11:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        else:
            return False, f"Python {version.major}.{version.minor}.{version.micro} (requer 3.11+)"
    except Exception as e:
        return False, f"Erro ao verificar Python: {e}"

def verificar_uv() -> Tuple[bool, str]:
    """Verifica se uv está instalado"""
    try:
        result = subprocess.run(
            ['uv', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        else:
            return False, "uv não encontrado"
    except FileNotFoundError:
        return False, "uv não instalado"
    except Exception as e:
        return False, f"Erro ao verificar uv: {e}"

def encontrar_chrome() -> Tuple[bool, str]:
    """Encontra instalação do Chrome"""
    sistema = platform.system()
    
    caminhos_chrome = {
        'Linux': [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/snap/bin/chromium',
        ],
        'Windows': [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe'),
        ],
        'Darwin': [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
        ]
    }
    
    caminhos = caminhos_chrome.get(sistema, [])
    
    for caminho in caminhos:
        if os.path.exists(caminho):
            try:
                # Tentar obter versão
                if sistema == 'Windows':
                    cmd = [caminho, '--version']
                else:
                    cmd = [caminho, '--version']
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 or result.stdout or result.stderr:
                    version = (result.stdout or result.stderr).strip()
                    return True, f"{caminho} ({version})"
            except:
                return True, caminho
    
    return False, "Chrome não encontrado"

def encontrar_firefox() -> Tuple[bool, str]:
    """Encontra instalação do Firefox"""
    sistema = platform.system()
    
    caminhos_firefox = {
        'Linux': [
            '/usr/bin/firefox',
            '/usr/bin/firefox-esr',
            '/snap/bin/firefox',
        ],
        'Windows': [
            r'C:\Program Files\Mozilla Firefox\firefox.exe',
            r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe',
            os.path.expanduser(r'~\AppData\Local\Mozilla Firefox\firefox.exe'),
        ],
        'Darwin': [
            '/Applications/Firefox.app/Contents/MacOS/firefox',
        ]
    }
    
    caminhos = caminhos_firefox.get(sistema, [])
    
    for caminho in caminhos:
        if os.path.exists(caminho):
            try:
                # Tentar obter versão
                if sistema == 'Windows':
                    cmd = [caminho, '--version']
                else:
                    cmd = [caminho, '--version']
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 or result.stdout or result.stderr:
                    version = (result.stdout or result.stderr).strip()
                    return True, f"{caminho} ({version})"
            except:
                return True, caminho
    
    return False, "Firefox não encontrado"

def verificar_permissões_diretorio(caminho: Path) -> Tuple[bool, str]:
    """Verifica permissões de escrita em diretório"""
    try:
        # Criar diretório se não existir
        caminho.mkdir(parents=True, exist_ok=True)
        
        # Testar escrita
        arquivo_teste = caminho / '.teste_escrita'
        try:
            arquivo_teste.write_text('teste')
            arquivo_teste.unlink()
            return True, f"Permissões OK: {caminho}"
        except Exception as e:
            return False, f"Sem permissão de escrita em {caminho}: {e}"
    except Exception as e:
        return False, f"Erro ao verificar {caminho}: {e}"

def verificar_conectividade() -> Tuple[bool, str]:
    """Verifica conectividade de rede"""
    try:
        # Testar conexão com Google (DNS e conectividade)
        if platform.system() == 'Windows':
            result = subprocess.run(
                ['ping', '-n', '1', '8.8.8.8'],
                capture_output=True,
                timeout=5
            )
        else:
            result = subprocess.run(
                ['ping', '-c', '1', '8.8.8.8'],
                capture_output=True,
                timeout=5
            )
        
        if result.returncode == 0:
            return True, "Conectividade OK"
        else:
            return False, "Sem conectividade de rede"
    except Exception as e:
        return False, f"Erro ao verificar conectividade: {e}"

def verificar_estrutura_diretorios() -> Tuple[bool, List[str]]:
    """Verifica estrutura de diretórios necessários"""
    diretorios_necessarios = [
        'core',
        'scripts',
        'rpa_sienge',
        'rpa_sicredi',
        'rpa_coleta_indices',
        'rpa_analise_planilhas',
        'credentials',
        'data',
        'logs',
        'outputs',
    ]
    
    diretorios_faltando = []
    projeto_raiz = Path(__file__).parent.parent
    
    for diretorio in diretorios_necessarios:
        caminho = projeto_raiz / diretorio
        if not caminho.exists():
            diretorios_faltando.append(str(diretorio))
    
    if diretorios_faltando:
        return False, diretorios_faltando
    else:
        return True, []

def obter_info_sistema() -> Dict[str, str]:
    """Obtém informações do sistema"""
    return {
        'sistema': platform.system(),
        'arquitetura': platform.machine(),
        'processador': platform.processor(),
        'versao': platform.version(),
        'python': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

def main():
    """Função principal"""
    print("=" * 80)
    color_print("VERIFICAÇÃO DE PRÉ-REQUISITOS", Colors.BOLD + Colors.BLUE)
    print("=" * 80)
    print()
    
    # Informações do sistema
    info = obter_info_sistema()
    color_print(f"Sistema Operacional: {info['sistema']} {info['versao']}", Colors.BLUE)
    color_print(f"Arquitetura: {info['arquitetura']}", Colors.BLUE)
    color_print(f"Processador: {info['processador']}", Colors.BLUE)
    print()
    
    # Lista de verificações
    verificacoes = [
        ("Python 3.11+", verificar_python),
        ("uv instalado", verificar_uv),
        ("Google Chrome", encontrar_chrome),
        ("Mozilla Firefox", encontrar_firefox),
        ("Conectividade de rede", verificar_conectividade),
    ]
    
    resultados = []
    projeto_raiz = Path(__file__).parent.parent
    
    # Verificar permissões de diretórios
    diretorios_verificar = [
        projeto_raiz / 'data',
        projeto_raiz / 'logs',
        projeto_raiz / 'outputs',
        projeto_raiz / 'credentials',
    ]
    
    for nome, funcao in verificacoes:
        sucesso, mensagem = funcao()
        resultados.append((nome, sucesso, mensagem))
        
        if sucesso:
            color_print(f"✅ {nome}: {mensagem}", Colors.GREEN)
        else:
            color_print(f"❌ {nome}: {mensagem}", Colors.RED)
    
    print()
    color_print("Verificando permissões de diretórios...", Colors.BLUE)
    for diretorio in diretorios_verificar:
        sucesso, mensagem = verificar_permissões_diretorio(diretorio)
        if sucesso:
            color_print(f"✅ {mensagem}", Colors.GREEN)
        else:
            color_print(f"❌ {mensagem}", Colors.RED)
    
    print()
    color_print("Verificando estrutura de diretórios...", Colors.BLUE)
    sucesso, faltando = verificar_estrutura_diretorios()
    if sucesso:
        color_print("✅ Estrutura de diretórios OK", Colors.GREEN)
    else:
        color_print(f"❌ Diretórios faltando: {', '.join(faltando)}", Colors.RED)
    
    print()
    print("=" * 80)
    
    # Resumo
    total = len(resultados)
    aprovados = sum(1 for _, sucesso, _ in resultados if sucesso)
    
    if aprovados == total:
        color_print(f"✅ TODAS AS VERIFICAÇÕES PASSARAM ({aprovados}/{total})", Colors.GREEN + Colors.BOLD)
        return 0
    else:
        color_print(f"⚠️  ALGUMAS VERIFICAÇÕES FALHARAM ({aprovados}/{total})", Colors.YELLOW + Colors.BOLD)
        color_print("Execute os scripts de setup para corrigir os problemas.", Colors.YELLOW)
        return 1

if __name__ == "__main__":
    sys.exit(main())

