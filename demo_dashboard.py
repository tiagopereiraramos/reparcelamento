"""
Dashboard RPA - Versão Demo com Dados de Exemplo
Interface web para demonstrar o sistema funcionando

Desenvolvido em Português Brasileiro
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import json
import time

# Configuração da página
st.set_page_config(
    page_title="Sistema RPA - Dashboard Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dados demonstrativos
def gerar_dados_demo():
    """Gera dados de exemplo para demonstração"""
    
    # Últimas 30 execuções (exemplo)
    dados_execucoes = []
    for i in range(30):
        data = datetime.now() - timedelta(days=i//4, hours=i%24)
        rpa_tipo = ["Coleta_Indices", "Analise_Planilhas", "Sienge", "Sicredi"][i % 4]
        sucesso = True if i % 5 != 0 else False  # 80% de sucesso
        
        execucao = {
            "timestamp": data.isoformat(),
            "nome_rpa": rpa_tipo,
            "sucesso": sucesso,
            "tempo_execucao": 120 + (i * 10) % 300,  # 2-7 minutos
            "contratos_processados": 5 + i % 15 if rpa_tipo == "Analise_Planilhas" else 0,
            "indices_coletados": {"ipca": 4.5 + i*0.1, "igpm": 3.2 + i*0.05} if rpa_tipo == "Coleta_Indices" else None
        }
        dados_execucoes.append(execucao)
    
    return dados_execucoes

def gerar_metricas_demo():
    """Gera métricas de exemplo"""
    return {
        "total_execucoes": 247,
        "execucoes_hoje": 4,
        "taxa_sucesso": 85.2,
        "contratos_processados_mes": 89,
        "fonte_dados": "Demo - Dados de Exemplo"
    }

# CSS customizado
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin: 0.5rem 0;
}

.status-online {
    color: #28a745;
    font-weight: bold;
}

.status-offline {
    color: #dc3545;
    font-weight: bold;
}

.demo-banner {
    background: #fff3cd;
    border: 1px solid #ffeaa7;
    padding: 1rem;
    border-radius: 5px;
    margin-bottom: 1rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# Banner de demonstração
st.markdown("""
<div class="demo-banner">
🚀 <strong>DEMONSTRAÇÃO DO SISTEMA RPA v2.0</strong><br>
Este dashboard está rodando com dados de exemplo para demonstrar as funcionalidades.
</div>
""", unsafe_allow_html=True)

# Cabeçalho principal
st.markdown('<h1 class="main-header">🤖 Sistema RPA de Reparcelamento</h1>', unsafe_allow_html=True)

# Sidebar com controles
st.sidebar.header("⚙️ Controles do Sistema")

# Status da API (simulado)
st.sidebar.subheader("🔗 Status da API")
api_status = st.sidebar.selectbox("Simular Status:", ["🟢 Online", "🔴 Offline"], index=0)
if "Online" in api_status:
    st.sidebar.success("API funcionando normalmente")
else:
    st.sidebar.error("API indisponível")

# Controles manuais
st.sidebar.subheader("🎮 Controles Manuais")

if st.sidebar.button("🚀 Executar RPAs 1+2 Agora", type="primary"):
    st.sidebar.success("✅ Execução iniciada! (Demo)")

if st.sidebar.button("🔄 Workflow Completo"):
    st.sidebar.info("🔄 Workflow em execução... (Demo)")

if st.sidebar.button("⏸️ Parar Agendador"):
    st.sidebar.warning("⏸️ Agendador pausado (Demo)")

# Auto-refresh
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=True)

# Métricas principais
st.header("📊 Métricas do Sistema")

metricas = gerar_metricas_demo()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🤖 RPAs Ativos",
        value="4",
        delta="Todos operacionais"
    )

with col2:
    st.metric(
        label="📊 Execuções Totais",
        value=metricas["total_execucoes"],
        delta=f"+{metricas['execucoes_hoje']} hoje"
    )

with col3:
    st.metric(
        label="✅ Taxa de Sucesso",
        value=f"{metricas['taxa_sucesso']}%",
        delta="↗️ +2.1%"
    )

with col4:
    st.metric(
        label="📋 Contratos/Mês",
        value=metricas["contratos_processados_mes"],
        delta="↗️ +15"
    )

# Tabs principais
tab1, tab2, tab3, tab4 = st.tabs(["📈 Visão Geral", "⏰ Agendamentos", "🔍 Execuções Ativas", "📊 Histórico"])

with tab1:
    st.subheader("📈 Visão Geral do Sistema")
    
    # Status individual dos RPAs
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Status dos RPAs")
        
        rpas_status = [
            {"nome": "RPA 1 - Coleta de Índices", "status": "🟢 Ativo", "ultima_exec": "Hoje 08:00"},
            {"nome": "RPA 2 - Análise de Planilhas", "status": "🟢 Ativo", "ultima_exec": "Hoje 08:15"},
            {"nome": "RPA 3 - Processamento Sienge", "status": "🟡 Standby", "ultima_exec": "Ontem 16:30"},
            {"nome": "RPA 4 - Processamento Sicredi", "status": "🟡 Standby", "ultima_exec": "Ontem 17:00"}
        ]
        
        for rpa in rpas_status:
            with st.container():
                st.write(f"**{rpa['nome']}**")
                st.write(f"Status: {rpa['status']}")
                st.write(f"Última execução: {rpa['ultima_exec']}")
                st.divider()
    
    with col2:
        st.subheader("📊 Execuções por Dia")
        
        # Gráfico de execuções
        dados_grafico = []
        for i in range(7):
            data = datetime.now() - timedelta(days=i)
            dados_grafico.append({
                "Data": data.strftime("%d/%m"),
                "Execuções": 4 + (i * 2) % 8,
                "Sucessos": 3 + (i * 2) % 6
            })
        
        df_grafico = pd.DataFrame(dados_grafico)
        
        fig = px.bar(df_grafico, x="Data", y=["Execuções", "Sucessos"], 
                    title="Execuções nos Últimos 7 Dias",
                    color_discrete_map={"Execuções": "#1f77b4", "Sucessos": "#2ca02c"})
        
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("⏰ Agendamentos e Cronograma")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚙️ Configuração Atual")
        st.info("""
        **Horário de Execução:** 08:00 (diário)
        **Timezone:** America/Sao_Paulo
        **RPAs Agendados:** 1 e 2 (automático)
        **Status:** 🟢 Ativo
        """)
        
        if st.button("⚙️ Alterar Configurações"):
            st.success("Configurações atualizadas! (Demo)")
    
    with col2:
        st.subheader("📅 Próximas Execuções")
        
        proximas_exec = []
        for i in range(7):
            data = datetime.now() + timedelta(days=i+1)
            proximas_exec.append({
                "Data": data.strftime("%d/%m/%Y"),
                "Horário": "08:00",
                "RPAs": "1 + 2 (automático)",
                "Status": "🕐 Agendado"
            })
        
        df_agenda = pd.DataFrame(proximas_exec)
        st.dataframe(df_agenda, use_container_width=True)

with tab3:
    st.subheader("🔍 Execuções Ativas")
    
    # Simular execução ativa
    if st.button("🎬 Simular Execução Ativa"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        etapas = [
            "🤖 Iniciando RPA 1 - Coleta de Índices...",
            "📊 Coletando IPCA do IBGE...",
            "📈 Coletando IGPM da FGV...",
            "✅ RPA 1 concluído com sucesso!",
            "🤖 Iniciando RPA 2 - Análise de Planilhas...",
            "📋 Analisando contratos...",
            "🎯 15 contratos identificados para reajuste",
            "✅ RPA 2 concluído com sucesso!"
        ]
        
        for i, etapa in enumerate(etapas):
            progress_bar.progress((i + 1) / len(etapas))
            status_text.text(etapa)
            time.sleep(0.8)
        
        st.success("🎉 Workflow concluído com sucesso!")
    
    st.subheader("📋 Status Atual")
    st.info("Nenhuma execução ativa no momento.")

with tab4:
    st.subheader("📊 Histórico de Execuções")
    
    # Gerar dados de histórico
    dados_execucoes = gerar_dados_demo()
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_rpa = st.selectbox("Filtrar por RPA:", 
                                 ["Todos"] + list(set([ex["nome_rpa"] for ex in dados_execucoes])))
    
    with col2:
        filtro_status = st.selectbox("Filtrar por Status:", ["Todos", "Sucesso", "Erro"])
    
    with col3:
        filtro_periodo = st.selectbox("Período:", ["Últimos 7 dias", "Últimos 30 dias", "Todos"])
    
    # Aplicar filtros
    dados_filtrados = dados_execucoes.copy()
    if filtro_rpa != "Todos":
        dados_filtrados = [ex for ex in dados_filtrados if ex["nome_rpa"] == filtro_rpa]
    
    if filtro_status != "Todos":
        sucesso_filtro = filtro_status == "Sucesso"
        dados_filtrados = [ex for ex in dados_filtrados if ex["sucesso"] == sucesso_filtro]
    
    # Tabela de histórico
    if dados_filtrados:
        df_historico = pd.DataFrame(dados_filtrados)
        df_historico["Status"] = df_historico["sucesso"].apply(lambda x: "✅ Sucesso" if x else "❌ Erro")
        df_historico["Tempo (min)"] = df_historico["tempo_execucao"].apply(lambda x: f"{x//60}:{x%60:02d}")
        df_historico["Data/Hora"] = pd.to_datetime(df_historico["timestamp"]).dt.strftime("%d/%m %H:%M")
        
        st.dataframe(
            df_historico[["Data/Hora", "nome_rpa", "Status", "Tempo (min)"]].rename(columns={
                "nome_rpa": "RPA",
                "Data/Hora": "Data/Hora"
            }),
            use_container_width=True
        )
        
        # Gráfico de performance
        st.subheader("📈 Performance por RPA")
        
        df_perf = df_historico.groupby("nome_rpa").agg({
            "sucesso": "mean",
            "tempo_execucao": "mean"
        }).reset_index()
        
        df_perf["Taxa de Sucesso (%)"] = df_perf["sucesso"] * 100
        df_perf["Tempo Médio (min)"] = df_perf["tempo_execucao"] / 60
        
        fig_perf = px.scatter(df_perf, x="Tempo Médio (min)", y="Taxa de Sucesso (%)", 
                            text="nome_rpa", title="Performance dos RPAs",
                            size=[10]*len(df_perf))
        
        fig_perf.update_traces(textposition="top center")
        st.plotly_chart(fig_perf, use_container_width=True)
    
    else:
        st.warning("Nenhum resultado encontrado para os filtros selecionados.")

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666;">
🤖 Sistema RPA de Reparcelamento v2.0 - Dashboard Demo<br>
Persistência Híbrida: MongoDB + JSON | Deploy Self-Hosted<br>
<em>Dados demonstrativos para visualização das funcionalidades</em>
</div>
""", unsafe_allow_html=True)

# Auto-refresh (simulado)
if auto_refresh:
    time.sleep(0.1)  # Simular refresh