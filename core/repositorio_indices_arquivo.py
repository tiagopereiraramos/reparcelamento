"""Repositório de índices econômicos utilizando armazenamento JSON transacional."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from core.json_rpa_framework import JSONRPAFramework

CAMPO_TIPO = "tipo"
CAMPO_MES = "mes"
CAMPO_PERIODO = "periodo"
CAMPO_PLANILHA = "planilha_id"


@dataclass
class IndiceEconomicoRegistro:
    """Estrutura de dados para persistir índices econômicos no framework JSON."""

    dados: Dict[str, Any]
    planilha: Optional[str]

    def __post_init__(self) -> None:
        self.dados = dict(self.dados)
        self.dados[CAMPO_TIPO] = str(
            self.dados.get(CAMPO_TIPO, "")).strip().upper()
        self.dados[CAMPO_MES] = str(self.dados.get(CAMPO_MES, "")).strip()
        self.dados.setdefault(CAMPO_PERIODO, str(
            self.dados.get(CAMPO_PERIODO, "")).strip())
        planilha_id = str(self.planilha or self.dados.get(
            CAMPO_PLANILHA, "")).strip()
        self.planilha = planilha_id
        self.dados[CAMPO_PLANILHA] = planilha_id

        valor_original = str(self.dados.get("valor", "")
                             ).replace("%", "").strip()
        valor_numerico = self._converter_valor(valor_original)
        if valor_numerico is not None:
            self.dados["valor_numerico"] = valor_numerico

        timestamp_atual = datetime.now().isoformat()
        metadata = dict(self.dados.get("_metadata", {}))
        metadata.setdefault("timestamp_registro", timestamp_atual)
        metadata["timestamp_ultima_atualizacao"] = timestamp_atual
        self.dados["_metadata"] = metadata

        if "timestamp" not in self.dados:
            self.dados["timestamp"] = timestamp_atual

    @property
    def tipo(self) -> str:
        """Retorna o tipo de índice (ex.: IPCA, IGPM)."""

        return self.dados.get(CAMPO_TIPO, "")

    @property
    def mes(self) -> str:
        """Retorna o mês de referência do índice."""

        return self.dados.get(CAMPO_MES, "")

    @property
    def planilha_id(self) -> str:
        """Retorna o identificador da planilha associada ao índice."""

        return self.planilha or ""

    @staticmethod
    def _converter_valor(valor: str) -> Optional[float]:
        """Converte valor textual para número decimal quando possível."""

        if not valor:
            return None

        candidato = valor.replace(",", ".")
        try:
            return float(candidato)
        except ValueError:
            return None


class RepositorioIndicesArquivo:
    """Persistência de índices econômicos com suporte transacional."""

    def __init__(self, diretorio_dados: str = "data") -> None:
        self.framework = JSONRPAFramework(
            data_dir=diretorio_dados,
            main_file="indices_economicos.json",
            wal_file="indices_economicos.wal",
            index_file="indices_economicos_index.json",
            auto_index_fields=[CAMPO_TIPO, CAMPO_MES,
                               CAMPO_PERIODO, CAMPO_PLANILHA],
        )

    def salvar_indices(self, indices: Iterable[Dict[str, Any]], planilha_id: Optional[str]) -> Dict[str, int]:
        """Salva ou atualiza registros de índices econômicos."""

        inseridos = 0
        atualizados = 0
        erros = 0

        for indice in indices:
            registro = IndiceEconomicoRegistro(indice, planilha_id)
            if not registro.tipo or not registro.mes:
                erros += 1
                continue

            filtro = {
                CAMPO_TIPO: registro.tipo,
                CAMPO_MES: registro.mes,
                CAMPO_PLANILHA: registro.planilha_id,
            }
            existente = self.framework.find_one(filtro)

            try:
                if existente:
                    dados_atualizados = registro.dados.copy()
                    metadata_existente = existente.get("_metadata", {}).copy()
                    metadata_novo = dados_atualizados.get("_metadata", {})
                    metadata_existente.setdefault(
                        "timestamp_registro", metadata_novo.get(
                            "timestamp_registro")
                    )
                    metadata_existente.update(metadata_novo)
                    dados_atualizados["_metadata"] = metadata_existente

                    self.framework.update(
                        {"_id": existente.get("_id")}, dados_atualizados)
                    atualizados += 1
                else:
                    self.framework.insert(registro.dados)
                    inseridos += 1
            except Exception:
                erros += 1

        return {
            "inseridos": inseridos,
            "atualizados": atualizados,
            "erros": erros,
        }

    def buscar_por_tipo(self, tipo: str, limite: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        """Retorna registros filtrados pelo tipo de índice."""

        return self.framework.find({CAMPO_TIPO: tipo.strip().upper()}, limit=limite)

    def obter_mais_recente(self, tipo: str) -> Optional[Dict[str, Any]]:
        """Obtém o índice mais recente para o tipo informado."""

        registros = self.framework.find({CAMPO_TIPO: tipo.strip().upper()})
        if not registros:
            return None
        registros.sort(key=lambda item: item.get(
            "timestamp", ""), reverse=True)
        return registros[0]


repositorio_indices_arquivo = RepositorioIndicesArquivo()
