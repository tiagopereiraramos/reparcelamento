#!/usr/bin/env python3
"""
Main de emissão de carnês para processamento da Fase 2 do RPA Sienge
Sistema de geração de carnês independente

FASE 2: EMISSÃO DE CARNÊS
REPARCELADO → CARNE_GERADO

Conforme PDD Seção 10.2: Emissão de carnê + Geração de arquivos de remessa

Desenvolvido em Português Brasileiro
"""

from core.utils_sienge import (
    log,
    notificar_sucesso_simples,
    notificar_erro_simples,
    carregar_credenciais_sienge,
    get_env_or_fail
)
from rpa_sienge.rpa_sienge import RPASienge
from core.gerador_anexos import gerador_anexos
from core.templates_relatorios import templates_relatorios
import os
import sys
import asyncio
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Garante execução com browser visível para debug
os.environ["HEADLESS"] = "0"
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ARQUIVO_LOG_ATUAL: Optional[Path] = None


class LoggerMultiplo:
    """Direciona logs para stdout e arquivo do fluxo."""

    def __init__(self, *destinos):
        self.destinos = destinos

    def write(self, mensagem):
        for destino in self.destinos:
            destino.write(mensagem)

    def flush(self):
        for destino in self.destinos:
            destino.flush()


def preparar_logs_execucao():
    """Configura saída padrão para registrar logs da execução em arquivo."""
    global ARQUIVO_LOG_ATUAL

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ARQUIVO_LOG_ATUAL = LOGS_DIR / f"emissao_carnes_{timestamp}.log"

    stdout_original = sys.stdout
    stderr_original = sys.stderr

    arquivo_log = open(ARQUIVO_LOG_ATUAL, "a", encoding="utf-8")
    multilog = LoggerMultiplo(stdout_original, arquivo_log)
    sys.stdout = multilog
    sys.stderr = multilog
    log(f"📁 Log da execução: {ARQUIVO_LOG_ATUAL}")
    return arquivo_log, stdout_original, stderr_original


# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def obter_contratos_reparcelados() -> List[Dict[str, Any]]:
    """
    FASE 1: Buscar contratos com status REPARCELADO no banco

    Returns:
        Lista de contratos com status REPARCELADO
    """
    log("\n💾 FASE 1: BUSCANDO CONTRATOS REPARCELADOS NO BANCO...")
    log("=" * 60)

    try:
        # ✅ USAR MESMO PADRÃO DO alterar_status_direto.py
        from core.mongodb_manager import MongoDBManager

        # Conectar ao MongoDB
        mongo_manager = MongoDBManager()
        await mongo_manager.conectar()
        db = mongo_manager.database
        colecao = db.fila_contratos

        # Buscar contratos com status REPARCELADO
        contratos_reparcelados = list(colecao.find({"status": "REPARCELADO"}))

        if not contratos_reparcelados:
            log("⚠️ Nenhum contrato com status REPARCELADO encontrado no banco")
            return []

        log(f"✅ Encontrados {len(contratos_reparcelados)} contratos com status REPARCELADO:")
        for i, contrato in enumerate(contratos_reparcelados[:5], 1):
            codigo_cliente = contrato.get('codigo_cliente', 'N/A')
            cliente = contrato.get('cliente', 'N/A')
            numero_titulo = contrato.get('numero_titulo', 'N/A')
            log(f"   {i}. {codigo_cliente} - {cliente} (Título: {numero_titulo})")

        if len(contratos_reparcelados) > 5:
            log(f"   ... e mais {len(contratos_reparcelados) - 5} contratos")

        return contratos_reparcelados

    except Exception as e:
        log(f"❌ Erro ao buscar contratos reparcelados: {str(e)}")
        raise Exception(
            f"Erro ao buscar contratos reparcelados: {str(e)} - sem fallback")


