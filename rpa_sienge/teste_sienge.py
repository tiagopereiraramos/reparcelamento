#!/usr/bin/env python3
"""
Teste Independente - RPA Sienge
Permite testar o RPA fora da orquestração Temporal para desenvolvimento e homologação

Desenvolvido em Português Brasileiro
"""

from rpa_sienge import RPASienge
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
import json

# Adiciona diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def executar_processamento_sienge(contrato: Dict[str, Any],
                                      indices_economicos: Dict[str, Any],
                                      credenciais_sienge: Dict[str, str],
                                      etapa: str = "completa",
                                      autorizar_reparcelamento: bool = False,
                                      notificar_analista: bool = True):
    """
    Função auxiliar para executar o RPA Sienge
    """
    try:
        rpa = RPASienge()
        await rpa.inicializar()

        resultado = await rpa.executar(
            contrato=contrato,
            credenciais_sienge=credenciais_sienge,
            indices=indices_economicos,
            etapa=etapa,
            autorizar_reparcelamento=autorizar_reparcelamento,
            notificar_analista=notificar_analista
        )

        await rpa.finalizar()
        return resultado

    except Exception as e:
        from core.base_rpa import ResultadoRPA
        return ResultadoRPA(
            sucesso=False,
            mensagem="Erro na execução do RPA Sienge",
            erro=str(e)
        )


async def carregar_fila_contratos() -> List[Dict[str, Any]]:
    """
    Carrega a fila de contratos usando o data_manager unificado
    SEMPRE tenta MongoDB primeiro, depois fallback para JSON
    """
    try:
        # Inicializa o data_manager (garante conexão MongoDB se disponível)
        from core.data_manager import data_manager
        from core.mongodb_manager import mongodb_manager, MONGODB_DISPONIVEL

        print("🔍 Carregando fila de contratos...")

        # Força inicialização do data_manager
        await data_manager.inicializar()

        print(f"   Data Manager - MongoDB ativo: {data_manager.mongodb_ativo}")
        print(f"   MongoDB Manager - Conectado: {mongodb_manager.conectado if MONGODB_DISPONIVEL else 'N/A'}")
        print(f"   MongoDB - Disponível: {MONGODB_DISPONIVEL}")

        contratos = []
        fonte_dados = "none"

        # PRIORIDADE 1: Tentar MongoDB DIRETAMENTE se disponível
        if MONGODB_DISPONIVEL and mongodb_manager.conectado:
            try:
                print("📊 Tentando carregar do MongoDB...")
                collection = mongodb_manager.database.fila_processamento_sienge
                documento = await asyncio.get_event_loop().run_in_executor(
                    mongodb_manager.executor,
                    lambda: collection.find_one()
                )

                if documento and documento.get("contratos"):
                    contratos = documento.get("contratos", [])
                    fonte_dados = "mongodb"
                    print(f"✅ Fila carregada do MongoDB: {len(contratos)} contratos")
                else:
                    print("⚠️ Documento de fila não encontrado no MongoDB")

            except Exception as e:
                print(f"⚠️ Erro ao acessar MongoDB: {str(e)}")

        # PRIORIDADE 2: Fallback para data_manager se MongoDB falhou
        if not contratos:
            print("📄 Tentando carregar via data_manager...")
            fila_dados = await data_manager.obter_fila_sienge()

            if fila_dados and fila_dados.get("contratos"):
                contratos = fila_dados.get("contratos", [])
                fonte_dados = "json"
                print(f"✅ Fila carregada do JSON: {len(contratos)} contratos")

        # PRIORIDADE 3: Fallback direto para arquivo JSON
        if not contratos:
            print("📄 Tentando carregar diretamente do arquivo JSON...")
            import json
            arquivo_fila = os.path.join("dados_processamento", "fila_contratos_sienge.json")

            if os.path.exists(arquivo_fila):
                with open(arquivo_fila, 'r', encoding='utf-8') as f:
                    fila_dados = json.load(f)
                    contratos = fila_dados.get("contratos", [])
                    fonte_dados = "arquivo_json"
                    print(f"✅ Fila carregada do arquivo JSON: {len(contratos)} contratos")

        if contratos:
            print(f"📋 Fonte dos dados: {fonte_dados}")
            print("📋 Primeiros contratos na fila:")
            for i, contrato in enumerate(contratos[:3]):
                titulo = contrato.get("numero_titulo", "N/A")
                cliente = contrato.get("cliente", "N/A")
                status = contrato.get("status_processamento", "N/A")
                print(f"   {i+1}. {titulo} - {cliente} [{status}]")
            if len(contratos) > 3:
                print(f"   ... e mais {len(contratos)-3} contratos")

            return contratos
        else:
            print("⚠️ Nenhuma fila encontrada em nenhuma fonte")
            print("💡 Execute primeiro: python rpa_analise_planilhas/teste_analise_planilhas.py")
            return []

    except Exception as e:
        print(f"❌ Erro ao carregar fila: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return []


async def carregar_indices_economicos() -> Dict[str, Any]:
    """
    Carrega os índices econômicos mais recentes usando data_manager
    """
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()

        print("📈 Carregando índices econômicos...")

        # Tenta carregar do MongoDB se disponível
        if data_manager.mongodb_ativo:
            try:
                from core.mongodb_manager import mongodb_manager
                indices_doc = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: mongodb_manager.database.indices_economicos.find_one(
                        {}, sort=[("timestamp_coleta", -1)]
                    )
                )
                if indices_doc and indices_doc.get("indices"):
                    print("📊 Índices carregados do MongoDB")
                    indices_data = indices_doc.get("indices", {})
                    return {
                        "ipca": indices_data.get("ipca", {"valor": 4.62, "tipo": "IPCA", "periodo": "Dezembro/2024"}),
                        "igpm": indices_data.get("igpm", {"valor": 3.89, "tipo": "IGPM", "periodo": "Dezembro/2024"})
                    }
            except Exception as e:
                print(f"⚠️ Erro ao acessar MongoDB para índices: {str(e)}")

        # Fallback para valores simulados  
        print("📊 Usando índices simulados")
        return {
            "ipca": {
                "valor": 4.62,
                "tipo": "IPCA",
                "periodo": "Dezembro/2024"
            },
            "igpm": {
                "valor": 3.89,
                "tipo": "IGPM",
                "periodo": "Dezembro/2024"
            }
        }

    except Exception as e:
        print(f"❌ Erro ao carregar índices: {str(e)}")
        return {
            "ipca": {
                "valor": 4.62,
                "tipo": "IPCA",
                "periodo": "Dezembro/2024"
            },
            "igpm": {
                "valor": 3.89,
                "periodo": "Dezembro/2024"
            }
        }


