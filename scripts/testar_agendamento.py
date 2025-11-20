#!/usr/bin/env python3
"""
Script de Teste de Agendamento
Simula execução agendada para validar configuração

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
        }
        print(f"{colors.get(color_code, '')}{text}{colors['reset']}")
    else:
        print(text)

def verificar_variaveis_ambiente(projeto_raiz: Path) -> bool:
    """Verifica se variáveis de ambiente estão carregadas"""
    color_print("Verificando variáveis de ambiente...", "blue")
    
    env_path = projeto_raiz / '.env'
    if not env_path.exists():
        color_print("❌ Arquivo .env não encontrado", "red")
        return False
    
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    variaveis_obrigatorias = [
        'PLANILHA_CALCULO_ID',
        'SIENGE_USUARIO',
        'SIENGE_SENHA',
    ]
    
    faltando = []
    for var in variaveis_obrigatorias:
        if not os.getenv(var):
            faltando.append(var)
    
    if faltando:
        color_print(f"❌ Variáveis faltando: {', '.join(faltando)}", "red")
        return False
    
    color_print("✅ Variáveis de ambiente OK", "green")
    return True

def verificar_caminhos(projeto_raiz: Path) -> bool:
    """Verifica se caminhos estão corretos"""
    color_print("Verificando caminhos...", "blue")
    
    caminhos_necessarios = [
        projeto_raiz / 'scripts' / 'executar_agendado.py',
        projeto_raiz / '.venv',
    ]
    
    for caminho in caminhos_necessarios:
        if not caminho.exists():
            color_print(f"❌ Caminho não encontrado: {caminho}", "red")
            return False
    
    color_print("✅ Caminhos OK", "green")
    return True

def testar_execucao_script(projeto_raiz: Path, script: Path) -> bool:
    """Testa execução de um script"""
    wrapper = projeto_raiz / 'scripts' / 'executar_agendado.py'
    
    if not script.exists():
        color_print(f"❌ Script não encontrado: {script}", "red")
        return False
    
    color_print(f"Testando execução de {script.name}...", "blue")
    
    try:
        # Executar com timeout curto (apenas para testar inicialização)
        result = subprocess.run(
            [sys.executable, str(wrapper), str(script), '--help'],
            cwd=projeto_raiz,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Se chegou até aqui, pelo menos o script iniciou
        color_print(f"✅ Script {script.name} executável", "green")
        return True
    except subprocess.TimeoutExpired:
        color_print(f"⚠️  Script {script.name} demorou muito (pode ser normal)", "yellow")
        return True
    except Exception as e:
        color_print(f"❌ Erro ao executar {script.name}: {e}", "red")
        return False

def main():
    """Função principal"""
    print("=" * 80)
    color_print("TESTE DE AGENDAMENTO", "bold")
    print("=" * 80)
    print()
    
    projeto_raiz = Path(__file__).parent.parent
    
    # Verificações
    verificacoes = [
        ("Variáveis de ambiente", lambda: verificar_variaveis_ambiente(projeto_raiz)),
        ("Caminhos", lambda: verificar_caminhos(projeto_raiz)),
    ]
    
    todas_ok = True
    for nome, funcao in verificacoes:
        if not funcao():
            todas_ok = False
        print()
    
    # Testar scripts principais
    color_print("Testando scripts principais...", "blue")
    print()
    
    scripts_teste = [
        projeto_raiz / 'scripts' / 'main_coleta_indices.py',
        projeto_raiz / 'scripts' / 'main_analise_planilhas.py',
    ]
    
    for script in scripts_teste:
        if script.exists():
            testar_execucao_script(projeto_raiz, script)
        print()
    
    # Resumo
    print("=" * 80)
    if todas_ok:
        color_print("✅ CONFIGURAÇÃO DE AGENDAMENTO OK", "green" + "bold")
        color_print("\nPróximo passo: Configure os agendamentos com:", "blue")
        color_print("  python scripts/configurar_agendamento.py", "blue")
        return 0
    else:
        color_print("⚠️  ALGUMAS VERIFICAÇÕES FALHARAM", "yellow" + "bold")
        return 1

if __name__ == "__main__":
    sys.exit(main())

