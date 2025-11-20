#!/usr/bin/env python3
"""
Script de Configuração de Agendamento
Configura cron (Linux/macOS) ou Task Scheduler (Windows)

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from typing import List, Dict

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

def configurar_cron(projeto_raiz: Path) -> bool:
    """Configura cron jobs no Linux/macOS"""
    color_print("Configurando cron jobs...", "blue")
    
    # Scripts a agendar
    scripts_agendamento = [
        {
            'nome': 'Coleta de Índices',
            'script': 'scripts/main_coleta_indices.py',
            'cron': '0 9 11 * *',  # 11º dia do mês às 9h
            'descricao': 'Coleta índices IPCA e IGPM'
        },
        {
            'nome': 'Análise de Planilhas',
            'script': 'scripts/main_analise_planilhas.py',
            'cron': '0 10 11 * *',  # 11º dia do mês às 10h
            'descricao': 'Análise de planilhas e geração de fila'
        },
        {
            'nome': 'Extração Sienge',
            'script': 'scripts/main_extracao_relatorio_sienge.py',
            'cron': '0 9 16 * *',  # 16º dia do mês às 9h
            'descricao': 'Extração de relatórios do Sienge'
        },
        {
            'nome': 'Reparcelamento Sienge',
            'script': 'scripts/main_reparcelamento_sienge.py',
            'cron': '0 10 16 * *',  # 16º dia do mês às 10h
            'descricao': 'Execução de reparcelamentos'
        },
        {
            'nome': 'Sicredi',
            'script': 'scripts/main_sicredi.py',
            'cron': '0 11 16 * *',  # 16º dia do mês às 11h
            'descricao': 'Importação de arquivos no Sicredi'
        },
    ]
    
    # Gerar entradas de cron
    cron_entries = []
    python_wrapper = projeto_raiz / 'scripts' / 'executar_agendado.py'
    
    for item in scripts_agendamento:
        script_path = projeto_raiz / item['script']
        cron_line = f"{item['cron']} cd {projeto_raiz} && {sys.executable} {python_wrapper} {script_path} >> {projeto_raiz}/logs/cron.log 2>&1"
        cron_entries.append({
            'line': cron_line,
            'name': item['nome'],
            'description': item['descricao']
        })
    
    # Mostrar entradas
    color_print("\nEntradas de cron a serem adicionadas:", "blue")
    for entry in cron_entries:
        print(f"# {entry['name']}: {entry['description']}")
        print(entry['line'])
        print()
    
    # Confirmar
    confirmar = input("Deseja adicionar essas entradas ao crontab? (s/n): ").strip().lower()
    
    if confirmar != 's':
        color_print("Operação cancelada", "yellow")
        return False
    
    # Adicionar ao crontab
    try:
        # Ler crontab atual
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )
        crontab_atual = result.stdout if result.returncode == 0 else ""
        
        # Adicionar novas entradas
        crontab_novo = crontab_atual
        if crontab_novo and not crontab_novo.endswith('\n'):
            crontab_novo += '\n'
        
        crontab_novo += "\n# Entradas do RPA Reparcelamento\n"
        for entry in cron_entries:
            crontab_novo += f"# {entry['description']}\n"
            crontab_novo += f"{entry['line']}\n"
        
        # Instalar novo crontab
        process = subprocess.Popen(
            ['crontab', '-'],
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=crontab_novo)
        
        if process.returncode == 0:
            color_print("✅ Cron jobs configurados com sucesso", "green")
            return True
        else:
            color_print("❌ Erro ao configurar cron", "red")
            return False
            
    except Exception as e:
        color_print(f"❌ Erro: {e}", "red")
        return False

def configurar_taskscheduler(projeto_raiz: Path) -> bool:
    """Configura Task Scheduler no Windows"""
    color_print("Configurando Task Scheduler...", "blue")
    color_print("⚠️  Configuração manual necessária no Windows", "yellow")
    color_print("\nSiga estes passos:", "blue")
    print("1. Abra o Task Scheduler (taskschd.msc)")
    print("2. Crie uma nova tarefa para cada script")
    print("3. Configure o trigger (diário, mensal, etc.)")
    print("4. Configure a ação para executar:")
    print(f"   Programa: {sys.executable}")
    print(f"   Argumentos: {projeto_raiz / 'scripts' / 'executar_agendado.py'} <script>")
    print(f"   Diretório inicial: {projeto_raiz}")
    print("\nScripts a agendar:")
    
    scripts = [
        ('Coleta de Índices', 'scripts/main_coleta_indices.py', '11º dia do mês às 9h'),
        ('Análise de Planilhas', 'scripts/main_analise_planilhas.py', '11º dia do mês às 10h'),
        ('Extração Sienge', 'scripts/main_extracao_relatorio_sienge.py', '16º dia do mês às 9h'),
        ('Reparcelamento Sienge', 'scripts/main_reparcelamento_sienge.py', '16º dia do mês às 10h'),
        ('Sicredi', 'scripts/main_sicredi.py', '16º dia do mês às 11h'),
    ]
    
    for nome, script, quando in scripts:
        print(f"\n  - {nome} ({quando})")
        print(f"    {projeto_raiz / script}")
    
    return True

def main():
    """Função principal"""
    print("=" * 80)
    color_print("CONFIGURAÇÃO DE AGENDAMENTO", "bold")
    print("=" * 80)
    print()
    
    sistema = platform.system()
    projeto_raiz = Path(__file__).parent.parent
    
    if sistema == "Windows":
        return 0 if configurar_taskscheduler(projeto_raiz) else 1
    else:
        return 0 if configurar_cron(projeto_raiz) else 1

if __name__ == "__main__":
    sys.exit(main())

