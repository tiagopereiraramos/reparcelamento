
"""
Exemplo de como usar o novo sistema de logging com webhook
"""

import asyncio
from core.base_rpa import BaseRPA, ResultadoRPA
from typing import Dict, Any


class ExemploRPAComWebhook(BaseRPA):
    """
    Exemplo de RPA usando o novo sistema de logging com webhook opcional
    """
    
    def __init__(self, webhook_enabled: bool = False, webhook_url: str = None):
        super().__init__(
            nome_rpa="ExemploWebhook",
            usar_browser=False,
            webhook_enabled=webhook_enabled,  # Webhook opcional
            webhook_url=webhook_url,
            company_name="Trajetória Consultoria"
        )
    
    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """
        Executa exemplo com logs normais e webhook opcional
        """
        try:
            # Log normal - sempre vai para console e arquivo
            self.log_info("🚀 Iniciando processamento de exemplo")
            
            # Log com dados extras - também pode ir para webhook se habilitado
            self.log_info("📊 Processando dados", dados_extras={
                "total_registros": 100,
                "tipo_processamento": "exemplo"
            })
            
            # Simular processamento
            await asyncio.sleep(1)
            
            # Log de progresso
            self.log_info("📈 50% concluído")
            
            # Simular mais processamento  
            await asyncio.sleep(1)
            
            # Log de sucesso
            self.log_info("✅ Processamento concluído com sucesso", dados_extras={
                "registros_processados": 100,
                "tempo_processamento": "2 segundos"
            })
            
            return ResultadoRPA(
                sucesso=True,
                mensagem="Exemplo executado com sucesso",
                dados={"registros_processados": 100}
            )
            
        except Exception as e:
            # Log de erro - crítico vai para webhook se habilitado
            self.log_error("❌ Erro durante processamento", dados_extras={
                "erro_tipo": type(e).__name__,
                "erro_detalhe": str(e)
            })
            
            return ResultadoRPA(
                sucesso=False,
                mensagem="Erro durante execução",
                erro=str(e)
            )


async def exemplo_sem_webhook():
    """
    Exemplo usando apenas logs tradicionais (console + arquivo)
    """
    print("🧪 EXEMPLO SEM WEBHOOK")
    print("=" * 50)
    
    rpa = ExemploRPAComWebhook(webhook_enabled=False)
    resultado = await rpa.executar_com_monitoramento({})
    
    print(f"Status: {resultado.sucesso}")
    print(f"Mensagem: {resultado.mensagem}")


async def exemplo_com_webhook():
    """
    Exemplo usando logs + webhook
    """
    print("🧪 EXEMPLO COM WEBHOOK")
    print("=" * 50)
    
    # URL do webhook do cliente (substitua pela URL real)
    webhook_url = "https://api.exemplo.com/webhook/logs"
    
    rpa = ExemploRPAComWebhook(
        webhook_enabled=True,
        webhook_url=webhook_url
    )
    
    resultado = await rpa.executar_com_monitoramento({})
    
    print(f"Status: {resultado.sucesso}")
    print(f"Mensagem: {resultado.mensagem}")
    print("📡 Logs também enviados para webhook!")


if __name__ == "__main__":
    print("🚀 EXEMPLOS DE USO DO NOVO SISTEMA DE LOGGING")
    print("=" * 60)
    
    # Executa exemplo sem webhook
    asyncio.run(exemplo_sem_webhook())
    
    print("\n" + "=" * 60 + "\n")
    
    # Executa exemplo com webhook
    asyncio.run(exemplo_com_webhook())
