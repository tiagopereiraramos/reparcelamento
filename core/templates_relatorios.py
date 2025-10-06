"""
Templates HTML para Relatórios RPA
Sistema unificado para gerar relatórios HTML com quantitativos e informações resumidas para cada serviço

Desenvolvido em Português Brasileiro
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


class TemplatesRelatorios:
    """Classe para gerar templates HTML de relatórios RPA"""

    @staticmethod
    def gerar_template_base(titulo: str, conteudo: str, tipo_evento: str = "sucesso") -> str:
        """
        Gera template HTML base para relatórios

        Args:
            titulo: Título do relatório
            conteudo: Conteúdo HTML do relatório
            tipo_evento: Tipo do evento (sucesso, erro, alerta, info)

        Returns:
            str: HTML completo do relatório
        """
        # Cores por tipo de evento
        cores = {
            "sucesso": {"primaria": "#28a745", "secundaria": "#d4edda"},
            "erro": {"primaria": "#dc3545", "secundaria": "#f8d7da"},
            "alerta": {"primaria": "#ffc107", "secundaria": "#fff3cd"},
            "info": {"primaria": "#17a2b8", "secundaria": "#d1ecf1"}
        }

        cor_config = cores.get(tipo_evento, cores["info"])

        # Ícones por tipo
        icones = {
            "sucesso": "✅",
            "erro": "❌",
            "alerta": "⚠️",
            "info": "📋"
        }

        icone = icones.get(tipo_evento, "📋")
        timestamp = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')

        return f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{titulo}</title>
            <style>
                body {{
                    margin: 0; 
                    padding: 0; 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    overflow: hidden;
                    margin-top: 20px;
                    margin-bottom: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, {cor_config['primaria']}, {cor_config['primaria']}dd);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header .icon {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: 600;
                }}
                .header p {{
                    margin: 8px 0 0 0;
                    font-size: 14px;
                    opacity: 0.9;
                }}
                .content {{
                    padding: 30px;
                    line-height: 1.6;
                    color: #333;
                    font-size: 16px;
                }}
                .info-box {{
                    background-color: {cor_config['secundaria']};
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid {cor_config['primaria']};
                    margin: 20px 0;
                }}
                .info-box h3 {{
                    margin-top: 0;
                    color: {cor_config['primaria']};
                    font-size: 16px;
                }}
                .stats-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                .stats-table td {{
                    padding: 10px 0;
                    border-bottom: 1px solid #dee2e6;
                }}
                .stats-table .label {{
                    font-weight: bold;
                    width: 30%;
                }}
                .stats-table .value {{
                    color: {cor_config['primaria']};
                    font-weight: bold;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-top: 1px solid #e9ecef;
                }}
                .footer p {{
                    margin: 0;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .highlight {{
                    background-color: #fff3cd;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #ffc107;
                    margin: 20px 0;
                }}
                .highlight h4 {{
                    margin-top: 0;
                    color: #856404;
                }}
                .anexo-info {{
                    background-color: #e7f3ff;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                    margin: 20px 0;
                }}
                .anexo-info h4 {{
                    margin-top: 0;
                    color: #0056b3;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="icon">{icone}</div>
                    <h1>{titulo}</h1>
                    <p>Sistema RPA de Reparcelamento</p>
                </div>
                
                <div class="content">
                    {conteudo}
                </div>
                
                <div class="footer">
                    <p>
                        Esta é uma notificação automática do Sistema RPA.<br>
                        Para dúvidas ou suporte, entre em contato com a equipe de TI.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def relatorio_analise_planilhas(estatisticas: Dict[str, Any], anexos: Optional[Dict[str, str]] = None) -> str:
        """
        Gera relatório HTML para análise de planilhas

        Args:
            estatisticas: Dicionário com estatísticas do processamento
            anexos: Dicionário com caminhos dos anexos gerados

        Returns:
            str: HTML do relatório
        """
        total_contratos = estatisticas.get('total_contratos', 0)
        contratos_aprovados = estatisticas.get('contratos_aprovados', 0)
        contratos_rejeitados = estatisticas.get('contratos_rejeitados', 0)
        contratos_nao_processados = estatisticas.get(
            'contratos_nao_processados', 0)
        novos_contratos = estatisticas.get('novos_contratos', 0)

        conteudo = f"""
        <h2 style="color: #28a745; margin-bottom: 20px;">📊 Relatório de Análise de Planilhas</h2>
        
        <div class="info-box">
            <h3>📋 Resumo da Execução</h3>
            <table class="stats-table">
                <tr>
                    <td class="label">Total de Contratos Analisados:</td>
                    <td class="value">{total_contratos}</td>
                </tr>
                <tr>
                    <td class="label">Contratos Aprovados:</td>
                    <td class="value" style="color: #28a745;">{contratos_aprovados}</td>
                </tr>
                <tr>
                    <td class="label">Contratos Rejeitados:</td>
                    <td class="value" style="color: #dc3545;">{contratos_rejeitados}</td>
                </tr>
                <tr>
                    <td class="label">Contratos Não Processados:</td>
                    <td class="value" style="color: #6c757d;">{contratos_nao_processados}</td>
                </tr>
                <tr>
                    <td class="label">Novos Contratos Encontrados:</td>
                    <td class="value" style="color: #17a2b8;">{novos_contratos}</td>
                </tr>
            </table>
        </div>
        """

        # Adiciona informações sobre novos contratos se existirem
        if novos_contratos > 0:
            conteudo += f"""
            <div class="highlight">
                <h4>🆕 Novos Contratos Identificados</h4>
                <p>Foram encontrados <strong>{novos_contratos}</strong> novos contratos que foram adicionados à fila de processamento.</p>
                <p>Esses contratos serão processados na próxima execução do sistema.</p>
            </div>
            """

        # Adiciona informações sobre anexos se existirem
        if anexos:
            conteudo += """
            <div class="anexo-info">
                <h4>📎 Anexos Gerados</h4>
                <p>Os seguintes arquivos foram gerados com detalhes completos:</p>
                <ul>
            """

            if 'excel' in anexos:
                conteudo += f'<li><strong>Excel:</strong> {anexos["excel"]}</li>'
            if 'txt' in anexos:
                conteudo += f'<li><strong>Texto:</strong> {anexos["txt"]}</li>'

            conteudo += """
                </ul>
                <p><em>Os anexos contêm informações detalhadas de todos os contratos processados, incluindo códigos, nomes, títulos e meses de reparcelamento.</em></p>
            </div>
            """

        return TemplatesRelatorios.gerar_template_base(
            "Análise de Planilhas - Relatório de Execução",
            conteudo,
            "sucesso"
        )

    @staticmethod
    def relatorio_extracao(estatisticas: Dict[str, Any], anexos: Optional[Dict[str, str]] = None) -> str:
        """
        Gera relatório HTML para extração de contratos

        Args:
            estatisticas: Dicionário com estatísticas do processamento
            anexos: Dicionário com caminhos dos anexos gerados

        Returns:
            str: HTML do relatório
        """
        total_contratos = estatisticas.get('total_contratos', 0)
        contratos_processados = estatisticas.get('contratos_processados', 0)
        contratos_com_erro = estatisticas.get('contratos_com_erro', 0)
        mudancas_status = estatisticas.get('mudancas_status', 0)

        conteudo = f"""
        <h2 style="color: #17a2b8; margin-bottom: 20px;">📥 Relatório de Extração de Contratos</h2>
        
        <div class="info-box">
            <h3>📋 Resumo da Execução</h3>
            <table class="stats-table">
                <tr>
                    <td class="label">Total de Contratos na Fila:</td>
                    <td class="value">{total_contratos}</td>
                </tr>
                <tr>
                    <td class="label">Contratos Processados com Sucesso:</td>
                    <td class="value" style="color: #28a745;">{contratos_processados}</td>
                </tr>
                <tr>
                    <td class="label">Contratos com Erro:</td>
                    <td class="value" style="color: #dc3545;">{contratos_com_erro}</td>
                </tr>
                <tr>
                    <td class="label">Mudanças de Status Realizadas:</td>
                    <td class="value" style="color: #17a2b8;">{mudancas_status}</td>
                </tr>
            </table>
        </div>
        """

        # Adiciona informações sobre anexos se existirem
        if anexos:
            conteudo += """
            <div class="anexo-info">
                <h4>📎 Anexos Gerados</h4>
                <p>Os seguintes arquivos foram gerados com detalhes completos:</p>
                <ul>
            """

            if 'excel' in anexos:
                conteudo += f'<li><strong>Excel:</strong> {anexos["excel"]}</li>'
            if 'txt' in anexos:
                conteudo += f'<li><strong>Texto:</strong> {anexos["txt"]}</li>'

            conteudo += """
                </ul>
                <p><em>Os anexos contêm informações detalhadas de todos os contratos processados, incluindo mudanças de status realizadas.</em></p>
            </div>
            """

        return TemplatesRelatorios.gerar_template_base(
            "Extração de Contratos - Relatório de Execução",
            conteudo,
            "sucesso"
        )

    @staticmethod
    def relatorio_reparcelamento(estatisticas: Dict[str, Any], anexos: Optional[Dict[str, str]] = None) -> str:
        """
        Gera relatório HTML para reparcelamento de contratos

        Args:
            estatisticas: Dicionário com estatísticas do processamento
            anexos: Dicionário com caminhos dos anexos gerados

        Returns:
            str: HTML do relatório
        """
        total_contratos = estatisticas.get('total_contratos', 0)
        contratos_sucesso = estatisticas.get('contratos_sucesso', 0)
        contratos_erro = estatisticas.get('contratos_erro', 0)
        tempo_medio = estatisticas.get('tempo_medio', 'N/A')

        conteudo = f"""
        <h2 style="color: #28a745; margin-bottom: 20px;">🔄 Relatório de Reparcelamento</h2>
        
        <div class="info-box">
            <h3>📋 Resumo da Execução</h3>
            <table class="stats-table">
                <tr>
                    <td class="label">Total de Contratos Processados:</td>
                    <td class="value">{total_contratos}</td>
                </tr>
                <tr>
                    <td class="label">Contratos com Sucesso:</td>
                    <td class="value" style="color: #28a745;">{contratos_sucesso}</td>
                </tr>
                <tr>
                    <td class="label">Contratos com Erro:</td>
                    <td class="value" style="color: #dc3545;">{contratos_erro}</td>
                </tr>
                <tr>
                    <td class="label">Tempo Médio por Contrato:</td>
                    <td class="value">{tempo_medio}</td>
                </tr>
            </table>
        </div>
        """

        # Adiciona informações sobre anexos se existirem
        if anexos:
            conteudo += """
            <div class="anexo-info">
                <h4>📎 Anexos Gerados</h4>
                <p>Os seguintes arquivos foram gerados com detalhes completos:</p>
                <ul>
            """

            if 'excel' in anexos:
                conteudo += f'<li><strong>Excel:</strong> {anexos["excel"]}</li>'
            if 'txt' in anexos:
                conteudo += f'<li><strong>Texto:</strong> {anexos["txt"]}</li>'

            conteudo += """
                </ul>
                <p><em>Os anexos contêm informações detalhadas de todos os contratos processados, incluindo motivos de erro para contratos com falha.</em></p>
            </div>
            """

        return TemplatesRelatorios.gerar_template_base(
            "Reparcelamento de Contratos - Relatório de Execução",
            conteudo,
            "sucesso"
        )

    @staticmethod
    def relatorio_carnes(estatisticas: Dict[str, Any], anexos: Optional[Dict[str, str]] = None) -> str:
        """
        Gera relatório HTML para geração de carnês

        Args:
            estatisticas: Dicionário com estatísticas do processamento
            anexos: Dicionário com caminhos dos anexos gerados

        Returns:
            str: HTML do relatório
        """
        total_empresas = estatisticas.get('total_empresas', 0)
        carnes_sucesso = estatisticas.get('carnes_sucesso', 0)
        carnes_erro = estatisticas.get('carnes_erro', 0)
        total_contratos = estatisticas.get('total_contratos', 0)

        conteudo = f"""
        <h2 style="color: #17a2b8; margin-bottom: 20px;">📄 Relatório de Geração de Carnês</h2>
        
        <div class="info-box">
            <h3>📋 Resumo da Execução</h3>
            <table class="stats-table">
                <tr>
                    <td class="label">Total de Empresas Processadas:</td>
                    <td class="value">{total_empresas}</td>
                </tr>
                <tr>
                    <td class="label">Carnês Gerados com Sucesso:</td>
                    <td class="value" style="color: #28a745;">{carnes_sucesso}</td>
                </tr>
                <tr>
                    <td class="label">Carnês com Erro:</td>
                    <td class="value" style="color: #dc3545;">{carnes_erro}</td>
                </tr>
                <tr>
                    <td class="label">Total de Contratos Incluídos:</td>
                    <td class="value" style="color: #17a2b8;">{total_contratos}</td>
                </tr>
            </table>
        </div>
        """

        # Adiciona informações sobre anexos se existirem
        if anexos:
            conteudo += """
            <div class="anexo-info">
                <h4>📎 Anexos Gerados</h4>
                <p>Os seguintes arquivos foram gerados com detalhes completos:</p>
                <ul>
            """

            if 'excel' in anexos:
                conteudo += f'<li><strong>Excel:</strong> {anexos["excel"]}</li>'
            if 'txt' in anexos:
                conteudo += f'<li><strong>Texto:</strong> {anexos["txt"]}</li>'

            conteudo += """
                </ul>
                <p><em>Os anexos contêm informações detalhadas de todos os carnês processados, incluindo motivos de erro para falhas.</em></p>
            </div>
            """

        return TemplatesRelatorios.gerar_template_base(
            "Geração de Carnês - Relatório de Execução",
            conteudo,
            "sucesso"
        )

    @staticmethod
    def relatorio_erro(nome_rpa: str, erro: str, detalhes: str) -> str:
        """
        Gera relatório HTML para erros

        Args:
            nome_rpa: Nome do RPA que falhou
            erro: Descrição do erro
            detalhes: Detalhes técnicos do erro

        Returns:
            str: HTML do relatório
        """
        conteudo = f"""
        <h2 style="color: #dc3545; margin-bottom: 20px;">⚠️ Erro Detectado no Sistema</h2>
        
        <div class="info-box">
            <h3>🚨 Detalhes do Erro</h3>
            <table class="stats-table">
                <tr>
                    <td class="label">RPA Afetado:</td>
                    <td class="value">{nome_rpa}</td>
                </tr>
                <tr>
                    <td class="label">Tipo de Erro:</td>
                    <td class="value" style="color: #dc3545; font-weight: bold;">{erro}</td>
                </tr>
            </table>
        </div>
        
        <div class="highlight">
            <h4>📝 Detalhes Técnicos</h4>
            <div style="background-color: #ffffff; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 14px; color: #495057; white-space: pre-wrap;">{detalhes}</div>
        </div>
        
        <div class="anexo-info">
            <h4>🔧 Próximos Passos</h4>
            <ol style="margin: 10px 0; padding-left: 20px; color: #495057;">
                <li>Verificar os logs detalhados no sistema</li>
                <li>Analisar as condições que causaram o erro</li>
                <li>Aplicar correções necessárias</li>
                <li>Executar teste para validar a correção</li>
            </ol>
        </div>
        """

        return TemplatesRelatorios.gerar_template_base(
            f"ERRO - RPA {nome_rpa}",
            conteudo,
            "erro"
        )


# Instância global para uso em outros módulos
templates_relatorios = TemplatesRelatorios()
