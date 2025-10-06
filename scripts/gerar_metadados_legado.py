#!/usr/bin/env python3
"""
Script para gerar metadados legado de arquivos de remessa já processados
Gera arquivos JSON de metadados baseado em contratos com status CARNE_GERADO

Desenvolvido em Português Brasileiro
"""

from core.mongodb_manager import MongoDBManager
from core.utils_sienge import log, get_env_or_fail
import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def buscar_contratos_carne_gerado() -> List[Dict[str, Any]]:
    """
    Buscar contratos com status CARNE_GERADO no banco

    Returns:
        Lista de contratos com status CARNE_GERADO
    """
    log("\n💾 BUSCANDO CONTRATOS COM STATUS CARNE_GERADO...")
    log("=" * 60)

    try:
        # Conectar ao MongoDB
        mongo_manager = MongoDBManager()
        await mongo_manager.conectar()
        db = mongo_manager.database
        colecao = db.fila_contratos

        # Buscar contratos com status CARNE_GERADO
        contratos_carne_gerado = list(colecao.find({"status": "CARNE_GERADO"}))

        if not contratos_carne_gerado:
            log("⚠️ Nenhum contrato com status CARNE_GERADO encontrado no banco")
            return []

        log(f"✅ Encontrados {len(contratos_carne_gerado)} contratos com status CARNE_GERADO:")
        for i, contrato in enumerate(contratos_carne_gerado[:5], 1):
            codigo_cliente = contrato.get('codigo_cliente', 'N/A')
            cliente = contrato.get('cliente', 'N/A')
            numero_titulo = contrato.get('numero_titulo', 'N/A')
            arquivo_remessa = contrato.get('arquivo_remessa', 'N/A')
            log(f"   {i}. {codigo_cliente} - {cliente} (Título: {numero_titulo}) - Arquivo: {arquivo_remessa}")

        if len(contratos_carne_gerado) > 5:
            log(f"   ... e mais {len(contratos_carne_gerado) - 5} contratos")

        return contratos_carne_gerado

    except Exception as e:
        log(f"❌ Erro ao buscar contratos CARNE_GERADO: {str(e)}")
        raise Exception(f"Erro ao buscar contratos CARNE_GERADO: {str(e)}")


async def carregar_dados_planilha_base_calculo() -> Dict[str, Any]:
    """
    Carregar dados da planilha base de cálculo

    Returns:
        Dados indexados da planilha por código_cliente + número_titulo
    """
    log("\n📋 CARREGANDO DADOS DA PLANILHA BASE DE CÁLCULO...")
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

        # Indexar dados por código_cliente + número_titulo para busca rápida
        dados_indexados = {}
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
        raise Exception(f"Erro ao carregar dados da planilha: {str(e)}")


