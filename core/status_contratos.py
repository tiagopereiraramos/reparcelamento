"""
Status dos Contratos - Definições Centralizadas
Sistema de status para contratos no fluxo de reparcelamento

Desenvolvido em Português Brasileiro
"""

from typing import Dict, List, Set
from enum import Enum


class StatusContrato:
    """
    Definições centralizadas de status para contratos
    Mantém compatibilidade com código existente
    """

    # === STATUS EXISTENTES (PRODUÇÃO) ===
    PENDENTE = "PENDENTE"
    EXTRAIDO = "EXTRAIDO"
    REPARCELADO = "REPARCELADO"
    CARNE_GERADO = "CARNE_GERADO"
    PROCESSANDO = "PROCESSANDO"  # Status intermediário durante processamento
    PROCESSADO = "PROCESSADO"
    ERRO = "ERRO"

    # === NOVOS STATUS PARA APROVAÇÃO POR E-MAIL ===
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    APROVACAO_REALIZADA = "APROVACAO_REALIZADA"
    APROVACAO_REJEITADA = "APROVACAO_REJEITADA"
    APROVACAO_EXPIRADA = "APROVACAO_EXPIRADA"

    # === STATUS GRANULARES DE PROCESSAMENTO ===
    PENDENTE_VALIDACAO = "PENDENTE_VALIDACAO"
    VALIDACAO_APROVADA = "VALIDACAO_APROVADA"
    VALIDACAO_REJEITADA = "VALIDACAO_REJEITADA"


class StatusDescricoes:
    """Descrições amigáveis para cada status"""

    DESCRICOES = {
        # Status existentes
        StatusContrato.PENDENTE: "Contrato aguardando processamento",
        StatusContrato.EXTRAIDO: "Dados extraídos da planilha",
        StatusContrato.REPARCELADO: "Reparcelamento processado no Sienge",
        StatusContrato.CARNE_GERADO: "Carnê gerado, aguardando upload no banco",
        StatusContrato.PROCESSANDO: "Contrato em processamento ativo",
        StatusContrato.PROCESSADO: "Processamento completo no banco",
        StatusContrato.ERRO: "Erro durante processamento",

        # Novos status de aprovação
        StatusContrato.AGUARDANDO_APROVACAO: "Planilha enviada, aguardando e-mail de aprovação",
        StatusContrato.APROVACAO_REALIZADA: "E-mail de aprovação recebido, pronto para processar",
        StatusContrato.APROVACAO_REJEITADA: "Aprovação rejeitada ou não autorizada",
        StatusContrato.APROVACAO_EXPIRADA: "Prazo de aprovação expirou (5 dias)",

        # Status granulares
        StatusContrato.PENDENTE_VALIDACAO: "Aguardando validação de dados",
        StatusContrato.VALIDACAO_APROVADA: "Dados validados e aprovados",
        StatusContrato.VALIDACAO_REJEITADA: "Dados rejeitados na validação"
    }


class FluxosStatus:
    """Define fluxos permitidos entre status"""

    # Fluxo principal existente (não modificar)
    FLUXO_PRINCIPAL = [
        StatusContrato.PENDENTE,
        StatusContrato.EXTRAIDO,
        StatusContrato.REPARCELADO,
        StatusContrato.CARNE_GERADO,
        StatusContrato.PROCESSADO
    ]

    # Novo fluxo com aprovação por e-mail
    FLUXO_COM_APROVACAO = [
        StatusContrato.PENDENTE,
        StatusContrato.EXTRAIDO,
        StatusContrato.REPARCELADO,
        StatusContrato.AGUARDANDO_APROVACAO,  # NOVO: pausa para aprovação
        StatusContrato.APROVACAO_REALIZADA,   # NOVO: aprovação recebida
        StatusContrato.CARNE_GERADO,
        StatusContrato.PROCESSADO
    ]

    # Status que indicam falhas
    STATUS_FALHAS = {
        StatusContrato.ERRO,
        StatusContrato.APROVACAO_REJEITADA,
        StatusContrato.APROVACAO_EXPIRADA,
        StatusContrato.VALIDACAO_REJEITADA
    }

    # Status que indicam sucesso/conclusão
    STATUS_SUCESSO = {
        StatusContrato.PROCESSADO,
        StatusContrato.APROVACAO_REALIZADA
    }

    # Status que requerem intervenção humana
    STATUS_INTERVENCAO_HUMANA = {
        StatusContrato.AGUARDANDO_APROVACAO,
        StatusContrato.APROVACAO_EXPIRADA,
        StatusContrato.PENDENTE_VALIDACAO
    }


