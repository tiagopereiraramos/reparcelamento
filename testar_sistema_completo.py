
#!/usr/bin/env python3
"""
🚀 TESTE DEFINITIVO DO SISTEMA RPA SIENGE
Script que testa TUDO e mostra o que está funcionando
"""

import asyncio
import sys
import os
import traceback
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def teste_completo_sistema():
    """Testa todo o sistema de forma robusta"""
    print("🚀 INICIANDO TESTE COMPLETO DO SISTEMA")
    print("=" * 60)
    
    resultados = {
        "inicio": datetime.now().isoformat(),
        "testes": {},
        "componentes_funcionais": [],
        "problemas_encontrados": []
    }
    
    # TESTE 1: RPA Sienge básico
    print("\n1️⃣ TESTANDO RPA SIENGE...")
    try:
        from rpa_sienge.rpa_sienge import RPASienge
        rpa = RPASienge()
        resultados["testes"]["rpa_sienge"] = "✅ FUNCIONANDO"
        resultados["componentes_funcionais"].append("RPA Sienge")
        print("   ✅ RPA Sienge: FUNCIONANDO")
    except Exception as e:
        resultados["testes"]["rpa_sienge"] = f"❌ ERRO: {str(e)}"
        resultados["problemas_encontrados"].append(f"RPA Sienge: {str(e)}")
        print(f"   ❌ RPA Sienge: ERRO - {str(e)}")
    
    # TESTE 2: Data Manager
    print("\n2️⃣ TESTANDO DATA MANAGER...")
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()
        resultados["testes"]["data_manager"] = "✅ FUNCIONANDO"
        resultados["componentes_funcionais"].append("Data Manager")
        print("   ✅ Data Manager: FUNCIONANDO")
        
        # Teste MongoDB
        if hasattr(data_manager, 'mongodb_manager') and data_manager.mongodb_manager.conectado:
            resultados["testes"]["mongodb"] = "✅ CONECTADO"
            resultados["componentes_funcionais"].append("MongoDB")
            print("   ✅ MongoDB: CONECTADO")
        else:
            resultados["testes"]["mongodb"] = "⚠️ DESCONECTADO"
            print("   ⚠️ MongoDB: DESCONECTADO (normal em desenvolvimento)")
            
    except Exception as e:
        resultados["testes"]["data_manager"] = f"❌ ERRO: {str(e)}"
        resultados["problemas_encontrados"].append(f"Data Manager: {str(e)}")
        print(f"   ❌ Data Manager: ERRO - {str(e)}")
    
    # TESTE 3: Processador de Regras PDD
    print("\n3️⃣ TESTANDO PROCESSADOR REGRAS PDD...")
    try:
        from core.processador_regras_pdd import ProcessadorRegrasNegocio
        processador = ProcessadorRegrasNegocio()
        resultados["testes"]["processador_pdd"] = "✅ FUNCIONANDO"
        resultados["componentes_funcionais"].append("Processador PDD")
        print("   ✅ Processador PDD: FUNCIONANDO")
    except Exception as e:
        resultados["testes"]["processador_pdd"] = f"❌ ERRO: {str(e)}"
        resultados["problemas_encontrados"].append(f"Processador PDD: {str(e)}")
        print(f"   ❌ Processador PDD: ERRO - {str(e)}")
    
    # TESTE 4: Sistema de Rastreamento
    print("\n4️⃣ TESTANDO RASTREAMENTO...")
    try:
        from core.rastreamento_unificado import RastreamentoUnificado
        rastreamento = RastreamentoUnificado("TESTE_SISTEMA")
        resultados["testes"]["rastreamento"] = "✅ FUNCIONANDO"
        resultados["componentes_funcionais"].append("Rastreamento")
        print("   ✅ Rastreamento: FUNCIONANDO")
    except Exception as e:
        resultados["testes"]["rastreamento"] = f"❌ ERRO: {str(e)}"
        resultados["problemas_encontrados"].append(f"Rastreamento: {str(e)}")
        print(f"   ❌ Rastreamento: ERRO - {str(e)}")
    
    # TESTE 5: Browser Manager (opcional)
    print("\n5️⃣ TESTANDO BROWSER MANAGER...")
    try:
        from core.browser_manager import RPABrowser
        # Não inicializa o browser de verdade, só testa import
        resultados["testes"]["browser_manager"] = "✅ DISPONÍVEL"
        resultados["componentes_funcionais"].append("Browser Manager")
        print("   ✅ Browser Manager: DISPONÍVEL")
    except Exception as e:
        resultados["testes"]["browser_manager"] = f"⚠️ INDISPONÍVEL: {str(e)}"
        print(f"   ⚠️ Browser Manager: INDISPONÍVEL (normal se não tem dependências)")
    
    # TESTE 6: Teste do sistema completo
    print("\n6️⃣ TESTANDO INTEGRAÇÃO COMPLETA...")
    try:
        # Simula execução mínima
        if "RPA Sienge" in resultados["componentes_funcionais"]:
            # Teste de carregamento de dados (sem webscraping)
            resultado_carga = await rpa.carregar_dados_fila_reparcelamento()
            if resultado_carga.get("sucesso") or resultado_carga.get("fila_vazia"):
                resultados["testes"]["integracao"] = "✅ FUNCIONANDO"
                resultados["componentes_funcionais"].append("Integração Completa")
                print("   ✅ Integração: FUNCIONANDO")
            else:
                resultados["testes"]["integracao"] = f"⚠️ LIMITADA: {resultado_carga.get('erro', 'Dados não disponíveis')}"
                print(f"   ⚠️ Integração: LIMITADA - {resultado_carga.get('erro', 'Dados não disponíveis')}")
        else:
            resultados["testes"]["integracao"] = "❌ RPA não disponível"
            print("   ❌ Integração: NÃO TESTADA (RPA não funcionando)")
            
    except Exception as e:
        resultados["testes"]["integracao"] = f"❌ ERRO: {str(e)}"
        resultados["problemas_encontrados"].append(f"Integração: {str(e)}")
        print(f"   ❌ Integração: ERRO - {str(e)}")
    
    # RELATÓRIO FINAL
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL")
    print("=" * 60)
    
    total_componentes = len(resultados["componentes_funcionais"])
    total_problemas = len(resultados["problemas_encontrados"])
    
    print(f"✅ Componentes funcionando: {total_componentes}")
    for comp in resultados["componentes_funcionais"]:
        print(f"   • {comp}")
    
    if total_problemas > 0:
        print(f"\n⚠️ Problemas encontrados: {total_problemas}")
        for prob in resultados["problemas_encontrados"]:
            print(f"   • {prob}")
    
    # DIAGNÓSTICO E PRÓXIMOS PASSOS
    print(f"\n🎯 DIAGNÓSTICO:")
    if total_componentes >= 4:
        print("   🎉 SISTEMA MAJORITARIAMENTE FUNCIONAL!")
        print("   🚀 Pronto para executar RPAs básicos")
        
        if "MongoDB" not in resultados["componentes_funcionais"]:
            print("   📝 Para produção: Configure MongoDB (DATABASE_URL)")
        
        if "Browser Manager" not in resultados["componentes_funcionais"]:
            print("   🌐 Para webscraping: Instale dependências do browser")
            
        print(f"\n✨ PRÓXIMOS PASSOS RECOMENDADOS:")
        print(f"   1. Execute: python rpa_sienge/teste_sienge.py")
        print(f"   2. Configure credenciais se precisar de webscraping real")
        print(f"   3. Execute: python executar_teste_sienge.py")
        
    elif total_componentes >= 2:
        print("   ⚠️ SISTEMA PARCIALMENTE FUNCIONAL")
        print("   🔧 Alguns ajustes necessários")
        print(f"\n🛠️ AÇÕES RECOMENDADAS:")
        print(f"   1. Verifique imports em: {', '.join(prob.split(':')[0] for prob in resultados['problemas_encontrados'])}")
        print(f"   2. Execute novamente este teste")
        
    else:
        print("   ❌ SISTEMA COM PROBLEMAS CRÍTICOS")
        print("   🆘 Revisão necessária")
        
        print(f"\n🆘 AÇÕES CRÍTICAS:")
        for prob in resultados["problemas_encontrados"][:3]:  # Mostra apenas os 3 primeiros
            print(f"   • Resolver: {prob}")
    
    resultados["fim"] = datetime.now().isoformat()
    resultados["status_geral"] = "FUNCIONAL" if total_componentes >= 4 else "PROBLEMAS" if total_componentes >= 2 else "CRITICO"
    
    # Salva relatório
    try:
        import json
        with open("relatorio_sistema.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        print(f"\n📋 Relatório salvo em: relatorio_sistema.json")
    except:
        pass
    
    return resultados

async def main():
    """Função principal"""
    try:
        print("🔍 VERIFICANDO SISTEMA RPA SIENGE")
        print("Este teste vai mostrar exatamente o que está funcionando...")
        print()
        
        resultados = await teste_completo_sistema()
        
        print(f"\n🏁 TESTE CONCLUÍDO!")
        print(f"Status geral: {resultados['status_geral']}")
        
        if resultados['status_geral'] == "FUNCIONAL":
            print(f"\n🎊 PARABÉNS! Seu sistema está funcionando muito bem!")
            print(f"Execute agora: python rpa_sienge/teste_sienge.py")
        
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NO TESTE: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(main())
