#!/usr/bin/env python3
"""
Teste Independente - RPA Sienge
Permite testar o RPA fora da orquestração Temporal para desenvolvimento e homologação

Desenvolvido em Português Brasileiro
"""

from rpa_sienge.rpa_sienge import RPASienge
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
        await data_manager.inicializar()
        
        print("🔍 Carregando fila de contratos...")
        print(f"   MongoDB ativo: {data_manager.mongodb_ativo}")
        
        # Usa o método unificado do data_manager
        fila_dados = await data_manager.obter_fila_sienge()
        
        if fila_dados and fila_dados.get("contratos"):
            contratos = fila_dados.get("contratos", [])
            total = len(contratos)
            
            if data_manager.mongodb_ativo:
                print(f"📊 Fila carregada do MongoDB: {total} contratos")
            else:
                print(f"📄 Fila carregada do JSON: {total} contratos")
                
            # Debug: mostra alguns contratos
            if total > 0:
                print("📋 Primeiros contratos na fila:")
                for i, contrato in enumerate(contratos[:3]):
                    titulo = contrato.get("numero_titulo", "N/A")
                    cliente = contrato.get("cliente", "N/A")
                    status = contrato.get("status_processamento", "N/A")
                    print(f"   {i+1}. {titulo} - {cliente} [{status}]")
                if total > 3:
                    print(f"   ... e mais {total-3} contratos")
            
            return contratos
        else:
            print("⚠️ Fila vazia ou não encontrada")
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
                indices_doc = await mongodb_manager.database.indices_economicos.find_one(
                    {}, sort=[("timestamp_coleta", -1)]  # Mais recente
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
                "tipo": "IGPM",
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
        
        print(f"📝 Atualizando status {numero_titulo}: {status}")
        
        # Tentar MongoDB primeiro se disponível
        if data_manager.mongodb_ativo:
            try:
                from core.mongodb_manager import mongodb_manager
                result = await mongodb_manager.database.fila_processamento_sienge.update_one(
                    {"contratos.numero_titulo": numero_titulo}, {
                        "$set": {
                            "contratos.$.status_processamento": status,
                            "contratos.$.processado_em": datetime.now().isoformat(),
                            "contratos.$.erro_processamento": erro
                        }
                    })
                
                if result.modified_count > 0:
                    print(f"✅ Status atualizado no MongoDB: {numero_titulo}")
                    return
                else:
                    print(f"⚠️ Contrato não encontrado no MongoDB: {numero_titulo}")
            except Exception as e:
                print(f"⚠️ Erro ao atualizar MongoDB: {str(e)}")

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
                print(f"✅ Status atualizado no JSON: {numero_titulo}")
            else:
                print(f"⚠️ Contrato não encontrado no JSON: {numero_titulo}")
        else:
            print(f"⚠️ Arquivo de fila não encontrado: {arquivo_fila}")

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
                
                # Atualizar status como erro
                await atualizar_status_contrato(
                    contrato_fila.get("numero_titulo"),
                    "erro_execucao",
                    erro_msg
                )

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

    # Carregar índices
    indices_economicos = await carregar_indices_economicos()

    # Credenciais Sienge
    credenciais_sienge = {
        "url": os.getenv("SIENGE_URL", "https://sienge-teste.com"),
        "usuario": os.getenv("SIENGE_USERNAME",
                             "tc@trajetoriaconsultoria.com.br"),
        "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
    }

    print(f"🏢 Contrato de Teste: {contrato_teste['numero_titulo']}")
    print(f"👤 Cliente: {contrato_teste['cliente']}")
    print(f"🔐 URL Sienge: {credenciais_sienge['url']}")
    print()

    try:
        print("🚀 Iniciando execução do RPA...")
        resultado = await executar_processamento_sienge(
            contrato=contrato_teste,
            indices_economicos=indices_economicos,
            credenciais_sienge=credenciais_sienge,
            etapa="completa",
            autorizar_reparcelamento=True,  # Para teste
            notificar_analista=False)

        # Mostra resultado
        print("\n📋 RESULTADO DA EXECUÇÃO:")
        print("-" * 30)
        print(f"Sucesso: {'✅ SIM' if resultado.sucesso else '❌ NÃO'}")
        print(f"Mensagem: {resultado.mensagem}")

        if resultado.tempo_execucao:
            print(f"Tempo: {resultado.tempo_execucao:.2f} segundos")

        if resultado.sucesso and resultado.dados:
            print("\n📊 DADOS PROCESSADOS:")
            dados = resultado.dados

            if "contrato_processado" in dados:
                contrato = dados["contrato_processado"]
                print(f"   Contrato: {contrato.get('numero_titulo', 'N/A')}")
                print(f"   Cliente: {contrato.get('cliente', 'N/A')}")

            if "reparcelamento" in dados:
                reparc = dados["reparcelamento"]
                if reparc.get("sucesso"):
                    print(
                        f"   Saldo Anterior: R$ {reparc.get('saldo_anterior', 0):,.2f}"
                    )
                    print(
                        f"   Novo Saldo: R$ {reparc.get('novo_saldo', 0):,.2f}"
                    )
                    print(
                        f"   Índice Aplicado: {reparc.get('indice_aplicado', 0)}%"
                    )
                    print(f"   Parcelas: {reparc.get('parcelas_total', 0)}")

            if "carne_gerado" in dados:
                carne = dados["carne_gerado"]
                if carne and carne.get("sucesso"):
                    print(f"   Carnê: {carne.get('nome_arquivo', 'N/A')}")

        if not resultado.sucesso:
            print(f"\n❌ ERRO: {resultado.erro or 'Erro desconhecido'}")

        return resultado.sucesso

    except Exception as e:
        print(f"\n💥 ERRO INESPERADO: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")
        return False


async def teste_validacao_contrato():
    """
    Testa apenas a validação de contrato
    """
    print("🧪 TESTE DE VALIDAÇÃO - CONTRATO")
    print("=" * 40)

    try:
        rpa = RPASienge()

        # Simula dados financeiros adimplente
        dados_financeiros_ok = {
            "cliente": "CLIENTE TESTE",
            "numero_titulo": "123456",
            "saldo_devedor": 150000.00,
            "parcelas_pendentes": 48,
            "parcelas_vencidas": 0,
            "pendencias_ct": [],  # Sem pendências CT
            "pendencias_rec_fat": [],
            "status": "adimplente"
        }

        # Simula dados financeiros inadimplente
        dados_financeiros_inadimplente = {
            "cliente": "CLIENTE INADIMPLENTE",
            "numero_titulo": "789012",
            "saldo_devedor": 100000.00,
            "parcelas_pendentes": 36,
            "parcelas_vencidas": 5,
            # 3 parcelas CT vencidas
            "pendencias_ct": ["CT001", "CT002", "CT003"],
            "pendencias_rec_fat": [],
            "status": "inadimplente"
        }

        # Testa cliente adimplente
        print("📊 Testando cliente adimplente...")
        validacao_ok = await rpa._validar_contrato_reparcelamento(
            dados_financeiros_ok)
        print(
            f"✅ Resultado: {validacao_ok['pode_reparcelar']} - {validacao_ok['motivo']}"
        )

        # Testa cliente inadimplente
        print("\n📊 Testando cliente inadimplente...")
        validacao_erro = await rpa._validar_contrato_reparcelamento(
            dados_financeiros_inadimplente)
        print(
            f"❌ Resultado: {validacao_erro['pode_reparcelar']} - {validacao_erro['motivo']}"
        )

        return True

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def teste_calculo_reparcelamento():
    """
    Testa apenas o cálculo de reparcelamento
    """
    print("🧪 TESTE DE CÁLCULO - REPARCELAMENTO")
    print("=" * 45)

    try:
        rpa = RPASienge()

        contrato = {
            "numero_titulo": "123456",
            "cliente": "CLIENTE TESTE",
            "indexador": "IPCA"
        }

        indices = {"ipca": {"valor": 4.62}, "igpm": {"valor": 3.89}}

        dados_financeiros = {
            "saldo_devedor": 100000.00,
            "parcelas_pendentes": 48
        }

        print("📊 Testando cálculo de reparcelamento...")
        print(f"   Saldo atual: R$ {dados_financeiros['saldo_devedor']:,.2f}")
        print(f"   Índice IPCA: {indices['ipca']['valor']}%")

        resultado = await rpa._processar_reparcelamento(
            contrato, indices, dados_financeiros)

        if resultado.get("sucesso"):
            print(f"✅ Novo saldo: R$ {resultado.get('novo_saldo', 0):,.2f}")
            print(
                f"✅ Diferença: R$ {resultado.get('diferenca_valor', 0):,.2f}")
            print(
                f"✅ Fator correção: {resultado.get('fator_correcao', 1):.4f}")
        else:
            print(f"❌ Erro no cálculo: {resultado.get('erro', 'N/A')}")

        return resultado.get("sucesso", False)

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def verificar_saude_rpa():
    """
    Verifica saúde do RPA (recursos disponíveis)
    """
    print("🧪 VERIFICAÇÃO DE SAÚDE - RPA SIENGE")
    print("=" * 40)

    try:
        rpa = RPASienge()

        print("🔧 Verificando inicialização...")
        if await rpa.inicializar():
            print("✅ Recursos inicializados com sucesso")

            # Verifica browser (se habilitado)
            if rpa.usar_browser and hasattr(rpa, 'browser') and rpa.browser:
                print("✅ Browser disponível")
            else:
                print("⚠️ Browser não configurado")

            # Verifica MongoDB (se disponível)
            if hasattr(rpa, 'mongo_manager') and rpa.mongo_manager:
                print("✅ MongoDB conectado")
            else:
                print("⚠️ MongoDB não disponível")

            await rpa.finalizar()
            return True
        else:
            print("❌ Falha na inicialização")
            return False

    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")
        return False


def menu_interativo():
    """
    Menu interativo para escolher tipo de teste
    """
    print("\n🎯 MENU DE TESTES - RPA SIENGE")
    print("=" * 50)
    print("1. 🚀 Teste Completo (Processamento Fila)")
    print("2. 🏢 Teste Contrato Único")
    print("3. 🔍 Teste Etapa 1 - Consulta")
    print("4. 🔄 Teste Etapa 2 - Reparcelamento")
    print("5. 🧪 Teste Validação de Contrato")
    print("6. 🧮 Teste Cálculo Reparcelamento")
    print("7. 🏥 Verificação de Saúde")
    print("8. ❌ Sair")
    print("=" * 50)

    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (1-6): ").strip()

            if opcao == "1":
                return teste_completo()
            elif opcao == "2":
                return teste_contrato_unico()
            elif opcao == "3":
                return teste_etapa_consulta()
            elif opcao == "4":
                return teste_etapa_reparcelamento()
            elif opcao == "5":
                return teste_validacao_contrato()
            elif opcao == "6":
                return teste_calculo_reparcelamento()
            elif opcao == "7":
                return verificar_saude_rpa()
            elif opcao == "8":
                print("👋 Encerrando testes...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 1-8.")

        except KeyboardInterrupt:
            print("\n👋 Teste interrompido pelo usuário")
            return None


async def main():
    """
    Função principal do teste
    """
    print("🤖 SISTEMA DE TESTES RPA - SIENGE")
    print("Desenvolvido em Python")
    print("Permite testar RPA independente da orquestração Temporal")

    # Verifica se é execução direta ou interativa
    if len(sys.argv) > 1:
        # Execução direta com parâmetros
        comando = sys.argv[1].lower()

        if comando == "completo":
            sucesso = await teste_completo()
        elif comando == "unico":
            sucesso = await teste_contrato_unico()
        elif comando == "consulta":
            sucesso = await teste_etapa_consulta()
        elif comando == "reparcelamento":
            sucesso = await teste_etapa_reparcelamento()
        elif comando == "validacao":
            sucesso = await teste_validacao_contrato()
        elif comando == "calculo":
            sucesso = await teste_calculo_reparcelamento()
        elif comando == "saude":
            sucesso = await verificar_saude_rpa()
        else:
            print(f"❌ Comando inválido: {comando}")
            print(
                "Comandos disponíveis: completo, unico, consulta, reparcelamento, validacao, calculo, saude"
            )
            return False

        return sucesso

    else:
        # Menu interativo
        teste_escolhido = menu_interativo()
        if teste_escolhido:
            sucesso = await teste_escolhido

            if sucesso:
                print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            else:
                print("\n❌ TESTE FALHOU!")

            return sucesso

        return True


if __name__ == "__main__":
    # Configura event loop para Windows se necessário
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Executa teste
    try:
        resultado = asyncio.run(main())

        if resultado is not None:
            sys.exit(0 if resultado else 1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n👋 Teste cancelado pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro fatal: {str(e)}")
        sys.exit(1)
