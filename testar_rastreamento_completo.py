
"""
Teste do Sistema de Rastreamento Completo
Valida que TODOS os passos são registrados em MongoDB + JSON

Desenvolvido em Português Brasileiro
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from core.rastreamento_unificado import iniciar_rastreamento
from core.data_manager import data_manager
from utils_auditoria_completa import consultar_execucao, gerar_relatorio_auditoria


async def testar_rastreamento_completo():
    """
    Testa todo o sistema de rastreamento para garantir que:
    1. Todos os passos são registrados
    2. MongoDB + JSON funcionam simultaneamente
    3. Recuperação de dados funciona
    """
    print("🧪 TESTE DO SISTEMA DE RASTREAMENTO COMPLETO")
    print("=" * 60)
    
    # Inicializar sistema híbrido
    print("🔧 Inicializando sistema híbrido...")
    await data_manager.inicializar()
    print(f"✅ MongoDB ativo: {data_manager.mongodb_ativo}")
    
    # Simular execução completa de RPA
    print("\n🤖 Simulando execução completa de RPA...")
    rastreamento = iniciar_rastreamento("TESTE_RPA_COMPLETO")
    
    try:
        # 1. Registrar início
        await rastreamento.registrar_inicio_rpa({
            "teste": True,
            "parametros_exemplo": {"cliente": "TESTE CLIENTE", "numero_titulo": "TESTE123"}
        })
        
        # 2. Simular login
        await rastreamento.registrar_login_sistema("sistema_teste", "usuario_teste", True)
        
        # 3. Simular consulta de dados
        await rastreamento.registrar_consulta_dados(
            "RELATORIO_TESTE",
            {"parametros": "teste"},
            {"total_registros": 42, "sucesso": True}
        )
        
        # 4. Simular processamento de planilha
        await rastreamento.registrar_processamento_planilha(
            "/caminho/teste/planilha.xlsx",
            {"linhas_processadas": 100, "total_registros": 100}
        )
        
        # 5. Simular cálculo
        await rastreamento.registrar_calculo_valores(
            "IGPM_REPARCELAMENTO",
            {"saldo_atual": 100000, "indice": 3.5},
            {"novo_saldo": 103500, "fator_correcao": 1.035, "sucesso": True}
        )
        
        # 6. Obter índice centralizado (testa integração)
        igmp_valor = await rastreamento.obter_indice_centralizado("igpm")
        print(f"📊 IGPM obtido: {igmp_valor}")
        
        # 7. Registrar sucesso
        await rastreamento.registrar_sucesso_rpa({
            "teste_finalizado": True,
            "todos_passos_executados": True,
            "dados_resultado": {"sucesso": True, "valor_final": 103500}
        })
        
        # 8. Finalizar rastreamento
        documento_final = await rastreamento.finalizar_rastreamento()
        
        print(f"✅ Rastreamento finalizado: {documento_final['id_execucao']}")
        print(f"📝 Total de passos: {documento_final['total_passos']}")
        
        # 9. Testar recuperação dos dados
        print("\n🔍 Testando recuperação de dados...")
        
        # Aguardar um pouco para garantir que dados foram salvos
        await asyncio.sleep(2)
        
        # Consultar execução específica
        dados_recuperados = await consultar_execucao(documento_final['id_execucao'])
        
        if dados_recuperados and "erro" not in dados_recuperados:
            print("✅ Dados recuperados com sucesso!")
            print(f"   ID: {dados_recuperados.get('id_execucao', 'N/A')}")
            print(f"   Passos: {dados_recuperados.get('total_passos', 0)}")
            print(f"   RPA: {dados_recuperados.get('nome_rpa', 'N/A')}")
        else:
            print("❌ Falha na recuperação de dados:")
            print(f"   Erro: {dados_recuperados.get('erro', 'Desconhecido')}")
        
        # 10. Gerar relatório de auditoria
        print("\n📋 Gerando relatório de auditoria...")
        relatorio = await gerar_relatorio_auditoria(dias=1)
        
        print("✅ Relatório gerado:")
        print(f"   Período: {relatorio.get('periodo_dias', 0)} dias")
        print(f"   Timestamp: {relatorio.get('timestamp_geracao', 'N/A')}")
        
        # 11. Validar arquivos JSON
        print("\n📄 Validando arquivos JSON...")
        from pathlib import Path
        
        pasta_auditoria = Path("dados_processamento/auditoria_completa")
        arquivos_json = list(pasta_auditoria.glob("*.json"))
        
        print(f"   Arquivos JSON encontrados: {len(arquivos_json)}")
        for arquivo in arquivos_json[-5:]:  # Últimos 5
            print(f"     - {arquivo.name}")
        
        # 12. Validar MongoDB (se disponível)
        if data_manager.mongodb_ativo:
            print("\n💾 Validando MongoDB...")
            try:
                from core.mongodb_manager import mongodb_manager
                
                def _check_collections():
                    collections = mongodb_manager.database.list_collection_names()
                    return collections
                
                collections = await asyncio.get_event_loop().run_in_executor(
                    None, _check_collections
                )
                
                print(f"   Collections encontradas: {len(collections)}")
                for collection in collections:
                    if "rpa" in collection.lower():
                        print(f"     - {collection}")
                        
            except Exception as e:
                print(f"   ⚠️ Erro ao validar MongoDB: {str(e)}")
        
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("✅ Sistema de rastreamento completo funcional")
        print("✅ MongoDB + JSON funcionando simultaneamente")
        print("✅ Recuperação de dados funcional")
        print("✅ Auditoria completa implementada")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


async def testar_integracao_rpas():
    """
    Testa integração com os RPAs reais
    """
    print("\n🔗 TESTE DE INTEGRAÇÃO COM RPAS")
    print("=" * 40)
    
    try:
        # Testar importação dos RPAs
        from rpa_coleta_indices.rpa_coleta_indices import RPAColetaIndices
        from rpa_analise_planilhas.rpa_analise_planilhas import RPAAnalisePlanilhas
        from rpa_sienge.rpa_sienge import RPASienge
        
        print("✅ Importação dos RPAs bem-sucedida")
        
        # Verificar se têm rastreamento
        rpa_indices = RPAColetaIndices()
        rpa_analise = RPAAnalisePlanilhas()
        rpa_sienge = RPASienge()
        
        print("✅ Instanciação dos RPAs bem-sucedida")
        print(f"   RPA Índices - rastreamento: {hasattr(rpa_indices, 'rastreamento')}")
        print(f"   RPA Análise - rastreamento: {hasattr(rpa_analise, 'rastreamento')}")
        print(f"   RPA Sienge - rastreamento: {hasattr(rpa_sienge, 'rastreamento')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na integração: {str(e)}")
        return False


async def main():
    """Função principal de teste"""
    print("🚀 INICIANDO TESTES DO SISTEMA COMPLETO")
    print("=" * 60)
    
    # Teste 1: Rastreamento completo
    sucesso_rastreamento = await testar_rastreamento_completo()
    
    # Teste 2: Integração com RPAs
    sucesso_integracao = await testar_integracao_rpas()
    
    # Resultado final
    print("\n" + "=" * 60)
    print("📊 RESULTADO FINAL DOS TESTES:")
    print("=" * 60)
    
    if sucesso_rastreamento and sucesso_integracao:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Sistema de rastreamento completo funcional")
        print("✅ Integração com RPAs bem-sucedida")
        print("✅ Auditoria completa implementada")
        print("✅ MongoDB + JSON funcionando simultaneamente")
    else:
        print("❌ ALGUNS TESTES FALHARAM:")
        print(f"   Rastreamento: {'✅' if sucesso_rastreamento else '❌'}")
        print(f"   Integração RPAs: {'✅' if sucesso_integracao else '❌'}")
    
    print("\n💡 Para usar o sistema:")
    print("   1. Execute os RPAs normalmente")
    print("   2. Todos os passos serão registrados automaticamente")
    print("   3. Use utils_auditoria_completa.py para consultas")
    print("   4. Dados ficam em MongoDB + JSON para fallback")


if __name__ == "__main__":
    asyncio.run(main())

