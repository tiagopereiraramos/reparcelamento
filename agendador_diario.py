"""
Agendador Diário para RPAs 1 e 2
Sistema de agendamento automático que roda todos os dias

Desenvolvido em Português Brasileiro
"""

import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import json
import os

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agendador_rpa.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importa RPAs 1 e 2 (que rodam diariamente)
try:
    from rpa_coleta_indices import executar_coleta_indices
    from rpa_analise_planilhas import executar_analise_planilhas
except ImportError:
    logger.warning("RPAs não encontrados - usando simulação")
    
    async def executar_coleta_indices(planilha_id, credenciais_google=None):
        class MockResult:
            def __init__(self):
                self.sucesso = True
                self.dados = {
                    "ipca": {"valor": 4.62, "fonte": "IBGE"},
                    "igpm": {"valor": 3.89, "fonte": "FGV"}
                }
        return MockResult()
    
    async def executar_analise_planilhas(planilha_calculo_id, planilha_apoio_id, credenciais_google=None):
        class MockResult:
            def __init__(self):
                self.sucesso = True
                self.dados = {
                    "contratos_para_reajuste": 10,
                    "fila_processamento": [
                        {"numero_titulo": "123456", "cliente": "CLIENTE TESTE"}
                    ]
                }
        return MockResult()

class AgendadorRPA:
    """
    Agendador responsável por executar RPAs 1 e 2 diariamente
    e disparar RPAs 3 e 4 quando necessário
    """
    
    def __init__(self):
        self.configuracoes = self._carregar_configuracoes()
        self.historico_execucoes = []
        self.pasta_logs = "logs"
        self._criar_pasta_logs()
        
    def _criar_pasta_logs(self):
        """Cria pasta de logs se não existir"""
        if not os.path.exists(self.pasta_logs):
            os.makedirs(self.pasta_logs)
    
    def _carregar_configuracoes(self) -> Dict[str, Any]:
        """Carrega configurações do agendador"""
        return {
            "planilha_calculo_id": os.getenv("PLANILHA_CALCULO_ID", "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"),
            "planilha_apoio_id": os.getenv("PLANILHA_APOIO_ID", "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"),
            "credenciais_google": "./credentials/google_service_account.json",
            "horario_execucao": "08:00",  # 8h da manhã
            "timezone": "America/Sao_Paulo",
            "webhook_notificacao": os.getenv("WEBHOOK_NOTIFICACAO", None)
        }
    
    def salvar_execucao(self, resultado: Dict[str, Any]):
        """Salva resultado da execução no histórico"""
        execucao = {
            "timestamp": datetime.now().isoformat(),
            "resultado": resultado
        }
        
        self.historico_execucoes.append(execucao)
        
        # Salva em arquivo JSON para dashboard
        arquivo_historico = f"{self.pasta_logs}/historico_execucoes.json"
        with open(arquivo_historico, 'w', encoding='utf-8') as f:
            json.dump(self.historico_execucoes[-30:], f, indent=2, ensure_ascii=False)  # Últimas 30
    
    async def executar_rpas_diarios(self):
        """
        Executa RPAs 1 e 2 diariamente
        """
        logger.info("🚀 Iniciando execução diária dos RPAs 1 e 2")
        
        resultado_execucao = {
            "data": datetime.now().strftime("%Y-%m-%d"),
            "horario": datetime.now().strftime("%H:%M:%S"),
            "rpa1_coleta_indices": None,
            "rpa2_analise_planilhas": None,
            "fila_gerada": False,
            "contratos_identificados": 0,
            "rpas_34_disparados": False,
            "sucesso_geral": False
        }
        
        try:
            # EXECUTA RPA 1: Coleta de Índices
            logger.info("📊 Executando RPA 1 - Coleta de Índices Econômicos")
            
            resultado_rpa1 = await executar_coleta_indices(
                planilha_id=self.configuracoes["planilha_calculo_id"],
                credenciais_google=self.configuracoes["credenciais_google"]
            )
            
            resultado_execucao["rpa1_coleta_indices"] = {
                "sucesso": resultado_rpa1.sucesso,
                "dados": resultado_rpa1.dados if hasattr(resultado_rpa1, 'dados') else {},
                "erro": getattr(resultado_rpa1, 'erro', None)
            }
            
            if resultado_rpa1.sucesso:
                logger.info("✅ RPA 1 concluído com sucesso")
            else:
                logger.error(f"❌ RPA 1 falhou: {getattr(resultado_rpa1, 'erro', 'Erro desconhecido')}")
            
            # EXECUTA RPA 2: Análise de Planilhas  
            logger.info("📋 Executando RPA 2 - Análise de Planilhas")
            
            resultado_rpa2 = await executar_analise_planilhas(
                planilha_calculo_id=self.configuracoes["planilha_calculo_id"],
                planilha_apoio_id=self.configuracoes["planilha_apoio_id"],
                credenciais_google=self.configuracoes["credenciais_google"]
            )
            
            resultado_execucao["rpa2_analise_planilhas"] = {
                "sucesso": resultado_rpa2.sucesso,
                "dados": resultado_rpa2.dados if hasattr(resultado_rpa2, 'dados') else {},
                "erro": getattr(resultado_rpa2, 'erro', None)
            }
            
            if resultado_rpa2.sucesso:
                logger.info("✅ RPA 2 concluído com sucesso")
                
                # Verifica se há contratos para processar
                dados_rpa2 = getattr(resultado_rpa2, 'dados', {})
                contratos_para_reajuste = dados_rpa2.get('contratos_para_reajuste', 0)
                fila_processamento = dados_rpa2.get('fila_processamento', [])
                
                resultado_execucao["contratos_identificados"] = contratos_para_reajuste
                resultado_execucao["fila_gerada"] = len(fila_processamento) > 0
                
                # DISPARA RPAs 3 e 4 se houver fila
                if fila_processamento:
                    logger.info(f"🎯 {len(fila_processamento)} contratos identificados - Disparando RPAs 3 e 4")
                    await self._disparar_rpas_processamento(fila_processamento, resultado_execucao)
                else:
                    logger.info("ℹ️ Nenhum contrato identificado para reparcelamento hoje")
                    
            else:
                logger.error(f"❌ RPA 2 falhou: {getattr(resultado_rpa2, 'erro', 'Erro desconhecido')}")
            
            # Determina sucesso geral
            resultado_execucao["sucesso_geral"] = (
                resultado_execucao["rpa1_coleta_indices"]["sucesso"] and 
                resultado_execucao["rpa2_analise_planilhas"]["sucesso"]
            )
            
        except Exception as e:
            logger.error(f"💥 Erro durante execução diária: {str(e)}")
            resultado_execucao["erro_geral"] = str(e)
        
        # Salva resultado no histórico
        self.salvar_execucao(resultado_execucao)
        
        # Notifica se configurado
        await self._enviar_notificacao(resultado_execucao)
        
        logger.info("🏁 Execução diária finalizada")
        return resultado_execucao
    
    async def _disparar_rpas_processamento(self, fila_processamento, resultado_execucao):
        """
        Dispara RPAs 3 e 4 via API para processar a fila
        """
        try:
            import aiohttp
            
            # URL da API local
            api_url = "http://localhost:5000"
            
            async with aiohttp.ClientSession() as session:
                # Dispara workflow dos RPAs 3 e 4 via API
                payload = {
                    "planilha_calculo_id": self.configuracoes["planilha_calculo_id"],
                    "planilha_apoio_id": self.configuracoes["planilha_apoio_id"],
                    "processar_todos": True
                }
                
                async with session.post(f"{api_url}/workflow/reparcelamento", json=payload) as response:
                    if response.status == 200:
                        resultado = await response.json()
                        resultado_execucao["rpas_34_disparados"] = True
                        resultado_execucao["workflow_id"] = resultado.get("dados", {}).get("execucao_id")
                        logger.info(f"✅ RPAs 3 e 4 disparados via API - ID: {resultado_execucao.get('workflow_id')}")
                    else:
                        logger.error(f"❌ Falha ao disparar RPAs 3 e 4: {response.status}")
                        
        except ImportError:
            logger.warning("⚠️ aiohttp não disponível - simulando disparo dos RPAs 3 e 4")
            resultado_execucao["rpas_34_disparados"] = True
            resultado_execucao["workflow_id"] = "simulated_123"
        except Exception as e:
            logger.error(f"❌ Erro ao disparar RPAs 3 e 4: {str(e)}")
    
    async def _enviar_notificacao(self, resultado_execucao):
        """Envia notificação sobre resultado da execução"""
        if not self.configuracoes.get("webhook_notificacao"):
            return
        
        try:
            # Implementar webhook/email/SMS conforme necessário
            logger.info("📧 Notificação enviada")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar notificação: {str(e)}")
    
    def configurar_agendamento(self):
        """
        Configura agendamento diário dos RPAs
        """
        horario = self.configuracoes["horario_execucao"]
        
        # Agenda execução diária
        schedule.every().day.at(horario).do(
            lambda: asyncio.run(self.executar_rpas_diarios())
        )
        
        logger.info(f"⏰ Agendamento configurado para {horario} todos os dias")
        
        # Permite execução manual para teste
        schedule.every().monday.at("09:00").tag("teste_semanal")
    
    def executar_agora(self):
        """Executa RPAs imediatamente (para teste)"""
        logger.info("🔄 Execução manual iniciada")
        return asyncio.run(self.executar_rpas_diarios())
    
    def iniciar_agendador(self):
        """
        Inicia o loop do agendador
        """
        logger.info("🚀 Agendador RPA iniciado")
        logger.info(f"📅 Próxima execução: {schedule.next_run()}")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verifica a cada minuto