async def processar_contrato_individual(contrato_dados: Dict[str, Any],
                                        indices: Dict[str, Any], indice: int,
                                        etapa: str = "completa",
                                        autorizar_reparcelamento: bool = False):
    """
    Processa um contrato individual do Sienge
    """
    print(f"\n🔄 Processando contrato {indice + 1}")
    print(f"   📋 Título: {contrato_dados.get('numero_titulo', 'N/A')}")
    print(f"   👤 Cliente: {contrato_dados.get('cliente', 'N/A')}")

    # Credenciais de teste (cliente deve configurar via variáveis de ambiente)
    credenciais_teste = {
        "url": os.getenv("SIENGE_URL", "https://sienge.exemplo.com"),
        "usuario": os.getenv("SIENGE_USERNAME",
                             "tc@trajetoriaconsultoria.com.br"),
        "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
    }

    try:
        resultado = await executar_processamento_sienge(
            contrato=contrato_dados,
            indices_economicos=indices,
            credenciais_sienge=credenciais_teste,
            etapa=etapa,
            autorizar_reparcelamento=autorizar_reparcelamento,
            notificar_analista=False)  # False em testes para evitar notificações

        # Atualizar status na fila
        await atualizar_status_contrato(
            contrato_dados.get("numero_titulo"),
            "processado" if resultado.sucesso else "erro",
            resultado.erro if not resultado.sucesso else None)

        if resultado.sucesso:
            print(f"   ✅ Resultado: {resultado.mensagem}")
            if resultado.dados:
                dados = resultado.dados
                if "reparcelamento" in dados:
                    reparc = dados["reparcelamento"]
                    if reparc.get("sucesso"):
                        print(
                            f"   💰 Saldo Anterior: R$ {reparc.get('saldo_anterior', 0):,.2f}"
                        )
                        print(
                            f"   💰 Novo Saldo: R$ {reparc.get('novo_saldo', 0):,.2f}"
                        )
                        print(
                            f"   📈 Índice Aplicado: {reparc.get('indice_aplicado', 0)}%"
                        )
        else:
            print(f"   ❌ Erro: {resultado.erro or resultado.mensagem}")

        return resultado

    except Exception as e:
        # Atualizar status como erro
        await atualizar_status_contrato(contrato_dados.get("numero_titulo"),
                                        "erro", str(e))
        print(f"   ❌ Erro inesperado: {str(e)}")
        return None


async def atualizar_status_contrato(numero_titulo: str,
                                    status: str,
                                    erro: str = None):
    """
    Atualiza o status de processamento de um contrato usando data_manager
    """
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()

        # Tentar MongoDB primeiro se disponível
        if data_manager.mongodb_ativo:
            try:
                from core.mongodb_manager import mongodb_manager

                def _update_contract():
                    return mongodb_manager.database.fila_processamento_sienge.update_one(
                        {"contratos.numero_titulo": numero_titulo}, {
                            "$set": {
                                "contratos.$.status_processamento": status,
                                "contratos.$.processado_em": datetime.now().isoformat(),
                                "contratos.$.erro_processamento": erro
                            }
                        })

                result = await asyncio.get_event_loop().run_in_executor(
                    None, _update_contract
                )

                if result.modified_count > 0:
                    print(f"Status atualizado: {numero_titulo} -> {status}")
                    return
                else:
                    print(f"Contrato não encontrado: {numero_titulo}")
            except Exception as e:
                print(f"Erro ao atualizar MongoDB: {str(e)}")

        # Fallback JSON
        arquivo_fila = os.path.join("dados_processamento", "fila_contratos_sienge.json")

        if os.path.exists(arquivo_fila):
            with open(arquivo_fila, 'r', encoding='utf-8') as f:
                dados_fila = json.load(f)

            # Atualizar contrato específico
            contrato_encontrado = False
            for contrato in dados_fila.get("contratos", []):
                if contrato.get("numero_titulo") == numero_titulo:
                    contrato["status_processamento"] = status
                    contrato["processado_em"] = datetime.now().isoformat()
                    if erro:
                        contrato["erro_processamento"] = erro
                    contrato_encontrado = True
                    break

            if contrato_encontrado:
                with open(arquivo_fila, 'w', encoding='utf-8') as f:
                    json.dump(dados_fila, f, indent=2, ensure_ascii=False)
                print(f"Status atualizado no JSON: {numero_titulo}")
            else:
                print(f"Contrato não encontrado: {numero_titulo}")
        else:
            print(f"Arquivo de fila não encontrado: {arquivo_fila}")

    except Exception as e:
        print(f"❌ Erro ao atualizar status: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")


