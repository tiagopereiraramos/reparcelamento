"""
Sistema de Relatórios Simplificado para RPA Sicredi
Cria relatórios claros e objetivos para o cliente
"""

from datetime import datetime
from typing import Dict, Any, List
import json
from pathlib import Path


class RelatorioSicredi:
    """
    Classe para gerar relatórios simplificados do processamento Sicredi
    """
    
    def __init__(self):
        self.inicio_execucao = None
        self.fim_execucao = None
        self.empresas_processadas = []
        self.erros_gerais = []
        self.arquivos_enviados = []
        self.contratos_vinculados = 0
        
    def iniciar_execucao(self):
        """Inicia o tracking de tempo de execução"""
        self.inicio_execucao = datetime.now()
        
    def finalizar_execucao(self):
        """Finaliza o tracking de tempo de execução"""
        self.fim_execucao = datetime.now()
        
    def adicionar_empresa_sucesso(self, empresa: str, arquivo: str, contratos: int, detalhes: Dict[str, Any] = None):
        """Adiciona uma empresa processada com sucesso"""
        self.empresas_processadas.append({
            "empresa": empresa,
            "status": "SUCESSO",
            "arquivo_enviado": arquivo,
            "contratos_vinculados": contratos,
            "timestamp": datetime.now().isoformat(),
            "detalhes": detalhes or {}
        })
        self.arquivos_enviados.append(arquivo)
        self.contratos_vinculados += contratos
        
    def adicionar_empresa_erro(self, empresa: str, arquivo: str, erro: str, detalhes: Dict[str, Any] = None):
        """Adiciona uma empresa que falhou no processamento"""
        self.empresas_processadas.append({
            "empresa": empresa,
            "status": "ERRO",
            "arquivo_tentado": arquivo,
            "erro": erro,
            "timestamp": datetime.now().isoformat(),
            "detalhes": detalhes or {}
        })
        self.erros_gerais.append({
            "empresa": empresa,
            "erro": erro,
            "timestamp": datetime.now().isoformat()
        })
        
    def adicionar_erro_geral(self, erro: str, detalhes: Dict[str, Any] = None):
        """Adiciona um erro geral do sistema"""
        self.erros_gerais.append({
            "erro": erro,
            "timestamp": datetime.now().isoformat(),
            "detalhes": detalhes or {}
        })
        
    def calcular_tempo_execucao(self) -> str:
        """Calcula o tempo total de execução"""
        if not self.inicio_execucao or not self.fim_execucao:
            return "N/A"
        
        duracao = self.fim_execucao - self.inicio_execucao
        return str(duracao)
        
    def gerar_relatorio_resumido(self) -> Dict[str, Any]:
        """Gera relatório resumido para o cliente"""
        empresas_sucesso = len([e for e in self.empresas_processadas if e["status"] == "SUCESSO"])
        empresas_erro = len([e for e in self.empresas_processadas if e["status"] == "ERRO"])
        total_empresas = len(self.empresas_processadas)
        
        # Determinar status geral
        if empresas_erro == 0:
            status_geral = "SUCESSO_COMPLETO"
        elif empresas_sucesso > 0:
            status_geral = "SUCESSO_PARCIAL"
        else:
            status_geral = "FALHA_COMPLETA"
            
        relatorio = {
            "resumo_execucao": {
                "status_geral": status_geral,
                "inicio_execucao": self.inicio_execucao.isoformat() if self.inicio_execucao else None,
                "fim_execucao": self.fim_execucao.isoformat() if self.fim_execucao else None,
                "tempo_total": self.calcular_tempo_execucao(),
                "total_empresas": total_empresas,
                "empresas_sucesso": empresas_sucesso,
                "empresas_erro": empresas_erro,
                "arquivos_enviados": len(self.arquivos_enviados),
                "contratos_vinculados": self.contratos_vinculados
            },
            "empresas_processadas": self.empresas_processadas,
            "erros_gerais": self.erros_gerais,
            "arquivos_enviados": self.arquivos_enviados
        }
        
        return relatorio
        
    def gerar_mensagem_cliente(self) -> str:
        """Gera mensagem simplificada para o cliente"""
        relatorio = self.gerar_relatorio_resumido()
        resumo = relatorio["resumo_execucao"]
        
        if resumo["status_geral"] == "SUCESSO_COMPLETO":
            mensagem = f"✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO!\n"
            mensagem += f"📊 {resumo['empresas_sucesso']} empresas processadas\n"
            mensagem += f"📁 {resumo['arquivos_enviados']} arquivos enviados\n"
            mensagem += f"📋 {resumo['contratos_vinculados']} contratos vinculados\n"
            mensagem += f"⏱️ Tempo total: {resumo['tempo_total']}"
            
        elif resumo["status_geral"] == "SUCESSO_PARCIAL":
            mensagem = f"⚠️ PROCESSAMENTO PARCIALMENTE CONCLUÍDO\n"
            mensagem += f"✅ {resumo['empresas_sucesso']} empresas processadas com sucesso\n"
            mensagem += f"❌ {resumo['empresas_erro']} empresas com erro\n"
            mensagem += f"📁 {resumo['arquivos_enviados']} arquivos enviados\n"
            mensagem += f"📋 {resumo['contratos_vinculados']} contratos vinculados\n"
            mensagem += f"⏱️ Tempo total: {resumo['tempo_total']}\n\n"
            mensagem += f"❌ ERROS ENCONTRADOS:\n"
            for erro in self.erros_gerais:
                mensagem += f"   • {erro['empresa']}: {erro['erro']}\n"
                
        else:  # FALHA_COMPLETA
            mensagem = f"❌ PROCESSAMENTO FALHOU COMPLETAMENTE\n"
            mensagem += f"❌ Todas as {resumo['total_empresas']} empresas falharam\n"
            mensagem += f"⏱️ Tempo total: {resumo['tempo_total']}\n\n"
            mensagem += f"❌ ERROS ENCONTRADOS:\n"
            for erro in self.erros_gerais:
                mensagem += f"   • {erro.get('empresa', 'Sistema')}: {erro['erro']}\n"
                
        return mensagem
        
    def salvar_relatorio_cliente(self, arquivo: str = None) -> str:
        """Salva relatório simplificado para o cliente"""
        if not arquivo:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            arquivo = f"outputs/relatorios/relatorio_sicredi_cliente_{timestamp}.json"
            
        # Garante que o diretório existe
        Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
        
        relatorio = self.gerar_relatorio_resumido()
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)
            
        return arquivo
        
    def salvar_mensagem_cliente(self, arquivo: str = None) -> str:
        """Salva mensagem de texto para o cliente"""
        if not arquivo:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            arquivo = f"outputs/relatorios/relatorio_sicredi_cliente_{timestamp}.txt"
            
        # Garante que o diretório existe
        Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
        
        mensagem = self.gerar_mensagem_cliente()
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(mensagem)
            
        return arquivo
