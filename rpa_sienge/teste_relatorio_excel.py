
import asyncio
import sys
import os
from pathlib import Path

# Adiciona o diretório pai ao path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

# Import funciona tanto quando executado da raiz quanto da pasta rpa_sienge
try:
    from rpa_sienge.rpa_sienge import RPASienge
except ImportError:
    from rpa_sienge import RPASienge

async def testar_processamento_relatorio():
    """
    Testa o processamento do relatório Excel com o arquivo exemplo
    """
    print("🧪 TESTE - PROCESSAMENTO RELATÓRIO SALDO DEVEDOR PRESENTE")
    print("=" * 60)
    
    try:
        # Caminho do arquivo exemplo
        arquivo_exemplo = "saldo_devedor_presente-20250610-093716.xlsx"
        
        if not os.path.exists(arquivo_exemplo):
            print(f"❌ Arquivo exemplo não encontrado: {arquivo_exemplo}")
            print("   Certifique-se de que o arquivo está na raiz do projeto")
            return False
        
        print(f"📁 Processando arquivo: {arquivo_exemplo}")
        
        # Cria instância do RPA
        rpa = RPASienge()
        
        # Dados de contrato exemplo para teste
        contrato_teste = {
            "cliente": "CLIENTE TESTE",
            "numero_titulo": "123456789",
            "cnpj_unidade": "12.345.678/0001-90",
            "indexador": "IPCA"
        }
        
        # Processa o relatório
        print("🔄 Iniciando processamento...")
        dados_financeiros = await rpa._processar_relatorio_excel(arquivo_exemplo, contrato_teste)
        
        # Mostra resultados
        print("\n✅ PROCESSAMENTO CONCLUÍDO")
        print("=" * 40)
        print(f"Cliente: {dados_financeiros.get('cliente', 'N/A')}")
        print(f"Título: {dados_financeiros.get('numero_titulo', 'N/A')}")
        print(f"Saldo Total: R$ {dados_financeiros.get('saldo_total', 0):,.2f}")
        print(f"Total de Parcelas: {dados_financeiros.get('total_parcelas', 0)}")
        print(f"Parcelas Pendentes: {dados_financeiros.get('parcelas_pendentes', 0)}")
        print(f"Parcelas Vencidas: {len(dados_financeiros.get('parcelas_vencidas', []))}")
        print(f"Parcelas CT Vencidas: {len(dados_financeiros.get('parcelas_ct_vencidas', []))}")
        print(f"Parcelas REC/FAT: {len(dados_financeiros.get('parcelas_rec_fat', []))}")
        print(f"Status Cliente: {dados_financeiros.get('status_cliente', 'N/A')}")
        print(f"Pode Reparcelar: {'✅ SIM' if dados_financeiros.get('pode_reparcelar', False) else '❌ NÃO'}")
        print(f"Motivo: {dados_financeiros.get('motivo_validacao', 'N/A')}")
        
        # Mostra algumas parcelas como exemplo
        parcelas_vencidas = dados_financeiros.get('parcelas_vencidas', [])
        if parcelas_vencidas:
            print(f"\n📋 EXEMPLOS DE PARCELAS VENCIDAS ({min(3, len(parcelas_vencidas))}):")
            for i, parcela in enumerate(parcelas_vencidas[:3], 1):
                print(f"{i}. Título: {parcela.get('numero_titulo', 'N/A')} | "
                      f"Parcela: {parcela.get('numero_parcela', 'N/A')} | "
                      f"Vencto: {parcela.get('data_vencimento', 'N/A')} | "
                      f"Valor: R$ {parcela.get('valor', 0):,.2f} | "
                      f"Tipo: {parcela.get('tipo_documento', 'N/A')}")
        
        print("\n✅ Teste realizado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    resultado = asyncio.run(testar_processamento_relatorio())
    if resultado:
        print("\n🎉 TESTE APROVADO!")
    else:
        print("\n💥 TESTE FALHOU!")
