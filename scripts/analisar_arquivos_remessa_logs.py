#!/usr/bin/env python3
"""
Script para analisar logs e mapear empresas com seus arquivos de remessa gerados
Baseado nos logs de 27/10/2025
"""

import re
from datetime import datetime
from typing import Dict, List, Any

def analisar_logs_arquivos_remessa():
    """
    Analisa os logs para extrair o mapeamento empresa -> arquivo_remessa
    """
    
    # Dados extraídos dos logs de 27/10/2025
    empresas_arquivos = {
        "18 - URUCUI SCP 2": "24053O27.2877",
        "10 - RAJ": "62520O27.600", 
        "3 - BVRB": "37853O27.1407",
        "9 - SPE PARQUE DA LAGOA": "79512O27.3583",
        "5 - URUÇUI": "52163O27.2407",
        "14 - URUCUI SCP 3": "15437O27.1800",
        "15 - URUCUI SCP": "68852O27.158",
        "8 - OLIVEIRA": "19308O27.2348"
    }
    
    # Empresas que foram processadas mas não geraram arquivos (erro)
    empresas_com_erro = [
        "11 - TVU",
        "16 - TAURIDEA", 
        "6 - CATACUY",
        "1 - CEC SCP"
    ]
    
    print("📊 ANÁLISE DOS ARQUIVOS DE REMESSA GERADOS EM 27/10/2025")
    print("=" * 80)
    print()
    
    print("✅ EMPRESAS QUE GERARAM ARQUIVOS DE REMESSA:")
    print("-" * 50)
    for empresa, arquivo in empresas_arquivos.items():
        print(f"🏢 {empresa}")
        print(f"   📁 Arquivo: {arquivo}")
        print()
    
    print("❌ EMPRESAS COM ERRO (NÃO GERARAM ARQUIVOS):")
    print("-" * 50)
    for empresa in empresas_com_erro:
        print(f"🏢 {empresa}")
        print(f"   ❌ Erro: Não gerou arquivo de remessa")
        print()
    
    print("📋 MAPEAMENTO COMPLETO:")
    print("-" * 50)
    print("EMPRESA → ARQUIVO_REMESSA")
    print()
    
    for empresa, arquivo in empresas_arquivos.items():
        print(f"{empresa} → {arquivo}")
    
    print()
    print("📊 ESTATÍSTICAS:")
    print(f"   ✅ Empresas com sucesso: {len(empresas_arquivos)}")
    print(f"   ❌ Empresas com erro: {len(empresas_com_erro)}")
    print(f"   📁 Total de arquivos gerados: {len(empresas_arquivos)}")
    
    return empresas_arquivos, empresas_com_erro

def verificar_arquivos_existem(empresas_arquivos: Dict[str, str]):
    """
    Verifica se os arquivos de remessa realmente existem no sistema
    """
    import os
    from pathlib import Path
    
    print("\n🔍 VERIFICAÇÃO DE EXISTÊNCIA DOS ARQUIVOS:")
    print("-" * 50)
    
    pasta_remessas = Path("outputs/remessas")
    arquivos_existentes = 0
    arquivos_inexistentes = 0
    total_tamanho = 0
    
    for empresa, arquivo in empresas_arquivos.items():
        caminho_arquivo = pasta_remessas / arquivo
        
        if caminho_arquivo.exists():
            tamanho = caminho_arquivo.stat().st_size
            tamanho_mb = tamanho / (1024 * 1024)
            print(f"✅ {empresa}: {arquivo} ({tamanho_mb:.2f} MB)")
            arquivos_existentes += 1
            total_tamanho += tamanho
        else:
            print(f"❌ {empresa}: {arquivo} (NÃO ENCONTRADO)")
            arquivos_inexistentes += 1
    
    print(f"\n📊 RESUMO DA VERIFICAÇÃO:")
    print(f"   ✅ Arquivos existentes: {arquivos_existentes}")
    print(f"   ❌ Arquivos inexistentes: {arquivos_inexistentes}")
    print(f"   💾 Tamanho total: {total_tamanho / (1024 * 1024):.2f} MB")

def main():
    """Função principal"""
    try:
        print(f"🚀 Análise iniciada em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Analisar logs
        empresas_arquivos, empresas_com_erro = analisar_logs_arquivos_remessa()
        
        # Verificar existência dos arquivos
        verificar_arquivos_existem(empresas_arquivos)
        
        print(f"\n✅ Análise concluída em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
