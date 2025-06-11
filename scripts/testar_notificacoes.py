"""
Script de Teste - Sistema de Notificações
Testa envio de notificações por email usando Gmail API

Desenvolvido em Português Brasileiro
"""

import sys
import os
from datetime import datetime

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notificacoes_simples import (
    notificar_sucesso, 
    notificar_erro, 
    notificar_workflow,
    testar_notificacoes,
    notificacoes
)

def testar_sistema_notificacoes():
    """Testa todas as funcionalidades de notificação"""
    print("🔔 Testando Sistema de Notificações")
    print("=" * 50)
    
    # 1. Verificar configurações
    print("\n📋 Verificando configurações...")
    config = notificacoes.configuracoes
    print(f"✅ Sistema habilitado: {config.get('habilitado', False)}")
    print(f"📧 Destinatários: {config.get('destinatarios', [])}")
    print(f"📅 Eventos configurados: {list(config.get('eventos', {}).keys())}")
    
    # 2. Teste básico de configuração
    print("\n🧪 Executando teste básico...")
    resultado_teste = testar_notificacoes()
    
    if resultado_teste:
        print("✅ Teste básico: SUCESSO")
    else:
        print("❌ Teste básico: FALHOU")
        print("💡 Verifique se:")
        print("   - As credenciais do Google estão configuradas")
        print("   - O email remetente tem permissões delegadas")
        print("   - Os destinatários estão corretos")
        return False
    
    # 3. Teste de notificação de sucesso
    print("\n🎉 Testando notificação de sucesso...")
    resultado_sucesso = notificar_sucesso(
        nome_rpa="RPA Teste de Notificações",
        tempo_execucao="2 minutos",
        resultados={
            "registros_processados": 150,
            "arquivos_gerados": 3,
            "tempo_total": "2m 15s",
            "status_final": "Concluído com êxito"
        }
    )
    
    if resultado_sucesso:
        print("✅ Notificação de sucesso: ENVIADA")
    else:
        print("❌ Notificação de sucesso: FALHOU")
    
    # 4. Teste de notificação de erro
    print("\n⚠️ Testando notificação de erro...")
    resultado_erro = notificar_erro(
        nome_rpa="RPA Teste de Erro",
        erro="Timeout na conexão",
        detalhes="""
Erro detectado durante execução:
- Componente: Selenium WebDriver
- Tipo: TimeoutException
- Timestamp: {timestamp}
- Ação: Aguardando elemento #btn-login
- Timeout configurado: 30 segundos

Stack trace:
selenium.common.exceptions.TimeoutException: 
Message: Element not found within timeout period
        """.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    
    if resultado_erro:
        print("✅ Notificação de erro: ENVIADA")
    else:
        print("❌ Notificação de erro: FALHOU")
    
    # 5. Teste de notificação de workflow
    print("\n🔄 Testando notificação de workflow...")
    resultado_workflow = notificar_workflow(
        rpas=["RPA Coleta Índices", "RPA Análise Planilhas", "RPA Sienge", "RPA Sicredi"],
        contratos=25,
        tempo="45 minutos"
    )
    
    if resultado_workflow:
        print("✅ Notificação de workflow: ENVIADA")
    else:
        print("❌ Notificação de workflow: FALHOU")
    
    # 6. Resumo final
    print("\n📊 RESUMO DOS TESTES")
    print("=" * 30)
    
    testes_realizados = [
        ("Teste básico", resultado_teste),
        ("Notificação de sucesso", resultado_sucesso),
        ("Notificação de erro", resultado_erro),
        ("Notificação de workflow", resultado_workflow)
    ]
    
    sucessos = sum(1 for _, resultado in testes_realizados if resultado)
    total = len(testes_realizados)
    
    for nome, resultado in testes_realizados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{nome}: {status}")
    
    print(f"\n🎯 Resultado final: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("🎉 TODOS OS TESTES PASSARAM! Sistema de notificações funcionando perfeitamente.")
    elif sucessos > 0:
        print("⚠️ ALGUNS TESTES FALHARAM. Verifique as configurações.")
    else:
        print("🚨 TODOS OS TESTES FALHARAM. Sistema de notificações não está funcionando.")
    
    return sucessos == total

def configurar_notificacoes_exemplo():
    """Configura exemplo de notificações"""
    print("\n⚙️ Configurando exemplo de notificações...")
    
    # Configuração de exemplo
    config_exemplo = {
        "habilitado": True,
        "destinatarios": [
            "admin@empresa.com",
            "ti@empresa.com"
        ],
        "eventos": {
            "rpa_concluido": True,
            "rpa_erro": True,
            "workflow_concluido": True,
            "indices_atualizados": False,
            "contratos_identificados": True
        }
    }
    
    notificacoes.configuracoes.update(config_exemplo)
    notificacoes.salvar_configuracoes()
    
    print("✅ Configuração de exemplo salva!")
    print("📧 Destinatários configurados:")
    for email in config_exemplo["destinatarios"]:
        print(f"   - {email}")

def main():
    """Função principal do teste"""
    print("🚀 SISTEMA DE NOTIFICAÇÕES RPA v2.0")
    print("Teste completo de funcionalidades")
    print("=" * 50)
    
    # Configurar exemplo
    configurar_notificacoes_exemplo()
    
    # Executar testes
    sucesso = testar_sistema_notificacoes()
    
    print("\n" + "=" * 50)
    if sucesso:
        print("🎯 SISTEMA PRONTO PARA USO!")
        print("\n💡 Próximos passos:")
        print("1. Configure seus emails reais no dashboard")
        print("2. Teste com o botão 'Testar Notificações'")
        print("3. Execute os RPAs e receba notificações automaticamente")
    else:
        print("🔧 CONFIGURAÇÃO NECESSÁRIA!")
        print("\n💡 Para ativar as notificações:")
        print("1. Configure suas credenciais do Google Gmail API")
        print("2. Configure o email remetente nas variáveis de ambiente")
        print("3. Adicione seus emails de destino no dashboard")

if __name__ == "__main__":
    main()