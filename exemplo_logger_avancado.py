
"""
Exemplo de Uso do Logger Avançado
Demonstra como integrar o novo sistema de logging com webhook
"""

import asyncio
from core.base_rpa import BaseRPA, ResultadoRPA
from core.logger_avancado import LoggerAvancado, register_log
from typing import Dict, Any

class ExemploRPALoggerAvancado(BaseRPA):
    """Exemplo de RPA usando o logger avançado"""
    
    def __init__(self):
        # Inicializar com logger avançado habilitado
        super().__init__(
            nome_rpa="ExemploLogger",
            usar_browser=False,
            usar_logger_avancado=True,  # ✅ Habilita logger avançado
            empresa="Trajetória"        # Nome da empresa
        )
    
    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """Exemplo de execução com diferentes tipos de log"""
        
        # Log de informação básico
        self.log_progresso("Iniciando processamento de exemplo")
        
        # Log avançado com dados extras
        self.log_avancado("Processando dados do cliente", "info", {
            "cliente_id": parametros.get("cliente_id", "N/A"),
            "processo": "validacao_inicial"
        })
        
        # Simular algum processamento
        await asyncio.sleep(1)
        
        # Log de warning
        self.log_avancado("Atenção: dados incompletos detectados", "warning", {
            "campos_faltantes": ["email", "telefone"],
            "impacto": "baixo"
        })
        
        # Log de erro simulado
        try:
            # Simular erro
            if parametros.get("simular_erro", False):
                raise Exception("Erro simulado para teste")
                
        except Exception as e:
            self.log_erro("Erro durante processamento", e)
            return ResultadoRPA(
                sucesso=False,
                mensagem="Erro simulado durante execução",
                erro=str(e)
            )
        
        # Log de debug
        self.log_avancado("Processamento concluído com sucesso", "debug", {
            "registros_processados": 150,
            "tempo_processamento": "1.2s"
        })
        
        return ResultadoRPA(
            sucesso=True,
            mensagem="Exemplo executado com sucesso!",
            dados={
                "registros_processados": 150,
                "logs_enviados": 4
            }
        )

async def exemplo_uso_direto():
    """Exemplo de uso direto do logger avançado"""
    print("\n" + "="*50)
    print("🧪 EXEMPLO DE USO DIRETO DO LOGGER AVANÇADO")
    print("="*50)
    
    # Criar logger para um RPA específico
    logger = LoggerAvancado(
        nome_rpa="TesteLogger",
        empresa="Trajetória"
    )
    
    # Diferentes tipos de log
    logger.info("Sistema iniciado", {"versao": "2.0", "ambiente": "desenvolvimento"})
    logger.warning("Configuração padrão sendo usada", {"config_file": "não encontrado"})
    logger.error("Falha na conexão", {"servidor": "192.168.1.100", "porta": 5432})
    logger.debug("Estado interno", {"memoria_usada": "128MB", "threads_ativas": 4})
    
    print("✅ Logs enviados com sucesso!")

def exemplo_compatibilidade_cliente():
    """Exemplo usando a função de compatibilidade do código do cliente"""
    print("\n" + "="*50)
    print("🔄 EXEMPLO DE COMPATIBILIDADE COM CÓDIGO DO CLIENTE")
    print("="*50)
    
    # Usar exatamente como o cliente solicitou
    register_log("Sistema iniciado", "info", "Trajetória", "RoboTeste")
    register_log("Erro de conexão", "error", "Trajetória", "RoboTeste")
    register_log("Situação crítica detectada", "critical", "Trajetória", "RoboTeste")
    register_log("Informação de debug", "debug", "Trajetória", "RoboTeste")
    
    print("✅ Logs de compatibilidade enviados!")

async def main():
    """Função principal de exemplo"""
    print("🚀 DEMONSTRAÇÃO DO SISTEMA DE LOGGER AVANÇADO")
    print("Criado conforme solicitação do cliente")
    print("Integrado ao sistema RPA existente")
    
    # Exemplo 1: Uso direto do logger
    await exemplo_uso_direto()
    
    # Exemplo 2: Compatibilidade com código do cliente
    exemplo_compatibilidade_cliente()
    
    # Exemplo 3: RPA com logger avançado
    print("\n" + "="*50)
    print("🤖 EXEMPLO DE RPA COM LOGGER AVANÇADO")
    print("="*50)
    
    rpa = ExemploRPALoggerAvancado()
    
    # Executar com sucesso
    resultado = await rpa.executar_com_monitoramento({
        "cliente_id": "12345",
        "simular_erro": False
    })
    
    print(f"Resultado: {resultado}")
    
    print("\n✅ Todos os exemplos executados!")
    print("📁 Logs salvos em: outputs/YYYY/MM/DD/logsYYYYMMDD.txt")
    print("🌐 Logs enviados via webhook para:", rpa.logger_avancado.webhook_url if rpa.logger_avancado else "N/A")

if __name__ == "__main__":
    asyncio.run(main())
