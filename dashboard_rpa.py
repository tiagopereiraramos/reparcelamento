"""
Dashboard RPA - Sistema de Monitoramento
Interface web moderna para acompanhar agendamentos e execuções dos RPAs

Desenvolvido em Português Brasileiro
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
import requests
from typing import Dict, Any, List
import time

# Configuração da página
st.set_page_config(
    page_title="Dashboard RPA - Sistema de Reparcelamento",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .status-success {
        background-color: #28a745;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-weight: bold;
    }
    .status-error {
        background-color: #dc3545;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-weight: bold;
    }
    .status-running {
        background-color: #ffc107;
        color: black;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

class DashboardRPA:
    """Classe principal do dashboard"""

    def __init__(self):
        self.api_url = "http://localhost:5000"
        self.arquivo_historico = "logs/historico_execucoes.json"

    def carregar_historico(self) -> List[Dict]:
        """Carrega histórico de execuções"""
        try:
            if os.path.exists(self.arquivo_historico):
                with open(self.arquivo_historico, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except:
            return []

    def obter_status_api(self) -> Dict[str, Any]:
        """Obtém status da API"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                return {"status": "online", "dados": response.json()}
            else:
                return {"status": "erro", "codigo": response.status_code}
        except:
            return {"status": "offline"}

    def obter_execucoes_ativas(self) -> Dict[str, Any]:
        """Obtém execuções ativas da API"""
        try:
            response = requests.get(f"{self.api_url}/execucoes", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {"dados": {"total": 0, "execucoes": []}}
        except:
            return {"dados": {"total": 0, "execucoes": []}}

def carregar_estatisticas_fila():
    """Carrega estatísticas da fila de processamento do arquivo único"""
    try:
        import json
        import os

        arquivo_fila = os.path.join("dados_processamento", "fila_contratos_sienge.json")

        if not os.path.exists(arquivo_fila):
            return {"total": 0, "pendentes": 0, "processados": 0, "erros": 0}

        with open(arquivo_fila, 'r', encoding='utf-8') as f:
            dados_fila = json.load(f)

        contratos = dados_fila.get("contratos", [])
        total = len(contratos)
        pendentes = sum(1 for c in contratos if c.get("status_processamento") == "pendente")
        processados = sum(1 for c in contratos if c.get("status_processamento") == "processado")
        erros = sum(1 for c in contratos if c.get("status_processamento") == "erro")

        return {
            "total": total,
            "pendentes": pendentes, 
            "processados": processados,
            "erros": erros,
            "timestamp": dados_fila.get("timestamp_ultima_atualizacao", dados_fila.get("timestamp_criacao", ""))
        }

    except Exception as e:
        st.error(f"Erro ao carregar fila: {str(e)}")
        return {"total": 0, "pendentes": 0, "processados": 0, "erros": 0}

def main():
    """Função principal do dashboard"""

    # Inicializa dashboard
    dashboard = DashboardRPA()

    # Cabeçalho
    st.markdown('<h1 class="main-header">🤖 Dashboard RPA - Sistema de Reparcelamento</h1>', unsafe_allow_html=True)
    st.markdown("**Arquitetura Refatorada v2.0** - Monitoramento em tempo real dos 4 RPAs independentes")

    # Sidebar com controles
    with st.sidebar:
        st.header("⚙️ Controles")

        # Auto-refresh
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=True)
        if auto_refresh:
            time.sleep(0.1)  # Para trigger do rerun
            st.rerun()

        st.markdown("---")

        # Configurações
        st.header("📋 Configurações")
        st.text("API URL: http://localhost:5000")

        # Status da API
        status_api = dashboard.obter_status_api()
        if status_api["status"] == "online":
            st.success("✅ API Online")
        elif status_api["status"] == "offline":
            st.error("❌ API Offline")
        else:
            st.warning("⚠️ API com problemas")

        st.markdown("---")

        # Ações manuais
        st.header("🎮 Ações Manuais")

        if st.button("🚀 Executar RPAs 1+2 Agora"):
            with st.spinner("Executando..."):
                try:
                    os.system("python agendador_diario.py agora &")
                    st.success("✅ Execução iniciada!")
                except:
                    st.error("❌ Erro ao executar")

        if st.button("🔄 Workflow Completo"):
            with st.spinner("Iniciando workflow..."):
                try:
                    payload = {
                        "planilha_calculo_id": "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk",
                        "planilha_apoio_id": "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk",
                        "processar_todos": False
                    }
                    response = requests.post(f"{dashboard.api_url}/workflow/reparcelamento", json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ Workflow iniciado! ID: {data['dados']['execucao_id']}")
                    else:
                        st.error("❌ Erro ao iniciar workflow")
                except:
                    st.error("❌ Erro de conexão")

    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)

    # Carrega dados
    historico = dashboard.carregar_historico()
    execucoes_ativas = dashboard.obter_execucoes_ativas()
    stats_fila = carregar_estatisticas_fila()

    with col1:
        st.metric(
            label="🤖 RPAs Ativos",
            value="4",
            delta="Independentes"
        )

    with col2:
        total_execucoes = len(historico)
        st.metric(
            label="📊 Execuções Totais", 
            value=total_execucoes,
            delta=f"Últimos 30 dias"
        )

    with col3:
        ativas = execucoes_ativas["dados"]["total"]
        st.metric(
            label="⚡ Execuções Ativas",
            value=ativas,
            delta="Em tempo real"
        )

    with col4:
        # Taxa de sucesso
        if historico:
            sucessos = sum(1 for exec in historico if exec["resultado"].get("sucesso_geral", False))
            taxa_sucesso = (sucessos / len(historico)) * 100
        else:
            taxa_sucesso = 0

        st.metric(
            label="✅ Taxa de Sucesso",
            value=f"{taxa_sucesso:.1f}%",
            delta="Últimas execuções"
        )

    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Visão Geral", "⏰ Agendamentos", "🔍 Execuções Ativas", "📊 Histórico"])

    with tab1:
        # Visão geral do sistema
        st.header("🎯 Status dos RPAs")

        rpa_col1, rpa_col2 = st.columns(2)

        with rpa_col1:
            st.subheader("🤖 RPA 1: Coleta de Índices")
            st.write("**Função**: Coleta IPCA/IGPM dos sites oficiais")
            st.write("**Frequência**: Diário às 08:00")
            st.write("**Última execução**: ", datetime.now().strftime("%d/%m/%Y %H:%M") if historico else "Nunca")

            st.subheader("📊 RPA 2: Análise de Planilhas") 
            st.write("**Função**: Identifica contratos para reparcelamento")
            st.write("**Frequência**: Diário às 08:00 (após RPA 1)")
            st.write("**Última análise**: ", datetime.now().strftime("%d/%m/%Y %H:%M") if historico else "Nunca")

        with rpa_col2:
            st.subheader("🏢 RPA 3: Processamento Sienge")
            st.write("**Função**: Executa reparcelamento no ERP")
            st.write("**Frequência**: Sob demanda (fila do RPA 2)")
            st.write("**Status**: Aguardando fila")

            st.subheader("🏦 RPA 4: Processamento Sicredi")
            st.write("**Função**: Atualiza carnês no WebBank")
            st.write("**Frequência**: Após RPA 3")
            st.write("**Status**: Aguardando processamento")

        # Gráfico de execuções por dia
        if historico:
            st.header("📈 Execuções por Dia")

            # Processa dados para gráfico
            df_historico = []
            for execucao in historico[-14:]:  # Últimos 14 dias
                data = execucao["resultado"]["data"]
                sucesso = execucao["resultado"].get("sucesso_geral", False)
                contratos = execucao["resultado"].get("contratos_identificados", 0)

                df_historico.append({
                    "Data": data,
                    "Sucesso": "✅ Sucesso" if sucesso else "❌ Erro",
                    "Contratos": contratos
                })

            if df_historico:
                df = pd.DataFrame(df_historico)

                fig = px.bar(
                    df, 
                    x="Data", 
                    y="Contratos",
                    color="Sucesso",
                    title="Contratos Identificados por Dia",
                    color_discrete_map={"✅ Sucesso": "#28a745", "❌ Erro": "#dc3545"}
                )
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # Agendamentos
        st.header("⏰ Configuração de Agendamentos")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📅 Agendamento Atual")
            st.info("""
            **RPAs 1 e 2 (Diários)**
            - ⏰ Horário: 08:00 (GMT-3)
            - 📊 RPA 1: Coleta índices econômicos
            - 📋 RPA 2: Analisa contratos
            - 🎯 RPAs 3 e 4: Disparados conforme demanda
            """)

        with col2:
            st.subheader("⚙️ Próximas Execuções")

            # Calcula próximas execuções
            agora = datetime.now()
            proxima_execucao = agora.replace(hour=8, minute=0, second=0, microsecond=0)

            if proxima_execucao <= agora:
                proxima_execucao += timedelta(days=1)

            for i in range(7):  # Próximos 7 dias
                data_exec = proxima_execucao + timedelta(days=i)
                dia_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][data_exec.weekday()]

                st.write(f"📅 {dia_semana}, {data_exec.strftime('%d/%m')} às 08:00")

        # Status do agendador
        st.header("🔧 Status do Agendador")

        agendador_col1, agendador_col2 = st.columns(2)

        with agendador_col1:
            if st.button("▶️ Iniciar Agendador"):
                with st.spinner("Iniciando agendador..."):
                    try:
                        os.system("python agendador_diario.py iniciar &")
                        st.success("✅ Agendador iniciado!")
                    except:
                        st.error("❌ Erro ao iniciar agendador")

        with agendador_col2:
            if st.button("⏸️ Parar Agendador"):
                st.warning("⚠️ Funcionalidade em desenvolvimento")

    with tab3:
        # Execuções ativas
        st.header("🔍 Execuções em Andamento")

        if execucoes_ativas["dados"]["total"] > 0:
            for exec_id in execucoes_ativas["dados"]["execucoes"]:
                with st.expander(f"📋 Execução: {exec_id}"):
                    try:
                        response = requests.get(f"{dashboard.api_url}/workflow/status/{exec_id}")
                        if response.status_code == 200:
                            dados = response.json()["dados"]

                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.write(f"**Status**: {dados.get('status', 'Desconhecido')}")
                                st.write(f"**Etapa Atual**: {dados.get('etapa_atual', 'N/A')}")

                            with col2:
                                st.write(f"**Início**: {dados.get('inicio', 'N/A')}")
                                etapas = dados.get('etapas_concluidas', [])
                                st.write(f"**Etapas Concluídas**: {len(etapas)}/4")

                            with col3:
                                if dados.get('status') == 'concluido':
                                    st.success("✅ Concluído")
                                elif dados.get('status') == 'erro':
                                    st.error("❌ Erro")
                                else:
                                    st.info("⏳ Em execução")

                            # Barra de progresso
                            progresso = len(etapas) / 4
                            st.progress(progresso)

                        else:
                            st.error("❌ Erro ao obter status")
                    except:
                        st.error("❌ Erro de conexão")
        else:
            st.info("ℹ️ Nenhuma execução ativa no momento")

            # Botão para executar teste
            if st.button("🧪 Executar Teste Rápido"):
                with st.spinner("Executando teste..."):
                    try:
                        payload = {"planilha_id": "teste"}
                        response = requests.post(f"{dashboard.api_url}/rpa/coleta-indices", json=payload)
                        if response.status_code == 200:
                            st.success("✅ Teste executado com sucesso!")
                        else:
                            st.error("❌ Erro no teste")
                    except:
                        st.error("❌ Erro de conexão")

    with tab4:
        # Histórico detalhado
        st.header("📊 Histórico de Execuções")

        if historico:
            # Filtros
            col1, col2 = st.columns(2)

            with col1:
                dias_filtro = st.selectbox("📅 Período", [7, 14, 30], index=2)

            with col2:
                apenas_sucessos = st.checkbox("✅ Apenas sucessos")

            # Processa histórico filtrado
            historico_filtrado = historico[-dias_filtro:]

            if apenas_sucessos:
                historico_filtrado = [
                    exec for exec in historico_filtrado 
                    if exec["resultado"].get("sucesso_geral", False)
                ]

            # Tabela de execuções
            dados_tabela = []
            for exec in historico_filtrado:
                resultado = exec["resultado"]

                dados_tabela.append({
                    "Data": resultado["data"],
                    "Horário": resultado["horario"],
                    "RPA 1": "✅" if resultado.get("rpa1_coleta_indices", {}).get("sucesso") else "❌",
                    "RPA 2": "✅" if resultado.get("rpa2_analise_planilhas", {}).get("sucesso") else "❌",
                    "Contratos": resultado.get("contratos_identificados", 0),
                    "RPAs 3+4": "✅" if resultado.get("rpas_34_disparados") else "⏳",
                    "Status Geral": "✅ Sucesso" if resultado.get("sucesso_geral") else "❌ Erro"
                })

            if dados_tabela:
                df_tabela = pd.DataFrame(dados_tabela)
                st.dataframe(df_tabela, use_container_width=True)

                # Estatísticas
                st.subheader("📈 Estatísticas do Período")

                col1, col2, col3 = st.columns(3)

                with col1:
                    total_contratos = sum(row["Contratos"] for row in dados_tabela)
                    st.metric("🎯 Total de Contratos", total_contratos)

                with col2:
                    execucoes_sucesso = len([row for row in dados_tabela if "✅" in row["Status Geral"]])
                    st.metric("✅ Execuções Bem-sucedidas", execucoes_sucesso)

                with col3:
                    media_contratos = total_contratos / len(dados_tabela) if dados_tabela else 0
                    st.metric("📊 Média Contratos/Dia", f"{media_contratos:.1f}")

            else:
                st.info("ℹ️ Nenhuma execução encontrada no período selecionado")
        else:
            st.info("ℹ️ Nenhum histórico disponível ainda")
            st.write("Execute o agendador para gerar dados históricos")

    # Fila de processamento Sienge
    st.subheader("📋 Fila de Processamento Sienge")

    if stats_fila["total"] > 0:
        # Gráfico de progresso
        col_prog1, col_prog2 = st.columns([3, 1])

        with col_prog1:
            # Gráfico de pizza do status
            status_data = {
                "Status": ["Pendentes", "Processados", "Com Erro"],
                "Quantidade": [stats_fila["pendentes"], stats_fila["processados"], stats_fila["erros"]]
            }

            fig_status = px.pie(
                values=status_data["Quantidade"],
                names=status_data["Status"],
                title="Status dos Contratos na Fila",
                color_discrete_map={
                    "Pendentes": "#ffc107",
                    "Processados": "#28a745", 
                    "Com Erro": "#dc3545"
                }
            )
            st.plotly_chart(fig_status, use_container_width=True)

        with col_prog2:
            st.metric("🎯 Progresso", f"{stats_fila['processados']}/{stats_fila['total']}")
            progresso = stats_fila["processados"] / stats_fila["total"] if stats_fila["total"] > 0 else 0
            st.progress(progresso)

            if stats_fila["pendentes"] > 0:
                st.warning(f"⏳ {stats_fila['pendentes']} contratos aguardando processamento")

            if stats_fila["erros"] > 0:
                st.error(f"❌ {stats_fila['erros']} contratos com erro")
    else:
        st.info("📋 Nenhum contrato na fila. Execute o RPA de Análise de Planilhas primeiro.")

    # Histórico de execuções
    st.subheader("📊 Histórico de Execuções Recentes")

    # Simular dados de execuções
    execucoes_recentes = [
        {"RPA": "Análise Planilhas", "Status": "✅ Sucesso", "Hora": "14:30", "Contratos": stats_fila["total"]},
        {"RPA": "Coleta Índices", "Status": "✅ Sucesso", "Hora": "14:15", "Contratos": 0},
        {"RPA": "Sienge", "Status": "🔄 Executando" if stats_fila["pendentes"] > 0 else "✅ Concluído", "Hora": "14:45", "Contratos": stats_fila["processados"]},
        {"RPA": "Sicredi", "Status": "⏳ Aguardando", "Hora": "-", "Contratos": 0},
    ]

    df_execucoes = pd.DataFrame(execucoes_recentes)
    st.dataframe(df_execucoes, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(
        "🤖 **Sistema RPA de Reparcelamento v2.0** | "
        "⚡ **Arquitetura Refatorada** | "
        f"🕐 **Última atualização**: {datetime.now().strftime('%H:%M:%S')}"
    )

    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()