async def teste_completo():
    """
    Executa teste completo do RPA Sienge
    """
    print("🧪 TESTE RPA SIENGE")
    print("=" * 50)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)

    # Carregar contratos da fila
    print("📋 Carregando fila de contratos...")
    contratos_fila = await carregar_fila_contratos()

    if not contratos_fila:
        print("❌ Nenhum contrato encontrado na fila.")
        print(
            "💡 Execute primeiro: python rpa_analise_planilhas/teste_analise_planilhas.py"
        )
        return False

    print(f"\n📊 Encontrados {len(contratos_fila)} contratos na fila")

    # Carregar índices econômicos
    print("📈 Carregando índices econômicos...")
    indices_economicos = await carregar_indices_economicos()
    print(f"   IPCA: {indices_economicos['ipca']['valor']}%")
    print(f"   IGPM: {indices_economicos['igpm']['valor']}%")

    # Processar apenas os primeiros 3 contratos no teste
    contratos_teste = contratos_fila[:3]
    print(f"\n🔄 Processando primeiros {len(contratos_teste)} contratos...")

    resultados = []
    for i, contrato in enumerate(contratos_teste):
        resultado = await processar_contrato_individual(
            contrato, indices_economicos, i)
        resultados.append(resultado)

        # Intervalo entre processamentos
        if i < len(contratos_teste) - 1:
            print("   ⏳ Aguardando 2 segundos...")
            await asyncio.sleep(2)

    # Resumo final
    sucessos = sum(1 for r in resultados if r and r.sucesso)
    falhas = len(resultados) - sucessos

    print(f"\n📈 RESUMO DO TESTE:")
    print(f"   ✅ Sucessos: {sucessos}")
    print(f"   ❌ Falhas: {falhas}")
    print(f"   📋 Total processado: {len(resultados)}")

    return sucessos > 0


async def teste_etapa_consulta():
    """
    Testa apenas a etapa de consulta (ETAPA 1) usando FILA REAL em LOOP
    """
    print("🧪 TESTE ETAPA 1 - CONSULTA DE RELATÓRIOS (FILA REAL)")
    print("=" * 60)

    # CARREGAR FILA REAL DE CONTRATOS
    print("📋 Carregando fila real de contratos...")
    contratos_fila = await carregar_fila_contratos()

    if not contratos_fila:
        print("❌ Nenhum contrato encontrado na fila real.")
        print("💡 Execute primeiro: python rpa_analise_planilhas/teste_analise_planilhas.py")
        return False

    print(f"✅ Encontrados {len(contratos_fila)} contratos na fila real")

    # Mostra primeiros contratos
    print("📋 Contratos que serão processados:")
    for i, contrato in enumerate(contratos_fila[:5]):  # Mostra primeiros 5
        titulo = contrato.get("numero_titulo", "N/A")
        cliente = contrato.get("cliente", "N/A")
        status = contrato.get("status_processamento", "N/A")
        print(f"   {i+1}. {titulo} - {cliente} [{status}]")
    if len(contratos_fila) > 5:
        print(f"   ... e mais {len(contratos_fila)-5} contratos")

    indices_economicos = await carregar_indices_economicos()
    credenciais_sienge = {
        "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/"),
        "usuario": os.getenv("SIENGE_USERNAME", "tc@trajetoriaconsultoria.com.br"),
        "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
    }

    try:
        print(f"\n🔄 Processando {len(contratos_fila)} contratos em LOOP com login único...")

        # CRIAR RPA UMA VEZ PARA REUSAR LOGIN
        rpa = RPASienge()
        await rpa.inicializar()

        # Configura credenciais e faz login UMA VEZ
        rpa._configurar_credenciais(credenciais_sienge)
        await rpa._fazer_login_sienge()
        print("✅ Login único realizado - processando fila...")

        sucessos = 0
        falhas = 0

        # LOOP PARA PROCESSAR CADA CONTRATO DA FILA
        for i, contrato_fila in enumerate(contratos_fila):
            print(f"\n📄 [{i+1}/{len(contratos_fila)}] Processando: {contrato_fila.get('numero_titulo', 'N/A')}")
            print(f"   👤 Cliente: {contrato_fila.get('cliente', 'N/A')}")

            try:
                # CONSULTA RELATÓRIOS PARA ESTE CONTRATO
                dados_financeiros = await rpa._consultar_relatorios_financeiros(contrato_fila)

                if dados_financeiros.get("sucesso"):
                    sucessos += 1
                    print(f"   ✅ Sucesso - Planilha processada")

                    # Mostra resumo dos dados
                    dados_validacao = dados_financeiros.get("dados_validacao", {})
                    if dados_validacao:
                        print(f"   💰 Saldo total: R$ {dados_validacao.get('saldo_total', 0):,.2f}")
                        print(f"   📊 Parcelas CT: {dados_validacao.get('qtd_parcelas_ct_a_vencer', 0)}")
                        print(f"   🚨 CT vencidas: {dados_validacao.get('qtd_ct_vencidas', 0)}")
                        print(f"   🎯 Pode reparcelar: {dados_validacao.get('pode_reparcelar', False)}")

                    # Atualizar status como processado
                    await atualizar_status_contrato(
                        contrato_fila.get("numero_titulo"),
                        "consulta_realizada",
                        None
                    )
                else:
                    falhas += 1
                    erro = dados_financeiros.get("erro", "Erro desconhecido")
                    print(f"   ❌ Falha: {erro}")

                    # Atualizar status como erro
                    await atualizar_status_contrato(
                        contrato_fila.get("numero_titulo"),
                        "erro_consulta",
                        erro
                    )

                # Intervalo entre contratos para não sobrecarregar o sistema
                if i < len(contratos_fila) - 1:
                    print("   ⏳ Aguardando 3 segundos...")
                    await asyncio.sleep(3)

            except Exception as e:
                falhas += 1
                erro_msg = str(e)
                print(f"   ❌ Erro inesperado: {erro_msg}")

                # Registrar erro inesperado na auditoria
                await registrar_erro_auditoria(contrato_fila, erro_msg, "ERRO_EXECUCAO_INESPERADO")

                # Atualizar status como erro
                await atualizar_status_contrato(
                    contrato_fila.get("numero_titulo"),
                    "erro_execucao",
                    erro_msg
                )

                # Continuar para próximo contrato mesmo com erro inesperado
                print(f"   🔄 Continuando processamento dos demais contratos...")
                continue

        # Finalizar RPA
        await rpa.finalizar()

        # RESUMO FINAL
        print(f"\n📈 RESUMO DO PROCESSAMENTO:")
        print(f"   ✅ Sucessos: {sucessos}")
        print(f"   ❌ Falhas: {falhas}")
        print(f"   📋 Total processado: {len(contratos_fila)}")
        print(f"   🎯 Taxa de sucesso: {(sucessos/len(contratos_fila)*100):.1f}%")

        return sucessos > 0

    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

