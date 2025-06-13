
"""
Script de Teste - Logger Avançado
Valida todas as funcionalidades do novo sistema de logging
"""

import asyncio
import os
from pathlib import Path
from core.logger_avancado import LoggerAvancado, register_log
from core.base_rpa import BaseRPA, ResultadoRPA
from typing import Dict, Any

def testar_estrutura_pastas():
    """Testa criação da estrutura de pastas"""
    print("🧪 Testando estrutura de pastas...")
    
    logger = LoggerAvancado("TesteEstrutura", "TesteCorp")
    logger.info("Teste de criação de estrutura")
    
    # Verificar se a estrutura foi criada
    from datetime import datetime
    now = datetime.now()
    pasta_esperada = Path("outputs") / now.strftime('%Y') / now.strftime('%m') / now.strftime('%d')
    arquivo_esperado = pasta_esperada / f"logs{now.strftime('%Y%m%d')}.txt"
    
    if pasta_esperada.exists():
        print(f"   ✅ Pasta criada: {pasta_esperada}")
    else:
        print(f"   ❌ Pasta não encontrada: {pasta_esperada}")
    
    if arquivo_esperado.exists():
        print(f"   ✅ Arquivo criado: {arquivo_esperado}")
    else:
        print(f"   ❌ Arquivo não encontrado: {arquivo_esperado}")

def testar_compatibilidade_cliente():
    """Testa compatibilidade com código do cliente"""
    print("\n🧪 Testando compatibilidade com código do cliente...")
    
    # Exatamente como o cliente enviou
    register_log("teste", "debug", "trajetoria", "apilogs")
    register_log("Sistema operacional", "info", "trajetoria", "sistema")
    register_log("Erro simulado", "error", "trajetoria", "processamento")
    
    print("   ✅ Funções de compatibilidade funcionando")

def testar_niveis_log():
    """Testa todos os níveis de log"""
    print("\n🧪 Testando todos os níveis de log...")
    
    logger = LoggerAvancado("TesteNiveis", "TesteCorp")
    
    # Testar cada nível
    niveis = [
        ("info", "Informação de teste"),
        ("warning", "Aviso de teste"), 
        ("error", "Erro simulado"),
        ("critical", "Situação crítica simulada"),
        ("debug", "Debug de teste")
    ]
    
    for nivel, mensagem in niveis:
        resultado = logger.register_log(mensagem, nivel, {
            "teste": True,
            "nivel": nivel
        })
        
        if resultado:
            print(f"   ✅ {nivel.upper()}: {mensagem}")
        else:
            print(f"   ❌ {nivel.upper()}: Falhou")

async def testar_rpa_integrado():
    """Testa RPA com logger avançado integrado"""
    print("\n🧪 Testando RPA com logger avançado...")
    
    class RPATeste(BaseRPA):
        def __init__(self):
            super().__init__(
                nome_rpa="RPATeste",
                usar_browser=False,
                usar_logger_avancado=True,
                empresa="TesteCorp"
            )
        
        async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
            self.log_progresso("Iniciando teste integrado")
            
            # Teste log avançado
            self.log_avancado("Processamento iniciado", "info", {
                "parametros_recebidos": len(parametros)
            })
            
            # Simular erro se solicitado
            if parametros.get("erro", False):
                raise Exception("Erro de teste")
            
            self.log_avancado("Teste concluído", "debug", {
                "resultado": "sucesso"
            })
            
            return ResultadoRPA(
                sucesso=True,
                mensagem="RPA teste executado com sucesso"
            )
    
    # Testar RPA
    rpa = RPATeste()
    resultado = await rpa.executar_com_monitoramento({"teste": True})
    
    if resultado.sucesso:
        print("   ✅ RPA com logger avançado funcionando")
    else:
        print("   ❌ RPA com logger avançado falhou")

def testar_webhook_config():
    """Testa configuração do webhook"""
    print("\n🧪 Testando configuração do webhook...")
    
    # Testar com URL padrão
    logger1 = LoggerAvancado("TesteWebhook1", "TesteCorp")
    print(f"   📡 URL padrão: {logger1.webhook_url}")
    
    # Testar com URL customizada
    logger2 = LoggerAvancado("TesteWebhook2", "TesteCorp", "http://exemplo.com/logs")
    print(f"   📡 URL customizada: {logger2.webhook_url}")
    
    # Testar variável de ambiente
    os.environ['WEBHOOK_LOGS_URL'] = 'http://env.exemplo.com/logs'
    logger3 = LoggerAvancado("TesteWebhook3", "TesteCorp")
    print(f"   📡 URL via ENV: {logger3.webhook_url}")
    
    print("   ✅ Configurações de webhook testadas")

def verificar_arquivos_gerados():
    """Verifica arquivos de log gerados"""
    print("\n🧪 Verificando arquivos de log gerados...")
    
    pasta_outputs = Path("outputs")
    if not pasta_outputs.exists():
        print("   ❌ Pasta outputs não encontrada")
        return
    
    # Listar arquivos gerados
    arquivos_log = list(pasta_outputs.rglob("logs*.txt"))
    
    if arquivos_log:
        print(f"   ✅ Encontrados {len(arquivos_log)} arquivos de log:")
        for arquivo in arquivos_log:
            tamanho = arquivo.stat().st_size
            print(f"      📄 {arquivo.relative_to(pasta_outputs)} ({tamanho} bytes)")
    else:
        print("   ⚠️ Nenhum arquivo de log encontrado")

async def main():
    """Executa todos os testes"""
    print("🚀 INICIANDO TESTES DO LOGGER AVANÇADO")
    print("="*60)
    
    # Executar testes
    testar_estrutura_pastas()
    testar_compatibilidade_cliente()
    testar_niveis_log()
    await testar_rpa_integrado()
    testar_webhook_config()
    verificar_arquivos_gerados()
    
    print("\n" + "="*60)
    print("✅ TODOS OS TESTES CONCLUÍDOS!")
    print("📁 Verifique a pasta 'outputs' para os logs gerados")
    print("🌐 Logs também foram enviados via webhook (se configurado)")

if __name__ == "__main__":
    asyncio.run(main())
