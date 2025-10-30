"""
Enum para status dos contratos na fila de processamento.

Este módulo define todos os status possíveis que um contrato pode ter
durante o processamento no sistema de reparcelamento.
"""

from enum import Enum


class StatusContrato(Enum):
    """
    Enum com todos os status possíveis para contratos na fila.

    Status disponíveis:
    - PENDENTE: Contrato aguardando processamento
    - PROCESSANDO: Contrato em processamento ativo
    - APROVACAO_REALIZADA: Contrato aprovado e pronto para reparcelamento
    - REPARCELADO: Contrato reparcelado com sucesso
    - ERRO: Contrato com erro no processamento
    - CANCELADO: Contrato cancelado
    - IGNORADO: Contrato ignorado (não elegível)
    - AGUARDANDO_APROVACAO: Contrato aguardando aprovação manual
    - REJEITADO: Contrato rejeitado
    - FINALIZADO: Contrato finalizado (processo completo)
    """

    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    APROVACAO_REALIZADA = "APROVACAO_REALIZADA"
    REPARCELADO = "REPARCELADO"
    ERRO = "ERRO"
    CANCELADO = "CANCELADO"
    IGNORADO = "IGNORADO"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    REJEITADO = "REJEITADO"
    FINALIZADO = "FINALIZADO"

    @classmethod
    def from_string(cls, status_str: str) -> "StatusContrato":
        """
        Converte string para StatusContrato.

        Args:
            status_str: String do status

        Returns:
            StatusContrato correspondente

        Raises:
            ValueError: Se o status não for válido
        """
        status_str = status_str.upper().strip()

        for status in cls:
            if status.value == status_str:
                return status

        raise ValueError(
            f"Status inválido: '{status_str}'. Status válidos: {[s.value for s in cls]}")

    @classmethod
    def list_all(cls) -> list[str]:
        """
        Retorna lista com todos os status disponíveis.

        Returns:
            Lista com todos os status
        """
        return [status.value for status in cls]

    def __str__(self) -> str:
        """Retorna string do status."""
        return self.value
