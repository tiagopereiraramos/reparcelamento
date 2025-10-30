"""
Relatório genérico para RPAs

Fornece uma API simples para:
- rastrear início/fim de execução
- registrar itens de sucesso e erro
- gerar mensagem amigável ao cliente
- salvar JSON e TXT
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


class RelatorioRPA:
    """
    Relatório genérico reutilizável entre RPAs.
    """

    def __init__(self, nome_rpa: str):
        self.nome_rpa = nome_rpa
        self.inicio_execucao: Optional[datetime] = None
        self.fim_execucao: Optional[datetime] = None
        self.sucessos: List[Dict[str, Any]] = []
        self.erros: List[Dict[str, Any]] = []
        self.metricas: Dict[str, Any] = {}

    def iniciar_execucao(self) -> None:
        self.inicio_execucao = datetime.now()

    def finalizar_execucao(self) -> None:
        self.fim_execucao = datetime.now()

    def adicionar_sucesso(self, titulo: str, detalhes: Optional[Dict[str, Any]] = None) -> None:
        self.sucessos.append({
            "titulo": titulo,
            "timestamp": datetime.now().isoformat(),
            "detalhes": detalhes or {}
        })

    def adicionar_erro(self, titulo: str, erro: str, detalhes: Optional[Dict[str, Any]] = None) -> None:
        self.erros.append({
            "titulo": titulo,
            "erro": erro,
            "timestamp": datetime.now().isoformat(),
            "detalhes": detalhes or {}
        })

    def set_metricas(self, metricas: Dict[str, Any]) -> None:
        self.metricas.update(metricas)

    def gerar_resumo(self) -> Dict[str, Any]:
        total_itens = len(self.sucessos) + len(self.erros)
        status_geral = "SUCESSO_COMPLETO"
        if len(self.erros) > 0:
            status_geral = "SUCESSO_PARCIAL" if len(self.sucessos) > 0 else "FALHA_COMPLETA"

        tempo_total = (self.fim_execucao - self.inicio_execucao) if (self.inicio_execucao and self.fim_execucao) else timedelta(0)

        return {
            "resumo_execucao": {
                "rpa": self.nome_rpa,
                "status_geral": status_geral,
                "inicio_execucao": self.inicio_execucao.isoformat() if self.inicio_execucao else None,
                "fim_execucao": self.fim_execucao.isoformat() if self.fim_execucao else None,
                "tempo_total": str(tempo_total),
                "total_itens": total_itens,
                "sucessos": len(self.sucessos),
                "erros": len(self.erros),
                **self.metricas,
            },
            "itens_sucesso": self.sucessos,
            "itens_erro": self.erros,
        }

    def gerar_mensagem_cliente(self) -> str:
        rel = self.gerar_resumo()["resumo_execucao"]
        status = rel["status_geral"]

        linhas: List[str] = []
        if status == "SUCESSO_COMPLETO":
            linhas.append("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO")
        elif status == "SUCESSO_PARCIAL":
            linhas.append("⚠️ PROCESSAMENTO PARCIALMENTE CONCLUÍDO")
        else:
            linhas.append("❌ PROCESSAMENTO FALHOU")

        linhas.append(f"📋 Itens OK: {rel['sucessos']} | ❌ Erros: {rel['erros']}")
        if "arquivos_enviados" in rel:
            linhas.append(f"📁 Arquivos: {rel['arquivos_enviados']}")
        if "contratos_vinculados" in rel:
            linhas.append(f"📄 Contratos: {rel['contratos_vinculados']}")
        linhas.append(f"⏱️ Tempo total: {rel['tempo_total']}")

        if self.erros:
            linhas.append("\n❌ ERROS:")
            for e in self.erros:
                linhas.append(f"   • {e['titulo']}: {e.get('erro','')}")

        return "\n".join(linhas)

    def salvar_relatorio_json(self, subdir: str = "outputs/relatorios") -> Path:
        pasta = Path(subdir)
        pasta.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        arquivo = pasta / f"relatorio_{self._slug(self.nome_rpa)}_{ts}.json"
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(self.gerar_resumo(), f, ensure_ascii=False, indent=2, default=str)
        return arquivo

    def salvar_relatorio_txt(self, subdir: str = "outputs/relatorios") -> Path:
        pasta = Path(subdir)
        pasta.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        arquivo = pasta / f"relatorio_{self._slug(self.nome_rpa)}_{ts}.txt"
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(self.gerar_mensagem_cliente())
        return arquivo

    @staticmethod
    def _slug(texto: str) -> str:
        return (
            texto.lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
        )


