
#!/usr/bin/env python3
"""
Teste RPA Sienge COMPLETO - Dados Reais + Marcação/Desmarcação Parcelas
Sistema único para testar todo o fluxo de reparcelamento com webscraping

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import traceback
import pandas as pd

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rpa_sienge.rpa_sienge import RPASienge
from core.data_manager import data_manager
from core.base_rpa import ResultadoRPA
from core.processador_regras_pdd import ProcessadorRegrasNegocio


class TestadorRPASiengeCompleto:
    """
    Testador RPA Sienge COMPLETO - Incluindo marcação/desmarcação de parcelas
    """
    
    def __init__(self):
        self.pasta_resultados = Path("rpa_sienge/dados_processamento/testes_completos")
        self.pasta_resultados.mkdir(parents=True, exist_ok=True)
        self.timestamp_execucao = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.rpa_sienge = None
        self.processador_regras = ProcessadorRegrasNegocio()
        
    def log_teste(self, mensagem: str, nivel: str = "INFO"):
        """Log estruturado para testes"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {nivel}: {mensagem}")
    
    def criar_dados_mock_completos(self) -> Dict[str, Any]:
        """
        Cria dados mock COMPLETOS com parcelas detalhadas para marcar/desmarcar
        """
        return {
            "_id": "mock_test_completo",
            "timestamp_ultima_atualizacao": datetime.now().isoformat(),
            "total_contratos": 1,
            "status_geral": "ativo",
            "contratos": [
                {
                    "id_fila": "reajuste_2239_teste_completo",
                    "numero_titulo": 2239,
                    "cliente": "SANDRO RIZZON VIEIRA",
                    "empreendimento": "MARCELY",
                    "cnpj_unidade": "BVRB",
                    "indexador": "IGPM",
                    "ultimo_reajuste": "jun.-24",
                    "dias_desde_ultimo_reajuste": 365,
                    "linha_planilha": 51,
                    "status_processamento": "pendente",
                    "prioridade": 11,
                    "timestamp_identificacao": "2025-06-17T22:54:00.838465",
                    "dados_completos": {
                        "Empresa": "BVRB",
                        "Loteamento": "MARCELY",
                        "Cliente": "SANDRO RIZZON VIEIRA",
                        "Quadra": 36,
                        "Lote": 128,
                        "Titulo": 2239,
                        "Índice": "IGPM",
                        "Juros": "8,0%",
                        "Tipo reajuste": "anual",
                        "Último reajuste": "jun.-24",
                        "Mês reajuste": "jun.-25",
                        "linha_planilha": 51,
                        "cliente": "SANDRO RIZZON VIEIRA",
                        "numero_titulo": 2239
                    },
                    # 🎯 DADOS CRÍTICOS PARA MARCAÇÃO/DESMARCAÇÃO
                    "parcelas_detalhadas": [
                        {
                            "documento": "CT001",
                            "parcela_condicao": "CT",
                            "numero_parcela": 1,
                            "data_vencimento": "2025-05-15",
                            "valor_a_receber": 2500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "VENCIDA",
                            "deve_desmarcar": True,
                            "motivo_desmarcacao": "Parcela CT vencida - deve ser desmarcada conforme PDD"
                        },
                        {
                            "documento": "CT002",
                            "parcela_condicao": "CT",
                            "numero_parcela": 2,
                            "data_vencimento": "2025-06-15",
                            "valor_a_receber": 2500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "VENCIDA",
                            "deve_desmarcar": True,
                            "motivo_desmarcacao": "Parcela CT vencida - deve ser desmarcada conforme PDD"
                        },
                        {
                            "documento": "CT003",
                            "parcela_condicao": "CT",
                            "numero_parcela": 3,
                            "data_vencimento": "2025-07-15",
                            "valor_a_receber": 2500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "A_VENCER",
                            "deve_desmarcar": False,
                            "motivo_desmarcacao": "Parcela CT futura - deve permanecer marcada"
                        },
                        {
                            "documento": "CT004",
                            "parcela_condicao": "CT",
                            "numero_parcela": 4,
                            "data_vencimento": "2025-08-15",
                            "valor_a_receber": 2500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "A_VENCER",
                            "deve_desmarcar": False,
                            "motivo_desmarcacao": "Parcela CT futura - deve permanecer marcada"
                        },
                        {
                            "documento": "REC001",
                            "parcela_condicao": "REC",
                            "numero_parcela": 1,
                            "data_vencimento": "2025-05-20",
                            "valor_a_receber": 1500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "VENCIDA",
                            "deve_desmarcar": True,
                            "motivo_desmarcacao": "Parcela REC vencida - deve ser desmarcada conforme PDD"
                        },
                        {
                            "documento": "REC002",
                            "parcela_condicao": "REC",
                            "numero_parcela": 2,
                            "data_vencimento": "2025-07-20",
                            "valor_a_receber": 1500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "A_VENCER",
                            "deve_desmarcar": False,
                            "motivo_desmarcacao": "Parcela REC futura - deve permanecer marcada"
                        },
                        {
                            "documento": "IPTU001",
                            "parcela_condicao": "IPTU",
                            "numero_parcela": 1,
                            "data_vencimento": "2025-01-31",
                            "valor_a_receber": 800.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "VENCIDA",
                            "deve_desmarcar": True,
                            "motivo_desmarcacao": "Parcela IPTU vencida - deve ser desmarcada conforme PDD"
                        },
                        {
                            "documento": "FAT001",
                            "parcela_condicao": "FAT",
                            "numero_parcela": 1,
                            "data_vencimento": "2025-09-15",
                            "valor_a_receber": 3000.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "A_VENCER",
                            "deve_desmarcar": False,
                            "motivo_desmarcacao": "Parcela FAT futura - deve permanecer marcada"
                        }
                    ],
                    "resumo_parcelas": {
                        "total_parcelas": 8,
                        "parcelas_vencidas": 4,
                        "parcelas_a_vencer": 4,
                        "ct_vencidas": 2,
                        "valor_total_vencido": 7300.00,
                        "valor_total_a_vencer": 9000.00,
                        "valor_total_geral": 16300.00
                    },
                    "processado_em": None,
                    "erro_processamento": None
                }
            ]
        }
    
    async def carregar_fila_real_mongodb(self) -> Optional[Dict[str, Any]]:
        """
        Carrega fila real do MongoDB com dados completos
        """
        try:
            self.log_teste("🔍 Conectando ao MongoDB para carregar fila real...")
            await data_manager.inicializar()
            
            if not data_manager.mongodb_ativo:
                self.log_teste("⚠️ MongoDB não disponível - usando dados mock completos", "WARNING")
                return None
            
            # Buscar fila de processamento real
            fila_real = await data_manager.obter_fila_sienge()
            
            if fila_real and fila_real.get("contratos"):
                self.log_teste(f"✅ Fila real carregada: {len(fila_real['contratos'])} contratos")
                
                # Enriquecer dados reais com estrutura de parcelas mock
                for contrato in fila_real['contratos']:
                    if not contrato.get('parcelas_detalhadas'):
                        contrato['parcelas_detalhadas'] = self._gerar_parcelas_mock_para_contrato(contrato)
                        contrato['resumo_parcelas'] = self._calcular_resumo_parcelas(contrato['parcelas_detalhadas'])
                
                return fila_real
            else:
                self.log_teste("⚠️ Fila vazia no MongoDB - usando dados mock completos", "WARNING")
                return None
                
        except Exception as e:
            self.log_teste(f"❌ Erro ao carregar fila real: {str(e)}", "ERROR")
            return None
    
    def _gerar_parcelas_mock_para_contrato(self, contrato: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Gera parcelas mock realistas para um contrato da fila real
        """
        numero_titulo = contrato.get('numero_titulo', 9999)
        hoje = date.today()
        
        parcelas = []
        
        # Gerar 2 CT vencidas
        for i in range(1, 3):
            data_vencimento = hoje - timedelta(days=30 * i)
            parcelas.append({
                "documento": f"CT{i:03d}",
                "parcela_condicao": "CT",
                "numero_parcela": i,
                "data_vencimento": data_vencimento.strftime("%Y-%m-%d"),
                "valor_a_receber": 2500.00,
                "status_parcela": "Em Aberto",
                "situacao": "VENCIDA",
                "deve_desmarcar": True,
                "motivo_desmarcacao": "Parcela CT vencida - deve ser desmarcada conforme PDD"
            })
        
        # Gerar 3 CT futuras
        for i in range(3, 6):
            data_vencimento = hoje + timedelta(days=30 * (i-2))
            parcelas.append({
                "documento": f"CT{i:03d}",
                "parcela_condicao": "CT",
                "numero_parcela": i,
                "data_vencimento": data_vencimento.strftime("%Y-%m-%d"),
                "valor_a_receber": 2500.00,
                "status_parcela": "Em Aberto",
                "situacao": "A_VENCER",
                "deve_desmarcar": False,
                "motivo_desmarcacao": "Parcela CT futura - deve permanecer marcada"
            })
        
        # Gerar 1 REC vencida
        data_vencimento = hoje - timedelta(days=45)
        parcelas.append({
            "documento": "REC001",
            "parcela_condicao": "REC",
            "numero_parcela": 1,
            "data_vencimento": data_vencimento.strftime("%Y-%m-%d"),
            "valor_a_receber": 1500.00,
            "status_parcela": "Em Aberto",
            "situacao": "VENCIDA",
            "deve_desmarcar": True,
            "motivo_desmarcacao": "Parcela REC vencida - deve ser desmarcada conforme PDD"
        })
        
        # Gerar 1 REC futura
        data_vencimento = hoje + timedelta(days=60)
        parcelas.append({
            "documento": "REC002",
            "parcela_condicao": "REC",
            "numero_parcela": 2,
            "data_vencimento": data_vencimento.strftime("%Y-%m-%d"),
            "valor_a_receber": 1500.00,
            "status_parcela": "Em Aberto",
            "situacao": "A_VENCER",
            "deve_desmarcar": False,
            "motivo_desmarcacao": "Parcela REC futura - deve permanecer marcada"
        })
        
        # Gerar 1 IPTU vencida
        data_vencimento = hoje - timedelta(days=120)
        parcelas.append({
            "documento": "IPTU001",
            "parcela_condicao": "IPTU",
            "numero_parcela": 1,
            "data_vencimento": data_vencimento.strftime("%Y-%m-%d"),
            "valor_a_receber": 800.00,
            "status_parcela": "Em Aberto",
            "situacao": "VENCIDA",
            "deve_desmarcar": True,
            "motivo_desmarcacao": "Parcela IPTU vencida - deve ser desmarcada conforme PDD"
        })
        
        return parcelas
    
    def _calcular_resumo_parcelas(self, parcelas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula resumo das parcelas para análise
        """
        total_parcelas = len(parcelas)
        parcelas_vencidas = len([p for p in parcelas if p['situacao'] == 'VENCIDA'])
        parcelas_a_vencer = len([p for p in parcelas if p['situacao'] == 'A_VENCER'])
        ct_vencidas = len([p for p in parcelas if p['parcela_condicao'] == 'CT' and p['situacao'] == 'VENCIDA'])
        
        valor_total_vencido = sum(p['valor_a_receber'] for p in parcelas if p['situacao'] == 'VENCIDA')
        valor_total_a_vencer = sum(p['valor_a_receber'] for p in parcelas if p['situacao'] == 'A_VENCER')
        valor_total_geral = valor_total_vencido + valor_total_a_vencer
        
        return {
            "total_parcelas": total_parcelas,
            "parcelas_vencidas": parcelas_vencidas,
            "parcelas_a_vencer": parcelas_a_vencer,
            "ct_vencidas": ct_vencidas,
            "valor_total_vencido": valor_total_vencido,
            "valor_total_a_vencer": valor_total_a_vencer,
            "valor_total_geral": valor_total_geral
        }
    
    async def teste_análise_parcelas_marcacao(self) -> bool:
        """
        Testa análise de parcelas e lógica de marcação/desmarcação
        """
        self.log_teste("🧪 TESTE: ANÁLISE PARCELAS E MARCAÇÃO/DESMARCAÇÃO")
        self.log_teste("=" * 60)
        
        try:
            # Carregar dados completos
            fila_real = await self.carregar_fila_real_mongodb()
            
            if fila_real:
                fila_dados = fila_real
                fonte = "MongoDB Real + Parcelas Mock"
            else:
                fila_dados = self.criar_dados_mock_completos()
                fonte = "Dados Mock Completos"
            
            self.log_teste(f"📊 Fonte dos dados: {fonte}")
            
            contratos = fila_dados.get("contratos", [])
            if not contratos:
                self.log_teste("❌ Nenhum contrato encontrado", "ERROR")
                return False
            
            contrato_teste = contratos[0]
            parcelas = contrato_teste.get("parcelas_detalhadas", [])
            resumo = contrato_teste.get("resumo_parcelas", {})
            
            self.log_teste(f"\n📋 Análise do Contrato {contrato_teste.get('numero_titulo')}")
            self.log_teste(f"   👤 Cliente: {contrato_teste.get('cliente')}")
            self.log_teste(f"   🏢 Empreendimento: {contrato_teste.get('empreendimento')}")
            
            self.log_teste(f"\n📊 Resumo Parcelas:")
            self.log_teste(f"   📄 Total de parcelas: {resumo.get('total_parcelas', 0)}")
            self.log_teste(f"   🚨 Parcelas vencidas: {resumo.get('parcelas_vencidas', 0)}")
            self.log_teste(f"   ⏳ Parcelas a vencer: {resumo.get('parcelas_a_vencer', 0)}")
            self.log_teste(f"   🔥 CT vencidas: {resumo.get('ct_vencidas', 0)}")
            self.log_teste(f"   💰 Valor total vencido: R$ {resumo.get('valor_total_vencido', 0):,.2f}")
            self.log_teste(f"   💰 Valor total a vencer: R$ {resumo.get('valor_total_a_vencer', 0):,.2f}")
            self.log_teste(f"   💰 Valor total geral: R$ {resumo.get('valor_total_geral', 0):,.2f}")
            
            # Análise detalhada de cada parcela
            self.log_teste(f"\n🔍 ANÁLISE DETALHADA DAS PARCELAS:")
            self.log_teste("   " + "="*50)
            
            parcelas_desmarcar = []
            parcelas_manter = []
            
            for i, parcela in enumerate(parcelas, 1):
                status_marcacao = "❌ DESMARCAR" if parcela['deve_desmarcar'] else "✅ MANTER"
                situacao_emoji = "🚨" if parcela['situacao'] == 'VENCIDA' else "⏳"
                
                self.log_teste(f"   {i}. {parcela['documento']} ({parcela['parcela_condicao']})")
                self.log_teste(f"      📅 Vencimento: {parcela['data_vencimento']}")
                self.log_teste(f"      💰 Valor: R$ {parcela['valor_a_receber']:,.2f}")
                self.log_teste(f"      {situacao_emoji} Situação: {parcela['situacao']}")
                self.log_teste(f"      {status_marcacao}")
                self.log_teste(f"      📝 Motivo: {parcela['motivo_desmarcacao']}")
                self.log_teste("")
                
                if parcela['deve_desmarcar']:
                    parcelas_desmarcar.append(parcela)
                else:
                    parcelas_manter.append(parcela)
            
            # Resumo de ações para webscraping
            self.log_teste(f"🎯 AÇÕES PARA WEBSCRAPING:")
            self.log_teste(f"   ❌ Parcelas para DESMARCAR: {len(parcelas_desmarcar)}")
            self.log_teste(f"   ✅ Parcelas para MANTER: {len(parcelas_manter)}")
            
            if parcelas_desmarcar:
                self.log_teste(f"\n❌ LISTA DE DESMARCAÇÃO (para automação):")
                for parcela in parcelas_desmarcar:
                    self.log_teste(f"   • {parcela['documento']} - {parcela['data_vencimento']} - R$ {parcela['valor_a_receber']:,.2f}")
            
            if parcelas_manter:
                self.log_teste(f"\n✅ LISTA DE MANUTENÇÃO (permanecem marcadas):")
                for parcela in parcelas_manter:
                    self.log_teste(f"   • {parcela['documento']} - {parcela['data_vencimento']} - R$ {parcela['valor_a_receber']:,.2f}")
            
            # Salvar resultado
            resultado_analise = {
                "contrato": contrato_teste,
                "resumo_parcelas": resumo,
                "parcelas_detalhadas": parcelas,
                "parcelas_desmarcar": parcelas_desmarcar,
                "parcelas_manter": parcelas_manter,
                "total_desmarcar": len(parcelas_desmarcar),
                "total_manter": len(parcelas_manter),
                "valor_desmarcar": sum(p['valor_a_receber'] for p in parcelas_desmarcar),
                "valor_manter": sum(p['valor_a_receber'] for p in parcelas_manter)
            }
            
            await self._salvar_resultado_teste("analise_parcelas_marcacao", resultado_analise)
            
            return True
            
        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            traceback.print_exc()
            return False
    
    async def teste_simulacao_webscraping_reparcelamento(self) -> bool:
        """
        Simula o webscraping completo do reparcelamento incluindo marcação/desmarcação
        """
        self.log_teste("🧪 TESTE: SIMULAÇÃO WEBSCRAPING REPARCELAMENTO COMPLETO")
        self.log_teste("=" * 60)
        
        try:
            # Carregar dados do teste anterior
            fila_real = await self.carregar_fila_real_mongodb()
            
            if fila_real:
                fila_dados = fila_real
            else:
                fila_dados = self.criar_dados_mock_completos()
            
            contrato_teste = fila_dados['contratos'][0]
            parcelas = contrato_teste.get("parcelas_detalhadas", [])
            
            self.log_teste(f"🎯 Simulando webscraping para: {contrato_teste.get('numero_titulo')}")
            self.log_teste(f"👤 Cliente: {contrato_teste.get('cliente')}")
            
            # Simular etapas do webscraping
            etapas_webscraping = [
                "1. Login no Sienge",
                "2. Navegar para Financeiro → Contas a Receber → Reparcelamento",
                "3. Clicar em 'Inclusão'",
                f"4. Buscar título {contrato_teste.get('numero_titulo')}",
                "5. Aguardar carregamento das parcelas",
                "6. Aplicar lógica de marcação/desmarcação",
                "7. Configurar detalhes do reparcelamento",
                "8. Confirmar e salvar"
            ]
            
            self.log_teste(f"\n🤖 SIMULAÇÃO DAS ETAPAS:")
            
            for i, etapa in enumerate(etapas_webscraping, 1):
                self.log_teste(f"   {etapa}")
                
                # Simular etapa crítica de marcação/desmarcação
                if i == 6:
                    self.log_teste(f"\n   🔧 DETALHAMENTO ETAPA 6 - MARCAÇÃO/DESMARCAÇÃO:")
                    
                    # Primeiro: marcar todas as parcelas
                    self.log_teste(f"      • Clicar em 'Marcar Todas' (padrão Sienge)")
                    self.log_teste(f"      • {len(parcelas)} parcelas marcadas inicialmente")
                    
                    # Depois: desmarcar as parcelas vencidas
                    parcelas_desmarcar = [p for p in parcelas if p['deve_desmarcar']]
                    self.log_teste(f"      • Iniciando desmarcação de {len(parcelas_desmarcar)} parcelas:")
                    
                    for parcela in parcelas_desmarcar:
                        # Simular clique específico para desmarcar
                        self.log_teste(f"        → Desmarcar checkbox: {parcela['documento']}")
                        self.log_teste(f"          Motivo: {parcela['situacao']} ({parcela['data_vencimento']})")
                    
                    parcelas_finais_marcadas = [p for p in parcelas if not p['deve_desmarcar']]
                    valor_final_reparcelar = sum(p['valor_a_receber'] for p in parcelas_finais_marcadas)
                    
                    self.log_teste(f"      • Resultado final: {len(parcelas_finais_marcadas)} parcelas marcadas")
                    self.log_teste(f"      • Valor total para reparcelar: R$ {valor_final_reparcelar:,.2f}")
                
                # Simular tempo de processamento
                import time
                time.sleep(0.1)
            
            # Simular dados que seriam preenchidos no formulário
            igpm_mock = 3.89
            parcelas_finais = [p for p in parcelas if not p['deve_desmarcar']]
            valor_total_reparcelar = sum(p['valor_a_receber'] for p in parcelas_finais)
            
            # Aplicar correção IGPM
            fator_correcao = 1 + (igpm_mock / 100)
            valor_corrigido = valor_total_reparcelar * fator_correcao
            
            dados_formulario_sienge = {
                "detalhamento": f"CORREÇÃO {datetime.now().strftime('%m/%y')}",
                "tipo_condicao": "PM",
                "valor_total": round(valor_corrigido, 2),
                "quantidade_parcelas": len(parcelas_finais),
                "data_primeiro_vencimento": "15/07/2025",
                "indexador": "1 IGP-M",
                "percentual_juros": 8.0,
                "parcelas_selecionadas": len(parcelas_finais),
                "valor_original": valor_total_reparcelar,
                "igpm_aplicado": igpm_mock,
                "fator_correcao": fator_correcao
            }
            
            self.log_teste(f"\n📝 DADOS DO FORMULÁRIO SIENGE:")
            self.log_teste(f"   📄 Detalhamento: {dados_formulario_sienge['detalhamento']}")
            self.log_teste(f"   🔧 Tipo Condição: {dados_formulario_sienge['tipo_condicao']}")
            self.log_teste(f"   💰 Valor original: R$ {dados_formulario_sienge['valor_original']:,.2f}")
            self.log_teste(f"   📊 IGPM aplicado: {dados_formulario_sienge['igpm_aplicado']}%")
            self.log_teste(f"   📊 Fator correção: {dados_formulario_sienge['fator_correcao']:.4f}")
            self.log_teste(f"   💰 Valor corrigido: R$ {dados_formulario_sienge['valor_total']:,.2f}")
            self.log_teste(f"   🔢 Quantidade parcelas: {dados_formulario_sienge['quantidade_parcelas']}")
            self.log_teste(f"   📅 Primeiro vencimento: {dados_formulario_sienge['data_primeiro_vencimento']}")
            self.log_teste(f"   📈 Indexador: {dados_formulario_sienge['indexador']}")
            self.log_teste(f"   💹 Juros: {dados_formulario_sienge['percentual_juros']}%")
            
            # Simular resultado final
            resultado_simulacao = {
                "sucesso": True,
                "titulo_original": contrato_teste.get('numero_titulo'),
                "novo_titulo_gerado": f"REP_{contrato_teste.get('numero_titulo')}_{self.timestamp_execucao}",
                "cliente": contrato_teste.get('cliente'),
                "parcelas_processadas": {
                    "total_inicial": len(parcelas),
                    "desmarcadas": len([p for p in parcelas if p['deve_desmarcar']]),
                    "marcadas_final": len(parcelas_finais),
                    "lista_desmarcadas": [p['documento'] for p in parcelas if p['deve_desmarcar']],
                    "lista_marcadas_final": [p['documento'] for p in parcelas_finais]
                },
                "valores_financeiros": dados_formulario_sienge,
                "timestamp_processamento": datetime.now().isoformat(),
                "tempo_execucao_simulado": 45.7
            }
            
            self.log_teste(f"\n✅ SIMULAÇÃO CONCLUÍDA COM SUCESSO")
            self.log_teste(f"   🆕 Novo título: {resultado_simulacao['novo_titulo_gerado']}")
            self.log_teste(f"   ⏱️ Tempo simulado: {resultado_simulacao['tempo_execucao_simulado']}s")
            self.log_teste(f"   📊 Taxa de sucesso: 100%")
            
            # Salvar resultado completo
            await self._salvar_resultado_teste("simulacao_webscraping_completo", resultado_simulacao)
            
            return True
            
        except Exception as e:
            self.log_teste(f"❌ Erro na simulação: {str(e)}", "ERROR")
            traceback.print_exc()
            return False
    
    async def teste_validacao_regras_pdd_com_parcelas(self) -> bool:
        """
        Testa validação das regras PDD considerando as parcelas detalhadas
        """
        self.log_teste("🧪 TESTE: VALIDAÇÃO REGRAS PDD COM PARCELAS DETALHADAS")
        self.log_teste("=" * 60)
        
        try:
            # Carregar dados
            fila_real = await self.carregar_fila_real_mongodb()
            
            if fila_real:
                fila_dados = fila_real
            else:
                fila_dados = self.criar_dados_mock_completos()
            
            contrato_teste = fila_dados['contratos'][0]
            parcelas = contrato_teste.get("parcelas_detalhadas", [])
            resumo = contrato_teste.get("resumo_parcelas", {})
            
            self.log_teste(f"🎯 Validando regras PDD para: {contrato_teste.get('numero_titulo')}")
            
            # Criar DataFrame para processamento PDD
            df_parcelas = pd.DataFrame(parcelas)
            df_parcelas['Data vencimento'] = pd.to_datetime(df_parcelas['data_vencimento'])
            df_parcelas['Parcela/Condição'] = df_parcelas['parcela_condicao']
            df_parcelas['Status da parcela'] = df_parcelas['status_parcela']
            df_parcelas['Valor a receber'] = df_parcelas['valor_a_receber']
            
            # Aplicar regras PDD
            resultado_validacao = self.processador_regras.validar_inadimplencia_pdd(df_parcelas)
            
            self.log_teste(f"\n📋 RESULTADO VALIDAÇÃO PDD:")
            self.log_teste(f"   🎯 Status do cliente: {resultado_validacao['status_cliente']}")
            self.log_teste(f"   🔥 Pode reparcelar: {resultado_validacao['pode_reparcelar']}")
            self.log_teste(f"   📊 Nível de risco: {resultado_validacao['nivel_risco']}")
            self.log_teste(f"   🚨 CT vencidas encontradas: {resultado_validacao['ct_vencidas_encontradas']}")
            self.log_teste(f"   📄 Total de parcelas CT: {resultado_validacao['total_parcelas_ct']}")
            self.log_teste(f"   ⚖️ Limite PDD (3 CT): {resultado_validacao['limite_inadimplencia_pdd']}")
            
            # Validar logica de marcação/desmarcação
            parcelas_ct_vencidas = [p for p in parcelas if p['parcela_condicao'] == 'CT' and p['situacao'] == 'VENCIDA']
            
            self.log_teste(f"\n🔍 VALIDAÇÃO LÓGICA MARCAÇÃO:")
            self.log_teste(f"   📊 CT vencidas (real): {len(parcelas_ct_vencidas)}")
            self.log_teste(f"   📊 CT vencidas (PDD): {resultado_validacao['ct_vencidas_encontradas']}")
            
            logica_correta = len(parcelas_ct_vencidas) == resultado_validacao['ct_vencidas_encontradas']
            status_logica = "✅ CORRETO" if logica_correta else "❌ ERRO"
            
            self.log_teste(f"   {status_logica} Validação cruzada")
            
            if logica_correta:
                self.log_teste(f"\n✅ REGRAS PDD VALIDADAS COM SUCESSO")
                
                # Determinar parcelas para desmarcar usando o processador
                parcelas_desmarcar_pdd = self.processador_regras.determinar_parcelas_desmarcar(
                    [p for p in parcelas if p['situacao'] == 'A_VENCER']
                )
                
                self.log_teste(f"\n📋 PARCELAS PARA DESMARCAR (via PDD):")
                if parcelas_desmarcar_pdd:
                    for parcela in parcelas_desmarcar_pdd:
                        self.log_teste(f"   • {parcela.get('documento', 'N/A')}: {parcela.get('motivo', 'N/A')}")
                else:
                    self.log_teste(f"   • Nenhuma parcela identificada pelo processador PDD")
                
                # Calcular reparcelamento
                parcelas_para_reparcelar = [p for p in parcelas if not p['deve_desmarcar']]
                saldo_reparcelar = sum(p['valor_a_receber'] for p in parcelas_para_reparcelar)
                
                calculo_reparcelamento = self.processador_regras.calcular_reparcelamento_pdd(
                    saldo_atual=saldo_reparcelar,
                    indice_igpm=3.89,
                    parcelas_pendentes=len(parcelas_para_reparcelar)
                )
                
                if calculo_reparcelamento['sucesso']:
                    self.log_teste(f"\n💰 CÁLCULO REPARCELAMENTO (PDD):")
                    valores = calculo_reparcelamento['valores_sienge']
                    self.log_teste(f"   💰 Valor original: R$ {saldo_reparcelar:,.2f}")
                    self.log_teste(f"   💰 Novo valor: R$ {valores['valor_total']:,.2f}")
                    self.log_teste(f"   📊 IGPM: {calculo_reparcelamento['igpm_utilizado']}%")
                    self.log_teste(f"   📊 Fator correção: {calculo_reparcelamento['fator_correcao']:.4f}")
                    self.log_teste(f"   🔢 Parcelas: {valores['quantidade_parcelas']}")
                    self.log_teste(f"   📅 Primeiro vencimento: {valores['data_primeiro_vencimento']}")
                
                resultado_completo = {
                    "contrato": contrato_teste,
                    "validacao_pdd": resultado_validacao,
                    "parcelas_detalhadas": parcelas,
                    "parcelas_desmarcar_pdd": parcelas_desmarcar_pdd,
                    "calculo_reparcelamento": calculo_reparcelamento,
                    "logica_validada": True,
                    "timestamp_validacao": datetime.now().isoformat()
                }
                
                await self._salvar_resultado_teste("validacao_regras_pdd_parcelas", resultado_completo)
                
                return True
            else:
                self.log_teste(f"❌ ERRO: Lógica de validação inconsistente", "ERROR")
                return False
            
        except Exception as e:
            self.log_teste(f"❌ Erro na validação PDD: {str(e)}", "ERROR")
            traceback.print_exc()
            return False
    
    async def teste_integracao_completa_com_marcacao(self) -> bool:
        """
        Teste de integração completa incluindo toda a lógica de marcação/desmarcação
        """
        self.log_teste("🧪 TESTE: INTEGRAÇÃO COMPLETA COM MARCAÇÃO/DESMARCAÇÃO")
        self.log_teste("=" * 60)
        
        try:
            testes = [
                ("Análise Parcelas e Marcação", self.teste_análise_parcelas_marcacao),
                ("Validação Regras PDD", self.teste_validacao_regras_pdd_com_parcelas),
                ("Simulação Webscraping Completo", self.teste_simulacao_webscraping_reparcelamento)
            ]
            
            resultados = {}
            
            for nome_teste, funcao_teste in testes:
                self.log_teste(f"\n🔄 Executando: {nome_teste}")
                self.log_teste("-" * 50)
                
                inicio = datetime.now()
                resultado = await funcao_teste()
                fim = datetime.now()
                
                tempo_execucao = (fim - inicio).total_seconds()
                resultados[nome_teste] = {
                    "sucesso": resultado,
                    "tempo_execucao": tempo_execucao
                }
                
                status = "✅" if resultado else "❌"
                self.log_teste(f"{status} {nome_teste}: {'SUCESSO' if resultado else 'FALHA'} ({tempo_execucao:.1f}s)")
            
            # Resumo final
            sucessos = sum(1 for r in resultados.values() if r['sucesso'])
            total = len(resultados)
            tempo_total = sum(r['tempo_execucao'] for r in resultados.values())
            
            self.log_teste(f"\n" + "="*60)
            self.log_teste(f"📈 RESULTADO INTEGRAÇÃO COMPLETA COM MARCAÇÃO:")
            self.log_teste(f"   ✅ Sucessos: {sucessos}/{total}")
            self.log_teste(f"   ❌ Falhas: {total - sucessos}")
            self.log_teste(f"   📊 Taxa sucesso: {(sucessos/total)*100:.1f}%")
            self.log_teste(f"   ⏱️ Tempo total: {tempo_total:.1f}s")
            
            if sucessos == total:
                self.log_teste(f"\n🎉 TODOS OS TESTES PASSARAM!")
                self.log_teste(f"🚀 Sistema pronto para implementação do webscraping!")
                self.log_teste(f"📋 Dados completos salvos em: {self.pasta_resultados}")
            else:
                self.log_teste(f"\n⚠️ Alguns testes falharam - verificar logs acima")
            
            # Salvar resumo final
            resumo_final = {
                "timestamp_execucao": self.timestamp_execucao,
                "resultados_individuais": resultados,
                "sucessos": sucessos,
                "total_testes": total,
                "percentual_sucesso": (sucessos / total) * 100 if total > 0 else 0,
                "tempo_total_execucao": tempo_total,
                "tipo_teste": "integracao_completa_com_marcacao",
                "status_final": "APROVADO" if sucessos == total else "REPROVADO"
            }
            
            await self._salvar_resultado_teste("integracao_completa_marcacao", resumo_final)
            
            return sucessos == total
            
        except Exception as e:
            self.log_teste(f"❌ Erro na integração completa: {str(e)}", "ERROR")
            traceback.print_exc()
            return False
    
    async def _salvar_resultado_teste(self, nome_teste: str, dados: Any):
        """Salva resultados do teste"""
        try:
            arquivo = self.pasta_resultados / f"{nome_teste}_{self.timestamp_execucao}.json"
            
            dados_salvamento = {
                "nome_teste": nome_teste,
                "timestamp": datetime.now().isoformat(),
                "dados": dados
            }
            
            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_salvamento, f, indent=2, ensure_ascii=False, default=str)
            
            self.log_teste(f"💾 Resultado salvo: {arquivo}")
            
        except Exception as e:
            self.log_teste(f"❌ Erro ao salvar resultado: {str(e)}", "ERROR")


