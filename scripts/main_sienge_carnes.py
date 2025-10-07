#!/usr/bin/env python3
"""
Main de geração de carnês para processamento da Fase 3 do RPA Sienge
Sistema de geração de carnê independente

FASE 3: GERAÇÃO DE CARNÊS
REPARCELADO → CARNE_GERADO

Conforme PDD Seção 10.2: Geração de arquivos de remessa por empresa
INCLUI VERIFICAÇÃO DE AUTORIZAÇÃO NA PLANILHA

Desenvolvido em Português Brasileiro
"""

import os
import asyncio
import argparse
import re
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from core.templates_relatorios import templates_relatorios
from core.gerador_anexos import gerador_anexos
from rpa_sienge.rpa_sienge import RPASienge
from core.utils_sienge import (
    log,
    notificar_sucesso_simples,
    notificar_erro_simples,
    carregar_credenciais_sienge,
    get_env_or_fail
)
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para importações
sys.path.append(str(Path(__file__).parent.parent))

sys.path.append(str(Path(__file__).parent.parent))

# Adicionar o diretório raiz ao path para imports
sys.path.append(str(Path(__file__).parent.parent))


# Garante execução headless em produção
# Para debug, comentar esta linha ou alterar para "1"
# os.environ["HEADLESS"] = "0"

# Configuração HEADLESS baseada na variável de ambiente
HEADLESS_MODE = os.getenv("HEADLESS", "1") == "1"

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def validar_formato_data(data_str: str) -> Optional[str]:
    """
    Valida formato de data DD-MM ou DD/MM

    Args:
        data_str: String da data no formato DD-MM ou DD/MM

    Returns:
        String normalizada DD-MM ou None se inválida
    """
    if not data_str:
        return None

    # Remover espaços
    data_str = data_str.strip()

    # Padrões aceitos: DD-MM ou DD/MM
    padrao_traco = r'^(\d{1,2})-(\d{1,2})$'
    padrao_barra = r'^(\d{1,2})/(\d{1,2})$'

    match_traco = re.match(padrao_traco, data_str)
    match_barra = re.match(padrao_barra, data_str)

    if match_traco:
        dia, mes = match_traco.groups()
    elif match_barra:
        dia, mes = match_barra.groups()
    else:
        return None

    # Validar valores
    try:
        dia_int = int(dia)
        mes_int = int(mes)

        if not (1 <= dia_int <= 31):
            return None
        if not (1 <= mes_int <= 12):
            return None

        # Retornar no formato padronizado DD-MM
        return f"{dia_int:02d}-{mes_int:02d}"

    except ValueError:
        return None


