import asyncio
from core.mongodb_manager import mongodb_manager
from datetime import datetime


async def reativar_fila_para_pendente():
    await mongodb_manager.conectar()
    collection = mongodb_manager.database.fila_contratos
    # Atualiza todos os contratos para status PENDENTE e limpa campos de processamento
    result = collection.update_many(
        {},
        {
            "$set": {
                "status": "PENDENTE",
                "status_processamento": "PENDENTE",
                "timestamp_ultima_atualizacao": datetime.now().isoformat(),
                "tentativas_processamento": 0
            },
            "$unset": {
                "erro_extracao": "",
                "erro_retroalimentacao": "",
                "erro_reparcelamento": "",
                "processo_completo": "",
                "resultado_final": "",
                "dados_extraidos": "",
                "timestamp_finalizacao": "",
                "timestamp_aguardando_aprovacao": ""
            }
        }
    )
    print(f"Contratos atualizados para PENDENTE: {result.modified_count}")
    await mongodb_manager.desconectar()

if __name__ == "__main__":
    asyncio.run(reativar_fila_para_pendente())