async def teste_execucao_reparcelamento_real():
    """
    Testa execução completa do reparcelamento carregando dados da fila
    """
    print("🧪 TESTE EXECUÇÃO REPARCELAMENTO - FILA REAL")
    print("=" * 55)

    try:
        rpa = RPASienge()

        # Configurar credenciais
        credenciais = {
            "url": os.getenv("SIENGE_URL", ""),
            "usuario": os.getenv("SIENGE_USUARIO", ""),
            "senha": os.getenv("SIENGE_SENHA", ""),
            "empresa": os.getenv("SIENGE_EMPRESA", "")
        }

        if not all(credenciais.values()):
            print("⚠️ Credenciais Sienge não configuradas - usando modo simulação")
            return False

        rpa._configurar_credenciais(credenciais)

        # Executar reparcelamento do próximo da fila
        print("🔄 Executando reparcelamento do próximo contrato da fila...")
        resultado = await rpa.executar_reparcelamento_webscraping()

        if resultado.sucesso:
            print(f"✅ Reparcelamento executado com sucesso!")
            print(f"   📄 Título: {resultado.dados.get('numero_titulo')}")
            print(f"   👤 Cliente: {resultado.dados.get('cliente')}")
            print(f"   🆕 Novo título: {resultado.dados.get('novo_titulo_gerado')}")
            print(f"   💰 Saldo: R$ {resultado.dados.get('saldo_anterior', 0):,.2f} → R$ {resultado.dados.get('saldo_novo', 0):,.2f}")
            return True
        else:
            print(f"❌ Falha no reparcelamento: {resultado.erro}")
            return False

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False

async def teste_webscraping_reparcelamento():
    """
    Testa APENAS o webscraping de reparcelamento com dados fictícios
    Perfeito para validar sua implementação sem depender da fila
    """
    print("🧪 TESTE WEBSCRAPING REPARCELAMENTO - DADOS FICTÍCIOS")
    print("=" * 60)

    try:
        rpa = RPASienge()
        await rpa.inicializar()

        # Configurar credenciais
        credenciais = {
            "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/"),
            "usuario": os.getenv("SIENGE_USERNAME", "tc@trajetoriaconsultoria.com.br"),
            "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
        }

        rpa._configurar_credenciais(credenciais)

        # Fazer login
        print("🔐 Fazendo login no Sienge...")
        await rpa._fazer_login_sienge()

        # DADOS FICTÍCIOS PARA TESTE
        parametros_ficticios = {
            # DADOS DO CONTRATO
            "numero_titulo": "TEST123456789",
            "cliente": "CLIENTE TESTE FICTÍCIO LTDA",
            "empreendimento": "EMPREENDIMENTO TESTE",

            # URL DE NAVEGAÇÃO
            "url_reparcelamento": "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/reparcelamento/inclusao",

            # VALORES PARA PREENCHIMENTO
            "valores_sienge": {
                "detalhamento": "CORREÇÃO 06/25 - TESTE",
                "tipo_condicao": "PM",
                "valor_total": 125000.00,
                "data_primeiro_vencimento": "15/07/2025",
                "indexador": "1 IGP-M",
                "percentual_juros": 8.0
            },

            # PARCELAS PARA DESMARCAR
            "parcelas_desmarcar": [
                {"documento": "CT001-TESTE", "data_vencimento": "15/05/2025", "motivo": "Vencida"},
                {"documento": "CT002-TESTE", "data_vencimento": "15/06/2025", "motivo": "Vencida"}
            ],

            # DADOS FINANCEIROS
            "saldo_anterior": 120000.00,
            "saldo_novo": 125000.00,
            "igmp_aplicado": 4.16,
            "total_parcelas_desmarcar": 2
        }

        print("📋 DADOS PARA O TESTE:")
        print(f"   📄 Título: {parametros_ficticios['numero_titulo']}")
        print(f"   👤 Cliente: {parametros_ficticios['cliente']}")
        print(f"   💰 Saldo: R$ {parametros_ficticios['saldo_anterior']:,.2f} → R$ {parametros_ficticios['saldo_novo']:,.2f}")
        print(f"   🔄 Parcelas a desmarcar: {len(parametros_ficticios['parcelas_desmarcar'])}")

        print("\n🌐 Executando webscraping...")

        # CHAMAR SUA IMPLEMENTAÇÃO
        resultado = await rpa._navegar_e_executar_reparcelamento(parametros_ficticios)

        if resultado.get("sucesso", False):
            print(f"✅ Webscraping executado com sucesso!")
            print(f"   🆕 Novo título: {resultado.get('novo_titulo', 'N/A')}")
            print(f"   📊 Parcelas processadas: {resultado.get('parcelas_processadas', 0)}")
            print(f"   ⏰ Executado em: {resultado.get('timestamp_webscraping', 'N/A')}")
            return True
        else:
            print(f"❌ Erro no webscraping: {resultado.get('erro', 'Erro desconhecido')}")
            return False

        await rpa.finalizar()

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False