class StatusTransicoes:
    """Define transições válidas entre status"""

    TRANSICOES_PERMITIDAS = {
        StatusContrato.PENDENTE: [
            StatusContrato.EXTRAIDO,
            StatusContrato.ERRO
        ],
        StatusContrato.EXTRAIDO: [
            StatusContrato.REPARCELADO,
            StatusContrato.PENDENTE_VALIDACAO,
            StatusContrato.ERRO
        ],
        StatusContrato.REPARCELADO: [
            StatusContrato.AGUARDANDO_APROVACAO,  # NOVO: fluxo com aprovação
            StatusContrato.CARNE_GERADO,          # Existente: fluxo direto
            StatusContrato.ERRO
        ],
        StatusContrato.AGUARDANDO_APROVACAO: [
            StatusContrato.APROVACAO_REALIZADA,
            StatusContrato.APROVACAO_REJEITADA,
            StatusContrato.APROVACAO_EXPIRADA
        ],
        StatusContrato.APROVACAO_REALIZADA: [
            StatusContrato.CARNE_GERADO,
            StatusContrato.ERRO
        ],
        StatusContrato.CARNE_GERADO: [
            StatusContrato.PROCESSADO,
            StatusContrato.ERRO
        ],
        StatusContrato.PROCESSADO: [],  # Estado final
        StatusContrato.ERRO: [
            StatusContrato.PENDENTE  # Permite retry
        ]
    }

    @classmethod
    def pode_transicionar(cls, status_atual: str, status_novo: str) -> bool:
        """Verifica se uma transição de status é válida"""
        return status_novo in cls.TRANSICOES_PERMITIDAS.get(status_atual, [])


class StatusFiltros:
    """Filtros úteis para consultas"""

    @staticmethod
    def contratos_ativos() -> List[str]:
        """Status que indicam contratos em processamento ativo"""
        return [
            StatusContrato.PENDENTE,
            StatusContrato.EXTRAIDO,
            StatusContrato.REPARCELADO,
            StatusContrato.AGUARDANDO_APROVACAO,
            StatusContrato.APROVACAO_REALIZADA,
            StatusContrato.CARNE_GERADO
        ]

    @staticmethod
    def contratos_finalizados() -> List[str]:
        """Status que indicam contratos finalizados (sucesso ou falha)"""
        return [
            StatusContrato.PROCESSADO,
            StatusContrato.ERRO,
            StatusContrato.APROVACAO_REJEITADA,
            StatusContrato.APROVACAO_EXPIRADA
        ]

    @staticmethod
    def contratos_aguardando_aprovacao() -> List[str]:
        """Status relacionados ao processo de aprovação"""
        return [
            StatusContrato.AGUARDANDO_APROVACAO,
            StatusContrato.APROVACAO_REALIZADA
        ]

    @staticmethod
    def contratos_prontos_sicredi() -> List[str]:
        """Status que indicam contratos prontos para processamento no Sicredi"""
        return [StatusContrato.CARNE_GERADO]


# === FUNÇÕES UTILITÁRIAS ===

def obter_descricao_status(status: str) -> str:
    """Retorna descrição amigável do status"""
    return StatusDescricoes.DESCRICOES.get(status, f"Status desconhecido: {status}")


def validar_status(status: str) -> bool:
    """Valida se um status é conhecido pelo sistema"""
    todos_status = {
        StatusContrato.PENDENTE,
        StatusContrato.EXTRAIDO,
        StatusContrato.REPARCELADO,
        StatusContrato.CARNE_GERADO,
        StatusContrato.PROCESSADO,
        StatusContrato.ERRO,
        StatusContrato.AGUARDANDO_APROVACAO,
        StatusContrato.APROVACAO_REALIZADA,
        StatusContrato.APROVACAO_REJEITADA,
        StatusContrato.APROVACAO_EXPIRADA,
        StatusContrato.PENDENTE_VALIDACAO,
        StatusContrato.VALIDACAO_APROVADA,
        StatusContrato.VALIDACAO_REJEITADA
    }
    return status in todos_status


def status_requer_aprovacao(status: str) -> bool:
    """Verifica se o status está no fluxo de aprovação por e-mail"""
    return status in [
        StatusContrato.AGUARDANDO_APROVACAO,
        StatusContrato.APROVACAO_REALIZADA,
        StatusContrato.APROVACAO_REJEITADA,
        StatusContrato.APROVACAO_EXPIRADA
    ]


# === CONSTANTES PARA COMPATIBILIDADE ===
# Mantém compatibilidade com código existente que usa strings diretas

# Status mais usados (para facilitar imports)
PENDENTE = StatusContrato.PENDENTE
EXTRAIDO = StatusContrato.EXTRAIDO
REPARCELADO = StatusContrato.REPARCELADO
CARNE_GERADO = StatusContrato.CARNE_GERADO
PROCESSADO = StatusContrato.PROCESSADO
ERRO = StatusContrato.ERRO

# Novos status
AGUARDANDO_APROVACAO = StatusContrato.AGUARDANDO_APROVACAO
APROVACAO_REALIZADA = StatusContrato.APROVACAO_REALIZADA
APROVACAO_REJEITADA = StatusContrato.APROVACAO_REJEITADA
APROVACAO_EXPIRADA = StatusContrato.APROVACAO_EXPIRADA
