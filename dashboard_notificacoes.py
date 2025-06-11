"""
Dashboard de Notificações - Sistema RPA v2.0
Interface para configurar notificações por email

Desenvolvido em Português Brasileiro
"""

import streamlit as st
import json
import os
from datetime import datetime
from core.notificacoes_simples import notificacoes, testar_notificacoes

def renderizar_aba_notificacoes():
    """Renderiza aba de configuração de notificações"""
    
    st.header("📧 Configuração de Notificações")
    
    # Carregar configurações atuais
    config = notificacoes.configuracoes
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("⚙️ Configurações Gerais")
        
        # Toggle geral de notificações
        habilitado = st.toggle(
            "🔔 Notificações Habilitadas",
            value=config.get('habilitado', True),
            help="Ativa ou desativa todas as notificações do sistema"
        )
        
        if habilitado:
            # Configuração de destinatários
            st.subheader("📬 Destinatários")
            
            # Lista atual de emails
            emails_atuais = config.get('destinatarios', ['admin@empresa.com'])
            
            # Editor de emails
            for i, email in enumerate(emails_atuais):
                col_email, col_remover = st.columns([3, 1])
                with col_email:
                    novo_email = st.text_input(
                        f"Email {i+1}",
                        value=email,
                        key=f"email_{i}",
                        placeholder="exemplo@empresa.com"
                    )
                    emails_atuais[i] = novo_email
                
                with col_remover:
                    if len(emails_atuais) > 1:  # Manter pelo menos um email
                        if st.button("🗑️", key=f"remover_{i}", help="Remover este email"):
                            emails_atuais.pop(i)
                            st.rerun()
            
            # Botão para adicionar novo email
            if st.button("➕ Adicionar Email"):
                emails_atuais.append("")
                st.rerun()
            
            # Configuração de eventos
            st.subheader("📅 Eventos para Notificar")
            
            eventos_config = config.get('eventos', {})
            
            col_evento1, col_evento2 = st.columns(2)
            
            with col_evento1:
                st.write("**RPAs Individuais:**")
                rpa_concluido = st.checkbox(
                    "✅ RPA Concluído com Sucesso",
                    value=eventos_config.get('rpa_concluido', True),
                    help="Notifica quando um RPA individual é concluído"
                )
                
                rpa_erro = st.checkbox(
                    "❌ Erro no RPA",
                    value=eventos_config.get('rpa_erro', True),
                    help="Notifica quando ocorre erro em um RPA"
                )
                
                indices_atualizados = st.checkbox(
                    "📊 Índices Econômicos Atualizados",
                    value=eventos_config.get('indices_atualizados', False),
                    help="Notifica quando IPCA/IGPM são atualizados"
                )
            
            with col_evento2:
                st.write("**Workflows Completos:**")
                workflow_concluido = st.checkbox(
                    "🔄 Workflow Concluído",
                    value=eventos_config.get('workflow_concluido', True),
                    help="Notifica quando workflow completo é finalizado"
                )
                
                contratos_identificados = st.checkbox(
                    "📋 Contratos Identificados",
                    value=eventos_config.get('contratos_identificados', True),
                    help="Notifica quando contratos para reparcelamento são identificados"
                )
        
        # Botões de ação
        st.markdown("---")
        col_salvar, col_testar, col_reset = st.columns(3)
        
        with col_salvar:
            if st.button("💾 Salvar Configurações", type="primary", use_container_width=True):
                # Atualizar configurações
                nova_config = {
                    'habilitado': habilitado,
                    'destinatarios': [email for email in emails_atuais if email.strip()],
                    'eventos': {
                        'rpa_concluido': rpa_concluido if habilitado else False,
                        'rpa_erro': rpa_erro if habilitado else False,
                        'workflow_concluido': workflow_concluido if habilitado else False,
                        'indices_atualizados': indices_atualizados if habilitado else False,
                        'contratos_identificados': contratos_identificados if habilitado else False
                    }
                }
                
                notificacoes.configuracoes.update(nova_config)
                notificacoes.salvar_configuracoes()
                
                st.success("✅ Configurações salvas com sucesso!")
                time.sleep(1)
                st.rerun()
        
        with col_testar:
            if st.button("🧪 Testar Notificações", use_container_width=True):
                if habilitado and emails_atuais:
                    with st.spinner("Enviando email de teste..."):
                        resultado = testar_notificacoes()
                        if resultado:
                            st.success("✅ Email de teste enviado com sucesso!")
                        else:
                            st.error("❌ Falha ao enviar email de teste. Verifique as configurações.")
                else:
                    st.warning("⚠️ Configure ao menos um email e habilite as notificações")
        
        with col_reset:
            if st.button("🔄 Restaurar Padrões", use_container_width=True):
                if st.button("✅ Confirmar Reset", key="confirmar_reset"):
                    # Restaurar configurações padrão
                    config_padrao = {
                        "habilitado": True,
                        "destinatarios": ["admin@empresa.com"],
                        "eventos": {
                            "rpa_concluido": True,
                            "rpa_erro": True,
                            "workflow_concluido": True,
                            "indices_atualizados": False,
                            "contratos_identificados": True
                        }
                    }
                    
                    notificacoes.configuracoes.update(config_padrao)
                    notificacoes.salvar_configuracoes()
                    
                    st.success("✅ Configurações restauradas!")
                    time.sleep(1)
                    st.rerun()
    
    with col2:
        st.subheader("📋 Status do Sistema")
        
        # Card de status
        if habilitado:
            st.success("🟢 Sistema Ativo")
        else:
            st.error("🔴 Sistema Inativo")
        
        # Informações de configuração
        st.metric("📧 Emails Configurados", len([e for e in emails_atuais if e.strip()]))
        
        eventos_ativos = sum(1 for v in eventos_config.values() if v) if habilitado else 0
        st.metric("📅 Eventos Ativos", eventos_ativos)
        
        # Últimas notificações (simulado)
        st.subheader("📨 Últimas Notificações")
        
        historico_simulado = [
            {"data": "27/05/2025 14:30", "evento": "RPA Concluído", "status": "✅"},
            {"data": "27/05/2025 09:15", "evento": "Workflow Iniciado", "status": "🔄"},
            {"data": "26/05/2025 18:45", "evento": "Índices Atualizados", "status": "📊"}
        ]
        
        for item in historico_simulado:
            with st.container():
                st.markdown(f"""
                <div style="
                    background-color: #f8f9fa;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 5px 0;
                    border-left: 3px solid #007bff;
                ">
                    <strong>{item['status']} {item['evento']}</strong><br>
                    <small style="color: #6c757d;">{item['data']}</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Configurações do sistema
        st.subheader("⚙️ Configurações do Sistema")
        
        with st.expander("🔧 Configurações Avançadas"):
            st.info("""
            **Email de Remetente:** sistema.rpa@empresa.com
            
            **Template:** HTML responsivo
            
            **Método:** Gmail API com Service Account
            
            **Configuração:** Automática via credenciais Google
            """)
            
            # Variáveis de ambiente relevantes
            st.code("""
            # Variáveis de ambiente necessárias:
            EMAIL_REMETENTE=sistema.rpa@empresa.com
            EMAIL_ADMIN=admin@empresa.com
            """)

def main():
    """Função principal para teste standalone"""
    st.title("🔔 Sistema de Notificações RPA")
    renderizar_aba_notificacoes()

if __name__ == "__main__":
    main()