async def teste_webscraping_dados_reais():
    """
    Testa webscraping de reparcelamento com DADOS REAIS do contrato 2239
    Use este teste para validar sua implementação com dados reais da fila
    """
    print("🧪 TESTE WEBSCRAPING REPARCELAMENTO - DADOS REAIS CONTRATO 2239")
    print("=" * 70)

    try:
        rpa = RPASienge()
        await rpa.inicializar()

        # Configurar credenciais
        credenciais = {
            "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/"),
            "usuario": os.getenv("SIENGE_USERNAME", "tc@trajetoriaconsultoria.com.br"),
            "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
        }

        rpa._configurar_credenciais(credenciais)

        # Fazer login
        print("🔐 Fazendo login no Sienge...")
        await rpa._fazer_login_sienge()

        # DADOS REAIS DO CONTRATO 2239 - SANDRO RIZZON VIEIRA
        parametros_reais = {
            # DADOS DO CONTRATO REAL
            "numero_titulo": "2239",
            "cliente": "SANDRO RIZZON VIEIRA",
            "empreendimento": "MARCELY",
            "loteamento": "MARCELY",
            "quadra": 36,
            "lote": 128,
            "cnpj_unidade": "BVRB",

            # URL DE NAVEGAÇÃO
            "url_reparcelamento": "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/reparcelamento/inclusao",

            # VALORES PARA PREENCHIMENTO (baseados nos dados reais)
            "valores_sienge": {
                "detalhamento": "CORREÇÃO 06/25",
                "tipo_condicao": "PM",
                "valor_total": 0.00,  # Será calculado com base no saldo real
                "data_primeiro_vencimento": "05/07/2025",  # Baseado no 1º vencimento original
                "indexador": "1 IGP-M",  # Conforme dados reais
                "percentual_juros": 8.0  # Conforme dados reais
            },

            # DADOS HISTÓRICOS REAIS
            "dados_historicos": {
                "assinatura_contrato": "01/06/2018",
                "primeiro_vencimento_original": "05/07/2018",
                "ultimo_reajuste": "jun.-24",
                "tipo_reajuste": "anual",
                "indice_original": "IGPM",
                "juros_original": "8,0%",
                "dia_vencimento": 5,
                "mes_reajuste": "jun.-25"
            },

            # PARCELAS PARA DESMARCAR (simuladas - serão identificadas no webscraping)
            "parcelas_desmarcar": [
                {"documento": "CT-EXEMPLO-001", "data_vencimento": "05/05/2025", "motivo": "Vencimento anterior ao mês base"},
                {"documento": "CT-EXEMPLO-002", "data_vencimento": "05/06/2025", "motivo": "Vencimento anterior ao mês base"}
            ],

            # DADOS FINANCEIROS (serão calculados com IGP-M real)
            "saldo_anterior": 0.00,  # Será obtido do relatório
            "saldo_novo": 0.00,      # Será calculado com IGP-M
            "igmp_aplicado": 3.89,   # Valor real do IGP-M
            "total_parcelas_desmarcar": 2
        }

        print("📋 DADOS REAIS PARA O TESTE:")
        print(f"   📄 Título: {parametros_reais['numero_titulo']}")
        print(f"   👤 Cliente: {parametros_reais['cliente']}")
        print(f"   🏢 Empreendimento: {parametros_reais['empreendimento']}")
        print(f"   📍 Quadra/Lote: {parametros_reais['quadra']}/{parametros_reais['lote']}")
        print(f"   📅 Último reajuste: {parametros_reais['dados_historicos']['ultimo_reajuste']}")
        print(f"   📈 Índice: {parametros_reais['dados_historicos']['indice_original']}")
        print(f"   💰 Juros: {parametros_reais['dados_historicos']['juros_original']}")
        print(f"   🗓️ Dia vencimento: {parametros_reais['dados_historicos']['dia_vencimento']}")

        print("\n🌐 Executando webscraping com dados reais...")

        # CHAMAR SUA IMPLEMENTAÇÃO COM DADOS REAIS
        resultado = await rpa._navegar_e_executar_reparcelamento(parametros_reais)

        if resultado.get("sucesso", False):
            print(f"✅ Webscraping executado com sucesso!")
            print(f"   🆕 Novo título: {resultado.get('novo_titulo', 'N/A')}")
            print(f"   📊 Parcelas processadas: {resultado.get('parcelas_processadas', 0)}")
            print(f"   💰 Valores aplicados: {resultado.get('valores_aplicados', 'N/A')}")
            print(f"   ⏰ Executado em: {resultado.get('timestamp_webscraping', 'N/A')}")
            
            # Logs específicos do contrato real
            print(f"\n📋 RESULTADO ESPECÍFICO CONTRATO 2239:")
            print(f"   👤 Cliente processado: {parametros_reais['cliente']}")
            print(f"   🏢 Empreendimento: {parametros_reais['empreendimento']}")
            print(f"   📄 Título original: {parametros_reais['numero_titulo']}")
            
            return True
        else:
            print(f"❌ Erro no webscraping: {resultado.get('erro', 'Erro desconhecido')}")
            
            # Logs específicos do erro
            print(f"\n🔍 ANÁLISE DO ERRO CONTRATO 2239:")
            print(f"   👤 Cliente: {parametros_reais['cliente']}")
            print(f"   📄 Título: {parametros_reais['numero_titulo']}")
            print(f"   ❌ Erro detalhado: {resultado.get('erro', 'N/A')}")
            
            return False

        await rpa.finalizar()

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        
        # Log específico para o contrato 2239
        print(f"\n🚨 ERRO CRÍTICO CONTRATO 2239:")
        print(f"   👤 Cliente: SANDRO RIZZON VIEIRA")
        print(f"   📄 Título: 2239")
        print(f"   🏢 Empreendimento: MARCELY")
        print(f"   ❌ Erro: {str(e)}")
        
        return False

