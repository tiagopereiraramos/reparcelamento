
#!/usr/bin/env python3
"""
Teste de Conexão MongoDB
Verifica se o MongoDB está configurado e funcionando corretamente

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def testar_mongodb():
    """
    Testa conexão e operações básicas do MongoDB
    """
    print("🧪 TESTE DE CONEXÃO MONGODB")
    print("=" * 40)

    try:
        # Importa e testa conexão
        from core.mongodb_manager import mongodb_manager
        
        print("📡 Tentando conectar ao MongoDB...")
        conectado = await mongodb_manager.conectar()
        
        if not conectado:
            print("❌ Falha na conexão - verificar DATABASE_URL")
            return False

        print("✅ MongoDB conectado com sucesso!")
        
        # Testa saúde
        saude = await mongodb_manager.verificar_saude()
        print(f"🏥 Status: {saude['status']}")
        print(f"📊 Database: {saude.get('database', 'N/A')}")
        print(f"📈 Total execuções: {saude.get('total_execucoes', 0)}")

        # Testa operação de escrita
        print("\n🔧 Testando operação de escrita...")
        dados_teste = {
            "nome_rpa": "TesteConexao",
            "sucesso": True,
            "mensagem": "Teste de conexão MongoDB",
            "tempo_execucao": 1.0
        }
        
        mongo_id = await mongodb_manager.salvar_execucao_rpa(
            "TesteConexao", 
            {"teste": True}, 
            dados_teste
        )
        
        if mongo_id:
            print(f"✅ Documento salvo com ID: {mongo_id}")
        else:
            print("❌ Falha ao salvar documento")
            return False

        # Testa leitura
        print("\n📖 Testando operação de leitura...")
        execucoes = await mongodb_manager.obter_execucoes_recentes(5)
        print(f"✅ Obtidas {len(execucoes)} execuções recentes")

        # Testa estatísticas
        print("\n📊 Testando estatísticas...")
        stats = await mongodb_manager.obter_estatisticas_dashboard()
        if stats:
            print(f"✅ Estatísticas obtidas: {len(stats)} campos")
            print(f"   Total execuções: {stats.get('total_execucoes', 0)}")
            print(f"   Execuções hoje: {stats.get('execucoes_hoje', 0)}")
        else:
            print("❌ Falha ao obter estatísticas")

        await mongodb_manager.desconectar()
        print("\n✅ Teste MongoDB concluído com sucesso!")
        return True

    except ImportError as e:
        print(f"❌ Erro de importação: {str(e)}")
        print("   Instale dependências: pip install motor pymongo")
        return False
        
    except Exception as e:
        print(f"❌ Erro durante teste: {str(e)}")
        return False

async def testar_data_manager():
    """
    Testa o data_manager com MongoDB ativo
    """
    print("\n🧪 TESTE DATA MANAGER HÍBRIDO")
    print("=" * 40)

    try:
        from core.data_manager import data_manager
        
        # Inicializa sistema híbrido
        await data_manager.inicializar()
        
        # Testa salvamento de execução
        print("💾 Testando salvamento híbrido...")
        resultados = await data_manager.salvar_execucao_rpa(
            "TesteHibrido",
            {"planilha_id": "teste123"},
            {
                "sucesso": True,
                "mensagem": "Teste sistema híbrido",
                "dados": {"ipca": "5.32", "igpm": "7.02"},
                "tempo_execucao": 2.5
            }
        )
        
        print(f"📊 MongoDB: {resultados.get('mongodb', 'N/A')}")
        print(f"📄 JSON: {resultados.get('json', 'N/A')}")
        
        if resultados.get('mongodb') == 'sucesso' and resultados.get('json') == 'sucesso':
            print("✅ Sistema híbrido funcionando perfeitamente!")
            return True
        elif resultados.get('json') == 'sucesso':
            print("⚠️ Sistema funcionando apenas com JSON (MongoDB indisponível)")
            return True
        else:
            print("❌ Falha no sistema híbrido")
            return False

    except Exception as e:
        print(f"❌ Erro no data_manager: {str(e)}")
        return False

async def main():
    """
    Executa todos os testes de MongoDB
    """
    print("🚀 INICIANDO TESTES MONGODB SISTEMA RPA")
    print("=" * 50)
    
    # Mostra configuração
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Mascarar senha na URL para log
        url_safe = database_url.split('@')[0].split('://')[-1].split(':')[0] + "@" + database_url.split('@')[-1]
        print(f"🔗 DATABASE_URL configurada: {url_safe}")
    else:
        print("⚠️ DATABASE_URL não encontrada - usando MongoDB local")
    
    # Executa testes
    teste1 = await testar_mongodb()
    teste2 = await testar_data_manager()
    
    print("\n" + "=" * 50)
    if teste1 and teste2:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Sistema MongoDB totalmente funcional")
    elif teste2:
        print("⚠️ Sistema funcionando com JSON apenas")
        print("💡 Configure DATABASE_URL para ativar MongoDB")
    else:
        print("❌ Falhas detectadas nos testes")
        print("🔧 Verifique configuração e dependências")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Teste cancelado pelo usuário")
    except Exception as e:
        print(f"\n💥 Erro fatal: {str(e)}")
