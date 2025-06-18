
"""
Exemplo de uso do sistema centralizado de IGPM
Demonstra como buscar IGPM de forma unificada em todo o sistema
"""

import asyncio
from core.data_manager import obter_igpm_mais_recente, data_manager
from rpa_sienge.processador_regras_pdd import ProcessadorRegrasNegocio


async def exemplo_uso_igpm():
    """
    Demonstra como usar o IGPM centralizado em qualquer parte do sistema
    """
    print("🔧 Inicializando sistema...")
    
    # Inicializar data_manager
    await data_manager.inicializar()
    
    print("\n📊 Buscando IGPM mais recente...")
    
    # MÉTODO 1: Buscar IGPM diretamente
    igpm_atual = await obter_igpm_mais_recente()
    
    if igmp_atual:
        print(f"✅ IGPM encontrado: {igpm_atual}%")
        
        # MÉTODO 2: Usar no processador de regras
        processador = ProcessadorRegrasNegocio()
        
        resultado_calculo = await processador.calcular_valores_reparcelamento(
            saldo_atual=100000.00,  # R$ 100.000,00
            indice_igpm=None,       # Será buscado automaticamente
            parcelas_pendentes=60
        )
        
        if resultado_calculo.get("sucesso"):
            print(f"✅ Cálculo realizado com sucesso:")
            print(f"   💰 Saldo anterior: R$ 100.000,00")
            print(f"   📈 IGPM aplicado: {resultado_calculo['igpm_utilizado']}%")
            print(f"   💰 Novo saldo: R$ {resultado_calculo['novo_saldo']:,.2f}")
            print(f"   📊 Fonte: {resultado_calculo['fonte_igpm']}")
        else:
            print(f"❌ Erro no cálculo: {resultado_calculo.get('erro')}")
            if resultado_calculo.get('acao_requerida') == 'EXECUTAR_RPA_COLETA_INDICES':
                print("🔄 Execute o RPA de Coleta de Índices para obter o IGPM")
                
    else:
        print("❌ IGPM não disponível no banco de dados")
        print("🔄 Execute o RPA de Coleta de Índices primeiro")
        
        # Exemplo de como usar com valor manual
        processador = ProcessadorRegrasNegocio()
        
        resultado_manual = await processador.calcular_valores_reparcelamento(
            saldo_atual=100000.00,
            indice_igpm=5.2,  # Valor manual
            parcelas_pendentes=60
        )
        
        if resultado_manual.get("sucesso"):
            print(f"\n✅ Cálculo com IGPM manual:")
            print(f"   💰 Novo saldo: R$ {resultado_manual['novo_saldo']:,.2f}")
            print(f"   📊 Fonte: manual")


async def exemplo_integração_rpa_sienge():
    """
    Demonstra integração completa com RPA Sienge
    """
    print("\n🔄 Exemplo de integração com RPA Sienge...")
    
    from rpa_sienge.rpa_sienge import RPASienge
    
    # Dados de exemplo
    contrato_exemplo = {
        "numero_titulo": "CT123456",
        "cliente": "Cliente Exemplo Ltda",
        "empreendimento": "Residencial Exemplo"
    }
    
    credenciais_exemplo = {
        "url": "https://sistema.sienge.com.br",
        "usuario": "usuario@empresa.com",
        "senha": "senha123",
        "empresa": "Empresa Exemplo"
    }
    
    # RPA vai buscar IGPM automaticamente
    print("📝 O RPA Sienge agora busca o IGPM automaticamente:")
    print("   1. Verifica se foi fornecido nos parâmetros")
    print("   2. Se não, busca no MongoDB via data_manager")
    print("   3. Se não encontrar, solicita execução do RPA de Coleta")
    print("   4. Usa valor centralizado para todos os cálculos")
    
    print("\n✅ Sistema totalmente centralizado!")


if __name__ == "__main__":
    print("🚀 Demonstração do Sistema Centralizado de IGPM")
    print("=" * 50)
    
    asyncio.run(exemplo_uso_igpm())
    asyncio.run(exemplo_integração_rpa_sienge())