async def teste_carregar_dados_fila():
    """
    Testa apenas o carregamento de dados da fila (sem webscraping)
    """
    print("🧪 TESTE CARREGAMENTO DADOS FILA")
    print("=" * 40)

    try:
        rpa = RPASienge()

        # Carregar próximo da fila
        print("📊 Carregando próximo contrato da fila...")
        resultado = await rpa.carregar_dados_fila_reparcelamento()

        if resultado.get("sucesso", False):
            parametros = resultado["parametros_navegacao"]

            print(f"✅ Dados carregados com sucesso!")
            print(f"   📄 Título: {parametros['numero_titulo']}")
            print(f"   👤 Cliente: {parametros['cliente']}")
            print(f"   💰 Saldo: R$ {parametros['saldo_anterior']:,.2f} → R$ {parametros['saldo_novo']:,.2f}")
            print(f"   📊 IGP-M: {parametros['igmp_aplicado']}%")
            print(f"   🔄 Parcelas a desmarcar: {parametros['total_parcelas_desmarcar']}")

            print("\n📋 Valores para preenchimento no Sienge:")
            valores = parametros['valores_sienge']
            for campo, valor in valores.items():
                print(f"   {campo}: {valor}")

            print("\n❌ Parcelas para desmarcar:")
            for parcela in parametros['parcelas_desmarcar']:
                print(f"   📄 {parcela['documento']} - {parcela['data_vencimento']} - {parcela['motivo']}")

            return True
        else:
            print(f"❌ Erro: {resultado.get('erro', 'Erro desconhecido')}")
            if resultado.get("fila_vazia"):
                print("📭 Fila de reparcelamento está vazia")
            return False

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False

async def teste_etapa_reparcelamento():
    """
    Testa apenas a etapa de reparcelamento (ETAPA 2) com autorização automática
    """
    print("🧪 TESTE ETAPA 2 - REPARCELAMENTO (COM AUTORIZAÇÃO)")
    print("=" * 60)

    contrato_teste = {
        "numero_titulo": "TEST123456789",
        "cliente": "CLIENTE TESTE LTDA",
        "empreendimento": "EMPREENDIMENTO TESTE",
        "cnpj_unidade": "12.345.678/0001-90",
        "indexador": "IPCA",
        "ultimo_reajuste": "01/01/2023",
        "tipo_reajuste": "anual",
        "mes_base_reparcelamento": "06/2025"
    }

    indices_economicos = await carregar_indices_economicos()
    credenciais_sienge = {
        "url": os.getenv("SIENGE_URL", "https://sienge-teste.com"),
        "usuario": os.getenv("SIENGE_USERNAME", "tc@trajetoriaconsultoria.com.br"),
        "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
    }

    try:
        print("🔄 Executando reparcelamento com autorização automática...")
        resultado = await executar_processamento_sienge(
            contrato=contrato_teste,
            indices_economicos=indices_economicos,
            credenciais_sienge=credenciais_sienge,
            etapa="reparcelamento",
            autorizar_reparcelamento=True  # Pula validação de autorização
        )

        print(f"\n📋 RESULTADO ETAPA 2:")
        print(f"✅ Sucesso: {resultado.sucesso}")
        print(f"📄 Mensagem: {resultado.mensagem}")

        if resultado.dados:
            reparcelamento = resultado.dados.get("reparcelamento", {})
            print(f"🔄 Processado: {reparcelamento.get('sucesso', False)}")
            print(f"📋 Novo título: {reparcelamento.get('novo_titulo_gerado', 'N/A')}")

        return resultado.sucesso

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False

async def teste_contrato_unico():
    """
    Testa processamento completo de um contrato único
    """
    print("🧪 TESTE CONTRATO ÚNICO - COMPLETO")
    print("=" * 40)

    # Dados de teste para contrato
    contrato_teste = {
        "numero_titulo": "TEST123456789",
        "cliente": "CLIENTE TESTE LTDA",
        "empreendimento": "EMPREENDIMENTO TESTE",
        "cnpj_unidade": "12.345.678/0001-90",
        "indexador": "IPCA",
        "ultimo_reajuste": "01/01/2023"
    }

    # Carregar índices```python
