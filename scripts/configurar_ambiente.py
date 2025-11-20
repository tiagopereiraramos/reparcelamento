#!/usr/bin/env python3
"""
Script de Configuração Interativa de Ambiente
Guia o usuário na criação do arquivo .env

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
from pathlib import Path
from typing import Dict, Optional

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

def ler_input(prompt: str, default: Optional[str] = None, obrigatorio: bool = False) -> str:
    """Lê input do usuário com valor padrão"""
    if default:
        prompt_completo = f"{prompt} [{default}]: "
    else:
        prompt_completo = f"{prompt}: "
    
    while True:
        valor = input(prompt_completo).strip()
        
        if not valor:
            if default:
                return default
            elif obrigatorio:
                color_print("⚠️  Este campo é obrigatório", "yellow")
                continue
            else:
                return ""
        
        return valor

def validar_email(email: str) -> bool:
    """Valida formato básico de e-mail"""
    return '@' in email and '.' in email.split('@')[1]

def validar_arquivo_existe(caminho: str) -> bool:
    """Valida se arquivo existe"""
    return os.path.exists(caminho)

def configurar_google_sheets() -> Dict[str, str]:
    """Configura variáveis do Google Sheets"""
    color_print("\n=== CONFIGURAÇÃO GOOGLE SHEETS ===", "blue")
    
    config = {}
    
    config['PLANILHA_CALCULO_ID'] = ler_input(
        "ID da planilha Base de Cálculo",
        obrigatorio=True
    )
    
    config['PLANILHA_APOIO_ID'] = ler_input(
        "ID da planilha Base de Apoio",
        obrigatorio=True
    )
    
    config['PLANILHA_TESTE_HOM'] = ler_input(
        "ID da planilha de teste/homologação (opcional)"
    )
    
    # Credenciais Google
    projeto_raiz = Path(__file__).parent.parent
    credenciais_padrao = projeto_raiz / 'credentials' / 'gspread-459713-aab8a657f9b0.json'
    
    caminho_credenciais = ler_input(
        "Caminho do arquivo JSON de credenciais Google",
        default=str(credenciais_padrao)
    )
    
    if caminho_credenciais and not validar_arquivo_existe(caminho_credenciais):
        color_print(f"⚠️  Arquivo não encontrado: {caminho_credenciais}", "yellow")
        copiar = input("Deseja copiar o arquivo para credentials/? (s/n): ").strip().lower()
        if copiar == 's':
            # Criar diretório se não existir
            credenciais_dir = projeto_raiz / 'credentials'
            credenciais_dir.mkdir(exist_ok=True)
            
            origem = input(f"Digite o caminho completo do arquivo de credenciais: ").strip()
            if validar_arquivo_existe(origem):
                import shutil
                destino = credenciais_dir / 'gspread-459713-aab8a657f9b0.json'
                shutil.copy2(origem, destino)
                caminho_credenciais = f"./credentials/gspread-459713-aab8a657f9b0.json"
                color_print(f"✅ Arquivo copiado para {destino}", "green")
            else:
                color_print("❌ Arquivo de origem não encontrado", "red")
    
    config['GOOGLE_CREDENTIALS_PATH'] = caminho_credenciais
    
    return config

def configurar_sienge() -> Dict[str, str]:
    """Configura variáveis do Sienge"""
    color_print("\n=== CONFIGURAÇÃO SIENGE ===", "blue")
    
    config = {}
    
    config['SIENGE_URL'] = ler_input(
        "URL do Sienge",
        default="https://jmservicos.sienge.com.br/sienge/8/index.html"
    )
    
    config['SIENGE_USUARIO'] = ler_input(
        "Usuário do Sienge",
        obrigatorio=True
    )
    
    config['SIENGE_SENHA'] = ler_input(
        "Senha do Sienge",
        obrigatorio=True
    )
    
    config['SIENGE_EMPRESA'] = ler_input(
        "Código da empresa no Sienge",
        default="1"
    )
    
    return config

def configurar_sicredi() -> Dict[str, str]:
    """Configura variáveis do Sicredi"""
    color_print("\n=== CONFIGURAÇÃO SICREDI ===", "blue")
    
    config = {}
    
    config['SICREDI_URL'] = ler_input(
        "URL do Sicredi",
        default="https://www.sicredi.com.br/home/"
    )
    
    # Empresa 1 (obrigatória)
    color_print("\n--- Empresa 1 (obrigatória) ---", "blue")
    config['SICREDI_CNPJ_1'] = ler_input(
        "CNPJ da Empresa 1",
        obrigatorio=True
    )
    config['SICREDI_USUARIO_1'] = ler_input(
        "Usuário da Empresa 1",
        obrigatorio=True
    )
    config['SICREDI_SENHA_1'] = ler_input(
        "Senha da Empresa 1",
        obrigatorio=True
    )
    
    # Empresas adicionais
    adicionar_mais = input("\nDeseja adicionar mais empresas? (s/n): ").strip().lower()
    num_empresa = 2
    
    while adicionar_mais == 's':
        color_print(f"\n--- Empresa {num_empresa} ---", "blue")
        cnpj = ler_input(f"CNPJ da Empresa {num_empresa}")
        if cnpj:
            config[f'SICREDI_CNPJ_{num_empresa}'] = cnpj
            config[f'SICREDI_USUARIO_{num_empresa}'] = ler_input(f"Usuário da Empresa {num_empresa}")
            config[f'SICREDI_SENHA_{num_empresa}'] = ler_input(f"Senha da Empresa {num_empresa}")
            num_empresa += 1
        else:
            break
        adicionar_mais = input("Deseja adicionar mais empresas? (s/n): ").strip().lower()
    
    return config

def configurar_sendgrid() -> Dict[str, str]:
    """Configura variáveis do SendGrid"""
    color_print("\n=== CONFIGURAÇÃO SENDGRID ===", "blue")
    
    config = {}
    
    config['SENDGRID_API_KEY'] = ler_input(
        "API Key do SendGrid",
        obrigatorio=True
    )
    
    email_from = ler_input(
        "E-mail remetente (deve estar verificado no SendGrid)",
        obrigatorio=True
    )
    
    while not validar_email(email_from):
        color_print("⚠️  E-mail inválido", "yellow")
        email_from = ler_input(
            "E-mail remetente",
            obrigatorio=True
        )
    
    config['SENDGRID_FROM_EMAIL'] = email_from
    
    email_to = ler_input(
        "E-mail destinatário para notificações",
        obrigatorio=True
    )
    
    while not validar_email(email_to):
        color_print("⚠️  E-mail inválido", "yellow")
        email_to = ler_input(
            "E-mail destinatário",
            obrigatorio=True
        )
    
    config['SENDGRID_TO_EMAIL'] = email_to
    
    return config

def configurar_navegador() -> Dict[str, str]:
    """Configura variáveis do navegador"""
    color_print("\n=== CONFIGURAÇÃO DE NAVEGADOR ===", "blue")
    
    config = {}
    
    headless = ler_input(
        "Modo headless? (1 = sim, 0 = não)",
        default="1"
    )
    config['HEADLESS'] = headless
    
    config['RPA_DOWNLOADS_FOLDER'] = ler_input(
        "Pasta de downloads do RPA",
        default="RPA_DOWNLOADS"
    )
    
    return config

def criar_arquivo_env(config: Dict[str, str], projeto_raiz: Path):
    """Cria arquivo .env"""
    env_path = projeto_raiz / '.env'
    
    # Ler template se existir
    template_path = projeto_raiz / 'env.example'
    template_content = ""
    
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    
    # Criar conteúdo do .env
    linhas = []
    linhas.append("# Arquivo .env gerado automaticamente")
    linhas.append("# NUNCA commite este arquivo no repositório!")
    linhas.append("")
    
    # Agrupar por seção
    secoes = {
        'GOOGLE SHEETS': ['PLANILHA_CALCULO_ID', 'PLANILHA_APOIO_ID', 'PLANILHA_TESTE_HOM', 'GOOGLE_CREDENTIALS_PATH'],
        'SIENGE': ['SIENGE_URL', 'SIENGE_USUARIO', 'SIENGE_SENHA', 'SIENGE_EMPRESA'],
        'SICREDI': [k for k in config.keys() if k.startswith('SICREDI_')],
        'SENDGRID': ['SENDGRID_API_KEY', 'SENDGRID_FROM_EMAIL', 'SENDGRID_TO_EMAIL'],
        'NAVEGADOR': ['HEADLESS', 'RPA_DOWNLOADS_FOLDER'],
    }
    
    nomes_secoes = {
        'GOOGLE SHEETS': '# ============================================\n# GOOGLE SHEETS\n# ============================================',
        'SIENGE': '# ============================================\n# SIENGE\n# ============================================',
        'SICREDI': '# ============================================\n# SICREDI\n# ============================================',
        'SENDGRID': '# ============================================\n# SENDGRID\n# ============================================',
        'NAVEGADOR': '# ============================================\n# CONFIGURAÇÕES DE NAVEGADOR\n# ============================================',
    }
    
    for secao, variaveis in secoes.items():
        if any(var in config for var in variaveis):
            linhas.append(nomes_secoes[secao])
            linhas.append("")
            
            for var in variaveis:
                if var in config:
                    valor = config[var]
                    linhas.append(f"{var}={valor}")
            
            linhas.append("")
    
    # Escrever arquivo
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(linhas))
    
    color_print(f"✅ Arquivo .env criado em: {env_path}", "green")

def main():
    """Função principal"""
    print("=" * 80)
    color_print("CONFIGURAÇÃO INTERATIVA DE AMBIENTE", "bold")
    print("=" * 80)
    print()
    color_print("Este script irá guiá-lo na criação do arquivo .env", "blue")
    color_print("Pressione Enter para usar valores padrão (quando disponível)", "blue")
    print()
    
    projeto_raiz = Path(__file__).parent.parent
    
    # Verificar se .env já existe
    env_path = projeto_raiz / '.env'
    if env_path.exists():
        sobrescrever = input(f"Arquivo .env já existe em {env_path}. Deseja sobrescrever? (s/n): ").strip().lower()
        if sobrescrever != 's':
            color_print("Operação cancelada", "yellow")
            return 0
    
    # Coletar configurações
    config = {}
    
    try:
        config.update(configurar_google_sheets())
        config.update(configurar_sienge())
        config.update(configurar_sicredi())
        config.update(configurar_sendgrid())
        config.update(configurar_navegador())
        
        # Criar arquivo .env
        criar_arquivo_env(config, projeto_raiz)
        
        print()
        print("=" * 80)
        color_print("✅ CONFIGURAÇÃO CONCLUÍDA", "green" + "bold")
        print("=" * 80)
        print()
        color_print("Próximo passo:", "blue")
        color_print("Execute: python scripts/validar_credenciais.py", "blue")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print()
        color_print("\n⚠️  Operação cancelada pelo usuário", "yellow")
        return 1
    except Exception as e:
        color_print(f"\n❌ Erro: {e}", "red")
        return 1

if __name__ == "__main__":
    sys.exit(main())