async def carregar_dados_planilha_base_calculo() -> Dict[str, Any]:
    """
    FASE 2: Carregar dados da planilha base de cálculo

    Returns:
        Dados indexados da planilha por código_cliente + número_titulo
    """
    log("\n📋 FASE 2: CARREGANDO DADOS DA PLANILHA BASE DE CÁLCULO...")
    log("=" * 60)

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        # Configurar credenciais Google Sheets
        credenciais_path = get_env_or_fail("GOOGLE_CREDENTIALS_PATH")
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_file(
            credenciais_path, scopes=scope)
        cliente_sheets = gspread.authorize(credentials)

        # Abrir planilha base de cálculo
        planilha_calculo_id = get_env_or_fail("PLANILHA_CALCULO_ID")
        planilha_calculo = cliente_sheets.open_by_key(planilha_calculo_id)
        aba_base_calculo = planilha_calculo.worksheet("Base de cálculo")

        # Obter todos os dados da planilha
        dados_planilha_brutos = aba_base_calculo.get_all_records()

        # 🔍 DEBUG: Verificar primeiros registros
        if dados_planilha_brutos:
            log(f"🔍 DEBUG: Primeiro registro da planilha:")
            primeiro_registro = dados_planilha_brutos[0]
            for chave, valor in primeiro_registro.items():
                if 'empresa' in chave.lower() or 'loteamento' in chave.lower():
                    log(f"   📋 '{chave}': '{valor}' (tipo: {type(valor)})")

        # Indexar dados por código_cliente + número_titulo para busca rápida
        dados_indexados = {}
        # Linha 2 é o primeiro registro
        for i, registro in enumerate(dados_planilha_brutos, 2):
            codigo_cliente_raw = registro.get("Código Cliente", "")
            numero_titulo_raw = registro.get("Titulo", "")

            codigo_cliente = str(codigo_cliente_raw).strip(
            ) if codigo_cliente_raw is not None else ""
            numero_titulo = str(numero_titulo_raw).strip(
            ) if numero_titulo_raw is not None else ""

            if codigo_cliente and numero_titulo:
                chave_busca = f"{codigo_cliente}_{numero_titulo}"
                # Adicionar número da linha para futuras atualizações
                registro['linha_planilha'] = i
                dados_indexados[chave_busca] = registro

        log(f"✅ Carregados {len(dados_indexados)} registros da planilha base de cálculo")
        log(f"📋 Dados indexados por código_cliente + número_titulo")

        return dados_indexados

    except Exception as e:
        log(f"❌ Erro ao carregar dados da planilha: {str(e)}")
        raise Exception(
            f"Erro ao carregar dados da planilha: {str(e)} - sem fallback")