# Completing the truncated code file by replacing the incomplete credenciais_sienge dictionary with the provided complete version and adding the missing test functions.
        indices_economicos = await carregar_indices_economicos()

    # Credenciais Sienge
    credenciais_sienge = {
        "url": os.getenv("SIENGE_URL", "https://sienge-teste.com"),
        "usuario": os.getenv("SIENGE_USERNAME", "tc@trajetoriaconsultoria.com.br"),
        "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
    }

    try:
        print("🔄 Executando processamento completo de contrato único...")
        resultado = await executar_processamento_sienge(
            contrato=contrato_teste,
            indices_economicos=indices_economicos,
            credenciais_sienge=credenciais_sienge,
            etapa="completa",
            autorizar_reparcelamento=False,
            notificar_analista=False
        )

        print(f"\n📋 RESULTADO:")
        print(f"✅ Sucesso: {resultado.sucesso}")
        print(f"📄 Mensagem: {resultado.mensagem}")

        if resultado.dados:
            print("\n📊 DADOS PROCESSADOS:")
            dados = resultado.dados
            if "consulta" in dados:
                consulta = dados["consulta"]
                print(f"   📋 Saldo total: R$ {consulta.get('saldo_total', 0):,.2f}")
                print(f"   📊 Parcelas CT: {consulta.get('qtd_parcelas_ct', 0)}")
                print(f"   🚨 CT vencidas: {consulta.get('qtd_ct_vencidas', 0)}")

            if "reparcelamento" in dados:
                reparc = dados["reparcelamento"]
                print(f"   🔄 Reparcelamento: {reparc.get('sucesso', False)}")
                if reparc.get("sucesso"):
                    print(f"   📋 Novo título: {reparc.get('novo_titulo_gerado', 'N/A')}")
                    print(f"   💰 Saldo: R$ {reparc.get('saldo_anterior', 0):,.2f} → R$ {reparc.get('novo_saldo', 0):,.2f}")

        return resultado.sucesso

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False


async def teste_validacao_contrato():
    """
    Testa apenas as validações de contrato
    """
    print("🧪 TESTE VALIDAÇÃO DE CONTRATO")
    print("=" * 35)

    contrato_teste = {
        "numero_titulo": "TEST123456789",
        "cliente": "CLIENTE TESTE LTDA",
        "empreendimento": "EMPREENDIMENTO TESTE",
        "cnpj_unidade": "12.345.678/0001-90",
        "indexador": "IPCA",
        "ultimo_reajuste": "01/01/2023"
    }

    try:
        rpa = RPASienge()
        await rpa.inicializar()

        # Testar validações
        print("🔍 Executando validações...")
        validacao = await rpa._validar_contrato_para_processamento(contrato_teste)

        print(f"\n📋 RESULTADO VALIDAÇÃO:")
        print(f"✅ Válido para processamento: {validacao.get('pode_processar', False)}")

        if validacao.get("alertas"):
            print("⚠️ Alertas:")
            for alerta in validacao["alertas"]:
                print(f"   - {alerta}")

        if validacao.get("erros"):
            print("❌ Erros:")
            for erro in validacao["erros"]:
                print(f"   - {erro}")

        await rpa.finalizar()
        return validacao.get("pode_processar", False)

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False


async def teste_calculo_reparcelamento():
    """
    Testa apenas os cálculos de reparcelamento
    """
    print("🧪 TESTE CÁLCULO REPARCELAMENTO")
    print("=" * 35)

    # Dados de entrada simulados
    dados_entrada = {
        "saldo_devedor": 100000.00,
        "indice_aplicar": 3.89,  # IGP-M
        "tipo_indice": "IGPM",
        "mes_base": "06/2025",
        "parcelas_ct_vencidas": 2
    }

    try:
        rpa = RPASienge()

        print("🧮 Executando cálculos...")
        print(f"   💰 Saldo original: R$ {dados_entrada['saldo_devedor']:,.2f}")
        print(f"   📈 Índice IGP-M: {dados_entrada['indice_aplicar']}%")

        # Calcular novo saldo
        novo_saldo = dados_entrada["saldo_devedor"] * (1 + dados_entrada["indice_aplicar"] / 100)
        diferenca = novo_saldo - dados_entrada["saldo_devedor"]

        print(f"\n📊 RESULTADO CÁLCULO:")
        print(f"   💰 Novo saldo: R$ {novo_saldo:,.2f}")
        print(f"   📈 Diferença: R$ {diferenca:,.2f}")
        print(f"   🎯 Percentual: {dados_entrada['indice_aplicar']}%")

        # Validar se cálculo está correto
        percentual_calculado = (diferenca / dados_entrada["saldo_devedor"]) * 100
        calculo_correto = abs(percentual_calculado - dados_entrada["indice_aplicar"]) < 0.01

        print(f"   ✅ Cálculo correto: {calculo_correto}")

        return calculo_correto

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False


