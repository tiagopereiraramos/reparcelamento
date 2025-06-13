
#!/usr/bin/env python3
"""
Teste Específico - Processamento de Planilhas Sienge
Permite testar o processamento da planilha saldo_devedor_presente
"""

import sys
import os
from pathlib import Path
import asyncio
from datetime import datetime
import shutil

# Adiciona diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rpa_sienge import RPASienge


async def testar_com_planilha_exemplo():
    """
    Testa processamento com planilha de exemplo
    """
    print("🧪 TESTE PROCESSAMENTO PLANILHA SIENGE")
    print("=" * 50)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)

    try:
        # Caminho da planilha de exemplo
        planilha_exemplo = "attached_assets/saldo_devedor_presente-20250610-093716.xlsx"
        
        if not os.path.exists(planilha_exemplo):
            print(f"❌ Planilha de exemplo não encontrada: {planilha_exemplo}")
            return False
        
        print(f"📄 Planilha encontrada: {planilha_exemplo}")
        
        # Copiar planilha para pasta Downloads para simular download
        from platformdirs import user_downloads_dir
        pasta_downloads = user_downloads_dir()
        
        # Garantir que pasta Downloads existe
        os.makedirs(pasta_downloads, exist_ok=True)
        
        # Nome da cópia
        nome_copia = f"saldo_devedor_presente-{datetime.now().strftime('%Y%m%d-%H%M%S')}.xlsx"
        caminho_copia = os.path.join(pasta_downloads, nome_copia)
        
        # Copiar arquivo
        shutil.copy2(planilha_exemplo, caminho_copia)
        print(f"📁 Planilha copiada para Downloads: {nome_copia}")
        
        # Criar instância do RPA
        rpa = RPASienge()
        
        # Testar processamento
        print("\n🔄 Iniciando teste de processamento...")
        resultado = await rpa._processar_planilha_baixada(
            cliente="CLIENTE TESTE LTDA",
            numero_titulo="123456789"
        )
        
        # Mostrar resultados
        print("\n📊 RESULTADO DO PROCESSAMENTO:")
        print("=" * 40)
        
        if resultado.get("sucesso"):
            print("✅ Status: SUCESSO")
            print(f"💰 Saldo Total: R$ {resultado.get('saldo_total', 0):,.2f}")
            print(f"📋 Total Registros: {resultado.get('total_registros', 0)}")
            print(f"🎯 Status Cliente: {resultado.get('status_cliente', 'N/A').upper()}")
            
            resumo = resultado.get("resumo", {})
            print(f"📊 Parcelas CT: {resumo.get('total_ct', 0)}")
            print(f"📊 Parcelas REC/FAT: {resumo.get('total_rec_fat', 0)}")
            print(f"📊 Outras Parcelas: {resumo.get('total_outras', 0)}")
            print(f"⚠️ CT Vencidas: {resultado.get('qtd_ct_vencidas', 0)}")
            print(f"🔄 Pode Reparcelar: {'✅ SIM' if resumo.get('pode_reparcelar') else '❌ NÃO'}")
            
            # Mostrar algumas parcelas CT para debug
            parcelas_ct = resultado.get("parcelas_ct", [])[:3]  # Primeiras 3
            if parcelas_ct:
                print(f"\n📋 Primeiras Parcelas CT:")
                for i, parcela in enumerate(parcelas_ct, 1):
                    status = "VENCIDA" if parcela.get("vencida") else "NO PRAZO"
                    quitada = "QUITADA" if parcela.get("quitada") else "PENDENTE"
                    print(f"   {i}. {parcela.get('tipo_parcela', '')} - R$ {parcela.get('valor', 0):,.2f} - {status} - {quitada}")
            
            # Mostrar arquivo de auditoria
            arquivo_auditoria = resultado.get("arquivo_auditoria")
            if arquivo_auditoria:
                print(f"\n💾 Arquivo de Auditoria: {arquivo_auditoria}")
            
        else:
            print("❌ Status: ERRO")
            print(f"Erro: {resultado.get('erro', 'Erro desconhecido')}")
        
        # Limpar arquivo temporário
        try:
            os.remove(caminho_copia)
            print(f"\n🗑️ Arquivo temporário removido: {nome_copia}")
        except:
            pass
        
        return resultado.get("sucesso", False)
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def testar_localizacao_arquivo():
    """
    Testa apenas a localização de arquivos na pasta Downloads
    """
    print("🧪 TESTE LOCALIZAÇÃO DE ARQUIVO")
    print("=" * 40)
    
    try:
        from platformdirs import user_downloads_dir
        pasta_downloads = user_downloads_dir()
        
        print(f"📂 Pasta Downloads: {pasta_downloads}")
        
        # Listar arquivos .xlsx
        pasta_path = Path(pasta_downloads)
        if pasta_path.exists():
            arquivos_xlsx = list(pasta_path.glob("*.xlsx"))
            print(f"📊 Arquivos .xlsx encontrados: {len(arquivos_xlsx)}")
            
            for arquivo in arquivos_xlsx[:10]:  # Primeiros 10
                stat = arquivo.stat()
                tamanho = stat.st_size / 1024
                modificado = datetime.fromtimestamp(stat.st_mtime)
                print(f"   📄 {arquivo.name} ({tamanho:.1f} KB) - {modificado.strftime('%d/%m/%Y %H:%M:%S')}")
            
            # Testar localização específica
            rpa = RPASienge()
            arquivo_encontrado = rpa._localizar_arquivo_recente(pasta_downloads)
            print(f"\n✅ Arquivo mais recente: {Path(arquivo_encontrado).name}")
            
            return True
        else:
            print(f"❌ Pasta Downloads não existe: {pasta_downloads}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


def menu_testes():
    """
    Menu para escolher tipo de teste
    """
    print("\n🎯 MENU DE TESTES - PROCESSAMENTO PLANILHAS")
    print("=" * 50)
    print("1. 🧪 Teste Completo (com planilha exemplo)")
    print("2. 📁 Teste Localização de Arquivos")
    print("3. ❌ Sair")
    print("=" * 50)
    
    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (1-3): ").strip()
            
            if opcao == "1":
                return testar_com_planilha_exemplo()
            elif opcao == "2":
                return testar_localizacao_arquivo()
            elif opcao == "3":
                print("👋 Saindo...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 1-3.")
                
        except KeyboardInterrupt:
            print("\n👋 Teste interrompido")
            return None


async def main():
    """
    Função principal
    """
    print("🤖 SISTEMA DE TESTE - PROCESSAMENTO PLANILHAS SIENGE")
    print("Teste específico para validar processamento de planilhas baixadas")
    
    # Execução
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        if comando == "completo":
            sucesso = await testar_com_planilha_exemplo()
        elif comando == "localizacao":
            sucesso = await testar_localizacao_arquivo()
        else:
            print(f"❌ Comando inválido: {comando}")
            print("Comandos: completo, localizacao")
            return False
    else:
        # Menu interativo
        teste_escolhido = menu_testes()
        if teste_escolhido:
            sucesso = await teste_escolhido
        else:
            return True
    
    if sucesso:
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("\n❌ TESTE FALHOU!")
    
    return sucesso


if __name__ == "__main__":
    try:
        # Configurar event loop para Windows se necessário
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        resultado = asyncio.run(main())
        sys.exit(0 if resultado else 1)
        
    except KeyboardInterrupt:
        print("\n👋 Teste cancelado")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro fatal: {str(e)}")
        sys.exit(1)
