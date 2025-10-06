"""Repositório de contratos baseado em arquivos JSON transacionais."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from core.json_rpa_framework import JSONRPAFramework


CAMPO_STATUS = "status"
CAMPO_NUMERO_TITULO = "Titulo"
CAMPO_CLIENTE = "Cliente"
CAMPO_CODIGO = "Código Cliente"


@dataclass
class ContratoRegistro:
    """Representa um contrato na fila transacional."""

    dados: Dict[str, Any]

    def __post_init__(self) -> None:
        if CAMPO_STATUS not in self.dados:
            self.dados[CAMPO_STATUS] = "PENDENTE"
        codigo = self.dados.get(
            CAMPO_CODIGO) or self.dados.get('Codigo Cliente')
        if codigo is not None:
            self.dados[CAMPO_CODIGO] = str(codigo).strip()
        if "_metadata" not in self.dados:
            self.dados["_metadata"] = {}
        agora = datetime.now().isoformat()
        metadata = self.dados["_metadata"]
        metadata.setdefault("timestamp_registro", agora)
        metadata["timestamp_ultima_atualizacao"] = agora

    @property
    def numero_titulo(self) -> str:
        return str(self.dados.get(CAMPO_NUMERO_TITULO, "")).strip()

    @property
    def cliente(self) -> str:
        return str(self.dados.get(CAMPO_CLIENTE, "")).strip()

    @property
    def codigo_cliente(self) -> str:
        return str(self.dados.get(CAMPO_CODIGO, "")).strip()


class RepositorioContratosArquivo:
    """Repositório de contratos usando JSONRPAFramework."""

    def __init__(self, diretorio_dados: str = "data") -> None:
        self.framework = JSONRPAFramework(
            data_dir=diretorio_dados,
            main_file="fila_contratos.json",
            wal_file="fila_contratos.wal",
            index_file="index_status.json",
            auto_index_fields=[CAMPO_STATUS, CAMPO_NUMERO_TITULO,
                               CAMPO_CLIENTE, "Empresa", "Código Cliente"],
        )

    def salvar_lote(self, contratos: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        """Salvar ou atualizar um lote de contratos."""
        inseridos = 0
        atualizados = 0
        ignorados = 0
        erros = 0

        for contrato in contratos:
            registro = ContratoRegistro(contrato)
            if not registro.numero_titulo or not registro.codigo_cliente:
                erros += 1
                continue
            filtro = {
                CAMPO_NUMERO_TITULO: registro.numero_titulo,
                CAMPO_CODIGO: registro.codigo_cliente,
            }
            existente = self.framework.find_one(filtro)

            try:
                if existente:
                    status_existente = existente.get(CAMPO_STATUS, "")
                    dados_atualizados = registro.dados.copy()
                    metadata_existente = existente.get("_metadata", {}).copy()
                    metadata_novo = dados_atualizados.get("_metadata", {})
                    agora = datetime.now().isoformat()
                    # preserva timestamp de registro original
                    metadata_existente.setdefault("timestamp_registro",
                                                  metadata_novo.get("timestamp_registro", agora))
                    # aplica campos mais recentes
                    metadata_existente.update(
                        {k: v for k, v in metadata_novo.items() if v is not None})
                    metadata_existente["timestamp_ultima_atualizacao"] = agora
                    dados_atualizados["_metadata"] = metadata_existente

                    if status_existente and status_existente != "PENDENTE":
                        dados_atualizados[CAMPO_STATUS] = status_existente
                    else:
                        dados_atualizados.setdefault(CAMPO_STATUS, "PENDENTE")

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
            "ignorados": ignorados,
            "erros": erros,
        }

    def listar_por_status(self, status: str, limite: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retorna contratos por status."""
        return self.framework.find({CAMPO_STATUS: status}, limit=limite)

    def atualizar_status(
        self,
        contrato_id: str,
        novo_status: str,
        adicionais: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Atualiza o status de um contrato."""
        extras = adicionais.copy() if adicionais else {}
        extras["status_timestamp"] = datetime.now().isoformat()
        return self.framework.set_status(contrato_id, novo_status, extras)

    def obter_por_titulo(self, titulo: str) -> Optional[Dict[str, Any]]:
        """Busca contrato pelo título."""
        return self.framework.find_one({CAMPO_NUMERO_TITULO: titulo})

    def deduplicar(self) -> Dict[str, int]:
        """Remove duplicatas baseado em Código Cliente + Titulo, preservando o mais recente."""
        registros = self.framework.find({})
        vistos: Dict[tuple, Dict[str, Any]] = {}
        for registro in registros:
            chave = (str(registro.get(CAMPO_NUMERO_TITULO, "")).strip(),
                     str(registro.get(CAMPO_CODIGO, "")).strip())
            if not chave[0] or not chave[1]:
                continue
            atual = vistos.get(chave)
            if not atual or registro.get("_updated_at", "") >= atual.get("_updated_at", ""):
                vistos[chave] = registro

        self.framework._save_data(
            list(vistos.values()))  # pylint: disable=protected-access
        return {
            "total": len(registros),
            "remanescente": len(vistos),
        }

    def estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas do armazenamento."""
        return self.framework.get_stats()


repositorio_contratos_arquivo = RepositorioContratosArquivo()