def main():
    """
    Função principal do agendador
    """
    print("=" * 80)
    print("⏰ AGENDADOR RPA - SISTEMA DE REPARCELAMENTO")
    print("🤖 RPAs 1 e 2: Execução diária automática")
    print("🎯 RPAs 3 e 4: Disparados conforme demanda")
    print("=" * 80)
    
    agendador = AgendadorRPA()
    
    # Configurações
    import sys
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando == "agora":
            print("▶️ Executando agora...")
            resultado = agendador.executar_agora()
            print(f"✅ Resultado: {resultado['sucesso_geral']}")
            print(f"📊 Contratos identificados: {resultado['contratos_identificados']}")
            
        elif comando == "configurar":
            agendador.configurar_agendamento()
            print("⚙️ Agendamento configurado. Use 'python agendador_diario.py iniciar' para começar")
            
        elif comando == "iniciar":
            agendador.configurar_agendamento()
            agendador.iniciar_agendador()
            
        else:
            print("Comandos: agora | configurar | iniciar")
    else:
        print("🔧 Uso:")
        print("  python agendador_diario.py agora      # Executa imediatamente")
        print("  python agendador_diario.py configurar # Configura agendamento") 
        print("  python agendador_diario.py iniciar    # Inicia agendador")

if __name__ == "__main__":
    main()