def associar_contratos_com_planilha(contratos_carne_gerado: List[Dict[str, Any]],
                                    dados_planilha: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Associar contratos do banco com dados da planilha

    Args:
        contratos_carne_gerado: Lista de contratos do banco
        dados_planilha: Dados indexados da planilha

    Returns:
        Lista de contratos com dados da planilha associados
    """
    log("\n🔗 ASSOCIANDO CONTRATOS COM DADOS DA PLANILHA...")
    log("=" * 60)

    contratos_associados = []
    contratos_nao_encontrados = []

    for contrato in contratos_carne_gerado:
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

    return contratos_associados


def agrupar_contratos_por_arquivo_remessa(contratos_associados: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupar contratos por arquivo de remessa

    Args:
        contratos_associados: Lista de contratos com dados da planilha

    Returns:
        Dicionário com arquivo_remessa como chave e lista de contratos como valor
    """
    log("\n📁 AGRUPANDO CONTRATOS POR ARQUIVO DE REMESSA...")
    log("=" * 60)

    contratos_por_arquivo = {}

    for contrato in contratos_associados:
        arquivo_remessa = contrato.get('arquivo_remessa', '')

        if not arquivo_remessa:
            log(f"⚠️ Contrato {contrato.get('numero_titulo', 'N/A')} sem arquivo_remessa")
            continue

        if arquivo_remessa not in contratos_por_arquivo:
            contratos_por_arquivo[arquivo_remessa] = []

        contratos_por_arquivo[arquivo_remessa].append(contrato)

    log(f"✅ Encontrados {len(contratos_por_arquivo)} arquivos de remessa únicos:")
    for arquivo, contratos in contratos_por_arquivo.items():
        log(f"   📄 {arquivo}: {len(contratos)} contratos")

    return contratos_por_arquivo


def gerar_metadados_arquivo(arquivo_remessa: str, contratos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Gerar metadados para um arquivo de remessa específico

    Args:
        arquivo_remessa: Nome do arquivo de remessa
        contratos: Lista de contratos associados a este arquivo

    Returns:
        Metadados do arquivo de remessa
    """
    log(f"\n📋 GERANDO METADADOS PARA: {arquivo_remessa}")
    log("=" * 60)

    # Extrair informações do primeiro contrato (todos devem ter a mesma empresa)
    primeiro_contrato = contratos[0]
    dados_planilha = primeiro_contrato.get('dados_planilha', {})

    empresa = dados_planilha.get('Empresa', 'N/A')
    codigo_empresa = empresa.split(' - ')[0] if ' - ' in empresa else empresa

    # Extrair datas do primeiro vencimento carnê
    primeiro_vencimento = dados_planilha.get('1º vencimento carnê', '')

    # Calcular datas conforme PDD 10.2
    data_inicial = ""
    data_final = ""

    if primeiro_vencimento:
        try:
            from datetime import datetime
            if "/" in primeiro_vencimento:
                if len(primeiro_vencimento.split("/")[2]) == 2:
                    data_inicial_dt = datetime.strptime(
                        primeiro_vencimento, "%d/%m/%y")
                else:
                    data_inicial_dt = datetime.strptime(
                        primeiro_vencimento, "%d/%m/%Y")

                data_inicial = data_inicial_dt.strftime("%d/%m/%Y")

                # Data final: mesma data do mês anterior no ano seguinte
                if data_inicial_dt.month == 1:
                    data_final_dt = data_inicial_dt.replace(
                        year=data_inicial_dt.year, month=12)
                else:
                    data_final_dt = data_inicial_dt.replace(
                        year=data_inicial_dt.year + 1, month=data_inicial_dt.month - 1)

                data_final = data_final_dt.strftime("%d/%m/%Y")
        except Exception as e:
            log(f"⚠️ Erro ao calcular datas: {str(e)}")

    # Extrair títulos validados
    titulos_validados = [contrato.get('numero_titulo', '')
                         for contrato in contratos]
    titulos_validados = [titulo for titulo in titulos_validados if titulo]

    # Criar metadados
    metadados = {
        "timestamp_geracao": datetime.now().isoformat(),
        "empresa": empresa,
        "codigo_empresa": codigo_empresa,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "total_contratos_processados": len(contratos),
        "titulos_validados": titulos_validados,
        "contratos_detalhados": []
    }

    # Adicionar detalhes de cada contrato
    for contrato in contratos:
        metadados["contratos_detalhados"].append({
            "numero_titulo": contrato.get('numero_titulo', ''),
            "cliente": contrato.get('cliente', ''),
            "codigo_cliente": contrato.get('codigo_cliente', ''),
            "empresa": contrato.get('empresa', ''),
            "status": contrato.get('status', ''),
            "dados_planilha": contrato.get('dados_planilha', {})
        })

    log(f"✅ Metadados gerados para {arquivo_remessa}:")
    log(f"   🏢 Empresa: {empresa}")
    log(f"   📊 Contratos: {len(contratos)}")
    log(f"   📅 Período: {data_inicial} → {data_final}")

    return metadados


def salvar_metadados_arquivo(metadados: Dict[str, Any], arquivo_remessa: str) -> str:
    """
    Salvar metadados em arquivo JSON

    Args:
        metadados: Metadados do arquivo de remessa
        arquivo_remessa: Nome do arquivo de remessa

    Returns:
        Caminho do arquivo JSON salvo
    """
    try:
        # Criar diretório para metadados se não existir
        metadados_dir = "dados_extraidos/metadados_remessa"
        os.makedirs(metadados_dir, exist_ok=True)

        # Extrair nome base do arquivo (sem extensão)
        nome_arquivo_base = Path(arquivo_remessa).stem

        # Nome do arquivo JSON
        nome_arquivo_json = f"dados_{nome_arquivo_base}.json"
        caminho_arquivo = os.path.join(metadados_dir, nome_arquivo_json)

        # Salvar metadados
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(metadados, f, indent=2, ensure_ascii=False)

        # Incluir caminho dos metadados nos metadados
        metadados["caminho_arquivo_metadados"] = caminho_arquivo

        # Salvar novamente com o caminho incluído
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(metadados, f, indent=2, ensure_ascii=False)

        log(f"✅ Metadados salvos: {caminho_arquivo}")
        log(f"📊 {metadados['total_contratos_processados']} contratos incluídos no arquivo de remessa")

        return caminho_arquivo

    except Exception as e:
        log(f"❌ Erro ao salvar metadados: {str(e)}")
        return ""


async def main():
    """
    MAIN: Gerar metadados legado para arquivos de remessa já processados
    """
    log("📋 GERADOR DE METADADOS LEGADO")
    log("🎯 Gerando arquivos JSON de metadados para arquivos de remessa já processados")
    log("=" * 60)

    try:
        # 1. Buscar contratos com status CARNE_GERADO
        contratos_carne_gerado = await buscar_contratos_carne_gerado()

        if not contratos_carne_gerado:
            log("✅ Nenhum contrato para processar. Execução concluída.")
            return 0

        # 2. Carregar dados da planilha
        dados_planilha = await carregar_dados_planilha_base_calculo()

        # 3. Associar contratos com planilha
        contratos_associados = associar_contratos_com_planilha(
            contratos_carne_gerado, dados_planilha)

        if not contratos_associados:
            log("⚠️ Nenhum contrato associado com dados da planilha")
            return 0

        # 4. Agrupar contratos por arquivo de remessa
        contratos_por_arquivo = agrupar_contratos_por_arquivo_remessa(
            contratos_associados)

        # 5. Gerar metadados para cada arquivo de remessa
        arquivos_metadados_gerados = []

        for arquivo_remessa, contratos in contratos_por_arquivo.items():
            log(f"\n🔄 PROCESSANDO ARQUIVO: {arquivo_remessa}")

            # Gerar metadados
            metadados = gerar_metadados_arquivo(arquivo_remessa, contratos)

            # Salvar metadados
            caminho_metadados = salvar_metadados_arquivo(
                metadados, arquivo_remessa)

            if caminho_metadados:
                arquivos_metadados_gerados.append({
                    "arquivo_remessa": arquivo_remessa,
                    "caminho_metadados": caminho_metadados,
                    "total_contratos": len(contratos)
                })

        # 6. Relatório final
        log(f"\n🎉 GERAÇÃO DE METADADOS LEGADO CONCLUÍDA!")
        log(
            f"📊 Arquivos de remessa processados: {len(arquivos_metadados_gerados)}")
        log(f"📊 Total de contratos processados: {len(contratos_associados)}")

        log(f"\n📄 ARQUIVOS DE METADADOS GERADOS:")
        for item in arquivos_metadados_gerados:
            log(f"   📄 {item['arquivo_remessa']} → {item['caminho_metadados']} ({item['total_contratos']} contratos)")

        return 0  # Sucesso

    except Exception as e:
        log(f"\n❌ GERAÇÃO DE METADADOS LEGADO FALHOU")
        log(f"❌ Erro: {str(e)}")
        return 1  # Falha


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