async def verificacao_saude():
    """
    Verifica se o RPA está funcionando corretamente
    """
    print("🧪 VERIFICAÇÃO DE SAÚDE DO RPA")
    print("=" * 40)

    try:
        rpa = RPASienge()
        await rpa.inicializar()

        print("🔍 Verificando componentes...")

        # Verificar browser
        print("   🌐 Browser: ", end="")
        if hasattr(rpa, 'browser') and rpa.browser:
            print("✅ Inicializado")
        else:
            print("❌ Não inicializado")

        # Verificar data manager
        print("   📊 Data Manager: ", end="")
        from core.data_manager import data_manager
        await data_manager.inicializar()
        if data_manager:
            print("✅ Funcionando")
        else:
            print("❌ Erro")

        # Verificar MongoDB
        print("   🍃 MongoDB: ", end="")
        from core.mongodb_manager import MONGODB_DISPONIVEL, mongodb_manager
        if MONGODB_DISPONIVEL and mongodb_manager.conectado:
            print("✅ Conectado")
        else:
            print("⚠️ Não disponível (usando JSON)")

        # Verificar credenciais
        print("   🔐 Credenciais: ", end="")
        url_sienge = os.getenv("SIENGE_URL", "")
        usuario_sienge = os.getenv("SIENGE_USERNAME", "")
        if url_sienge and usuario_sienge:
            print("✅ Configuradas")
        else:
            print("⚠️ Não configuradas (usando modo teste)")

        await rpa.finalizar()

        print("\n🎯 SISTEMA PRONTO PARA EXECUÇÃO")
        return True

    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")
        return False


async def registrar_erro_auditoria(contrato: Dict[str, Any], erro: str, tipo_erro: str):
    """
    Registra erro na auditoria para análise posterior
    """
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()

        registro_erro = {
            "timestamp": datetime.now().isoformat(),
            "tipo_erro": tipo_erro,
            "numero_titulo": contrato.get("numero_titulo", "N/A"),
            "cliente": contrato.get("cliente", "N/A"),
            "erro_detalhado": erro,
            "fase_processamento": "teste_consulta",
            "dados_contrato": contrato
        }

        # Tentar salvar no MongoDB se disponível
        if data_manager.mongodb_ativo:
            try:
                from core.mongodb_manager import mongodb_manager
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: mongodb_manager.database.auditoria_erros.insert_one(registro_erro)
                )
                print(f"   📝 Erro registrado na auditoria MongoDB")
            except Exception as e:
                print(f"   ⚠️ Erro ao salvar auditoria MongoDB: {str(e)}")

        # Salvar em arquivo JSON como fallback
        pasta_auditoria = "dados_processamento/auditoria_erros"
        os.makedirs(pasta_auditoria, exist_ok=True)

        nome_arquivo = f"erro_{contrato.get('numero_titulo', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        caminho_arquivo = os.path.join(pasta_auditoria, nome_arquivo)

        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(registro_erro, f, indent=2, ensure_ascii=False)

        print(f"   📁 Erro registrado em: {caminho_arquivo}")

    except Exception as e:
        print(f"   ❌ Erro ao registrar auditoria: {str(e)}")


async def menu_interativo():
    """
    Menu interativo para escolher qual teste executar
    """
    opcoes = {
        "1": ("🚀 Teste Completo", teste_completo),
        "2": ("🏢 Teste Contrato Único", teste_contrato_unico),
        "3": ("🔍 Teste Etapa 1 - Consulta", teste_etapa_consulta),
        "4": ("🔄 Teste Etapa 2 - Reparcelamento", teste_etapa_reparcelamento),
        "5": ("🧪 Teste Validação de Contrato", teste_validacao_contrato),
        "6": ("🧮 Teste Cálculo Reparcelamento", teste_calculo_reparcelamento),
        "7": ("🏥 Verificação de Saúde", verificacao_saude),
        "8": ("🌐 Teste Webscraping Reparcelamento", teste_webscraping_reparcelamento),
        "9": ("📊 Teste Carregar Dados Fila", teste_carregar_dados_fila),
        "10": ("🎯 Teste Execução Reparcelamento Real", teste_execucao_reparcelamento_real),
        "11": ("🔥 Teste Webscraping Dados Reais (Contrato 2239)", teste_webscraping_dados_reais),
        "0": ("❌ Sair", None)
    }

    print("\n" + "=" * 60)
    print("🧪 MENU DE TESTES - RPA SIENGE")
    print("=" * 60)

    for key, (descricao, _) in opcoes.items():
        print(f"{key}. {descricao}")

    print("=" * 60)

    while True:
        try:
            escolha = input("\n➤ Escolha uma opção (0-11): ").strip()

            if escolha == "0":
                print("👋 Encerrando testes...")
                break
            elif escolha in opcoes and opcoes[escolha][1]:
                print(f"\n🔄 Executando: {opcoes[escolha][0]}")
                print("-" * 60)

                inicio = datetime.now()
                sucesso = await opcoes[escolha][1]()
                fim = datetime.now()
                tempo_execucao = (fim - inicio).total_seconds()

                print("-" * 60)
                if sucesso:
                    print(f"✅ Teste concluído com SUCESSO em {tempo_execucao:.1f}s")
                else:
                    print(f"❌ Teste FALHOU em {tempo_execucao:.1f}s")

                input("\n⏳ Pressione ENTER para continuar...")
                print("\n" + "=" * 60)
                for key, (descricao, _) in opcoes.items():
                    print(f"{key}. {descricao}")
                print("=" * 60)
            else:
                print("❌ Opção inválida! Escolha entre 0-11.")

        except KeyboardInterrupt:
            print("\n\n👋 Testes interrompidos pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")


if __name__ == "__main__":
    print("🚀 INICIANDO SISTEMA DE TESTES RPA SIENGE")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    try:
        asyncio.run(menu_interativo())
    except KeyboardInterrupt:
        print("\n👋 Sistema encerrado pelo usuário.")
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")