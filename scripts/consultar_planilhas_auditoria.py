
#!/usr/bin/env python3
"""
Script para consultar planilhas extraídas por cliente
Útil para auditoria e verificação de dados

Uso:
python scripts/consultar_planilhas_auditoria.py --cliente "NOME_CLIENTE"
python scripts/consultar_planilhas_auditoria.py --titulo "123456789"
python scripts/consultar_planilhas_auditoria.py --estatisticas
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Adiciona o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mongodb_manager import mongodb_manager

async def consultar_planilhas_cliente(cliente: str = None, numero_titulo: str = None, limite: int = 10):
    """Consulta planilhas de um cliente específico"""
    
    print("🔍 CONSULTANDO PLANILHAS EXTRAÍDAS")
    print("=" * 50)
    
    if cliente:
        print(f"👤 Cliente: {cliente}")
    if numero_titulo:
        print(f"📋 Título: {numero_titulo}")
    print(f"📊 Limite: {limite} registros")
    print()
    
    try:
        # Conecta ao MongoDB
        await mongodb_manager.conectar()
        
        # Busca planilhas
        planilhas = await mongodb_manager.obter_planilhas_cliente(
            numero_titulo=numero_titulo,
            cliente=cliente,
            limite=limite
        )
        
        if not planilhas:
            print("❌ Nenhuma planilha encontrada com os critérios especificados")
            return
        
        print(f"✅ Encontradas {len(planilhas)} planilhas:")
        print()
        
        for i, planilha in enumerate(planilhas, 1):
            print(f"📋 PLANILHA {i}")
            print(f"   🆔 ID: {planilha['_id']}")
            print(f"   📋 Título: {planilha['numero_titulo']}")
            print(f"   👤 Cliente: {planilha['cliente']}")
            print(f"   📅 Data extração: {planilha['data_extracao']}")
            print(f"   📁 Arquivo: {planilha['nome_arquivo']}")
            print(f"   ✅ Arquivo existe: {'SIM' if planilha['arquivo_existe'] else 'NÃO'}")
            print(f"   💰 Saldo total: R$ {planilha['dados_extracao']['saldo_total']:,.2f}")
            print(f"   📊 Total parcelas: {planilha['dados_extracao']['total_parcelas']}")
            print(f"   🎯 Status cliente: {planilha['dados_extracao']['status_cliente']}")
            print(f"   🏢 Sistema origem: {planilha['origem_sistema']}")
            print(f"   📍 Caminho completo: {planilha['caminho_arquivo']}")
            print()
        
    except Exception as e:
        print(f"❌ Erro na consulta: {str(e)}")
    
    finally:
        await mongodb_manager.desconectar()

async def mostrar_estatisticas():
    """Mostra estatísticas das planilhas extraídas"""
    
    print("📊 ESTATÍSTICAS PLANILHAS EXTRAÍDAS")
    print("=" * 50)
    
    try:
        # Conecta ao MongoDB
        await mongodb_manager.conectar()
        
        # Busca estatísticas
        stats = await mongodb_manager.obter_estatisticas_planilhas()
        
        if not stats:
            print("❌ Erro ao obter estatísticas")
            return
        
        print(f"📋 Total de planilhas: {stats['total_planilhas']}")
        print(f"📅 Planilhas hoje: {stats['planilhas_hoje']}")
        print(f"📆 Planilhas última semana: {stats['planilhas_semana']}")
        print(f"👥 Clientes únicos: {stats['clientes_unicos']}")
        print(f"🕐 Última atualização: {stats['ultima_atualizacao']}")
        print()
        
        # Busca últimas 5 planilhas
        print("📋 ÚLTIMAS 5 PLANILHAS EXTRAÍDAS:")
        print("-" * 30)
        
        ultimas = await mongodb_manager.obter_planilhas_cliente(limite=5)
        
        for planilha in ultimas:
            data_formatada = planilha['data_extracao'].strftime("%d/%m/%Y %H:%M")
            print(f"• {data_formatada} - {planilha['cliente']} - {planilha['numero_titulo']}")
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {str(e)}")
    
    finally:
        await mongodb_manager.desconectar()

def main():
    parser = argparse.ArgumentParser(description='Consultar planilhas extraídas por cliente')
    parser.add_argument('--cliente', '-c', help='Nome do cliente para buscar')
    parser.add_argument('--titulo', '-t', help='Número do título para buscar')
    parser.add_argument('--limite', '-l', type=int, default=10, help='Limite de resultados')
    parser.add_argument('--estatisticas', '-s', action='store_true', help='Mostrar estatísticas gerais')
    
    args = parser.parse_args()
    
    if args.estatisticas:
        asyncio.run(mostrar_estatisticas())
    elif args.cliente or args.titulo:
        asyncio.run(consultar_planilhas_cliente(
            cliente=args.cliente,
            numero_titulo=args.titulo,
            limite=args.limite
        ))
    else:
        print("❌ Especifique --cliente, --titulo ou --estatisticas")
        parser.print_help()

if __name__ == "__main__":
    main()
