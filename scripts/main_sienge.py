#!/usr/bin/env python3
"""
Main de produção para execução do RPA Sienge

Executa o RPA de reparcelamento no Sienge ERP em lote.
Processa contratos da collection fila_contratos em duas fases separadas.

Pode ser chamado por agendadores, CI/CD ou manualmente.
"""
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from rpa_sienge import RPASienge
from core.data_manager import data_manager

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def credenciais_sienge_env():
    """Carrega credenciais do Sienge das variáveis de ambiente"""
    return {
        "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/8/index.html"),
        "usuario": os.getenv("SIENGE_USUARIO", "tc@trajetoriaconsultoria.com.br"),
        "senha": os.getenv("SIENGE_SENHA", ""),
        "empresa": os.getenv("SIENGE_EMPRESA", "1")
    }


async def carregar_indices_economicos():
    """Carrega índices econômicos do data_manager"""
    try:
        await data_manager.inicializar()

        # Buscar IPCA e IGPM mais recentes
        ipca = await data_manager.obter_indice_mais_recente("ipca")
        igpm = await data_manager.obter_indice_mais_recente("igpm")

        return {
            "ipca": {"valor": ipca if ipca else 0.0},
            "igpm": {"valor": igpm if igpm else 0.0}
        }
    except Exception as e:
        log(f"⚠️ Erro ao carregar índices - usando valores padrão: {str(e)}")
        return {
            "ipca": {"valor": 0.0},
            "igpm": {"valor": 0.0}
        }


def obter_fase_execucao():
    """Obtém fase de execução do usuário ou variável de ambiente"""
    # Verifica variável de ambiente primeiro
    fase_env = os.getenv("SIENGE_FASE", "").lower()
    if fase_env in ["extracao", "reparcelamento", "ambas"]:
        return fase_env

    # Se não definida ou inválida, pergunta ao usuário
    print("\n🎯 PROCESSAMENTO RPA SIENGE EM LOTE")
    print("=" * 50)
    print("Escolha a fase de execução:")
    print("1. 📥 EXTRAÇÃO - Apenas extrair relatórios (PENDENTE → EXTRAIDO)")
    print("2. 📤 REPARCELAMENTO - Apenas reparcelamento (EXTRAIDO → PROCESSADO)")
    print("3. 🔄 AMBAS - Extração + Reparcelamento (processo completo)")
    print("=" * 50)

    while True:
        escolha = input("Digite sua escolha (1-3): ").strip()

        if escolha == "1":
            return "extracao"
        elif escolha == "2":
            return "reparcelamento"
        elif escolha == "3":
            return "ambas"
        else:
            print("❌ Opção inválida! Digite 1, 2 ou 3.")


async def verificar_fila_contratos():
    """Verifica e mostra estatísticas da fila de contratos"""
    try:
        from core.mongodb_manager import mongodb_manager
        await mongodb_manager.conectar()

        if not mongodb_manager.conectado or mongodb_manager.database is None:
            log("❌ Erro: MongoDB não conectado")
            return False

        collection = mongodb_manager.database.fila_contratos

        # Contar por status
        total = collection.count_documents({})
        pendentes = collection.count_documents({"status": "PENDENTE"})
        extraidos = collection.count_documents({"status": "EXTRAIDO"})
        processados = collection.count_documents({"status": "PROCESSADO"})
        erros = collection.count_documents({"status": "ERRO"})

        log(f"📊 ESTATÍSTICAS DA FILA DE CONTRATOS:")
        log(f"   📄 Total: {total}")
        log(f"   ⏳ Pendentes: {pendentes}")
        log(f"   📥 Extraídos: {extraidos}")
        log(f"   ✅ Processados: {processados}")
        log(f"   ❌ Com erro: {erros}")

        if total == 0:
            log("⚠️ Nenhum contrato encontrado na fila")
            return False

        return True

    except Exception as e:
        log(f"❌ Erro ao verificar fila: {str(e)}")
        return False


