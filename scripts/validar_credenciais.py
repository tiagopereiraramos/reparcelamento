#!/usr/bin/env python3
"""
Script de Validação de Credenciais
Testa conexões e valida credenciais configuradas

Suporta: Linux, Windows, macOS
"""

import sys
import os
import platform
from pathlib import Path
from typing import Dict, Tuple

# Adicionar raiz do projeto ao path
projeto_raiz = Path(__file__).parent.parent
sys.path.insert(0, str(projeto_raiz))

from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv(projeto_raiz / '.env')

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

def validar_arquivo_credenciais_google() -> Tuple[bool, str]:
    """Valida arquivo de credenciais do Google"""
    caminho = os.getenv('GOOGLE_CREDENTIALS_PATH', '')
    
    if not caminho:
        return False, "GOOGLE_CREDENTIALS_PATH não definido"
    
    # Converter caminho relativo para absoluto
    if not os.path.isabs(caminho):
        caminho = projeto_raiz / caminho
    
    if not os.path.exists(caminho):
        return False, f"Arquivo não encontrado: {caminho}"
    
    # Verificar se é JSON válido
    try:
        import json
        with open(caminho, 'r') as f:
            json.load(f)
        return True, f"Arquivo válido: {caminho}"
    except json.JSONDecodeError:
        return False, f"Arquivo JSON inválido: {caminho}"
    except Exception as e:
        return False, f"Erro ao ler arquivo: {e}"

def testar_google_sheets() -> Tuple[bool, str]:
    """Testa conexão com Google Sheets"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        planilha_id = os.getenv('PLANILHA_CALCULO_ID')
        if not planilha_id:
            return False, "PLANILHA_CALCULO_ID não definido"
        
        credenciais_path = os.getenv('GOOGLE_CREDENTIALS_PATH', '')
        if not credenciais_path:
            return False, "GOOGLE_CREDENTIALS_PATH não definido"
        
        if not os.path.isabs(credenciais_path):
            credenciais_path = projeto_raiz / credenciais_path
        
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_file(
            str(credenciais_path), scopes=scope)
        client = gspread.authorize(creds)
        
        # Tentar abrir planilha
        planilha = client.open_by_key(planilha_id)
        
        return True, f"Conexão OK - Planilha: {planilha.title}"
    except Exception as e:
        return False, f"Erro na conexão: {str(e)}"

def validar_credenciais_sienge() -> Tuple[bool, str]:
    """Valida credenciais do Sienge (sem testar conexão real)"""
    usuario = os.getenv('SIENGE_USUARIO')
    senha = os.getenv('SIENGE_SENHA')
    url = os.getenv('SIENGE_URL')
    
    if not usuario:
        return False, "SIENGE_USUARIO não definido"
    
    if not senha:
        return False, "SIENGE_SENHA não definido"
    
    if not url:
        return False, "SIENGE_URL não definido"
    
    # Validar formato básico
    if '@' not in usuario:
        return False, "SIENGE_USUARIO parece inválido (sem @)"
    
    return True, f"Credenciais configuradas: {usuario}"

def validar_credenciais_sicredi() -> Tuple[bool, str]:
    """Valida credenciais do Sicredi"""
    empresas = []
    
    # Procurar empresas configuradas
    i = 1
    while True:
        cnpj = os.getenv(f'SICREDI_CNPJ_{i}')
        usuario = os.getenv(f'SICREDI_USUARIO_{i}')
        senha = os.getenv(f'SICREDI_SENHA_{i}')
        
        if not cnpj or not usuario or not senha:
            break
        
        empresas.append({
            'numero': i,
            'cnpj': cnpj,
            'usuario': usuario
        })
        i += 1
    
    if not empresas:
        return False, "Nenhuma empresa Sicredi configurada"
    
    return True, f"{len(empresas)} empresa(s) configurada(s)"

def validar_sendgrid() -> Tuple[bool, str]:
    """Valida configuração do SendGrid"""
    api_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('SENDGRID_FROM_EMAIL')
    to_email = os.getenv('SENDGRID_TO_EMAIL')
    
    if not api_key:
        return False, "SENDGRID_API_KEY não definido"
    
    if not from_email:
        return False, "SENDGRID_FROM_EMAIL não definido"
    
    if not to_email:
        return False, "SENDGRID_TO_EMAIL não definido"
    
    # Validar formato de e-mail
    if '@' not in from_email or '@' not in to_email:
        return False, "E-mails inválidos"
    
    return True, f"SendGrid configurado: {from_email} -> {to_email}"

def main():
    """Função principal"""
    print("=" * 80)
    color_print("VALIDAÇÃO DE CREDENCIAIS", "bold")
    print("=" * 80)
    print()
    
    # Verificar se .env existe
    env_path = projeto_raiz / '.env'
    if not env_path.exists():
        color_print("❌ Arquivo .env não encontrado", "red")
        color_print("Execute: python scripts/configurar_ambiente.py", "yellow")
        return 1
    
    color_print(f"✅ Arquivo .env encontrado: {env_path}", "green")
    print()
    
    # Lista de validações
    validacoes = [
        ("Arquivo de Credenciais Google", validar_arquivo_credenciais_google),
        ("Conexão Google Sheets", testar_google_sheets),
        ("Credenciais Sienge", validar_credenciais_sienge),
        ("Credenciais Sicredi", validar_credenciais_sicredi),
        ("Configuração SendGrid", validar_sendgrid),
    ]
    
    resultados = []
    
    for nome, funcao in validacoes:
        color_print(f"Verificando {nome}...", "blue")
        try:
            sucesso, mensagem = funcao()
            resultados.append((nome, sucesso, mensagem))
            
            if sucesso:
                color_print(f"✅ {nome}: {mensagem}", "green")
            else:
                color_print(f"❌ {nome}: {mensagem}", "red")
        except Exception as e:
            resultados.append((nome, False, str(e)))
            color_print(f"❌ {nome}: Erro - {e}", "red")
        
        print()
    
    # Resumo
    print("=" * 80)
    total = len(resultados)
    aprovados = sum(1 for _, sucesso, _ in resultados if sucesso)
    
    if aprovados == total:
        color_print(f"✅ TODAS AS VALIDAÇÕES PASSARAM ({aprovados}/{total})", "green" + "bold")
        return 0
    else:
        color_print(f"⚠️  ALGUMAS VALIDAÇÕES FALHARAM ({aprovados}/{total})", "yellow" + "bold")
        color_print("\nCorrija os problemas acima antes de continuar", "yellow")
        return 1

if __name__ == "__main__":
    sys.exit(main())

