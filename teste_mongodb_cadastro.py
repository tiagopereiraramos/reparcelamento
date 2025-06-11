
import asyncio
from datetime import datetime
from core.mongodb_manager import mongodb_manager
from core.base_rpa import ResultadoRPA
from rpa_analise_planilhas.rpa_analise_planilhas import RPAAnalisePlanilhas

async def testar_cadastro_mongodb():
    """
    Testa se os registros estão sendo cadastrados corretamente no MongoDB
    """
    print("🧪 TESTE DE CADASTRO NO MONGODB")
    print("=" * 50)
    
    try:
        # 1. Testar conexão MongoDB
        print("📡 Testando conexão MongoDB...")
        if not mongodb_manager.conectado:
            conectado = await mongodb_manager.conectar()
            if conectado:
                print("✅ MongoDB conectado com sucesso")
            else:
                print("❌ Falha na conexão MongoDB")
                return
        else:
            print("✅ MongoDB já conectado")
        
        # 2. Testar cadastro direto de execução
        print("\n💾 Testando cadastro direto de execução...")
        documento_teste = {
            "nome_rpa": "Teste_Cadastro",
            "timestamp_inicio": datetime.now(),
            "timestamp_fim": datetime.now(),
            "parametros_entrada": {"teste": True},
            "resultado": {"sucesso": True, "mensagem": "Teste"},
            "sucesso": True,
            "tempo_execucao_segundos": 1.0,
            "mensagem": "Teste de cadastro",
            "erro": None
        }
        
        collection = mongodb_manager.database.execucoes_rpa
        result = await collection.insert_one(documento_teste)
        print(f"✅ Execução teste cadastrada: {result.inserted_id}")
        
        # 3. Verificar se foi salvo
        print("\n🔍 Verificando se registro foi salvo...")
        documento_salvo = await collection.find_one({"_id": result.inserted_id})
        if documento_salvo:
            print("✅ Registro encontrado no MongoDB")
            print(f"   📋 Nome RPA: {documento_salvo['nome_rpa']}")
            print(f"   📋 Sucesso: {documento_salvo['sucesso']}")
        else:
            print("❌ Registro não encontrado no MongoDB")
        
        # 4. Testar com RPA real
        print("\n🤖 Testando com RPA Análise Planilhas...")
        rpa = RPAAnalisePlanilhas()
        
        # Inicializa sem executar (só para testar salvamento)
        if not await rpa.inicializar():
            print("❌ Falha na inicialização do RPA")
            return
        
        # Simula um resultado e testa salvamento
        resultado_simulado = ResultadoRPA(
            sucesso=True,
            mensagem="Teste de cadastro via RPA",
            dados={"contratos_identificados": 0},
            tempo_execucao=2.5
        )
        
        # Força salvamento
        rpa.inicio_execucao = datetime.now()
        await rpa._salvar_execucao({"teste_rpa": True}, resultado_simulado)
        
        # 5. Verificar total de registros
        print("\n📊 Contando total de registros...")
        total_registros = await collection.count_documents({})
        print(f"📈 Total de execuções no banco: {total_registros}")
        
        if total_registros > 0:
            print("✅ CADASTRO FUNCIONANDO CORRETAMENTE!")
        else:
            print("❌ NENHUM REGISTRO ENCONTRADO!")
        
        # 6. Listar últimos registros
        print("\n📋 Últimos 5 registros:")
        cursor = collection.find().sort("timestamp_inicio", -1).limit(5)
        registros = await cursor.to_list(length=5)
        
        for i, registro in enumerate(registros, 1):
            print(f"   {i}. {registro['nome_rpa']} - {registro['sucesso']} - {registro.get('timestamp_inicio', 'N/A')}")
        
        await rpa.finalizar()
        
    except Exception as e:
        print(f"❌ Erro durante teste: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(testar_cadastro_mongodb())