async def main():
    log("🚀 Iniciando execução do RPA Sienge (produção em lote)...")

    # Verificar fila antes de iniciar
    fila_valida = await verificar_fila_contratos()
    if not fila_valida:
        log("❌ Erro na verificação da fila. Encerrando execução.")
        sys.exit(1)

    # Obter configurações
    credenciais = credenciais_sienge_env()
    indices = await carregar_indices_economicos()
    fase = obter_fase_execucao()

    # Validar credenciais obrigatórias
    if not credenciais.get("senha"):
        log("❌ ERRO: SIENGE_SENHA não configurada nas variáveis de ambiente")
        sys.exit(1)

    log(f"🎯 Fase selecionada: {fase.upper()}")
    log(f"📈 IGPM disponível: {indices['igpm']['valor']}%")
    log(f"📈 IPCA disponível: {indices['ipca']['valor']}%")

    # Inicializar RPA
    try:
        # Browser visível por padrão para desenvolvimento/debug
        headless = os.getenv("SIENGE_HEADLESS", "false").lower() == "true"
        rpa = RPASienge(headless=headless)
        await rpa.inicializar()

        log(f"🌐 Browser inicializado (headless: {headless})")

        # Executar processamento em lote
        resultado = await rpa.processar_fila_contratos_lote(
            credenciais_sienge=credenciais,
            indices=indices,
            fase=fase
        )

        # Relatório final
        if resultado.get("sucesso"):
            log("✅ PROCESSAMENTO EM LOTE CONCLUÍDO COM SUCESSO")

            if resultado["fase_extracao"]["executada"]:
                extracao = resultado["fase_extracao"]
                log(
                    f"   📥 EXTRAÇÃO: {extracao['contratos_processados']} sucessos, {extracao['contratos_erro']} erros")

            if resultado["fase_reparcelamento"]["executada"]:
                reparcelamento = resultado["fase_reparcelamento"]
                log(
                    f"   📤 REPARCELAMENTO: {reparcelamento['contratos_processados']} sucessos, {reparcelamento['contratos_erro']} erros")

            log(f"⏱️ Tempo total: {resultado.get('timestamp_inicio')} → {resultado.get('timestamp_fim')}")
            sys.exit(0)
        else:
            log(f"❌ ERRO NO PROCESSAMENTO: {resultado.get('erro', 'Erro desconhecido')}")
            sys.exit(1)

    except Exception as e:
        log(f"❌ ERRO FATAL: {str(e)}")
        sys.exit(1)
    finally:
        try:
            await rpa.finalizar()
        except:
            pass


async def main_contrato_unico():
    """
    MODO LEGADO: Processa um único contrato (mantido para compatibilidade)
    """
    log("🔧 Iniciando execução do RPA Sienge (contrato único - modo legado)...")
    credenciais = credenciais_sienge_env()

    # Busca o próximo contrato pendente da fila
    await data_manager.inicializar()
    fila_dados = await data_manager.obter_fila_sienge()
    contratos = fila_dados.get("contratos", []) if fila_dados else []
    contrato = next((c for c in contratos if c.get(
        "status_processamento") not in ["processado", "erro"]), None)

    if not contrato:
        log("Nenhum contrato pendente encontrado na fila. Encerrando execução.")
        sys.exit(0)

    log(f"Processando contrato: {contrato.get('numero_titulo', 'N/A')} - {contrato.get('cliente', 'N/A')}")

    rpa = RPASienge()  # Browser visível por padrão
    await rpa.inicializar()
    resultado = await rpa.executar(
        contrato=contrato,
        credenciais_sienge=credenciais,
        indices=None,  # Pode ser carregado conforme necessário
        etapa="completa",
        autorizar_reparcelamento=False,
        notificar_analista=True
    )
    await rpa.finalizar()

    if resultado.sucesso:
        log(f"SUCESSO: {resultado.mensagem}")
        sys.exit(0)
    else:
        log(f"FALHA: {resultado.mensagem}")
        if resultado.erro:
            log(f"Detalhe do erro: {resultado.erro}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        # Verifica se deve usar modo legado
        modo_legado = os.getenv("SIENGE_MODO_LEGADO",
                                "false").lower() == "true"

        if modo_legado:
            asyncio.run(main_contrato_unico())
        else:
            asyncio.run(main())

    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:
        log(f"Erro fatal: {e}")
        sys.exit(1)
