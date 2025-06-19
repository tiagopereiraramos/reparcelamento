#!/usr/bin/env python3
"""
Teste RPA Sienge - Baseado em Dados Reais da Fila
Sistema de testes que utiliza dados reais da fila de processamento MongoDB

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import traceback

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rpa_sienge.rpa_sienge import RPASienge
from core.data_manager import data_manager
from core.base_rpa import ResultadoRPA


class TestadorRPASiengeReal:
    """
    Testador RPA Sienge usando dados reais da fila de processamento
    """

    def __init__(self):
        self.pasta_resultados = Path("rpa_sienge/dados_processamento/testes_reais")
        self.pasta_resultados.mkdir(parents=True, exist_ok=True)
        self.timestamp_execucao = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.rpa_sienge = None

    def log_teste(self, mensagem: str, nivel: str = "INFO"):
        """Log estruturado para testes"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {nivel}: {mensagem}")

    def criar_dados_mock_fila(self) -> Dict[str, Any]:
        """
        Cria dados mock baseados na estrutura real da fila MongoDB
        """
        return {
            "_id": "mock_test_id",
            "timestamp_ultima_atualizacao": datetime.now().isoformat(),
            "total_contratos": 2,
            "status_geral": "ativo",
            "contratos": [
                {
                    "id_fila": "reajuste_2239_20250617_225400",
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
                    "processado_em": None,
                    "erro_processamento": None,
                    "parcelas_detalhadas": [
                        {
                            "documento": "CT001",
                            "parcela_condicao": "CT",
                            "numero_parcela": 48,
                            "data_vencimento": "2024-12-15",
                            "valor_a_receber": 2500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "VENCIDA",
                            "deve_desmarcar": True,
                            "motivo_desmarcacao": "Parcela CT vencida - deve ser desmarcada conforme PDD"
                        },
                        {
                            "documento": "CT002",
                            "parcela_condicao": "CT",
                            "numero_parcela": 49,
                            "data_vencimento": "2025-01-15",
                            "valor_a_receber": 2500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "VENCIDA",
                            "deve_desmarcar": True,
                            "motivo_desmarcacao": "Parcela CT vencida - deve ser desmarcada conforme PDD"
                        },
                        {
                            "documento": "CT003",
                            "parcela_condicao": "CT",
                            "numero_parcela": 50,
                            "data_vencimento": "2025-07-15",
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
                            "data_vencimento": "2025-08-31",
                            "valor_a_receber": 1200.00,
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
                    ]
                },
                {
                    "id_fila": "reajuste_2356_20250617_225400",
                    "numero_titulo": 2356,
                    "cliente": "MARCOS DE ALMEIDA VAZQUEZ / LUCAS FERNANDO VIEIRA DE ARAUJO",
                    "empreendimento": "MARCELY",
                    "cnpj_unidade": "BVRB",
                    "indexador": "IGPM",
                    "ultimo_reajuste": "jun.-24",
                    "dias_desde_ultimo_reajuste": 365,
                    "linha_planilha": 72,
                    "status_processamento": "pendente",
                    "prioridade": 11,
                    "timestamp_identificacao": "2025-06-17T22:54:00.838469",
                    "dados_completos": {
                        "Empresa": "BVRB",
                        "Loteamento": "MARCELY",
                        "Cliente": "MARCOS DE ALMEIDA VAZQUEZ / LUCAS FERNANDO VIEIRA DE ARAUJO",
                        "Quadra": 38,
                        "Lote": 258,
                        "Titulo": 2356,
                        "Índice": "IGPM",
                        "Juros": "8,0%",
                        "Tipo reajuste": "anual",
                        "Último reajuste": "jun.-24",
                        "Mês reajuste": "jun.-25",
                        "linha_planilha": 72,
                        "cliente": "MARCOS DE ALMEIDA VAZQUEZ / LUCAS FERNANDO VIEIRA DE ARAUJO",
                        "numero_titulo": 2356
                    },
                    "processado_em": None,
                    "erro_processamento": None,
                    "parcelas_detalhadas": [
                        {
                            "documento": "CT001",
                            "parcela_condicao": "CT",
                            "numero_parcela": 48,
                            "data_vencimento": "2024-12-15",
                            "valor_a_receber": 2500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "VENCIDA",
                            "deve_desmarcar": True,
                            "motivo_desmarcacao": "Parcela CT vencida - deve ser desmarcada conforme PDD"
                        },
                        {
                            "documento": "CT002",
                            "parcela_condicao": "CT",
                            "numero_parcela": 49,
                            "data_vencimento": "2025-01-15",
                            "valor_a_receber": 2500.00,
                            "status_parcela": "Em Aberto",
                            "situacao": "VENCIDA",
                            "deve_desmarcar": True,
                            "motivo_desmarcacao": "Parcela CT vencida - deve ser desmarcada conforme PDD"
                        },
                        {
                            "documento": "CT003",
                            "parcela_condicao": "CT",
                            "numero_parcela": 50,
                            "data_vencimento": "2025-07-15",
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
                            "data_vencimento": "2025-08-31",
                            "valor_a_receber": 1200.00,
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
                    ]
                }
            ]
        }

    async def carregar_fila_real_mongodb(self) -> Optional[Dict[str, Any]]:
        """
        Carrega fila real do MongoDB
        """
        try:
            self.log_teste("🔍 Conectando ao MongoDB para carregar fila real...")
            await data_manager.inicializar()

            if not data_manager.mongodb_ativo:
                self.log_teste("⚠️ MongoDB não disponível - usando dados mock", "WARNING")
                return None

            # Buscar fila de processamento real
            fila_real = await data_manager.obter_fila_sienge()

            if fila_real and fila_real.get("contratos"):
                self.log_teste(f"✅ Fila real carregada: {len(fila_real['contratos'])} contratos")
                return fila_real
            else:
                self.log_teste("⚠️ Fila vazia no MongoDB - usando dados mock", "WARNING")
                return None

        except Exception as e:
            self.log_teste(f"❌ Erro ao carregar fila real: {str(e)}", "ERROR")
            return None

    async def teste_carregamento_fila(self) -> bool:
        """
        Testa carregamento da fila de processamento
        """
        self.log_teste("🧪 TESTE: CARREGAMENTO FILA PROCESSAMENTO")
        self.log_teste("=" * 50)

        try:
            # Tentar carregar fila real primeiro
            fila_real = await self.carregar_fila_real_mongodb()

            if fila_real:
                fila_dados = fila_real
                fonte = "MongoDB Real"
            else:
                fila_dados = self.criar_dados_mock_fila()
                fonte = "Dados Mock"

            self.log_teste(f"📊 Fonte dos dados: {fonte}")
            self.log_teste(f"📄 Total contratos: {fila_dados.get('total_contratos', 0)}")
            self.log_teste(f"🔄 Status geral: {fila_dados.get('status_geral', 'N/A')}")

            # Validar estrutura
            contratos = fila_dados.get("contratos", [])
            if not contratos:
                self.log_teste("❌ Nenhum contrato encontrado na fila", "ERROR")
                return False

            # Analisar primeiro contrato
            primeiro_contrato = contratos[0]
            self.log_teste(f"\n📋 Análise do primeiro contrato:")
            self.log_teste(f"   📄 Título: {primeiro_contrato.get('numero_titulo')}")
            self.log_teste(f"   👤 Cliente: {primeiro_contrato.get('cliente')}")
            self.log_teste(f"   🏢 Empreendimento: {primeiro_contrato.get('empreendimento')}")
            self.log_teste(f"   🔄 Status: {primeiro_contrato.get('status_processamento')}")
            self.log_teste(f"   📊 Prioridade: {primeiro_contrato.get('prioridade')}")

            # Salvar dados para outros testes
            await self._salvar_fila_teste(fila_dados, fonte)

            return True

        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            return False

    async def teste_simulacao_consulta_sienge(self) -> bool:
        """
        Simula consulta no Sienge usando dados da fila
        """
        self.log_teste("🧪 TESTE: SIMULAÇÃO CONSULTA SIENGE")
        self.log_teste("=" * 50)

        try:
            # Carregar dados da fila
            fila_dados = await self._carregar_fila_teste()
            if not fila_dados:
                return False

            contratos = fila_dados.get("contratos", [])
            if not contratos:
                self.log_teste("❌ Nenhum contrato para testar", "ERROR")
                return False

            # Testar primeiro contrato pendente
            contrato_teste = None
            for contrato in contratos:
                if contrato.get("status_processamento") == "pendente":
                    contrato_teste = contrato
                    break

            if not contrato_teste:
                contrato_teste = contratos[0]

            self.log_teste(f"🎯 Testando contrato: {contrato_teste.get('numero_titulo')}")
            self.log_teste(f"👤 Cliente: {contrato_teste.get('cliente')}")

            # Simular parâmetros de consulta como seriam no RPA real
            parametros_consulta = {
                "numero_titulo": str(contrato_teste.get("numero_titulo")),
                "cliente": contrato_teste.get("cliente"),
                "empreendimento": contrato_teste.get("empreendimento"),
                "dados_completos": contrato_teste.get("dados_completos", {})
            }

            # Simular credenciais (não funcional, apenas estrutura)
            credenciais_mock = {
                "url": "https://jmservicos.sienge.com.br/sienge/8",
                "usuario": "usuario_teste",
                "senha": "senha_teste"
            }

            self.log_teste("🌐 Simulando consulta no Sienge...")

            # Simular resultado da consulta
            resultado_simulado = {
                "sucesso": True,
                "numero_titulo": parametros_consulta["numero_titulo"],
                "cliente": parametros_consulta["cliente"],
                "saldo_total": 150000.00,  # Valor simulado
                "parcelas_pendentes": 48,
                "parcelas_ct_vencidas": 2,
                "pode_reparcelar": True,
                "status_cliente": "ADIMPLENTE",
                "dados_processados": True,
                "timestamp_consulta": datetime.now().isoformat()
            }

            self.log_teste(f"✅ Consulta simulada com sucesso")
            self.log_teste(f"   💰 Saldo total: R$ {resultado_simulado['saldo_total']:,.2f}")
            self.log_teste(f"   📊 Parcelas pendentes: {resultado_simulado['parcelas_pendentes']}")
            self.log_teste(f"   🚨 CT vencidas: {resultado_simulado['parcelas_ct_vencidas']}")
            self.log_teste(f"   ✅ Pode reparcelar: {resultado_simulado['pode_reparcelar']}")

            # Salvar resultado
            await self._salvar_resultado_teste("consulta_sienge", {
                "parametros": parametros_consulta,
                "credenciais_estrutura": credenciais_mock,
                "resultado": resultado_simulado
            })

            return True

        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            return False

    async def teste_processamento_reparcelamento_mock(self) -> bool:
        """
        Testa processamento de reparcelamento com dados da fila
        """
        self.log_teste("🧪 TESTE: PROCESSAMENTO REPARCELAMENTO MOCK")
        self.log_teste("=" * 50)

        try:
            # Carregar dados da fila
            fila_dados = await self._carregar_fila_teste()
            if not fila_dados:
                return False

            contratos = fila_dados.get("contratos", [])
            contrato_teste = contratos[0] if contratos else None

            if not contrato_teste:
                self.log_teste("❌ Nenhum contrato para testar", "ERROR")
                return False

            self.log_teste(f"🎯 Processando reparcelamento para: {contrato_teste.get('numero_titulo')}")

            # Simular dados financeiros processados
            dados_financeiros = {
                "saldo_atual": 150000.00,
                "parcelas_pendentes": 48,
                "pode_reparcelar": True,
                "parcelas_ct_vencidas": 2,
                "status_cliente": "ADIMPLENTE"
            }

            # Simular IGPM (dados mock)
            igpm_mock = 3.89

            self.log_teste(f"📊 Dados financeiros:")
            self.log_teste(f"   💰 Saldo atual: R$ {dados_financeiros['saldo_atual']:,.2f}")
            self.log_teste(f"   📊 IGPM aplicado: {igpm_mock}%")
            self.log_teste(f"   🔢 Parcelas pendentes: {dados_financeiros['parcelas_pendentes']}")

            # Simular cálculo de reparcelamento
            fator_correcao = 1 + (igpm_mock / 100)
            novo_saldo = dados_financeiros["saldo_atual"] * fator_correcao

            valores_sienge = {
                "detalhamento": f"CORREÇÃO {datetime.now().strftime('%m/%y')}",
                "tipo_condicao": "PM",
                "valor_total": round(novo_saldo, 2),
                "quantidade_parcelas": dados_financeiros["parcelas_pendentes"],
                "data_primeiro_vencimento": "15/07/2025",
                "indexador": "1 IGP-M",
                "percentual_juros": 8.0
            }

            # Simular resultado do reparcelamento
            resultado_reparcelamento = {
                "sucesso": True,
                "numero_titulo_original": contrato_teste.get("numero_titulo"),
                "novo_titulo_gerado": f"REP_{contrato_teste.get('numero_titulo')}_{self.timestamp_execucao}",
                "saldo_anterior": dados_financeiros["saldo_atual"],
                "saldo_novo": novo_saldo,
                "fator_correcao": fator_correcao,
                "igpm_aplicado": igpm_mock,
                "valores_sienge": valores_sienge,
                "timestamp_processamento": datetime.now().isoformat()
            }

            self.log_teste(f"✅ Reparcelamento processado com sucesso")
            self.log_teste(f"   🆕 Novo título: {resultado_reparcelamento['novo_titulo_gerado']}")
            self.log_teste(f"   💰 Valor anterior: R$ {resultado_reparcelamento['saldo_anterior']:,.2f}")
            self.log_teste(f"   💰 Valor corrigido: R$ {resultado_reparcelamento['saldo_novo']:,.2f}")
            self.log_teste(f"   📊 Fator correção: {resultado_reparcelamento['fator_correcao']:.4f}")

            # Salvar resultado
            await self._salvar_resultado_teste("reparcelamento_mock", {
                "contrato_origem": contrato_teste,
                "dados_financeiros": dados_financeiros,
                "resultado_reparcelamento": resultado_reparcelamento
            })

            return True

        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            return False

    async def teste_integracao_completa_fila(self) -> bool:
        """
        Teste de integração usando toda a fila
        """
        self.log_teste("🧪 TESTE: INTEGRAÇÃO COMPLETA FILA")
        self.log_teste("=" * 50)

        try:
            testes = [
                ("Carregamento Fila", self.teste_carregamento_fila),
                ("Consulta Sienge", self.teste_simulacao_consulta_sienge),
                ("Reparcelamento Mock", self.teste_processamento_reparcelamento_mock)
            ]

            resultados = {}

            for nome_teste, funcao_teste in testes:
                self.log_teste(f"\n🔄 Executando: {nome_teste}")
                resultado = await funcao_teste()
                resultados[nome_teste] = resultado

                status = "✅" if resultado else "❌"
                self.log_teste(f"{status} {nome_teste}: {'SUCESSO' if resultado else 'FALHA'}")

            # Resumo final
            sucessos = sum(1 for r in resultados.values() if r)
            total = len(resultados)

            self.log_teste(f"\n📈 RESULTADO INTEGRAÇÃO FILA:")
            self.log_teste(f"   ✅ Sucessos: {sucessos}/{total}")
            self.log_teste(f"   ❌ Falhas: {total - sucessos}")
            self.log_teste(f"   📊 Taxa sucesso: {(sucessos/total)*100:.1f}%")

            # Salvar resumo
            resumo = {
                "timestamp_execucao": self.timestamp_execucao,
                "resultados_individuais": resultados,
                "sucessos": sucessos,
                "total_testes": total,
                "percentual_sucesso": (sucessos / total) * 100 if total > 0 else 0,
                "tipo_teste": "integracao_completa_fila"
            }

            await self._salvar_resultado_teste("integracao_completa_fila", resumo)

            return sucessos == total

        except Exception as e:
            self.log_teste(f"❌ Erro na integração: {str(e)}", "ERROR")
            return False

    async def teste_rpa_real_com_dados_fila(self) -> bool:
        """
        Testa RPA real usando dados da fila (apenas estrutura, sem webscraping)
        """
        self.log_teste("🧪 TESTE: RPA REAL COM DADOS FILA")
        self.log_teste("=" * 50)

        try:
            # Carregar fila
            fila_dados = await self._carregar_fila_teste()
            if not fila_dados:
                return False

            contratos = fila_dados.get("contratos", [])
            if not contratos:
                return False

            contrato_teste = contratos[0]

            self.log_teste(f"🎯 Testando RPA com: {contrato_teste.get('numero_titulo')}")

            # Preparar dados no formato esperado pelo RPA
            contrato_rpa = {
                "numero_titulo": str(contrato_teste.get("numero_titulo")),
                "cliente": contrato_teste.get("cliente"),
                "empreendimento": contrato_teste.get("empreendimento")
            }

            credenciais_mock = {
                "url": "https://jmservicos.sienge.com.br/sienge/8",
                "usuario": "teste_usuario",
                "senha": "teste_senha"
            }

            # Simular execução (sem webscraping real)
            self.log_teste("🤖 Simulando execução do RPA Sienge...")

            resultado_simulado = {
                "sucesso": True,
                "mensagem": f"Simulação concluída para {contrato_rpa['numero_titulo']}",
                "dados": {
                    "etapa_executada": "simulacao_com_dados_fila",
                    "contrato_processado": contrato_rpa,
                    "timestamp_processamento": datetime.now().isoformat(),
                    "fonte_dados": "fila_processamento_mongodb"
                },
                "tempo_execucao": 2.5
            }

            self.log_teste(f"✅ Simulação RPA concluída")
            self.log_teste(f"   📄 Contrato: {contrato_rpa['numero_titulo']}")
            self.log_teste(f"   👤 Cliente: {contrato_rpa['cliente']}")
            self.log_teste(f"   ⏱️ Tempo: {resultado_simulado['tempo_execucao']}s")

            # Salvar resultado
            await self._salvar_resultado_teste("rpa_real_dados_fila", {
                "contrato_origem": contrato_teste,
                "contrato_rpa": contrato_rpa,
                "credenciais_estrutura": credenciais_mock,
                "resultado_simulacao": resultado_simulado
            })

            return True

        except Exception as e:
            self.log_teste(f"❌ Erro no teste RPA: {str(e)}", "ERROR")
            return False

    async def _salvar_fila_teste(self, fila_dados: Dict[str, Any], fonte: str):
        """Salva dados da fila para uso em outros testes"""
        try:
            arquivo_fila = self.pasta_resultados / f"fila_teste_{self.timestamp_execucao}.json"

            dados_salvamento = {
                "fonte": fonte,
                "timestamp_salvamento": datetime.now().isoformat(),
                "fila_dados": fila_dados
            }

            with open(arquivo_fila, 'w', encoding='utf-8') as f:
                json.dump(dados_salvamento, f, indent=2, ensure_ascii=False)

            self.log_teste(f"💾 Fila salva: {arquivo_fila}")

        except Exception as e:
            self.log_teste(f"❌ Erro ao salvar fila: {str(e)}", "ERROR")

    async def _carregar_fila_teste(self) -> Optional[Dict[str, Any]]:
        """Carrega dados da fila salvos anteriormente"""
        try:
            # Buscar arquivo mais recente
            arquivos_fila = list(self.pasta_resultados.glob("fila_teste_*.json"))

            if not arquivos_fila:
                self.log_teste("⚠️ Nenhuma fila salva - executando carregamento primeiro", "WARNING")
                await self.teste_carregamento_fila()
                arquivos_fila = list(self.pasta_resultados.glob("fila_teste_*.json"))

            if not arquivos_fila:
                return None

            arquivo_mais_recente = max(arquivos_fila, key=lambda f: f.stat().st_mtime)

            with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
                dados = json.load(f)

            return dados.get("fila_dados")

        except Exception as e:
            self.log_teste(f"❌ Erro ao carregar fila: {str(e)}", "ERROR")
            return None

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
                json.dump(dados_salvamento, f, indent=2, ensure_ascii=False)

            self.log_teste(f"💾 Resultado salvo: {arquivo}")

        except Exception as e:
            self.log_teste(f"❌ Erro ao salvar resultado: {str(e)}", "ERROR")

    def calcular_resumo_parcelas(self, parcelas: List[Dict]) -> Dict[str, Any]:
        """
        Calcula resumo das parcelas para análise
        """
        hoje = datetime.now().date()

        total_parcelas = len(parcelas)
        parcelas_vencidas = 0
        parcelas_a_vencer = 0
        ct_vencidas = 0
        valor_total_vencido = 0
        valor_total_a_vencer = 0

        for parcela in parcelas:
            try:
                data_venc = datetime.strptime(parcela['data_vencimento'], '%Y-%m-%d').date()
                valor = parcela.get('valor_a_receber', 0)

                if data_venc < hoje:
                    parcelas_vencidas += 1
                    valor_total_vencido += valor

                    if parcela.get('parcela_condicao', '').upper() == 'CT':
                        ct_vencidas += 1
                else:
                    parcelas_a_vencer += 1
                    valor_total_a_vencer += valor

            except:
                continue

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
            # Carregar dados completos            fila_real = await self.carregar_fila_real_mongodb()

            if fila_real:
                fila_dados = fila_real
                fonte = "MongoDB Real + Parcelas Mock"
            else:
                fila_dados = self.criar_dados_mock_fila()
                fonte = "Dados Mock Completos"

            self.log_teste(f"📊 Fonte dos dados: {fonte}")

            contratos = fila_dados.get("contratos", [])
            if not contratos:
                self.log_teste("❌ Nenhum contrato encontrado", "ERROR")
                return False

            contrato_teste = contratos[0]
            parcelas = contrato_teste.get("parcelas_detalhadas", [])

            if not parcelas:
                self.log_teste("❌ Nenhuma parcela encontrada para análise", "ERROR")
                return False

            self.log_teste(f"🎯 Analisando contrato: {contrato_teste.get('numero_titulo')}")
            self.log_teste(f"📄 Total de parcelas: {len(parcelas)}")

            # Calcular resumo
            resumo = self.calcular_resumo_parcelas(parcelas)

            self.log_teste(f"\n📊 RESUMO FINANCEIRO:")
            self.log_teste(f"   📄 Total parcelas: {resumo['total_parcelas']}")
            self.log_teste(f"   🚨 Parcelas vencidas: {resumo['parcelas_vencidas']}")
            self.log_teste(f"   ⏳ Parcelas a vencer: {resumo['parcelas_a_vencer']}")
            self.log_teste(f"   💰 Valor vencido: R$ {resumo['valor_total_vencido']:,.2f}")
            self.log_teste(f"   💰 Valor a vencer: R$ {resumo['valor_total_a_vencer']:,.2f}")
            self.log_teste(f"   💰 Valor total: R$ {resumo['valor_total_geral']:,.2f}")

            # Análise detalhada de marcação/desmarcação
            self.log_teste(f"\n🔍 ANÁLISE DETALHADA - MARCAÇÃO/DESMARCAÇÃO:")

            parcelas_desmarcar = []
            parcelas_manter = []

            for i, parcela in enumerate(parcelas, 1):
                status_marcacao = "❌ DESMARCAR" if parcela['deve_desmarcar'] else "✅ MANTER MARCADA"
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
            # Carregar dados com parcelas
            fila_dados = await self._carregar_fila_teste()
            if not fila_dados:
                fila_dados = self.criar_dados_mock_fila()

            contratos = fila_dados.get("contratos", [])
            if not contratos:
                return False

            contrato_teste = contratos[0]
            parcelas = contrato_teste.get("parcelas_detalhadas", [])

            if not parcelas:
                self.log_teste("❌ Nenhuma parcela encontrada para simulação", "ERROR")
                return False

            self.log_teste(f"🎯 Simulando webscraping para: {contrato_teste.get('numero_titulo')}")
            self.log_teste(f"📄 Total parcelas: {len(parcelas)}")

            # Simular etapas do webscraping
            etapas_webscraping = [
                "1. 🔐 Login no Sienge",
                "2. 🔍 Buscar título por número",
                "3. 📊 Acessar aba de parcelas",
                "4. 📋 Carregar lista de parcelas",
                "5. ✅ Marcar todas as parcelas (padrão)",
                "6. ❌ Desmarcar parcelas vencidas conforme PDD",
                "7. 💰 Calcular novo reparcelamento",
                "8. 📝 Preencher formulário de reparcelamento",
                "9. ✅ Confirmar operação"
            ]

            self.log_teste(f"\n🤖 SIMULAÇÃO DAS ETAPAS DE WEBSCRAPING:")

            for etapa in etapas_webscraping:
                self.log_teste(f"   {etapa}")

                # Detalhar etapa 6 (marcação/desmarcação)
                if "6." in etapa:
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

                # Detalhar etapa 7 (cálculo)
                elif "7." in etapa:
                    parcelas_reparcelar = [p for p in parcelas if not p['deve_desmarcar']]
                    valor_base = sum(p['valor_a_receber'] for p in parcelas_reparcelar)
                    igpm_mock = 3.89

                    self.log_teste(f"\n   🔧 DETALHAMENTO ETAPA 7 - CÁLCULO:")
                    self.log_teste(f"      • Saldo base: R$ {valor_base:,.2f}")
                    self.log_teste(f"      • IGPM aplicado: {igpm_mock}%")

                    fator_correcao = 1 + (igpm_mock / 100)
                    novo_valor = valor_base * fator_correcao

                    self.log_teste(f"      • Fator correção: {fator_correcao:.4f}")
                    self.log_teste(f"      • Novo valor: R$ {novo_valor:,.2f}")

            # Resultado final da simulação
            resultado_simulacao = {
                "contrato_processado": contrato_teste.get('numero_titulo'),
                "total_parcelas_analisadas": len(parcelas),
                "parcelas_desmarcadas": len([p for p in parcelas if p['deve_desmarcar']]),
                "parcelas_mantidas": len([p for p in parcelas if not p['deve_desmarcar']]),
                "valor_final_reparcelamento": sum(p['valor_a_receber'] for p in parcelas if not p['deve_desmarcar']),
                "etapas_executadas": len(etapas_webscraping),
                "simulacao_completa": True,
                "timestamp_simulacao": datetime.now().isoformat()
            }

            self.log_teste(f"\n✅ SIMULAÇÃO WEBSCRAPING CONCLUÍDA:")
            self.log_teste(f"   📄 Contrato: {resultado_simulacao['contrato_processado']}")
            self.log_teste(f"   📊 Parcelas analisadas: {resultado_simulacao['total_parcelas_analisadas']}")
            self.log_teste(f"   ❌ Parcelas desmarcadas: {resultado_simulacao['parcelas_desmarcadas']}")
            self.log_teste(f"   ✅ Parcelas mantidas: {resultado_simulacao['parcelas_mantidas']}")
            self.log_teste(f"   💰 Valor final: R$ {resultado_simulacao['valor_final_reparcelamento']:,.2f}")

            await self._salvar_resultado_teste("simulacao_webscraping_reparcelamento", {
                "contrato": contrato_teste,
                "parcelas_detalhadas": parcelas,
                "resultado_simulacao": resultado_simulacao,
                "etapas_webscraping": etapas_webscraping
            })

            return True

        except Exception as e:
            self.log_teste(f"❌ Erro na simulação: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_validacao_regras_pdd_com_parcelas(self) -> bool:
        """
        Testa validação das regras PDD com parcelas reais
        """
        self.log_teste("🧪 TESTE: VALIDAÇÃO REGRAS PDD COM PARCELAS")
        self.log_teste("=" * 60)

        try:
            # Carregar dados com parcelas
            fila_dados = await self._carregar_fila_teste()
            if not fila_dados:
                fila_dados = self.criar_dados_mock_fila()

            contratos = fila_dados.get("contratos", [])
            contrato_teste = contratos[0] if contratos else None

            if not contrato_teste:
                return False

            parcelas = contrato_teste.get("parcelas_detalhadas", [])

            self.log_teste(f"🎯 Validando regras PDD para: {contrato_teste.get('numero_titulo')}")
            self.log_teste(f"📄 Parcelas para validação: {len(parcelas)}")

            # Converter parcelas para formato DataFrame simulado
            import pandas as pd

            parcelas_df_data = []
            for parcela in parcelas:
                parcelas_df_data.append({
                    'Documento': parcela['documento'],
                    'Parcela/Condição': parcela['parcela_condicao'],
                    'Data vencimento': parcela['data_vencimento'],
                    'Valor a receber': parcela['valor_a_receber'],
                    'Status da parcela': parcela['status_parcela']
                })

            df_parcelas = pd.DataFrame(parcelas_df_data)

            # Aplicar regras PDD usando o processador
            from core.processador_regras_pdd import ProcessadorRegrasNegocio
            processador = ProcessadorRegrasNegocio()
            
            resultado_validacao = processador.processar_dados_cliente_completo(
                df_planilha=df_parcelas,
                cliente=contrato_teste.get('cliente', ''),
                numero_titulo=str(contrato_teste.get('numero_titulo'))
            )

            if resultado_validacao.get('sucesso'):
                self.log_teste(f"✅ VALIDAÇÃO PDD APROVADA:")
                self.log_teste(f"   📊 Pode reparcelar: {resultado_validacao.get('pode_reparcelar')}")
                self.log_teste(f"   💰 Valor total CT: R$ {resultado_validacao.get('valor_total_ct', 0):,.2f}")
                self.log_teste(f"   🔢 Parcelas CT a vencer: {resultado_validacao.get('qtd_parcelas_ct_a_vencer', 0)}")
                self.log_teste(f"   🚨 CT vencidas: {resultado_validacao.get('qtd_ct_vencidas', 0)}")

                # Verificar parcelas identificadas para desmarcação
                parcelas_desmarcar_pdd = resultado_validacao.get('parcelas_desmarcar', [])

                if parcelas_desmarcar_pdd:
                    self.log_teste(f"\n❌ PARCELAS IDENTIFICADAS PELO PDD PARA DESMARCAÇÃO:")
                    for parcela in parcelas_desmarcar_pdd:
                        self.log_teste(f"   • {parcela.get('documento', 'N/A')}: {parcela.get('motivo', 'N/A')}")
                else:
                    self.log_teste(f"   • Nenhuma parcela identificada pelo processador PDD")

                # Calcular reparcelamento
                parcelas_para_reparcelar = [p for p in parcelas if not p['deve_desmarcar']]
                saldo_reparcelar = sum(p['valor_a_receber'] for p in parcelas_para_reparcelar)

                calculo_reparcelamento = await processador.calcular_valores_reparcelamento(
                    saldo_atual=saldo_reparcelar,
                    indice_igpm=3.89,
                    parcelas_pendentes=len(parcelas_para_reparcelar)
                )

                if calculo_reparcelamento.get('sucesso'):
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

    async def teste_webscraping_real_login_consulta(self) -> bool:
        """
        🎯 TESTE REAL: Login no Sienge + Consulta + Exportação
        Para debugar e implementar a parte de webscraping
        """
        self.log_teste("🧪 TESTE WEBSCRAPING REAL: LOGIN + CONSULTA + EXPORTAÇÃO")
        self.log_teste("=" * 70)

        try:
            # Configurar credenciais reais (precisam estar no ambiente)
            credenciais_sienge = {
                "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/8"),
                "usuario": os.getenv("SIENGE_USUARIO", ""),
                "senha": os.getenv("SIENGE_SENHA", "")
            }

            if not credenciais_sienge["usuario"] or not credenciais_sienge["senha"]:
                self.log_teste("❌ CREDENCIAIS SIENGE NÃO CONFIGURADAS", "ERROR")
                self.log_teste("Configure SIENGE_USUARIO e SIENGE_SENHA no ambiente", "WARNING")
                return False

            # Inicializar RPA Sienge real
            self.rpa_sienge = RPASienge()
            self.log_teste("✅ RPA Sienge inicializado")

            # Configurar credenciais
            self.rpa_sienge._configurar_credenciais(credenciais_sienge)
            self.log_teste("✅ Credenciais configuradas")

            # ETAPA 1: FAZER LOGIN REAL
            self.log_teste("\n🔐 ETAPA 1: FAZENDO LOGIN NO SIENGE...")
            await self.rpa_sienge._fazer_login_sienge()
            self.log_teste("✅ Login realizado com sucesso")

            # ETAPA 2: CONSULTAR RELATÓRIO COM CLIENTE REAL
            contrato_teste = {
                "numero_titulo": "2239",
                "cliente": "SANDRO RIZZON VIEIRA",
                "empreendimento": "MARCELY"
            }

            self.log_teste(f"\n📊 ETAPA 2: CONSULTANDO RELATÓRIO...")
            self.log_teste(f"   👤 Cliente: {contrato_teste['cliente']}")
            self.log_teste(f"   📄 Título: {contrato_teste['numero_titulo']}")

            # Fazer consulta real
            dados_financeiros = await self.rpa_sienge._consultar_relatorios_financeiros(contrato_teste)

            # VERIFICAR RESULTADO DA CONSULTA
            if dados_financeiros.get("sucesso"):
                self.log_teste("✅ CONSULTA REALIZADA COM SUCESSO!")
                self.log_teste(f"   📄 Arquivo processado: {dados_financeiros.get('arquivo_processado')}")
                
                dados_validacao = dados_financeiros.get("dados_validacao", {})
                if dados_validacao:
                    self.log_teste(f"   📊 Status cliente: {dados_validacao.get('status_cliente')}")
                    self.log_teste(f"   💰 Saldo total: R$ {dados_validacao.get('saldo_total', 0):,.2f}")
                    self.log_teste(f"   🔢 Parcelas CT a vencer: {dados_validacao.get('qtd_parcelas_ct_a_vencer', 0)}")
                    self.log_teste(f"   🚨 CT vencidas: {dados_validacao.get('qtd_ct_vencidas', 0)}")
                    self.log_teste(f"   ✅ Pode reparcelar: {dados_validacao.get('pode_reparcelar')}")

                # ETAPA 3: GERAR DADOS PARA IMPLEMENTAÇÃO
                self.log_teste(f"\n🎯 ETAPA 3: GERANDO DADOS PARA IMPLEMENTAÇÃO...")
                
                # Dados essenciais para implementação de reparcelamento
                dados_implementacao = {
                    "contrato": contrato_teste,
                    "dados_financeiros": dados_financeiros,
                    "login_realizado": True,
                    "relatorio_exportado": True,
                    "dados_processados": True,
                    "credenciais_funcionais": True,
                    "timestamp_teste": datetime.now().isoformat()
                }

                # Salvar dados para implementação
                await self._salvar_resultado_teste("webscraping_real_implementacao", dados_implementacao)

                self.log_teste("✅ DADOS SALVOS PARA IMPLEMENTAÇÃO!")
                self.log_teste(f"📁 Arquivo: dados_processamento/testes_reais/webscraping_real_implementacao_{self.timestamp_execucao}.json")

                return True
            else:
                self.log_teste("❌ FALHA NA CONSULTA", "ERROR")
                self.log_teste(f"   Erro: {dados_financeiros.get('erro', 'Erro desconhecido')}")
                return False

        except Exception as e:
            self.log_teste(f"❌ Erro no teste webscraping real: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

        finally:
            # Fechar browser se foi inicializado
            if self.rpa_sienge and hasattr(self.rpa_sienge, 'driver'):
                try:
                    self.rpa_sienge.driver.quit()
                except:
                    pass

    async def teste_navegacao_reparcelamento_mock(self) -> bool:
        """
        🎯 TESTE: Navegação para reparcelamento com dados mock mas login real
        Para debugar implementação de marcação/desmarcação
        """
        self.log_teste("🧪 TESTE NAVEGAÇÃO REPARCELAMENTO: LOGIN REAL + MOCK MARCAÇÃO")
        self.log_teste("=" * 70)

        try:
            # Configurar credenciais reais
            credenciais_sienge = {
                "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/8"),
                "usuario": os.getenv("SIENGE_USUARIO", ""),
                "senha": os.getenv("SIENGE_SENHA", "")
            }

            if not credenciais_sienge["usuario"] or not credenciais_sienge["senha"]:
                self.log_teste("❌ CREDENCIAIS SIENGE NÃO CONFIGURADAS", "ERROR")
                return False

            # Inicializar RPA
            self.rpa_sienge = RPASienge()
            self.rpa_sienge._configurar_credenciais(credenciais_sienge)

            # ETAPA 1: LOGIN REAL
            self.log_teste("\n🔐 ETAPA 1: LOGIN NO SIENGE...")
            await self.rpa_sienge._fazer_login_sienge()
            self.log_teste("✅ Login realizado")

            # ETAPA 2: NAVEGAR PARA REPARCELAMENTO
            self.log_teste("\n🌐 ETAPA 2: NAVEGANDO PARA REPARCELAMENTO...")
            url_reparcelamento = "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/reparcelamento/inclusao"
            
            self.rpa_sienge.get_page(url_reparcelamento)
            self.log_teste(f"✅ Navegou para: {url_reparcelamento}")

            # ETAPA 3: PREPARAR DADOS MOCK PARA MARCAÇÃO/DESMARCAÇÃO
            self.log_teste("\n📊 ETAPA 3: PREPARANDO DADOS MOCK...")
            
            contrato_mock = {
                "numero_titulo": "2239",
                "cliente": "SANDRO RIZZON VIEIRA"
            }

            # Parcelas mock baseadas em dados reais mas simplificadas
            parcelas_mock = [
                {
                    "documento": "CT001",
                    "data_vencimento": "2024-12-15",
                    "valor_a_receber": 2500.00,
                    "deve_desmarcar": True,
                    "motivo": "Parcela CT vencida"
                },
                {
                    "documento": "CT002",
                    "data_vencimento": "2025-01-15",
                    "valor_a_receber": 2500.00,
                    "deve_desmarcar": True,
                    "motivo": "Parcela CT vencida"
                },
                {
                    "documento": "CT003",
                    "data_vencimento": "2025-07-15",
                    "valor_a_receber": 2500.00,
                    "deve_desmarcar": False,
                    "motivo": "Parcela CT futura"
                },
                {
                    "documento": "REC001",
                    "data_vencimento": "2025-08-31",
                    "valor_a_receber": 1200.00,
                    "deve_desmarcar": False,
                    "motivo": "Parcela REC futura"
                },
                {
                    "documento": "IPTU001",
                    "data_vencimento": "2025-01-31",
                    "valor_a_receber": 800.00,
                    "deve_desmarcar": True,
                    "motivo": "Parcela IPTU vencida"
                }
            ]

            # ETAPA 4: GERAR INSTRUÇÕES PARA IMPLEMENTAÇÃO
            self.log_teste("\n🎯 ETAPA 4: INSTRUÇÕES PARA IMPLEMENTAÇÃO...")

            # Calcular estatísticas
            total_parcelas = len(parcelas_mock)
            parcelas_desmarcar = [p for p in parcelas_mock if p['deve_desmarcar']]
            parcelas_manter = [p for p in parcelas_mock if not p['deve_desmarcar']]
            
            valor_desmarcar = sum(p['valor_a_receber'] for p in parcelas_desmarcar)
            valor_manter = sum(p['valor_a_receber'] for p in parcelas_manter)

            self.log_teste(f"📊 ESTATÍSTICAS PARA IMPLEMENTAÇÃO:")
            self.log_teste(f"   📄 Total parcelas: {total_parcelas}")
            self.log_teste(f"   ❌ Para desmarcar: {len(parcelas_desmarcar)}")
            self.log_teste(f"   ✅ Para manter: {len(parcelas_manter)}")
            self.log_teste(f"   💰 Valor desmarcado: R$ {valor_desmarcar:,.2f}")
            self.log_teste(f"   💰 Valor mantido: R$ {valor_manter:,.2f}")

            self.log_teste(f"\n🔧 LISTA DE PARCELAS PARA DESMARCAR:")
            for parcela in parcelas_desmarcar:
                self.log_teste(f"   ❌ {parcela['documento']} - {parcela['data_vencimento']} - R$ {parcela['valor_a_receber']:,.2f}")
                self.log_teste(f"      Motivo: {parcela['motivo']}")

            self.log_teste(f"\n✅ LISTA DE PARCELAS PARA MANTER:")
            for parcela in parcelas_manter:
                self.log_teste(f"   ✅ {parcela['documento']} - {parcela['data_vencimento']} - R$ {parcela['valor_a_receber']:,.2f}")

            # ETAPA 5: SALVAR DADOS PARA IMPLEMENTAÇÃO
            dados_implementacao_marcacao = {
                "contrato": contrato_mock,
                "parcelas_detalhadas": parcelas_mock,
                "parcelas_desmarcar": parcelas_desmarcar,
                "parcelas_manter": parcelas_manter,
                "estatisticas": {
                    "total_parcelas": total_parcelas,
                    "total_desmarcar": len(parcelas_desmarcar),
                    "total_manter": len(parcelas_manter),
                    "valor_desmarcar": valor_desmarcar,
                    "valor_manter": valor_manter
                },
                "url_reparcelamento": url_reparcelamento,
                "login_realizado": True,
                "navegacao_realizada": True,
                "pronto_para_implementacao": True,
                "timestamp_teste": datetime.now().isoformat()
            }

            await self._salvar_resultado_teste("navegacao_reparcelamento_implementacao", dados_implementacao_marcacao)

            self.log_teste("\n✅ TESTE CONCLUÍDO - DADOS SALVOS PARA IMPLEMENTAÇÃO!")
            self.log_teste(f"📁 Arquivo: navegacao_reparcelamento_implementacao_{self.timestamp_execucao}.json")
            self.log_teste("\n🎯 PRÓXIMOS PASSOS PARA IMPLEMENTAÇÃO:")
            self.log_teste("   1. Buscar título específico no formulário")
            self.log_teste("   2. Identificar lista de parcelas na interface")
            self.log_teste("   3. Implementar marcação: primeiro marcar todas")
            self.log_teste("   4. Implementar desmarcação: desmarcar parcelas específicas")
            self.log_teste("   5. Validar seleção final antes de prosseguir")

            return True

        except Exception as e:
            self.log_teste(f"❌ Erro no teste navegação: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

        finally:
            # Manter browser aberto para debug se necessário
            if hasattr(self, 'manter_browser_aberto') and self.manter_browser_aberto:
                self.log_teste("🔧 Browser mantido aberto para debug")
                input("Pressione ENTER para fechar o browser...")
            
            if self.rpa_sienge and hasattr(self.rpa_sienge, 'driver'):
                try:
                    self.rpa_sienge.driver.quit()
                except:
                    pass

async def menu_interativo():
    """
    Menu interativo para execução dos testes baseados em dados reais
    """
    testador = TestadorRPASiengeReal()

    opcoes = {
        "1": ("🔥 Teste Integração Completa Fila (RECOMENDADO)", testador.teste_integracao_completa_fila),
        "2": ("📊 Teste Carregamento Fila MongoDB", testador.teste_carregamento_fila),
        "3": ("🌐 Teste Simulação Consulta Sienge", testador.teste_simulacao_consulta_sienge),
        "4": ("💰 Teste Processamento Reparcelamento", testador.teste_processamento_reparcelamento_mock),
        "5": ("🤖 Teste RPA Real com Dados Fila", testador.teste_rpa_real_com_dados_fila),
        "6": ("✅ Teste Análise Parcelas e Marcação/Desmarcação", testador.teste_análise_parcelas_marcacao),
        "7": ("✨ Teste Simulação Webscraping Rep", testador.teste_simulacao_webscraping_reparcelamento),
        "8": ("🧪 Teste Validação PDD com Parcelas", testador.teste_validacao_regras_pdd_com_parcelas),
        "9": ("🎯 TESTE WEBSCRAPING REAL: Login + Consulta + Dados", testador.teste_webscraping_real_login_consulta),
        "10": ("🔧 TESTE NAVEGAÇÃO REPARCELAMENTO: Login + Marcação Mock", testador.teste_navegacao_reparcelamento_mock),
        "0": ("❌ Sair", None)
    }

    print("\n" + "=" * 70)
    print("🧪 TESTES RPA SIENGE - DADOS REAIS DA FILA")
    print("Sistema de testes baseado na estrutura real do MongoDB")
    print("=" * 70)

    for key, (descricao, _) in opcoes.items():
        print(f"{key}. {descricao}")

    print("=" * 70)

    while True:
        try:
            escolha = input("\n➤ Escolha uma opção (0-10): ").strip()

            if escolha == "0":
                print("👋 Encerrando testes...")
                break
            elif escolha in opcoes and opcoes[escolha][1]:
                print(f"\n🔄 Executando: {opcoes[escolha][0]}")
                print("-" * 70)

                inicio = datetime.now()
                sucesso = await opcoes[escolha][1]()
                fim = datetime.now()
                tempo_execucao = (fim - inicio).total_seconds()

                print("-" * 70)
                if sucesso:
                    print(f"✅ Teste CONCLUÍDO COM SUCESSO em {tempo_execucao:.1f}s")
                else:
                    print(f"❌ Teste FALHOU em {tempo_execucao:.1f}s")

                input("\n⏳ Pressione ENTER para continuar...")

                # Reexibir menu
                print("\n" + "=" * 70)
                for key, (descricao, _) in opcoes.items():
                    print(f"{key}. {descricao}")
                print("=" * 70)
            else:
                print("❌ Opção inválida! Escolha entre 0-10.")

        except KeyboardInterrupt:
            print("\n\n👋 Testes interrompidos pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")
            traceback.print_exc()


if __name__ == "__main__":
    print("🚀 SISTEMA DE TESTES RPA SIENGE - DADOS REAIS")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("🎯 Baseado na estrutura real da fila MongoDB")

    try:
        asyncio.run(menu_interativo())
    except KeyboardInterrupt:
        print("\n👋 Sistema encerrado pelo usuário.")
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        import traceback
        traceback.print_exc()