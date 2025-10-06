#!/usr/bin/env python3
"""
Script para processar contratos aniversário agendados
Executa reparcelamento de contratos que foram agendados para o mês atual
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils_sienge import processar_contratos_agendados, log, notificar_sucesso_simples, notificar_erro_simples
from core.mongodb_manager import mongodb_manager


async def main():
    """
    Função principal para processar contratos agendados
    """
    try:
        log("🚀 Iniciando processamento de contratos aniversário agendados...")
        
        # Conectar ao MongoDB
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()
        
        if not mongodb_manager.conectado:
            raise Exception("Não foi possível conectar ao MongoDB")
        
        log("✅ Conectado ao MongoDB")
        
        # Processar contratos agendados
        resultado = await processar_contratos_agendados()
        
        if resultado.get("sucesso"):
            total_agendados = resultado.get("total_agendados", 0)
            processados = resultado.get("processados", 0)
            erros = resultado.get("erros", 0)
            
            log(f"📊 RESUMO DO PROCESSAMENTO:")
            log(f"   📅 Total de contratos agendados: {total_agendados}")
            log(f"   ✅ Contratos processados: {processados}")
            log(f"   ❌ Erros: {erros}")
            
            if total_agendados > 0:
                # Notificar sobre o processamento
                assunto = f"Contratos Aniversário Processados - {datetime.now().strftime('%d/%m/%Y')}"
                mensagem = f"""
🎂 PROCESSAMENTO DE CONTRATOS ANIVERSÁRIO AGENDADOS

📊 RESUMO:
- Total de contratos agendados: {total_agendados}
- Contratos processados com sucesso: {processados}
- Erros encontrados: {erros}

📅 Data de processamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

---
RPA Sienge - Sistema de Reparcelamento Automatizado
                """.strip()
                
                await notificar_sucesso_simples(assunto, mensagem)
                log("📧 Notificação de processamento enviada")
            else:
                log("ℹ️ Nenhum contrato agendado encontrado para o mês atual")
        else:
            erro = resultado.get("erro", "Erro desconhecido")
            log(f"❌ Erro ao processar contratos agendados: {erro}")
            
            # Notificar sobre o erro
            assunto = f"Erro no Processamento de Contratos Aniversário - {datetime.now().strftime('%d/%m/%Y')}"
            mensagem = f"""
❌ ERRO NO PROCESSAMENTO DE CONTRATOS ANIVERSÁRIO

Erro: {erro}

📅 Data do erro: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Verifique os logs para mais detalhes.

---
RPA Sienge - Sistema de Reparcelamento Automatizado
            """.strip()
            
            await notificar_erro_simples(assunto, mensagem)
            log("📧 Notificação de erro enviada")
            
    except Exception as e:
        erro_msg = f"Erro inesperado: {str(e)}"
        log(f"❌ {erro_msg}")
        
        # Notificar sobre o erro inesperado
        assunto = f"Erro Inesperado - Processamento Contratos Aniversário - {datetime.now().strftime('%d/%m/%Y')}"
        mensagem = f"""
❌ ERRO INESPERADO NO PROCESSAMENTO

Erro: {erro_msg}

📅 Data do erro: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Verifique os logs para mais detalhes.

---
RPA Sienge - Sistema de Reparcelamento Automatizado
        """.strip()
        
        await notificar_erro_simples(assunto, mensagem)
        log("📧 Notificação de erro inesperado enviada")
        
    finally:
        # Desconectar do MongoDB
        if mongodb_manager.conectado:
            await mongodb_manager.desconectar()
            log("🔌 Desconectado do MongoDB")


if __name__ == "__main__":
    asyncio.run(main())