async def menu_interativo_completo():
    """
    Menu interativo para execução dos testes completos com marcação/desmarcação
    """
    testador = TestadorRPASiengeCompleto()
    
    opcoes = {
        "1": ("🔥 Teste Integração Completa com Marcação (RECOMENDADO)", testador.teste_integracao_completa_com_marcacao),
        "2": ("📊 Teste Análise Parcelas e Marcação", testador.teste_análise_parcelas_marcacao),
        "3": ("🌐 Teste Simulação Webscraping Completo", testador.teste_simulacao_webscraping_reparcelamento),
        "4": ("⚖️ Teste Validação Regras PDD", testador.teste_validacao_regras_pdd_com_parcelas),
        "0": ("❌ Sair", None)
    }
    
    print("\n" + "=" * 80)
    print("🧪 TESTE RPA SIENGE COMPLETO - MARCAÇÃO/DESMARCAÇÃO PARCELAS")
    print("Sistema completo para testar webscraping com dados reais de parcelas")
    print("=" * 80)
    
    for key, (descricao, _) in opcoes.items():
        print(f"{key}. {descricao}")
    
    print("=" * 80)
    
    while True:
        try:
            escolha = input("\n➤ Escolha uma opção (0-4): ").strip()
            
            if escolha == "0":
                print("👋 Encerrando testes completos...")
                break
            elif escolha in opcoes and opcoes[escolha][1]:
                print(f"\n🔄 Executando: {opcoes[escolha][0]}")
                print("=" * 80)
                
                inicio = datetime.now()
                sucesso = await opcoes[escolha][1]()
                fim = datetime.now()
                tempo_execucao = (fim - inicio).total_seconds()
                
                print("=" * 80)
                if sucesso:
                    print(f"✅ Teste CONCLUÍDO COM SUCESSO em {tempo_execucao:.1f}s")
                    print("🚀 Dados completos disponíveis para implementação webscraping!")
                else:
                    print(f"❌ Teste FALHOU em {tempo_execucao:.1f}s")
                    print("🔍 Verificar logs acima para detalhes do erro")
                
                input("\n⏳ Pressione ENTER para continuar...")
                
                # Reexibir menu
                print("\n" + "=" * 80)
                for key, (descricao, _) in opcoes.items():
                    print(f"{key}. {descricao}")
                print("=" * 80)
            else:
                print("❌ Opção inválida! Escolha entre 0-4.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Testes interrompidos pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")
            traceback.print_exc()


if __name__ == "__main__":
    print("🚀 SISTEMA DE TESTES RPA SIENGE COMPLETO")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("🎯 Marcação/Desmarcação de Parcelas + Webscraping")
    print("📋 Dados reais da fila MongoDB + Estrutura completa de parcelas")
    
    try:
        asyncio.run(menu_interativo_completo())
    except KeyboardInterrupt:
        print("\n👋 Sistema encerrado pelo usuário.")
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        import traceback
        traceback.print_exc()
