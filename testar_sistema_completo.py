
import asyncio
import os
from datetime import datetime
from core.data_manager import data_manager
from core.mongodb_manager import mongodb_manager

async def testar_sistema_completo():
    """
    Teste completo do sistema de dados
    """
    print("🧪 TESTE COMPLETO DO SISTEMA DE DADOS")
    print("=" * 60)
    
    # 1. Inicializar data_manager
    print("\n1️⃣ INICIALIZANDO DATA_MANAGER")
    print("-" * 30)
    
    await data_manager.inicializar()
    
    # 2. Verificar estado do MongoDB
    print("\n2️⃣ VERIFICANDO ESTADO MONGODB")
    print("-" * 30)
    
    print(f"📊 Estado data_manager:")
    print(f"   mongodb_ativo: {data_manager.mongodb_ativo}")
    print(f"   MONGODB_DISPONIVEL: {data_manager.MONGODB_DISPONIVEL if hasattr(data_manager, 'MONGODB_DISPONIVEL') else 'N/A'}")
    
    if hasattr(data_manager, 'mongodb_manager') or mongodb_manager:
        print(f"📊 Estado mongodb_manager:")
        print(f"   conectado: {mongodb_manager.conectado}")
        print(f"   database: {'SET' if mongodb_manager.database else 'NOT SET'}")
        print(f"   client: {'SET' if mongodb_manager.client else 'NOT SET'}")
    
    # 3. Testar salvamento de execução
    print("\n3️⃣ TESTANDO SALVAMENTO DE EXECUÇÃO")
    print("-" * 30)
    
    parametros_teste = {
        "teste": True,
        "timestamp": datetime.now().isoformat(),
        "origem": "teste_sistema_completo"
    }
    
    resultado_teste = {
        "sucesso": True,
        "mensagem": "Teste de salvamento executado com sucesso",
        "dados": {"valor_teste": 123.45, "contagem": 5},
        "tempo_execucao": 2.5
    }
    
    print("💾 Executando salvamento de teste...")
    resultados_salvamento = await data_manager.salvar_execucao_rpa(
        nome_rpa="Teste_Sistema",
        parametros=parametros_teste,
        resultado=resultado_teste
    )
    
    print(f"📊 Resultados do salvamento:")
    for sistema, status in resultados_salvamento.items():
        emoji = "✅" if status == "sucesso" else "❌"
        print(f"   {sistema}: {emoji} {status}")
    
    # 4. Verificar se dados foram salvos
    print("\n4️⃣ VERIFICANDO DADOS SALVOS")
    print("-" * 30)
    
    # Verificar execuções recentes
    execucoes_recentes = await data_manager.obter_execucoes_recentes(limite=5)
    print(f"📊 Execuções recentes encontradas: {len(execucoes_recentes)}")
    
    if execucoes_recentes:
        ultima_execucao = execucoes_recentes[-1]
        print(f"📋 Última execução:")
        print(f"   Nome RPA: {ultima_execucao.get('nome_rpa', 'N/A')}")
        print(f"   Sucesso: {ultima_execucao.get('sucesso', 'N/A')}")
        print(f"   Timestamp: {ultima_execucao.get('timestamp_inicio', 'N/A')}")
    
    # 5. Testar debug de dados salvos
    print("\n5️⃣ DEBUG COMPLETO DOS DADOS")
    print("-" * 30)
    
    debug_dados = await data_manager.debug_verificar_dados_salvos()
    print(f"📊 Debug completo:")
    print(f"   Total execuções: {debug_dados.get('total_execucoes', 0)}")
    print(f"   Arquivo execuções existe: {debug_dados.get('arquivo_execucoes_existe', False)}")
    print(f"   MongoDB ativo: {debug_dados.get('sistema_ativo', {}).get('mongodb_ativo', False)}")
    
    # 6. Conclusão
    print("\n6️⃣ CONCLUSÃO DO TESTE")
    print("-" * 30)
    
    sucesso_mongodb = resultados_salvamento.get("mongodb") == "sucesso"
    sucesso_json = resultados_salvamento.get("json") == "sucesso"
    
    if sucesso_mongodb and sucesso_json:
        print("🎉 SISTEMA TOTALMENTE FUNCIONAL!")
        print("   ✅ MongoDB: Funcionando")
        print("   ✅ JSON: Funcionando")
    elif sucesso_json:
        print("⚠️ SISTEMA PARCIALMENTE FUNCIONAL")
        print("   ❌ MongoDB: Com problemas")
        print("   ✅ JSON: Funcionando")
        print("\n💡 Verificar:")
        print("   - Variáveis de ambiente DATABASE_URL")
        print("   - Conexão de rede")
        print("   - Logs de erro acima")
    else:
        print("❌ SISTEMA COM PROBLEMAS GRAVES!")
        print("   ❌ MongoDB: Com problemas")
        print("   ❌ JSON: Com problemas")
        
    return sucesso_json or sucesso_mongodb

if __name__ == "__main__":
    resultado = asyncio.run(testar_sistema_completo())
    exit(0 if resultado else 1)