def associar_contratos_com_planilha(contratos_reparcelados: List[Dict[str, Any]],
                                    dados_planilha: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    FASE 3: Associar contratos do banco com dados da planilha

    Args:
        contratos_reparcelados: Lista de contratos do banco
        dados_planilha: Dados indexados da planilha

    Returns:
        Lista de contratos com dados da planilha associados
    """
    log("\n🔗 FASE 3: ASSOCIANDO CONTRATOS COM DADOS DA PLANILHA...")
    log("=" * 60)

    contratos_associados = []
    contratos_nao_encontrados = []

    for contrato in contratos_reparcelados:
        codigo_cliente = contrato.get('codigo_cliente', '').strip()
        numero_titulo = contrato.get('numero_titulo', '').strip()
        cliente = contrato.get('cliente', 'N/A')

        if not codigo_cliente or not numero_titulo:
            log(f"⚠️ Contrato {cliente} sem código_cliente ou número_titulo válidos")
            contratos_nao_encontrados.append(contrato)
            continue

        # Buscar na planilha usando código + título
        chave_busca = f"{codigo_cliente}_{numero_titulo}"
        dados_planilha_contrato = dados_planilha.get(chave_busca)

        if dados_planilha_contrato:
            # Associar dados da planilha ao contrato
            contrato['dados_planilha'] = dados_planilha_contrato
            contratos_associados.append(contrato)
            log(f"✅ {cliente} (Código: {codigo_cliente}, Título: {numero_titulo}) - Dados da planilha associados")
        else:
            log(f"❌ {cliente} (Código: {codigo_cliente}, Título: {numero_titulo}) - NÃO encontrado na planilha")
            contratos_nao_encontrados.append(contrato)

    log(f"\n📊 RESULTADO DA ASSOCIAÇÃO:")
    log(f"   ✅ Contratos associados: {len(contratos_associados)}")
    log(
        f"   ❌ Contratos não encontrados na planilha: {len(contratos_nao_encontrados)}")

    if contratos_nao_encontrados:
        log(f"\n⚠️ CONTRATOS NÃO ENCONTRADOS NA PLANILHA:")
        for contrato in contratos_nao_encontrados:
            codigo = contrato.get('codigo_cliente', 'N/A')
            titulo = contrato.get('numero_titulo', 'N/A')
            cliente = contrato.get('cliente', 'N/A')
            log(f"   ❌ {cliente} (Código: {codigo}, Título: {titulo})")

        log(f"\n📋 CONTINUANDO COM {len(contratos_associados)} CONTRATOS ENCONTRADOS")
        log(f"📄 Contratos não encontrados serão incluídos no relatório de erro")

    return contratos_associados, contratos_nao_encontrados


def verificar_pendencias_contrato(contrato: Dict[str, Any]) -> Dict[str, Any]:
    """
    FASE 4: Verificar pendências IPTU e inadimplência conforme PDD

    Args:
        contrato: Contrato com dados da planilha associados

    Returns:
        Resultado da verificação de pendências
    """
    dados_planilha = contrato.get('dados_planilha', {})
    cliente = contrato.get('cliente', 'N/A')

    def obter_valor_coluna(nome_coluna: str) -> str:
        valor = dados_planilha.get(nome_coluna)
        if valor is None:
            nome_normalizado = nome_coluna.strip().upper()
            for chave_existente, valor_existente in dados_planilha.items():
                if isinstance(chave_existente, str) and chave_existente.strip().upper() == nome_normalizado:
                    valor = valor_existente
                    break
        return str(valor or "").strip()

    # Verificar PENDÊNCIAS PMFI (IPTU)
    pendencias_pmfi = obter_valor_coluna("PENDENCIAS PMFI")

    # Verificar PENDÊNCIAS SIENGE INAD (Inadimplência)
    pendencias_sienge_inad = obter_valor_coluna("PENDENCIAS SIENGE INAD")

    # Verificar PENDÊNCIAS SIENGE (Outras pendências)
    pendencias_sienge = obter_valor_coluna("PENDENCIAS SIENGE")

    # ✅ LÓGICA CORRETA CONFORME PDD ATUALIZADO:
    # IPTU: "SIM" = COM pendências (inapto), "NÃO" ou vazio = SEM pendências (apto)
    # INADIMPLÊNCIA: "Inadimplência" = COM pendência (inapto); vazio ou "OK" = adimplente (apto)
    # OUTRAS PENDÊNCIAS: qualquer valor preenchido = COM pendência (inapto); vazio = SEM pendências (apto)
    pmfi_ok = not pendencias_pmfi or pendencias_pmfi.upper() == "NÃO"

    sienge_inad_normalizado = pendencias_sienge_inad.casefold()
    sienge_inad_ok = (
        not pendencias_sienge_inad
        or sienge_inad_normalizado == "ok"
    )

    pendencia_sienge_normalizada = pendencias_sienge.upper()
    sienge_ok = (
        not pendencias_sienge
        or pendencia_sienge_normalizada == "OK"
    )

    # Contrato apto se TODAS as pendências estão OK
    contrato_apto = pmfi_ok and sienge_inad_ok and sienge_ok

    resultado = {
        "contrato_apto": contrato_apto,
        "pendencias_pmfi": pendencias_pmfi if pendencias_pmfi else "OK",
        "pendencias_sienge_inad": pendencias_sienge_inad if pendencias_sienge_inad else "OK",
        "pendencias_sienge": pendencias_sienge if pendencias_sienge else "OK",
        "cliente": cliente
    }

    status_msg = "APTO" if contrato_apto else "PENDENTE"
    log(f"   🔍 {cliente}: {status_msg}")

    if not contrato_apto:
        if not pmfi_ok:
            log(
                f"      ❌ PENDÊNCIAS PMFI: '{pendencias_pmfi}' (deve ser 'NÃO' ou vazio para ser apto)")
        if not sienge_inad_ok:
            log(
                f"      ❌ PENDÊNCIAS SIENGE INAD: '{pendencias_sienge_inad}' (deve estar vazio ou 'OK' para ser adimplente)")
        if not sienge_ok:
            log(
                f"      ❌ PENDÊNCIAS SIENGE: '{pendencias_sienge}' (deve estar vazio ou 'OK' para ser apto)")

    return resultado


def filtrar_contratos_aptos(contratos_associados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    FASE 4: Filtrar contratos aptos para geração de carnê

    Args:
        contratos_associados: Lista de contratos com dados da planilha

    Returns:
        Lista de contratos aptos para geração de carnê
    """
    log("\n🔍 FASE 4: VERIFICANDO PENDÊNCIAS E FILTRANDO CONTRATOS APTOS...")
    log("=" * 60)

    contratos_aptos = []
    contratos_com_pendencias = []

    for contrato in contratos_associados:
        resultado_verificacao = verificar_pendencias_contrato(contrato)

        if resultado_verificacao["contrato_apto"]:
            contratos_aptos.append(contrato)
        else:
            contratos_com_pendencias.append({
                "contrato": contrato,
                "pendencias": resultado_verificacao
            })

    log(f"\n📊 RESULTADO DA VERIFICAÇÃO DE PENDÊNCIAS:")
    log(f"   ✅ Contratos aptos: {len(contratos_aptos)}")
    log(f"   ❌ Contratos com pendências: {len(contratos_com_pendencias)}")

    if contratos_com_pendencias:
        log(f"\n⚠️ CONTRATOS COM PENDÊNCIAS:")
        for item in contratos_com_pendencias:
            contrato = item["contrato"]
            pendencias = item["pendencias"]
            cliente = contrato.get('cliente', 'N/A')
            log(f"   ❌ {cliente}:")
            if pendencias["pendencias_pmfi"] != "OK":
                log(f"      📋 PMFI: {pendencias['pendencias_pmfi']}")
            if pendencias["pendencias_sienge_inad"] != "OK":
                log(
                    f"      📋 SIENGE INAD: {pendencias['pendencias_sienge_inad']}")
            if pendencias["pendencias_sienge"] != "OK":
                log(f"      📋 SIENGE: {pendencias['pendencias_sienge']}")

    if not contratos_aptos:
        # ❌ SEM FALLBACK: Erro se não há contratos aptos
        raise Exception(
            "Nenhum contrato apto para geração de carnê encontrado - sem fallback")

    return contratos_aptos


async def executar_fase_geracao_carnes(rpa: RPASienge, contratos_aptos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    FASE 5: Executar geração de carnês via RPA Sienge

    Args:
        rpa: Instância inicializada do RPA Sienge
        contratos_aptos: Lista de contratos aptos para geração

    Returns:
        Resultado da geração de carnês
    """
    log("\n🎫 FASE 5: EXECUTANDO GERAÇÃO DE CARNÊS VIA RPA SIENGE...")
    log("=" * 60)
    log(f"📋 Contratos para processar: {len(contratos_aptos)}")

    try:
        # ✅ USAR MÉTODO DIRETO DE GERAÇÃO DE CARNÊS
        # Agrupar contratos por empresa e chamar _gerar_carne_empresa_sienge diretamente
        contratos_por_empresa = {}
        for contrato in contratos_aptos:
            dados_planilha = contrato.get('dados_planilha', {})
            empresa = dados_planilha.get('Empresa', '')

            # 🔍 DEBUG: Verificar estrutura dos dados
            if not empresa:
                log(
                    f"❌ ERRO: Empresa vazia para contrato {contrato.get('numero_titulo', 'N/A')}")
                log(
                    f"   📋 Dados planilha disponíveis: {list(dados_planilha.keys())}")
                if 'Empresa' in dados_planilha:
                    log(
                        f"   📋 Valor 'Empresa': '{dados_planilha['Empresa']}' (tipo: {type(dados_planilha['Empresa'])})")
                    log(
                        f"   📋 Valor 'Empresa' repr: {repr(dados_planilha['Empresa'])}")

                # 🔍 DEBUG: Verificar se há outras colunas de empresa
                for chave in dados_planilha.keys():
                    if 'empresa' in chave.lower() or 'loteamento' in chave.lower():
                        log(
                            f"   📋 Coluna relacionada '{chave}': '{dados_planilha[chave]}'")

                # ❌ SEM FALLBACK: Erro se empresa estiver vazia
                raise Exception(
                    f"Empresa vazia para contrato {contrato.get('numero_titulo', 'N/A')} - sem fallback")

            if empresa not in contratos_por_empresa:
                contratos_por_empresa[empresa] = []
            contratos_por_empresa[empresa].append(contrato)

        log(
            f"📊 Contratos agrupados por empresa: {len(contratos_por_empresa)} empresas")
        for empresa, contratos in contratos_por_empresa.items():
            log(f"   🏢 {empresa}: {len(contratos)} contratos")

        # 🔍 DEBUG: Verificar se há múltiplas empresas
        if len(contratos_por_empresa) == 1:
            log(f"⚠️ ATENÇÃO: Apenas 1 empresa encontrada - loop executará apenas 1 vez")
        else:
            log(f"✅ {len(contratos_por_empresa)} empresas encontradas - loop executará {len(contratos_por_empresa)} vezes")

        # 🔍 DEBUG: Verificar se todos os contratos foram agrupados
        total_contratos_agrupados = sum(
            len(contratos) for contratos in contratos_por_empresa.values())
        log(
            f"🔍 DEBUG: Total de contratos agrupados: {total_contratos_agrupados}")
        log(
            f"🔍 DEBUG: Total de contratos aptos recebidos: {len(contratos_aptos)}")

        if total_contratos_agrupados != len(contratos_aptos):
            log(
                f"⚠️ ATENÇÃO: Discrepância! Contratos agrupados ({total_contratos_agrupados}) ≠ Contratos aptos ({len(contratos_aptos)})")

        contratos_processados = 0
        contratos_erro = 0
        carnês_gerados = []  # Lista para armazenar todos os carnês processados

        # Processar cada empresa
        log(f"\n🔄 INICIANDO LOOP DE PROCESSAMENTO...")
        log(
            f"📊 Total de empresas para processar: {len(contratos_por_empresa)}")

        for i, (empresa, contratos_empresa) in enumerate(contratos_por_empresa.items(), 1):
            log(f"\n🏢 PROCESSANDO EMPRESA {i}/{len(contratos_por_empresa)}: {empresa}")
            log(f"📋 {len(contratos_empresa)} contratos para esta empresa")

            try:
                # Preparar parâmetros para _gerar_carne_empresa_sienge
                # Incluir datas calculadas dos dados da planilha
                primeiro_vencimento = None
                for contrato in contratos_empresa:
                    dados_planilha = contrato.get('dados_planilha', {})
                    vencimento = dados_planilha.get('1º vencimento carnê', '')
                    if vencimento:
                        primeiro_vencimento = vencimento
                        break

                if not primeiro_vencimento:
                    raise Exception(
                        f"1º vencimento carnê não encontrado para empresa {empresa} - sem fallback")

                # Calcular datas conforme PDD 10.2
                from datetime import datetime
                if "/" in primeiro_vencimento:
                    if len(primeiro_vencimento.split("/")[2]) == 2:
                        data_temp = datetime.strptime(
                            primeiro_vencimento, "%d/%m/%y")
                    else:
                        data_temp = datetime.strptime(
                            primeiro_vencimento, "%d/%m/%Y")
                else:
                    raise Exception(
                        f"Formato de data não reconhecido: {primeiro_vencimento}")

                # Define data inicial sempre como dia 1 do mês/ano do primeiro vencimento
                data_inicial = data_temp.replace(day=1)
                data_inicial_formatada = data_inicial.strftime("%d/%m/%Y")

                # Data final: último dia do mês 12 meses após a data inicial
                import calendar
                meses_adiantados = data_inicial.month + 11
                ano_final = data_inicial.year + (meses_adiantados - 1) // 12
                mes_final = ((meses_adiantados - 1) % 12) + 1
                ultimo_dia = calendar.monthrange(
                    ano_final, mes_final)[1]
                data_final = data_inicial.replace(
                    year=ano_final,
                    month=mes_final,
                    day=ultimo_dia
                )
                data_final_formatada = data_final.strftime("%d/%m/%Y")

                parametros_empresa = {
                    "empresa": empresa,
                    "contratos": contratos_empresa,
                    "data_inicial": data_inicial_formatada,
                    "data_final": data_final_formatada
                }

                # Chamar webscraping real
                resultado_carne = await rpa._gerar_carne_empresa_sienge(parametros_empresa)

                if resultado_carne.get("sucesso", False):
                    contratos_processados += len(contratos_empresa)
                    log(f"✅ Carnê gerado com sucesso para {empresa}")

                    # ✅ ADICIONAR CARNÊ À LISTA DE CARNÊS GERADOS
                    carnês_gerados.append({
                        "empresa": empresa,
                        "arquivo_remessa": resultado_carne.get("arquivo_remessa", ""),
                        "contratos_processados": len(contratos_empresa),
                        "timestamp_geracao": resultado_carne.get("timestamp_geracao", ""),
                        "contratos": [c.get('numero_titulo', 'N/A') for c in contratos_empresa]
                    })
                else:
                    contratos_erro += len(contratos_empresa)
                    log(f"❌ Erro na geração de carnê para {empresa}")

            except Exception as e:
                contratos_erro += len(contratos_empresa)
                log(f"❌ Exceção na geração de carnê para {empresa}: {str(e)}")

            log(f"✅ EMPRESA {i}/{len(contratos_por_empresa)} CONCLUÍDA: {empresa}")

        log(f"\n🎯 LOOP CONCLUÍDO!")
        log(f"📊 Empresas processadas: {len(contratos_por_empresa)}")
        log(f"📊 Contratos processados: {contratos_processados}")
        log(f"📊 Contratos com erro: {contratos_erro}")

        resultado = {
            "sucesso": True,
            "contratos_processados": contratos_processados,
            "contratos_erro": contratos_erro,
            "empresas_processadas": len(contratos_por_empresa),
            "carnês_gerados": carnês_gerados  # ✅ LISTA DE TODOS OS CARNÊS PROCESSADOS
        }

        if not resultado.get("sucesso"):
            erro_msg = resultado.get(
                "erro", "Erro não especificado na geração de carnês")
            log(f"❌ Falha na geração de carnês: {erro_msg}")
            # ❌ SEM FALLBACK: Lançar exceção se método principal falhar
            raise Exception(
                f"Falha na geração de carnês: {erro_msg} - sem fallback")

        log(f"✅ Geração de carnês concluída com sucesso!")
        log(f"📊 Contratos processados: {resultado.get('contratos_processados', 0)}")
        log(f"📊 Contratos com erro: {resultado.get('contratos_erro', 0)}")

        return resultado

    except Exception as e:
        log(f"❌ Erro na execução da geração de carnês: {str(e)}")
        raise Exception(
            f"Erro na execução da geração de carnês: {str(e)} - sem fallback")


async def vincular_arquivos_gerados_banco(resultado_carnes: Dict[str, Any]) -> Dict[str, Any]:
    """
    FASE 6: Vincular arquivos de remessa gerados aos contratos no banco

    Args:
        resultado_carnes: Resultado da geração de carnês

    Returns:
        Resultado da vinculação
    """
    log("\n🔗 FASE 6: VINCULANDO ARQUIVOS GERADOS AOS CONTRATOS NO BANCO...")
    log("=" * 60)

    try:
        # ✅ USAR MESMO PADRÃO DO alterar_status_direto.py
        from core.mongodb_manager import MongoDBManager

        # Verificar se há carnês gerados com sucesso
        carnes_sucesso = resultado_carnes.get("detalhes_carnes_sucesso", [])

        if not carnes_sucesso:
            log("⚠️ Nenhum carnê foi gerado com sucesso para vincular")
            return {"sucesso": True, "contratos_vinculados": 0}

        # Conectar ao MongoDB
        mongo_manager = MongoDBManager()
        await mongo_manager.conectar()
        db = mongo_manager.database
        colecao = db.fila_contratos

        contratos_vinculados = 0

        for carne in carnes_sucesso:
            numero_titulo = carne.get("numero_titulo", "")
            arquivo_remessa = carne.get("arquivo_remessa", "")

            if numero_titulo and arquivo_remessa:
                # Buscar contrato pelo número do título
                contrato = colecao.find_one({"numero_titulo": numero_titulo})

                if contrato:
                    # Preparar dados de atualização
                    update_data = {
                        "status": "CARNE_GERADO",
                        "arquivo_remessa": arquivo_remessa,
                        "timestamp_carne_gerado": datetime.now().isoformat(),
                        "timestamp_ultima_atualizacao": datetime.now().isoformat()
                    }

                    # Atualizar contrato
                    resultado = colecao.update_one(
                        {"_id": contrato["_id"]},
                        {"$set": update_data}
                    )

                    if resultado.modified_count > 0:
                        contratos_vinculados += 1
                        log(f"✅ Contrato {numero_titulo} vinculado ao arquivo {arquivo_remessa}")
                    else:
                        log(f"❌ Falha ao vincular contrato {numero_titulo}")
                else:
                    log(f"❌ Contrato {numero_titulo} não encontrado no banco")

        log(f"✅ Vinculação concluída: {contratos_vinculados} contratos vinculados")

        return {
            "sucesso": True,
            "contratos_vinculados": contratos_vinculados,
            "arquivos_vinculados": len(carnes_sucesso)
        }

    except Exception as e:
        log(f"❌ Erro ao vincular arquivos ao banco: {str(e)}")
        raise Exception(
            f"Erro ao vincular arquivos ao banco: {str(e)} - sem fallback")


async def main():
    """
    MAIN DE EMISSÃO DE CARNÊS: Execução completa do fluxo
    """
    parser = argparse.ArgumentParser(
        description='RPA Sienge - Emissão de Carnês',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Fluxo de execução:
1. Buscar contratos REPARCELADOS no banco
2. Carregar dados da planilha base de cálculo  
3. Associar contratos com dados da planilha
4. Verificar pendências IPTU e inadimplência
5. Filtrar contratos aptos
6. Executar geração de carnês via RPA
7. Vincular arquivos gerados aos contratos no banco

Exemplos de uso:
  python main_sienge_emissao_carnes.py                    # Execução completa
  python main_sienge_emissao_carnes.py --teste            # Modo teste
        '''
    )
    parser.add_argument('--teste', action='store_true',
                        help='Executar em modo teste usando planilha de teste')
    args = parser.parse_args()

    # Configurar modo teste se solicitado
    if args.teste:
        log("🧪 MODO TESTE ATIVADO: Usando planilha de teste")
        planilha_teste = os.getenv("PLANILHA_TESTE_HOM")
        if planilha_teste:
            os.environ["PLANILHA_CALCULO_ID"] = planilha_teste
            log(f"🔄 Redirecionado para planilha de teste: {planilha_teste}")
        else:
            log("⚠️ PLANILHA_TESTE_HOM não configurada, usando planilha de produção")
    else:
        log("🏭 MODO PRODUÇÃO: Usando planilha de produção")

    inicio_execucao = datetime.now()

    log("🎫 RPA SIENGE - EMISSÃO DE CARNÊS")
    log("🎯 Fluxo: REPARCELADO → CARNE_GERADO")
    log("📋 Conforme PDD Seção 10.2: Emissão de carnê + Geração de arquivos de remessa")
    log("=" * 60)

    try:
        arquivo_log_execucao, stdout_original, stderr_original = preparar_logs_execucao()
        # Notificar início
        notificar_sucesso_simples(
            "🚀 EMISSÃO DE CARNÊS INICIADA",
            "Fluxo: Banco → Planilha → Verificação → Geração → Vinculação"
        )

        # FASE 1: Buscar contratos reparcelados no banco
        contratos_reparcelados = await obter_contratos_reparcelados()

        if not contratos_reparcelados:
            log("✅ Nenhum contrato para processar. Execução concluída.")
            return 0

        # FASE 2: Carregar dados da planilha
        dados_planilha = await carregar_dados_planilha_base_calculo()

        # FASE 3: Associar contratos com planilha
        contratos_associados, contratos_nao_encontrados = associar_contratos_com_planilha(
            contratos_reparcelados, dados_planilha)

        # FASE 4: Verificar pendências e filtrar contratos aptos
        contratos_aptos = filtrar_contratos_aptos(contratos_associados)

        # Inicializar RPA Sienge
        log(f"\n🤖 INICIALIZANDO RPA SIENGE...")
        headless = False  # Browser visível para acompanhar o processo
        rpa = RPASienge(headless=headless)
        await rpa.inicializar()

        # Carregar credenciais e fazer login
        credenciais = await carregar_credenciais_sienge()
        rpa._configurar_credenciais(credenciais)
        await rpa._fazer_login_sienge()
        log("✅ Login no Sienge realizado com sucesso")

        # FASE 5: Executar geração de carnês
        resultado_carnes = await executar_fase_geracao_carnes(rpa, contratos_aptos)

        # Finalizar RPA
        await rpa.finalizar()

        # ✅ FASE 6 REMOVIDA: O RPA já vincula os arquivos ao banco automaticamente
        # resultado_vinculacao = await vincular_arquivos_gerados_banco(resultado_carnes)

        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        # Processar resultados
        contratos_processados = resultado_carnes.get(
            "contratos_processados", 0)
        contratos_erro = resultado_carnes.get("contratos_erro", 0)
        # contratos_vinculados = resultado_vinculacao.get("contratos_vinculados", 0)
        contratos_vinculados = contratos_processados  # RPA já vincula automaticamente

        log(f"\n🎉 EMISSÃO DE CARNÊS CONCLUÍDA COM SUCESSO!")
        log(f"⏱️ Duração: {duracao}")
        log(
            f"📋 Contratos reparcelados encontrados: {len(contratos_reparcelados)}")
        log(
            f"🔗 Contratos associados com planilha: {len(contratos_associados)}")
        log(f"✅ Contratos aptos: {len(contratos_aptos)}")
        log(f"🎫 Carnês processados: {contratos_processados}")
        log(f"❌ Contratos com erro: {contratos_erro}")
        log(f"🔗 Contratos vinculados ao banco: {contratos_vinculados}")

        # Gerar relatório HTML - ajustar para template existente
        carnês_gerados = resultado_carnes.get("carnês_gerados", [])
        empresas_processadas = resultado_carnes.get("empresas_processadas", 0)
        estatisticas = {
            'total_empresas': empresas_processadas,
            'carnes_sucesso': contratos_processados,
            'carnes_erro': contratos_erro,
            'total_contratos': len(contratos_aptos),
            'contratos_reparcelados': len(contratos_reparcelados),
            'contratos_associados': len(contratos_associados),
            'contratos_nao_encontrados': len(contratos_nao_encontrados),
            'contratos_aptos': len(contratos_aptos),
            'contratos_vinculados': contratos_vinculados,
            'carnês_gerados': carnês_gerados,  # ✅ LISTA DE CARNÊS PARA ANEXO
            'duracao': str(duracao)
        }

        html_relatorio = templates_relatorios.relatorio_carnes(estatisticas)

        # Salvar relatório HTML
        diretorio_relatorios = Path("outputs/relatorios")
        diretorio_relatorios.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_html = diretorio_relatorios / \
            f"relatorio_emissao_carnes_{timestamp}.html"

        with open(arquivo_html, 'w', encoding='utf-8') as f:
            f.write(html_relatorio)

        log(f"📄 Relatório HTML salvo: {arquivo_html}")

        # Notificar sucesso
        from core.notificacoes_simples import notificar_sucesso

        resultados_notificacao = {
            "titulo": "🎉 RPA SIENGE: Emissão de carnês concluída",
            "mensagem": f"Duração: {duracao} | Carnês: {contratos_processados} | Erros: {contratos_erro} | Vinculados: {contratos_vinculados} | Não encontrados: {len(contratos_nao_encontrados)}",
            "caminhos_anexos": [str(ARQUIVO_LOG_ATUAL), str(arquivo_html)]
        }

        notificar_sucesso(
            nome_rpa="RPA Sienge - Emissão Carnês",
            tempo_execucao=str(duracao),
            resultados=resultados_notificacao
        )

        return 0  # Sucesso

    except Exception as e:
        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        log(f"\n❌ EMISSÃO DE CARNÊS FALHOU")
        log(f"⏱️ Duração: {duracao}")
        log(f"❌ Erro: {str(e)}")

        # Gerar relatório de erro com contratos não encontrados
        detalhes_erro = str(e)
        if 'contratos_nao_encontrados' in locals():
            if contratos_nao_encontrados:
                detalhes_erro += f"\n\n📋 CONTRATOS NÃO ENCONTRADOS NA PLANILHA ({len(contratos_nao_encontrados)}):\n"
                for contrato in contratos_nao_encontrados:
                    codigo = contrato.get('codigo_cliente', 'N/A')
                    titulo = contrato.get('numero_titulo', 'N/A')
                    cliente = contrato.get('cliente', 'N/A')
                    detalhes_erro += f"   ❌ {cliente} (Código: {codigo}, Título: {titulo})\n"

        html_erro = templates_relatorios.relatorio_erro(
            "RPA Sienge - Emissão de Carnês",
            detalhes_erro,
            f"Duração até erro: {duracao}"
        )

        # Salvar relatório de erro
        diretorio_relatorios = Path("outputs/relatorios")
        diretorio_relatorios.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_html_erro = diretorio_relatorios / \
            f"erro_emissao_carnes_{timestamp}.html"

        with open(arquivo_html_erro, 'w', encoding='utf-8') as f:
            f.write(html_erro)

        log(f"📄 Relatório de erro HTML salvo: {arquivo_html_erro}")

        # Notificar erro
        from core.notificacoes_simples import notificar_sucesso

        resultados_erro = {
            "titulo": "❌ RPA SIENGE: Emissão de carnês falhou",
            "mensagem": f"Erro: {str(e)} | Duração: {duracao}",
            "caminhos_anexos": [str(ARQUIVO_LOG_ATUAL)]
        }

        notificar_sucesso(
            nome_rpa="RPA Sienge - Emissão Carnês",
            tempo_execucao=str(duracao),
            resultados=resultados_erro
        )

        return 1  # Falha

    finally:
        try:
            arquivo_log_execucao.close()
        except Exception:
            pass

        if 'stdout_original' in locals() and 'stderr_original' in locals():
            sys.stdout = stdout_original
            sys.stderr = stderr_original
            try:
                arquivo_log_execucao.close()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:
        log(f"Erro fatal: {e}")
        sys.exit(1)
