
"""
Utilitários de Auditoria Completa
Sistema para consultar e recuperar TODAS as informações dos RPAs

Desenvolvido em Português Brasileiro
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.data_manager import data_manager


class ConsultorAuditoriaCompleta:
    """
    Consultor que acessa TODAS as informações de auditoria
    MongoDB + JSON para recuperação completa
    """

    def __init__(self):
        self.pasta_auditoria = Path("dados_processamento/auditoria_completa")
        self.pasta_auditoria.mkdir(parents=True, exist_ok=True)

    async def obter_execucao_completa(self, id_execucao: str) -> Dict[str, Any]:
        """
        Obtém execução completa com TODOS os passos
        MongoDB primeiro, JSON como fallback
        """
        # Tentar MongoDB primeiro
        if data_manager.mongodb_ativo:
            try:
                from core.mongodb_manager import mongodb_manager

                def _get_execution():
                    # Busca consolidado
                    consolidado = mongodb_manager.database.execucoes_consolidadas_rpa.find_one({
                        "id_execucao": id_execucao
                    })

                    if consolidado:
                        return consolidado

                    # Busca passos individuais
                    passos = list(mongodb_manager.database.rastreamento_passos_rpa.find({
                        "id_execucao": id_execucao
                    }).sort("ordem_execucao", 1))

                    return {"passos": passos} if passos else None

                resultado = await asyncio.get_event_loop().run_in_executor(
                    None, _get_execution
                )

                if resultado:
                    return self._limpar_objectids(resultado)

            except Exception as e:
                print(f"⚠️ Erro MongoDB: {str(e)}")

        # Fallback JSON
        try:
            # Busca consolidado
            arquivo_consolidado = self.pasta_auditoria / \
                f"CONSOLIDADO_{id_execucao}.json"
            if arquivo_consolidado.exists():
                with open(arquivo_consolidado, 'r', encoding='utf-8') as f:
                    return json.load(f)

            # Busca arquivo individual
            arquivo_execucao = self.pasta_auditoria / f"{id_execucao}.json"
            if arquivo_execucao.exists():
                with open(arquivo_execucao, 'r', encoding='utf-8') as f:
                    return json.load(f)

        except Exception as e:
            print(f"⚠️ Erro JSON: {str(e)}")

        return {"erro": "Execução não encontrada", "id_procurado": id_execucao}

    async def obter_historico_contrato(self, numero_titulo: str) -> Dict[str, Any]:
        """
        Obtém histórico COMPLETO de um contrato específico
        """
        historico = {
            "numero_titulo": numero_titulo,
            "execucoes_rpa": [],
            "planilhas_extraidas": [],
            "calculos_realizados": [],
            "indices_aplicados": [],
            "timeline_completa": []
        }

        # Buscar execuções que mencionam este contrato
        execucoes = await self._buscar_execucoes_por_contrato(numero_titulo)
        historico["execucoes_rpa"] = execucoes

        # Buscar planilhas extraídas
        planilhas = await self._buscar_planilhas_por_contrato(numero_titulo)
        historico["planilhas_extraidas"] = planilhas

        # Buscar cálculos realizados
        calculos = await self._buscar_calculos_por_contrato(numero_titulo)
        historico["calculos_realizados"] = calculos

        # Montar timeline
        historico["timeline_completa"] = self._montar_timeline(
            execucoes, planilhas, calculos
        )

        return historico

    async def obter_estatisticas_auditoria(self, periodo_dias: int = 30) -> Dict[str, Any]:
        """
        Obtém estatísticas completas de auditoria
        """
        data_limite = datetime.now() - timedelta(days=periodo_dias)

        stats = {
            "periodo_analise": f"Últimos {periodo_dias} dias",
            "data_limite": data_limite.isoformat(),
            "execucoes_por_rpa": {},
            "contratos_processados": 0,
            "planilhas_extraidas": 0,
            "indices_coletados": 0,
            "taxa_sucesso_geral": 0,
            "erros_por_categoria": {},
            "sistema_origem": "hibrido_mongodb_json"
        }

        # Buscar execuções
        try:
            execucoes = await data_manager.obter_execucoes_recentes(limite=1000)

            for execucao in execucoes:
                timestamp = execucao.get("timestamp_inicio", "")
                if timestamp and datetime.fromisoformat(timestamp.replace('Z', '')) >= data_limite:
                    nome_rpa = execucao.get("nome_rpa", "Desconhecido")
                    stats["execucoes_por_rpa"][nome_rpa] = stats["execucoes_por_rpa"].get(
                        nome_rpa, 0) + 1

            # Calcular taxa de sucesso
            execucoes_periodo = [e for e in execucoes
                                 if e.get("timestamp_inicio", "") and
                                 datetime.fromisoformat(e["timestamp_inicio"].replace('Z', '')) >= data_limite]

            if execucoes_periodo:
                sucessos = sum(
                    1 for e in execucoes_periodo if e.get("sucesso", False))
                stats["taxa_sucesso_geral"] = round(
                    (sucessos / len(execucoes_periodo)) * 100, 2)

        except Exception as e:
            stats["erro_consulta"] = str(e)

        return stats

    async def buscar_execucoes_por_filtro(self, filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Busca execuções com filtros específicos
        """
        resultados = []

        # Buscar nos arquivos JSON
        try:
            for arquivo in self.pasta_auditoria.glob("*.json"):
                if arquivo.name.startswith("CONSOLIDADO_"):
                    continue

                with open(arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)

                if self._execucao_atende_filtros(dados, filtros):
                    resultados.append(dados)

        except Exception as e:
            print(f"⚠️ Erro na busca JSON: {str(e)}")

        # Buscar no MongoDB se disponível
        if data_manager.mongodb_ativo:
            try:
                mongo_results = await self._buscar_mongodb_por_filtros(filtros)
                resultados.extend(mongo_results)

            except Exception as e:
                print(f"⚠️ Erro na busca MongoDB: {str(e)}")

        # Remover duplicatas por id_execucao
        seen_ids = set()
        resultados_unicos = []
        for resultado in resultados:
            id_exec = resultado.get("id_execucao", "")
            if id_exec not in seen_ids:
                seen_ids.add(id_exec)
                resultados_unicos.append(resultado)

        return resultados_unicos

    async def gerar_relatorio_completo(self, numero_titulo: str = None,
                                       periodo_dias: int = 7) -> Dict[str, Any]:
        """
        Gera relatório completo para auditoria
        """
        relatorio = {
            "timestamp_geracao": datetime.now().isoformat(),
            "tipo_relatorio": "auditoria_completa",
            "periodo_dias": periodo_dias,
            "numero_titulo_filtro": numero_titulo
        }

        if numero_titulo:
            # Relatório específico de contrato
            relatorio["dados_contrato"] = await self.obter_historico_contrato(numero_titulo)
        else:
            # Relatório geral
            relatorio["estatisticas_gerais"] = await self.obter_estatisticas_auditoria(periodo_dias)

            # Últimas execuções por RPA
            relatorio["ultimas_execucoes"] = {}
            for rpa in ["RPA_Coleta_Indices", "RPA_Analise_Planilhas", "RPA_Sienge"]:
                execucoes = await self.buscar_execucoes_por_filtro({"nome_rpa": rpa})
                # Últimas 5
                relatorio["ultimas_execucoes"][rpa] = execucoes[:5]

        return relatorio

    # Métodos auxiliares privados
    async def _buscar_execucoes_por_contrato(self, numero_titulo: str) -> List[Dict[str, Any]]:
        """Busca execuções que processaram um contrato específico"""
        filtros = {
            "dados_contem": numero_titulo,
            "campos_busca": ["numero_titulo", "cliente", "dados.contrato.numero_titulo"]
        }
        return await self.buscar_execucoes_por_filtro(filtros)

    async def _buscar_planilhas_por_contrato(self, numero_titulo: str) -> List[Dict[str, Any]]:
        """Busca planilhas extraídas para um contrato"""
        # TODO: Implementar busca nas collections de planilhas
        return []

    async def _buscar_calculos_por_contrato(self, numero_titulo: str) -> List[Dict[str, Any]]:
        """Busca cálculos realizados para um contrato"""
        # TODO: Implementar busca nos passos de cálculo
        return []

    def _montar_timeline(self, execucoes: List, planilhas: List, calculos: List) -> List[Dict[str, Any]]:
        """Monta timeline cronológica de eventos"""
        eventos = []

        for execucao in execucoes:
            eventos.append({
                "timestamp": execucao.get("timestamp_inicio", ""),
                "tipo": "execucao_rpa",
                "dados": execucao
            })

        # Ordena por timestamp
        eventos.sort(key=lambda x: x.get("timestamp", ""))
        return eventos

    def _execucao_atende_filtros(self, dados: Dict[str, Any], filtros: Dict[str, Any]) -> bool:
        """Verifica se execução atende aos filtros"""
        # Filtro por nome RPA
        if "nome_rpa" in filtros:
            if dados.get("nome_rpa") != filtros["nome_rpa"]:
                return False

        # Filtro por conteúdo
        if "dados_contem" in filtros:
            texto_busca = filtros["dados_contem"].lower()
            dados_str = json.dumps(dados, default=str).lower()
            if texto_busca not in dados_str:
                return False

        return True

    async def _buscar_mongodb_por_filtros(self, filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Busca no MongoDB com filtros"""
        try:
            from core.mongodb_manager import mongodb_manager

            def _search():
                query = {}

                if "nome_rpa" in filtros:
                    query["nome_rpa"] = filtros["nome_rpa"]

                cursor = mongodb_manager.database.execucoes_consolidadas_rpa.find(
                    query)
                return list(cursor)

            resultados = await asyncio.get_event_loop().run_in_executor(
                None, _search
            )

            return [self._limpar_objectids(r) for r in resultados]

        except Exception as e:
            print(f"❌ Erro busca MongoDB: {str(e)}")
            return []

    def _limpar_objectids(self, documento: Dict[str, Any]) -> Dict[str, Any]:
        """Remove ObjectIds do MongoDB para serialização JSON"""
        if isinstance(documento, dict):
            if "_id" in documento:
                documento["_id"] = str(documento["_id"])

            for key, value in documento.items():
                if hasattr(value, 'isoformat'):  # datetime
                    documento[key] = value.isoformat()
                elif isinstance(value, dict):
                    documento[key] = self._limpar_objectids(value)
                elif isinstance(value, list):
                    documento[key] = [self._limpar_objectids(item) if isinstance(
                        item, dict) else item for item in value]

        return documento


# Instância global para uso
consultor_auditoria = ConsultorAuditoriaCompleta()


# Funções auxiliares para uso direto
async def consultar_execucao(id_execucao: str) -> Dict[str, Any]:
    """Consulta execução específica com todos os detalhes"""
    return await consultor_auditoria.obter_execucao_completa(id_execucao)


async def consultar_contrato(numero_titulo: str) -> Dict[str, Any]:
    """Consulta histórico completo de um contrato"""
    return await consultor_auditoria.obter_historico_contrato(numero_titulo)


async def gerar_relatorio_auditoria(numero_titulo: str = None, dias: int = 7) -> Dict[str, Any]:
    """Gera relatório completo de auditoria"""
    return await consultor_auditoria.gerar_relatorio_completo(numero_titulo, dias)


async def buscar_execucoes(filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Busca execuções com filtros personalizados"""
    return await consultor_auditoria.buscar_execucoes_por_filtro(filtros)


# Script de exemplo/teste
if __name__ == "__main__":
    async def exemplo_uso():
        print("🔍 Exemplo de Consulta de Auditoria Completa")
        print("=" * 50)

        # Inicializar sistema
        await data_manager.inicializar()

        # Relatório geral dos últimos 7 dias
        print("\n📊 Relatório Geral:")
        relatorio = await gerar_relatorio_auditoria(dias=7)
        print(json.dumps(relatorio, indent=2, ensure_ascii=False, default=str))

        # Buscar execuções do RPA Sienge
        print("\n🔍 Execuções do RPA Sienge:")
        execucoes_sienge = await buscar_execucoes({"nome_rpa": "RPA_Sienge"})
        print(f"Encontradas: {len(execucoes_sienge)} execuções")

        # Exemplo de consulta por contrato específico
        print("\n📋 Histórico do contrato 123456789:")
        historico = await consultar_contrato("123456789")
        print(json.dumps(historico, indent=2, ensure_ascii=False, default=str))

    asyncio.run(exemplo_uso())