def parse_argumentos():
    """
    Parse dos argumentos de linha de comando

    Returns:
        Namespace com argumentos parseados
    """
    parser = argparse.ArgumentParser(
        description='RPA Sienge - Geração de Carnês com Filtro de Data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos de uso:
  python main_sienge_carnes.py                    # Processar todos os contratos
  python main_sienge_carnes.py -d 05-09           # Apenas contratos com vencimento dia 5/09
  python main_sienge_carnes.py --data-vencimento 10/12   # Apenas contratos com vencimento dia 10/12
        '''
    )

    parser.add_argument(
        '-d', '--data-vencimento',
        type=str,
        help='Filtrar contratos por data de vencimento (formato: DD-MM ou DD/MM). Ex: 05-09 ou 10/12'
    )

    args = parser.parse_args()

    # Validar data de vencimento se fornecida
    if args.data_vencimento:
        data_validada = validar_formato_data(args.data_vencimento)
        if not data_validada:
            parser.error(f"Formato de data inválido: '{args.data_vencimento}'. "
                         f"Use o formato DD-MM ou DD/MM (ex: 05-09 ou 10/12)")
        args.data_vencimento = data_validada

    return args


def verificar_pendencias_contrato(linha_planilha: Dict[str, Any]) -> tuple[bool, str]:
    """
    Verifica se um contrato pode ter carnê gerado baseado nas pendências da planilha.

    Args:
        linha_planilha: Dados da linha do contrato na planilha base de cálculo

    Returns:
        Tuple (pode_gerar: bool, motivo: str)
    """
    # Verificar PENDÊNCIAS PMFI (IPTU) - com espaço no final
    pendencias_pmfi = str(linha_planilha.get(
        "PENDENCIAS PMFI ", "")).strip().upper()

    if pendencias_pmfi == "SIM":  # SIM = tem pendência = NÃO gerar
        return False, "Pendência PMFI: SIM"

    # Verificar PENDÊNCIAS SIENGE INAD (Inadimplência) - com espaço no final
    pendencias_sienge_inad = str(linha_planilha.get(
        "PENDENCIAS SIENGE INAD ", "")).strip().upper()

    if pendencias_sienge_inad == "INADIMPLÊNCIA":
        return False, "Pendência Sienge Inad: INADIMPLÊNCIA"

    # Verificar PENDÊNCIAS SIENGE (Outras pendências)
    pendencias_sienge = str(linha_planilha.get(
        "PENDENCIAS SIENGE", "")).strip().upper()

    if pendencias_sienge and pendencias_sienge != "OK":  # Qualquer coisa diferente de OK = NÃO gerar
        return False, f"Pendência Sienge: {pendencias_sienge}"

    # ✅ CORREÇÃO: Campos vazios são válidos (não há pendência)
    # Só rejeitar se houver pendência explícita
    # Campos vazios = sem pendência = OK para gerar carnê

    return True, "OK para gerar carnê"


async def ler_dados_planilha_base_calculo(rpa: RPASienge) -> Dict[str, Any]:
    """
    Lê os dados da planilha base de cálculo para verificar pendências.

    Args:
        rpa: Instância do RPA Sienge com Google Sheets já conectado

    Returns:
        Dados da planilha indexados por código do cliente
    """
    log("\n📋 LENDO DADOS DA PLANILHA BASE DE CÁLCULO...")
    log("=" * 60)

    try:
        # Usar o cliente Google Sheets já inicializado no RPA
        if not hasattr(rpa, 'cliente_sheets') or not rpa.cliente_sheets:
            log("❌ Cliente Google Sheets não disponível no RPA")
            return {"sucesso": False, "erro": "Cliente Google Sheets não disponível"}

        # Carregar dados da planilha base de cálculo
        planilha_calculo_id = get_env_or_fail("PLANILHA_CALCULO_ID")
        log(f"🔑 Planilha ID: {planilha_calculo_id}")

        planilha_calculo = rpa.cliente_sheets.open_by_key(planilha_calculo_id)
        log(f"📊 Planilha aberta: {planilha_calculo.title}")

        # Listar todas as abas disponíveis
        abas_disponiveis = [aba.title for aba in planilha_calculo.worksheets()]
        log(f"📋 Abas disponíveis: {abas_disponiveis}")

        # Verificar se a aba "Base de cálculo" existe
        if "Base de cálculo" not in abas_disponiveis:
            log("❌ Aba 'Base de cálculo' não encontrada!")
            return {"sucesso": False, "erro": "Aba 'Base de cálculo' não encontrada na planilha"}

        aba_base_calculo = planilha_calculo.worksheet("Base de cálculo")
        log(f"📋 Aba 'Base de cálculo' encontrada")

        # Verificar se há dados na aba
        total_linhas = aba_base_calculo.row_count
        log(f"📊 Total de linhas na aba: {total_linhas}")

        if total_linhas <= 1:  # 1 linha = cabeçalho
            log("⚠️ Aba 'Base de cálculo' está vazia (apenas cabeçalho)")
            return {"sucesso": False, "erro": "Aba 'Base de cálculo' está vazia"}

        # Obter todos os dados da planilha
        dados_planilha_brutos = aba_base_calculo.get_all_records()
        log(f"📋 Registros brutos lidos: {len(dados_planilha_brutos)}")

        # Mostrar primeiros registros para debug
        if dados_planilha_brutos:
            log(f"🔍 Primeiro registro: {dados_planilha_brutos[0]}")
            log(
                f"🔍 Colunas disponíveis: {list(dados_planilha_brutos[0].keys())}")

        # Indexar por código do cliente para busca rápida
        dados_planilha_indexados = {}
        for i, registro in enumerate(dados_planilha_brutos):
            cod_cliente_raw = registro.get("Código Cliente", "")
            cod_cliente = str(cod_cliente_raw).strip(
            ) if cod_cliente_raw is not None else ""
            if cod_cliente:
                dados_planilha_indexados[cod_cliente] = registro
                if i < 3:  # Mostrar primeiros 3 para debug
                    log(f"🔍 Cliente {i+1}: {cod_cliente} - {registro.get('Cliente', 'N/A')}")

        log(f"📋 Carregados {len(dados_planilha_indexados)} registros da planilha base de cálculo")

        return {
            "sucesso": True,
            "dados_planilha": dados_planilha_indexados
        }

    except Exception as e:
        log(f"❌ Erro ao ler dados da planilha: {str(e)}")
        log(f"🔍 Traceback: {traceback.format_exc()}")
        return {
            "sucesso": False,
            "erro": str(e)
        }


async def executar_fase_geracao_carnes(credenciais: Dict[str, str], total_reparcelados: int, empresas_info: Dict[str, int], filtro_data: Optional[str] = None, contratos_filtrados: Optional[list] = None, data_vencimento_planilha: Optional[str] = None) -> Dict[str, Any]:
    """
    FASE 3: GERAÇÃO DE CARNÊS
    REPARCELADO → CARNE_GERADO

    Conforme PDD Seção 10.2: Geração de arquivos de remessa por empresa
    INCLUI VERIFICAÇÃO DE AUTORIZAÇÃO NA PLANILHA E VERIFICAÇÃO DE INADIMPLÊNCIA
    """
    log("\n🎫 EXECUTANDO FASE 3: GERAÇÃO DE CARNÊS")
    log("=" * 60)
    log(f"🎯 Meta: Processar {total_reparcelados} contratos reparcelados")
    log(f"🏢 Empresas: {len(empresas_info)} empresas diferentes")
    if filtro_data:
        log(
            f"📅 FILTRO APLICADO: Apenas contratos com vencimento {filtro_data}")
    log("📋 Processo: Geração arquivos remessa conforme PDD 10.2")
    log("🔍 INCLUI: Verificação de autorização na planilha")

    try:
        notificar_sucesso_simples(
            f"🚀 FASE 3 INICIADA: Geração de carnês",
            f"Contratos: {total_reparcelados} | Empresas: {len(empresas_info)}"
        )

        # Carregar configurações da planilha (usando variável existente)
        planilha_id = get_env_or_fail("PLANILHA_CALCULO_ID")
        credenciais_google = os.getenv("GOOGLE_CREDENTIALS_PATH", "")

        log(f"📋 Planilha ID: {planilha_id}")
        log(f"🔑 Credenciais Google: {'Configurado' if credenciais_google else 'Não configurado'}")

        # ✅ NOVO: FASE 3.1: Usar dados da planilha já carregados em memória
        log("🔍 FASE 3.1: Usando dados da planilha já carregados em memória...")

        # Os dados da planilha já estão em contratos_filtrados (cada contrato tem "dados_planilha")
        log(
            f"✅ Dados da planilha já disponíveis em {len(contratos_filtrados)} contratos")

        # ✅ NOVO: FASE 3.2: Filtrar contratos que podem ter carnê gerado
        log("🔍 FASE 3.2: Filtrando contratos aptos para geração de carnê...")

        contratos_aptos = []
        contratos_rejeitados = []

        # Se há contratos filtrados, usar eles; senão buscar todos os reparcelados
        if contratos_filtrados:
            contratos_para_verificar = contratos_filtrados
        else:
            # Buscar todos os contratos reparcelados
            from core.mongodb_manager import MongoDBManager
            mongodb = MongoDBManager()
            await mongodb.conectar()

            contratos_para_verificar = list(
                mongodb.database.fila_contratos.find({"status": "REPARCELADO"}))
            await mongodb.desconectar()

        log(f"🔍 Verificando {len(contratos_para_verificar)} contratos reparcelados...")

        for contrato in contratos_para_verificar:
            codigo_cliente = contrato.get('codigo_cliente', '').strip()
            cliente_nome = contrato.get('cliente', '').strip()

            if not codigo_cliente:
                continue

            # ✅ CORREÇÃO: Usar dados da planilha já carregados no contrato
            dados_cliente_planilha = contrato.get('dados_planilha', {})

            if not dados_cliente_planilha:
                log(f"⚠️ Cliente {codigo_cliente} ({cliente_nome}) não tem dados da planilha")
                contratos_rejeitados.append({
                    "codigo_cliente": codigo_cliente,
                    "cliente": cliente_nome,
                    "motivo": "Sem dados da planilha"
                })
                continue

            # Verificar se pode gerar carnê
            pode_gerar, motivo = verificar_pendencias_contrato(
                dados_cliente_planilha)

            if pode_gerar:
                log(f"✅ Cliente {codigo_cliente} ({cliente_nome}) - {motivo}")
                contratos_aptos.append(contrato)
            else:
                log(f"❌ Cliente {codigo_cliente} ({cliente_nome}) - {motivo}")
                contratos_rejeitados.append({
                    "codigo_cliente": codigo_cliente,
                    "cliente": cliente_nome,
                    "motivo": motivo
                })

        log(f"📊 Resultado da filtragem:")
        log(f"   ✅ Contratos aptos para carnê: {len(contratos_aptos)}")
        log(f"   ❌ Contratos rejeitados: {len(contratos_rejeitados)}")

        if not contratos_aptos:
            log("⚠️ Nenhum contrato apto para geração de carnê")
            return {
                "sucesso": True,
                "contratos_processados": 0,
                "contratos_erro": 0,
                "empresas_processadas": 0,
                "contratos_aptos": 0,
                "contratos_rejeitados": len(contratos_rejeitados),
                "detalhes_rejeitados": contratos_rejeitados,
                "detalhes": "Nenhum contrato apto para geração de carnê"
            }

        # ✅ NOVO: FASE 3.3: Processar apenas contratos aptos
        log("🔍 FASE 3.3: Processando geração de carnês para contratos aptos...")

        # ✅ CORREÇÃO: Usar RPA única sessão (como main_sienge_extracao.py)
        headless = os.getenv("HEADLESS", "1") == "1"
        # ✅ FORÇAR BROWSER VISÍVEL PARA DEBUG
        rpa = RPASienge(headless=False)
        await rpa.inicializar()

        log(f"🤖 RPA inicializado para geração de carnês (headless: False - BROWSER VISÍVEL)")
        log(f"🎯 Processando {len(contratos_aptos)} contratos aptos para geração de carnê...")

        # ✅ FLUXO ORIGINAL RESTAURADO: Usar método LOTE que fazia tudo automaticamente
        # MongoDB → Planilha → Verificação → Cálculo → Webscraping → Vínculo arquivo
        log("✅ Usando método processar_fila_geracao_carnes - FLUXO ORIGINAL completo")
        resultado = await rpa.processar_fila_geracao_carnes(
            credenciais_sienge=credenciais,
            pausar_entre_contratos=False  # Processamento contínuo em produção
        )

        if not resultado.get("sucesso"):
            log("❌ Método LOTE falhou - verificando métodos alternativos")
            log("🔍 Métodos disponíveis:")
            for attr in dir(rpa):
                if 'carnes' in attr.lower() or 'processar' in attr.lower() or 'gerar' in attr.lower():
                    log(f"   - {attr}")

            resultado = {
                "sucesso": False,
                "erro": "Método processar_fila_geracao_carnes falhou",
                "contratos_processados": 0,
                "contratos_erro": len(contratos_aptos)
            }

        await rpa.finalizar()

        # Processar resultado
        if resultado.get("sucesso"):
            sucessos = resultado.get("contratos_processados", 0)
            erros = resultado.get("contratos_erro", 0)
            empresas_processadas = resultado.get("empresas_processadas", 0)
            autorizado = resultado.get("autorizado", False)
            contratos_atualizados = resultado.get("contratos_atualizados", 0)

            log(f"✅ FASE 3 CONCLUÍDA:")
            log(f"   ✅ Autorizado: {autorizado}")
            log(f"   ✅ Contratos processados: {sucessos}")
            log(f"   ❌ Contratos com erro: {erros}")
            log(f"   🏢 Empresas processadas: {empresas_processadas}")
            log(f"   📋 Contratos atualizados: {contratos_atualizados}")
            log(f"   📊 Taxa de sucesso: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%")
            log(f"   ✅ Contratos aptos para carnê: {len(contratos_aptos)}")
            log(f"   ❌ Contratos rejeitados: {len(contratos_rejeitados)}")

            # ✅ NOVO: Coletar dados detalhados para anexos (incluindo contratos rejeitados)
            carnes_sucesso = []
            carnes_erro = []

            if hasattr(rpa, 'carnes_gerados_sucesso'):
                carnes_sucesso = rpa.carnes_gerados_sucesso
            elif resultado.get("detalhes_carnes_sucesso"):
                carnes_sucesso = resultado.get("detalhes_carnes_sucesso", [])

            if hasattr(rpa, 'carnes_erro'):
                carnes_erro = rpa.carnes_erro
            elif resultado.get("detalhes_carnes_erro"):
                carnes_erro = resultado.get("detalhes_carnes_erro", [])

            # Gera anexos se houver dados (incluindo contratos rejeitados)
            anexos = {}
            if carnes_sucesso or carnes_erro or contratos_rejeitados:
                try:
                    anexos = gerador_anexos.gerar_anexo_carnes(
                        carnes_sucesso=carnes_sucesso,
                        carnes_erro=carnes_erro,
                        # ✅ NOVO: Incluir contratos rejeitados
                        contratos_rejeitados=contratos_rejeitados
                    )
                    log(f"📎 Anexos gerados: {anexos}")
                except Exception as e:
                    log(f"⚠️ Erro ao gerar anexos: {e}")

            # Gera relatório HTML
            estatisticas = {
                'total_empresas': len(empresas_info),
                'carnes_sucesso': empresas_processadas,
                'carnes_erro': len([e for e in empresas_info.keys() if e not in resultado.get("empresas_processadas_lista", [])]),
                'total_contratos': total_reparcelados,
                'contratos_aptos': len(contratos_aptos),
                'contratos_rejeitados': len(contratos_rejeitados)
            }

            html_relatorio = templates_relatorios.relatorio_carnes(
                estatisticas, anexos)

            # Salva relatório HTML
            diretorio_relatorios = Path("outputs/relatorios")
            diretorio_relatorios.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_html = diretorio_relatorios / \
                f"relatorio_carnes_{timestamp}.html"

            with open(arquivo_html, 'w', encoding='utf-8') as f:
                f.write(html_relatorio)

            log(f"📄 Relatório HTML salvo: {arquivo_html}")

            # Criar função para notificar com relatório HTML como anexo
            from core.notificacoes_simples import notificar_sucesso

            # Preparar resultados com anexos
            resultados_email = {
                "titulo": f"✅ FASE 3 CONCLUÍDA: Geração de carnês",
                "mensagem": f"Contratos: {sucessos} | Empresas: {empresas_processadas} | Taxa: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%",
                "relatorio": html_relatorio,  # Incluir o relatório HTML completo
                "arquivo_html": str(arquivo_html),  # Caminho do arquivo HTML
                # Incluir os arquivos anexos (TXT, Excel, etc.)
                "caminhos_anexos": anexos
            }

            # Notificar com relatório HTML e arquivos anexados
            notificar_sucesso(
                nome_rpa="RPA Sienge",
                tempo_execucao="-",
                resultados=resultados_email
            )

            return {
                "sucesso": True,
                "autorizado": autorizado,
                "contratos_processados": sucessos,
                "contratos_erro": erros,
                "empresas_processadas": empresas_processadas,
                "contratos_atualizados": contratos_atualizados,
                "contratos_aptos": len(contratos_aptos),
                "contratos_rejeitados": len(contratos_rejeitados),
                "detalhes_rejeitados": contratos_rejeitados,
                "detalhes": resultado,
                "relatorio_html": str(arquivo_html),
                "anexos": anexos
            }
        else:
            erro_msg = resultado.get(
                "erro", "Erro desconhecido na geração de carnês")
            autorizado = resultado.get("autorizado", False)

            if not autorizado:
                log(f"❌ FASE 3 INTERROMPIDA: Reparcelamento não autorizado")
                notificar_erro_simples(
                    f"❌ FASE 3 INTERROMPIDA: Reparcelamento não autorizado",
                    f"Erro: {erro_msg}"
                )
            else:
                log(f"❌ FASE 3 FALHOU: {erro_msg}")
                notificar_erro_simples(
                    f"❌ FASE 3 FALHOU: Geração de carnês",
                    f"Erro: {erro_msg}"
                )

            return {"sucesso": False, "autorizado": autorizado, "erro": erro_msg}

    except Exception as e:
        erro_msg = f"Erro crítico na fase de geração de carnês: {str(e)}"
        log(f"💥 {erro_msg}")

        notificar_erro_simples(
            f"💥 FASE 3 ERRO CRÍTICO",
            erro_msg
        )

        return {"sucesso": False, "erro": erro_msg}

    finally:
        # Finalizar RPA se foi inicializado
        if 'rpa' in locals():
            await rpa.finalizar()


async def obter_empresas_reparceladas(filtro_data: Optional[str] = None) -> tuple[Dict[str, int], Optional[str], Optional[list]]:
    """
    Obtém informações sobre empresas com contratos reparcelados

    Args:
        filtro_data: Filtro de data no formato DD-MM (opcional)
    """
    try:
        from core.mongodb_manager import MongoDBManager

        # Criar instância LOCAL do MongoDB (não usar a global)
        mongodb = MongoDBManager()
        await mongodb.conectar()

        if not mongodb.conectado or mongodb.database is None:
            raise Exception("MongoDB não conectado ou database indisponível")

        collection = mongodb.database.fila_contratos

        # Construir filtro base
        match_filter = {"status": "REPARCELADO"}
        log(f"🔍 Filtro MongoDB: {match_filter}")

        # Se há filtro de data, primeiro ler a planilha para filtrar por mês reajuste e 1º vencimento carnê
        if filtro_data:
            dia, mes = filtro_data.split('-')
            dia_int = int(dia)
            mes_int = int(mes)

            log(
                f"📅 Aplicando filtro de data: {filtro_data} (dia {dia_int}, mês {mes_int})")

            # Converter mês numérico para formato da planilha (ex: 9 -> "set.-25")
            meses_planilha = {
                1: "jan.-25", 2: "fev.-25", 3: "mar.-25", 4: "abr.-25",
                5: "mai.-25", 6: "jun.-25", 7: "jul.-25", 8: "ago.-25",
                9: "set.-25", 10: "out.-25", 11: "nov.-25", 12: "dez.-25"
            }

            mes_planilha = meses_planilha.get(mes_int, f"{mes_int:02d}-25")
            log(f"📅 Mês na planilha: {mes_planilha}")

            # LER PLANILHA para obter códigos dos clientes que atendem aos critérios
            try:
                from rpa_sienge.rpa_sienge import RPASienge

                # Inicializar RPA temporariamente para ler planilha
                rpa_temp = RPASienge(headless=True)
                await rpa_temp.inicializar()

                # Conectar ao Google Sheets
                await rpa_temp._conectar_google_sheets()

                # ID da planilha (usar variável de ambiente)
                planilha_id = os.getenv("PLANILHA_CALCULO_ID")
                if not planilha_id:
                    raise Exception("PLANILHA_CALCULO_ID não configurada")

                # Abrir planilha
                planilha = rpa_temp.cliente_sheets.open_by_key(planilha_id)
                aba_calculo = "Base de cálculo"

                try:
                    aba = planilha.worksheet(aba_calculo)
                except Exception as e:
                    raise Exception(
                        f"Planilha de cálculo não encontrada: {aba_calculo} ({e})")

                # Ler dados da planilha
                valores = aba.get_all_values()
                if not valores or len(valores) < 2:
                    raise Exception(
                        f"Planilha de cálculo vazia: {aba_calculo}")

                # Encontrar índices das colunas
                cabecalhos = valores[0]
                idx_mes_reajuste = None
                idx_primeiro_vencimento = None
                idx_codigo_cliente = None

                for i, cabecalho in enumerate(cabecalhos):
                    cabecalho_str = str(cabecalho).strip().upper()
                    if "MÊS REAJUSTE" in cabecalho_str:
                        idx_mes_reajuste = i
                    elif "1º VENCIMENTO CARNÊ" in cabecalho_str or "1º VENCIMENTO CARNE" in cabecalho_str:
                        idx_primeiro_vencimento = i
                    elif "CÓDIGO CLIENTE" in cabecalho_str or "CODIGO CLIENTE" in cabecalho_str:
                        idx_codigo_cliente = i

                if idx_mes_reajuste is None:
                    raise Exception(
                        "Coluna 'Mês reajuste' não encontrada na planilha")
                if idx_primeiro_vencimento is None:
                    raise Exception(
                        "Coluna '1º vencimento carnê' não encontrada na planilha")
                if idx_codigo_cliente is None:
                    raise Exception(
                        "Coluna 'Código Cliente' não encontrada na planilha")

                log(f"📋 Colunas encontradas na planilha:")
                log(f"   📅 Mês reajuste: índice {idx_mes_reajuste}")
                log(
                    f"   📅 1º vencimento carnê: índice {idx_primeiro_vencimento}")
                log(f"   👤 Código cliente: índice {idx_codigo_cliente}")

                # Filtrar linhas que atendem aos critérios
                codigos_clientes_filtrados = []
                data_vencimento_planilha = None  # Capturar data da planilha

                # Pular cabeçalho
                for linha_idx, linha in enumerate(valores[1:], start=2):
                    # ✅ CORREÇÃO: Verificar índices antes de usar max()
                    max_idx = 0
                    if idx_mes_reajuste is not None:
                        max_idx = max(max_idx, idx_mes_reajuste)
                    if idx_primeiro_vencimento is not None:
                        max_idx = max(max_idx, idx_primeiro_vencimento)
                    if idx_codigo_cliente is not None:
                        max_idx = max(max_idx, idx_codigo_cliente)

                    if len(linha) > max_idx:
                        # ✅ CORREÇÃO: Verificar se os índices são None antes de acessar
                        mes_reajuste = str(linha[idx_mes_reajuste]).strip(
                        ) if idx_mes_reajuste is not None else ""
                        primeiro_vencimento = str(linha[idx_primeiro_vencimento]).strip(
                        ) if idx_primeiro_vencimento is not None else ""
                        codigo_cliente = str(linha[idx_codigo_cliente]).strip(
                        ) if idx_codigo_cliente is not None else ""

                        # Verificar se mês reajuste corresponde ao filtro
                        if mes_reajuste == mes_planilha:
                            # Verificar se o dia do primeiro vencimento corresponde ao filtro
                            try:
                                # Tentar diferentes formatos de data
                                dia_vencimento = None

                                # Formato DD/MM/YYYY ou DD/MM/YY
                                if "/" in primeiro_vencimento:
                                    partes = primeiro_vencimento.split("/")
                                    if len(partes) >= 2:
                                        dia_vencimento = int(partes[0])

                                # Formato YYYY-MM-DD
                                elif "-" in primeiro_vencimento and len(primeiro_vencimento.split("-")[0]) == 4:
                                    partes = primeiro_vencimento.split("-")
                                    if len(partes) >= 3:
                                        dia_vencimento = int(partes[2])

                                # Formato DD-MM (sem ano)
                                elif "-" in primeiro_vencimento and len(primeiro_vencimento.split("-")[0]) <= 2:
                                    partes = primeiro_vencimento.split("-")
                                    if len(partes) >= 2:
                                        dia_vencimento = int(partes[0])

                                # Se o dia corresponde ao filtro, adicionar código do cliente
                                if dia_vencimento == dia_int:
                                    if codigo_cliente and codigo_cliente.strip():
                                        codigos_clientes_filtrados.append(
                                            codigo_cliente.strip())
                                        # ✅ CAPTURAR A DATA DA PLANILHA
                                        if data_vencimento_planilha is None:
                                            data_vencimento_planilha = primeiro_vencimento
                                        log(
                                            f"✅ Cliente {codigo_cliente} atende aos critérios: mês {mes_reajuste}, dia {dia_vencimento}")

                            except (ValueError, IndexError) as e:
                                log(
                                    f"⚠️ Erro ao processar data '{primeiro_vencimento}' na linha {linha_idx}: {e}")
                                continue

                log(
                    f"🔍 Total de clientes filtrados na planilha: {len(codigos_clientes_filtrados)}")
                if data_vencimento_planilha:
                    log(
                        f"📅 Data de vencimento da planilha: {data_vencimento_planilha}")

                # Fechar RPA temporário
                await rpa_temp.finalizar()

                # Se encontrou clientes filtrados, usar seus códigos para filtrar no MongoDB
                if codigos_clientes_filtrados:
                    # Manter códigos como strings (MongoDB armazena como string)
                    codigos_numericos = []
                    for codigo in codigos_clientes_filtrados:
                        # Manter como string, apenas garantir que não esteja vazio
                        codigo_limpo = str(codigo).strip()
                        if codigo_limpo:
                            codigos_numericos.append(codigo_limpo)

                    # Buscar contratos por códigos de cliente (sem filtro de status para contornar problema do $in)
                    log(
                        f"🎯 Buscando contratos por códigos: {codigos_numericos}")

                    # Buscar todos os contratos com esses códigos (sem filtro de status)
                    # CORREÇÃO: Usar busca direta na collection em vez do método que está falhando
                    contratos_encontrados = []
                    for codigo in codigos_numericos:
                        contrato = mongodb.database.fila_contratos.find_one(
                            {"codigo_cliente": codigo})
                        if contrato:
                            # Converter ObjectId para string
                            if "_id" in contrato:
                                contrato["_id"] = str(contrato["_id"])
                            # ✅ ADICIONAR DADOS DA PLANILHA AO CONTRATO
                            if data_vencimento_planilha:
                                contrato["data_vencimento_planilha"] = data_vencimento_planilha

                            # ✅ CORREÇÃO: Adicionar empresa_planilha ao contrato
                            # Buscar a linha correspondente na planilha para obter a empresa
                            # Verificar se existe a coluna Empresa na planilha
                            idx_empresa = None
                            for i, cabecalho in enumerate(cabecalhos):
                                cabecalho_str = str(cabecalho).strip().upper()
                                if "EMPRESA" in cabecalho_str:
                                    idx_empresa = i
                                    break

                            if idx_empresa is not None:
                                for linha in valores[1:]:
                                    if idx_codigo_cliente is not None and len(linha) > idx_codigo_cliente and str(linha[idx_codigo_cliente]).strip() == codigo:
                                        # Adicionar empresa da planilha ao contrato
                                        if len(linha) > idx_empresa:
                                            contrato["empresa_planilha"] = str(
                                                linha[idx_empresa]).strip()
                                            log(
                                                f"✅ Adicionada empresa da planilha ao contrato: {contrato['empresa_planilha']}")
                            contratos_encontrados.append(contrato)
                            log(
                                f"✅ Contrato encontrado para código {codigo}: {contrato.get('cliente', 'N/A')}")
                        else:
                            log(
                                f"⚠️ Nenhum contrato encontrado para código {codigo}")

                    if not contratos_encontrados:
                        log(
                            f"❌ Nenhum contrato encontrado para os códigos de cliente: {codigos_numericos}")
                        # ✅ CORREÇÃO: Retornar uma tupla para manter consistência
                        return {}, None, None

                    log(f"✅ Encontrados {len(contratos_encontrados)} contratos no total")

                    # Filtrar em Python para manter apenas os com status REPARCELADO
                    contratos_reparcelados = [
                        contrato for contrato in contratos_encontrados
                        if contrato.get("status") == "REPARCELADO"
                    ]

                    log(f"✅ Encontrados {len(contratos_reparcelados)} contratos com status REPARCELADO")

                    # Agrupar por empresa e contar contratos
                    empresas_contadores = {}
                    for contrato in contratos_reparcelados:
                        # ✅ CORREÇÃO: Usar empresa_planilha em vez de empresa
                        empresa = contrato.get("empresa_planilha")
                        if empresa:
                            if empresa not in empresas_contadores:
                                empresas_contadores[empresa] = 0
                            empresas_contadores[empresa] += 1

                    log(f"📊 Agrupamento por empresa: {empresas_contadores}")

                    # ✅ RETORNAR TAMBÉM A DATA DA PLANILHA
                    return empresas_contadores, data_vencimento_planilha, contratos_reparcelados

                else:
                    log(
                        f"⚠️ Nenhum cliente encontrado na planilha com mês {mes_planilha} e dia {dia_int}")
                    # ✅ CORREÇÃO: Retornar uma tupla para manter consistência
                    return {}, None, None  # Retornar vazio se não há clientes filtrados

            except Exception as e:
                log(f"⚠️ Erro ao ler planilha para filtro: {str(e)}")
                log(f"📋 Continuando sem filtro de data...")
                # Se falhar ao ler planilha, continuar sem filtro

        # ✅ NOVA LÓGICA: Buscar contratos REPARCELADO no MongoDB e confrontar com planilha
        log(f"📋 FASE 1: Buscando contratos REPARCELADO no MongoDB...")

        # 1. Buscar todos os contratos com status REPARCELADO
        contratos_mongodb = list(
            mongodb.database.fila_contratos.find({"status": "REPARCELADO"}))
        log(f"🔍 Encontrados {len(contratos_mongodb)} contratos REPARCELADO no MongoDB")

        if not contratos_mongodb:
            log("⚠️ Nenhum contrato REPARCELADO encontrado no MongoDB")
            return {}, None, []

        # Mostrar primeiros contratos para debug
        for i, contrato in enumerate(contratos_mongodb[:3]):
            log(f"   📋 Contrato {i+1}: {contrato.get('codigo_cliente', 'N/A')} - {contrato.get('cliente', 'N/A')} - Título: {contrato.get('numero_titulo', 'N/A')}")

        log(f"📋 FASE 2: Lendo planilha base de cálculo...")

        try:
            # 2. Conectar ao Google Sheets
            import gspread
            from google.oauth2.service_account import Credentials

            credenciais_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
            if not credenciais_path:
                raise Exception("GOOGLE_CREDENTIALS_PATH não configurada")

            scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_file(
                credenciais_path, scopes=scope)
            cliente_sheets = gspread.authorize(creds)

            log("✅ Conectado ao Google Sheets com sucesso")

            # ID da planilha (usar variável de ambiente)
            planilha_id = os.getenv("PLANILHA_CALCULO_ID")
            if not planilha_id:
                raise Exception("PLANILHA_CALCULO_ID não configurada")

            planilha = cliente_sheets.open_by_key(planilha_id)
            log(f"📊 Planilha aberta: {planilha.title}")

            aba = planilha.worksheet("Base de cálculo")
            log(f"📋 Aba 'Base de cálculo' encontrada")

            # 3. Ler todos os dados da planilha
            dados_planilha_brutos = aba.get_all_records()
            log(
                f"📊 Total de registros na planilha: {len(dados_planilha_brutos)}")

            if dados_planilha_brutos:
                log(f"🔍 Primeiro registro: {dados_planilha_brutos[0]}")
                log(
                    f"🔍 Colunas disponíveis: {list(dados_planilha_brutos[0].keys())}")

            # 4. Indexar planilha por código cliente para busca rápida
            planilha_indexada = {}
            for registro in dados_planilha_brutos:
                cod_cliente_raw = registro.get("Código Cliente", "")
                cod_cliente = str(cod_cliente_raw).strip(
                ) if cod_cliente_raw is not None else ""
                if cod_cliente:
                    planilha_indexada[cod_cliente] = registro

            log(f"📋 Planilha indexada: {len(planilha_indexada)} registros")

            # 5. Confrontar MongoDB com planilha
            log(f"📋 FASE 3: Confrontando contratos MongoDB com planilha...")

            contratos_validos = []
            contratos_nao_encontrados = []

            for contrato_mongo in contratos_mongodb:
                cod_cliente = str(contrato_mongo.get(
                    "codigo_cliente", "")).strip()
                numero_titulo = str(contrato_mongo.get(
                    "numero_titulo", "")).strip()

                # Buscar na planilha
                if cod_cliente in planilha_indexada:
                    dados_planilha = planilha_indexada[cod_cliente]

                    # Verificar se o título também confere (se disponível na planilha)
                    titulo_planilha = str(
                        dados_planilha.get("Título", "")).strip()

                    if not titulo_planilha or titulo_planilha == numero_titulo:
                        # Contrato válido - adicionar dados da planilha
                        contrato_completo = contrato_mongo.copy()
                        contrato_completo["dados_planilha"] = dados_planilha
                        contrato_completo["_id"] = str(
                            contrato_completo["_id"])  # Converter ObjectId

                        contratos_validos.append(contrato_completo)
                        log(
                            f"✅ Contrato válido: {cod_cliente} - {contrato_mongo.get('cliente', 'N/A')}")
                    else:
                        log(
                            f"⚠️ Título não confere: {cod_cliente} - MongoDB: {numero_titulo} vs Planilha: {titulo_planilha}")
                        contratos_nao_encontrados.append(contrato_mongo)
                else:
                    log(
                        f"❌ Contrato não encontrado na planilha: {cod_cliente} - {contrato_mongo.get('cliente', 'N/A')}")
                    contratos_nao_encontrados.append(contrato_mongo)

            log(f"📊 RESULTADO DO CONFRONTO:")
            log(f"   ✅ Contratos válidos: {len(contratos_validos)}")
            log(
                f"   ❌ Contratos não encontrados: {len(contratos_nao_encontrados)}")

            # 6. Agrupar por empresa
            empresas_contadores = {}
            for contrato in contratos_validos:
                empresa = contrato.get("empresa", "")
                if empresa:
                    if empresa not in empresas_contadores:
                        empresas_contadores[empresa] = 0
                    empresas_contadores[empresa] += 1

            log(f"🏢 Agrupados em {len(empresas_contadores)} empresas")
            for empresa, count in list(empresas_contadores.items())[:5]:
                log(f"   🏢 {empresa}: {count} contratos")

            return empresas_contadores, None, contratos_validos

        except Exception as e:
            log(f"❌ Erro ao ler planilha: {str(e)}")
            log(f"🔍 Traceback: {traceback.format_exc()}")
            raise Exception(f"Falha ao ler planilha base de cálculo: {str(e)}")

    except Exception as e:
        log(f"❌ Erro ao obter empresas reparceladas: {str(e)}")
        log(f"🔍 Traceback: {traceback.format_exc()}")
        raise Exception(f"Falha ao obter empresas reparceladas: {str(e)}")
    finally:
        # Fechar conexão MongoDB
        if 'mongodb' in locals() and mongodb.conectado:
            await mongodb.desconectar()


async def main():
    """
    MAIN DE GERAÇÃO DE CARNÊS: Execução isolada da fase de geração de carnê
    """
    inicio_execucao = datetime.now()

    # Parse dos argumentos de linha de comando
    parser = argparse.ArgumentParser(
        description='RPA Sienge - Geração de Carnês com Verificação de Pendências',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos de uso:
  python main_sienge_carnes.py                                # Processar todos os contratos reparcelados
  python main_sienge_carnes.py -d 05-09                       # Apenas contratos com vencimento dia 5/9
  
NOTA: Agora a verificação de pendências é feita diretamente na planilha base de cálculo.
Não é mais necessário atualizar inadimplência separadamente.
        '''
    )

    parser.add_argument(
        '-d', '--data-vencimento',
        type=str,
        help='Filtrar contratos por data de vencimento (formato: DD-MM ou DD/MM). Ex: 05-09 ou 10/12'
    )

    # ✅ REMOVIDO: Argumentos para atualização de inadimplência e verificação IPTU
    # Agora a verificação é feita diretamente na planilha base de cálculo

    # ✅ REMOVIDO: Argumento max-arquivos (não mais necessário)

    args = parser.parse_args()

    # Validar data de vencimento se fornecida
    if args.data_vencimento:
        data_validada = validar_formato_data(args.data_vencimento)
        if not data_validada:
            parser.error(f"Formato de data inválido: '{args.data_vencimento}'. "
                         f"Use o formato DD-MM ou DD/MM (ex: 05-09 ou 10/12)")
        args.data_vencimento = data_validada

    log("🎫 RPA SIENGE - GERAÇÃO DE CARNÊS ISOLADA")

    # ✅ NOVO: Verificação de pendências integrada na geração de carnês
    log("🔍 NOVO FLUXO: Verificação de pendências diretamente na planilha base de cálculo")

    # Modo padrão: geração de carnês
    log("🎯 Fase 3: Processamento de contratos REPARCELADO → CARNE_GERADO")
    if args.data_vencimento:
        log(
            f"📅 FILTRO DE DATA: Apenas contratos com vencimento {args.data_vencimento}")
    log("=" * 60)

    try:
        # Carregar credenciais
        credenciais = await carregar_credenciais_sienge()

        # Configurar credenciais do Google Sheets
        credenciais_path = os.path.join(os.path.dirname(
            __file__), "..", "credentials", "gspread-459713-aab8a657f9b0.json")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credenciais_path

        # Obter informações sobre empresas reparceladas (com filtro de data se especificado)
        empresas_info, data_vencimento_planilha, contratos_reparcelados = await obter_empresas_reparceladas(filtro_data=args.data_vencimento)
        total_reparcelados = sum(
            empresas_info.values()) if empresas_info else 0

        if total_reparcelados == 0:
            log("⚠️ Nenhum contrato reparcelado encontrado - não há carnês para gerar")
            notificar_sucesso_simples(
                "✅ RPA SIENGE: Nenhum carnê para gerar",
                "Não há contratos reparcelados na fila"
            )
            return 0  # Sucesso (não é erro, apenas não há trabalho)

        log(f"🔍 Encontrados {total_reparcelados} contratos reparcelados em {len(empresas_info)} empresas")
        # Mostrar as 5 primeiras
        for empresa, count in list(empresas_info.items())[:5]:
            log(f"   📋 {empresa}: {count} contratos")

        # Executar geração de carnês
        resultado = await executar_fase_geracao_carnes(
            credenciais,
            total_reparcelados,
            empresas_info,
            filtro_data=args.data_vencimento,
            contratos_filtrados=contratos_reparcelados if 'contratos_reparcelados' in locals() else None,
            data_vencimento_planilha=data_vencimento_planilha if 'data_vencimento_planilha' in locals() else None
        )

        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        if resultado.get("sucesso"):
            sucessos = resultado.get("contratos_processados", 0)
            erros = resultado.get("contratos_erro", 0)
            empresas_processadas = resultado.get("empresas_processadas", 0)
            autorizado = resultado.get("autorizado", False)
            contratos_aptos = resultado.get("contratos_aptos", 0)
            contratos_rejeitados = resultado.get("contratos_rejeitados", 0)
            relatorio_html = resultado.get("relatorio_html", "N/A")
            anexos = resultado.get("anexos", {})

            log(f"\n🎉 GERAÇÃO DE CARNÊS CONCLUÍDA COM SUCESSO!")
            log(f"⏱️ Duração: {duracao}")
            log(f"✅ Autorizado: {autorizado}")
            log(f"✅ Contratos processados: {sucessos}")
            log(f"❌ Contratos com erro: {erros}")
            log(f"🏢 Empresas processadas: {empresas_processadas}")
            log(f"📊 Taxa de sucesso: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%")
            log(f"✅ Contratos aptos para carnê: {contratos_aptos}")
            log(f"❌ Contratos rejeitados: {contratos_rejeitados}")
            log(f"📄 Relatório HTML: {relatorio_html}")
            log(f"📎 Anexos gerados: {len(anexos)}")

            # Envia notificação com relatório HTML e informações dos anexos
            resultados_notificacao = {
                "mensagem": f"Geração de carnês concluída com sucesso - {sucessos} contratos processados",
                "relatorio_html": relatorio_html,
                "anexos_gerados": len(anexos),
                "estatisticas": {
                    "empresas_processadas": empresas_processadas,
                    "contratos_processados": sucessos,
                    "contratos_erro": erros,
                    "contratos_aptos": contratos_aptos,
                    "contratos_rejeitados": contratos_rejeitados,
                    "taxa_sucesso": f"{(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%",
                    "duracao": str(duracao)
                }
            }

            if anexos:
                resultados_notificacao["caminhos_anexos"] = anexos

                # Notificar com relatório HTML e arquivos anexados
            from core.notificacoes_simples import notificar_sucesso

            # Preparar resultados com anexos
            resultados_email = {
                "titulo": f"🎉 RPA SIENGE: Geração de carnês concluída",
                "mensagem": f"Duração: {duracao} | Contratos: {sucessos} | Empresas: {empresas_processadas} | Taxa: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}% | Aptos: {contratos_aptos} | Rejeitados: {contratos_rejeitados}",
                "relatorio": open(relatorio_html, 'r', encoding='utf-8').read() if os.path.exists(relatorio_html) else "",
                "arquivo_html": relatorio_html,
                # Incluir os arquivos anexos (TXT, Excel, etc.)
                "caminhos_anexos": anexos
            }

            # Notificar com relatório HTML e arquivos anexados
            notificar_sucesso(
                nome_rpa="RPA Sienge",
                tempo_execucao=str(duracao),
                resultados=resultados_email
            )

            return 0  # Sucesso
        else:
            erro_msg = resultado.get("erro", "Erro desconhecido")
            autorizado = resultado.get("autorizado", False)

            if not autorizado:
                log(f"\n❌ GERAÇÃO DE CARNÊS INTERROMPIDA: Reparcelamento não autorizado")
                log(f"⏱️ Duração: {duracao}")
                log(f"❌ Erro: {erro_msg}")

                # Gera relatório de erro para não autorizado
                html_erro = templates_relatorios.relatorio_erro(
                    "RPA Sienge - Geração de Carnês",
                    "Reparcelamento não autorizado",
                    f"Erro: {erro_msg}\nDuração até erro: {duracao}"
                )

                # Salva relatório de erro
                diretorio_relatorios = Path("outputs/relatorios")
                diretorio_relatorios.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                arquivo_html_erro = diretorio_relatorios / \
                    f"erro_nao_autorizado_carnes_{timestamp}.html"

                with open(arquivo_html_erro, 'w', encoding='utf-8') as f:
                    f.write(html_erro)

                log(f"📄 Relatório de erro HTML salvo: {arquivo_html_erro}")

                notificar_erro_simples(
                    f"❌ RPA SIENGE: Geração de carnês interrompida",
                    f"Reparcelamento não autorizado - {erro_msg} | Duração: {duracao} | Relatório: {arquivo_html_erro}"
                )

                return 0  # Sucesso (não é erro, apenas não autorizado)
            else:
                log(f"\n❌ GERAÇÃO DE CARNÊS FALHOU")
                log(f"⏱️ Duração: {duracao}")
                log(f"❌ Erro: {erro_msg}")

                # Gera relatório de erro
                html_erro = templates_relatorios.relatorio_erro(
                    "RPA Sienge - Geração de Carnês",
                    erro_msg,
                    f"Duração até erro: {duracao}"
                )

                # Salva relatório de erro
                diretorio_relatorios = Path("outputs/relatorios")
                diretorio_relatorios.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                arquivo_html_erro = diretorio_relatorios / \
                    f"erro_carnes_{timestamp}.html"

                with open(arquivo_html_erro, 'w', encoding='utf-8') as f:
                    f.write(html_erro)

                log(f"📄 Relatório de erro HTML salvo: {arquivo_html_erro}")

                notificar_erro_simples(
                    f"❌ RPA SIENGE: Geração de carnês falhou",
                    f"Erro: {erro_msg} | Duração: {duracao} | Relatório de erro: {arquivo_html_erro}"
                )

                return 1  # Falha

    except Exception as e:
        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        log(f"💥 ERRO CRÍTICO NA GERAÇÃO DE CARNÊS: {str(e)}")
        log(f"⏱️ Duração até erro: {duracao}")

        # Gera relatório de erro
        html_erro = templates_relatorios.relatorio_erro(
            "RPA Sienge - Geração de Carnês",
            f"Erro crítico: {str(e)}",
            f"Duração até erro: {duracao}"
        )

        # Salva relatório de erro
        diretorio_relatorios = Path("outputs/relatorios")
        diretorio_relatorios.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_html_erro = diretorio_relatorios / \
            f"erro_critico_carnes_{timestamp}.html"

        with open(arquivo_html_erro, 'w', encoding='utf-8') as f:
            f.write(html_erro)

        log(f"📄 Relatório de erro crítico HTML salvo: {arquivo_html_erro}")

        notificar_erro_simples(
            f"💥 RPA SIENGE: Erro crítico na geração de carnês",
            f"Erro: {str(e)} | Duração: {duracao} | Relatório de erro: {arquivo_html_erro}"
        )

        return 1  # Erro crítico


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"Erro fatal: {e}")
        sys.exit(1)
