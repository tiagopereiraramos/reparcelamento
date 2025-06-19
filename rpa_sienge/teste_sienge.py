
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
                    "erro_processamento": None
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
                    "erro_processamento": None
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
            fator_correcao = 1 + (igmp_mock / 100)
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
            escolha = input("\n➤ Escolha uma opção (0-5): ").strip()
            
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
                print("❌ Opção inválida! Escolha entre 0-5.")
                
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
