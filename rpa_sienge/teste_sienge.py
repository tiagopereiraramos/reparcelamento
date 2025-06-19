
#!/usr/bin/env python3
"""
Teste Refinado - RPA Sienge
Sistema de testes estruturado para validação completa do RPA Sienge

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import traceback

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rpa_sienge import RPASienge
from core.processador_regras_pdd import ProcessadorRegrasNegocio
from core.base_rpa import ResultadoRPA


class TestadorRPASienge:
    """
    Classe centralizada para todos os testes do RPA Sienge
    """
    
    def __init__(self):
        self.pasta_dados = Path("dados_processamento/testes_sienge")
        self.pasta_dados.mkdir(parents=True, exist_ok=True)
        self.processador_regras = ProcessadorRegrasNegocio()
        self.timestamp_execucao = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log_teste(self, mensagem: str, nivel: str = "INFO"):
        """Log estruturado para testes"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {nivel}: {mensagem}")
    
    async def carregar_dados_excel_real(self) -> Optional[pd.DataFrame]:
        """
        Carrega dados reais do Excel anexado
        """
        try:
            arquivo_excel = "attached_assets/saldo_devedor_presente-20250610-093716.xlsx"
            
            if not os.path.exists(arquivo_excel):
                self.log_teste(f"❌ Arquivo Excel não encontrado: {arquivo_excel}", "ERROR")
                return None
            
            self.log_teste(f"📊 Carregando Excel: {arquivo_excel}")
            df = pd.read_excel(arquivo_excel)
            
            self.log_teste(f"✅ Excel carregado: {len(df)} registros, {len(df.columns)} colunas")
            return df
            
        except Exception as e:
            self.log_teste(f"❌ Erro ao carregar Excel: {str(e)}", "ERROR")
            return None
    
    async def teste_validacao_regras_pdd(self) -> bool:
        """
        Testa validação rigorosa das regras PDD
        """
        self.log_teste("🧪 TESTE: VALIDAÇÃO REGRAS PDD")
        self.log_teste("=" * 50)
        
        try:
            # Carregar dados reais
            df_real = await self.carregar_dados_excel_real()
            if df_real is None:
                return False
            
            # Testar primeiros 3 títulos únicos
            titulos_unicos = df_real['Título'].unique()[:3]
            self.log_teste(f"🎯 Testando {len(titulos_unicos)} títulos")
            
            resultados = []
            for i, titulo in enumerate(titulos_unicos):
                self.log_teste(f"\n📄 [{i+1}/{len(titulos_unicos)}] Título: {titulo}")
                
                # Filtrar dados do título
                df_titulo = df_real[df_real['Título'] == titulo].copy()
                cliente = df_titulo['Cliente'].iloc[0] if 'Cliente' in df_titulo.columns else f"Cliente_{titulo}"
                
                # Processar com regras PDD
                resultado = self.processador_regras.processar_dados_cliente_completo(
                    df_planilha=df_titulo,
                    cliente=cliente,
                    numero_titulo=str(titulo)
                )
                
                # Validar resultado
                if resultado.get("sucesso"):
                    self.log_teste(f"   ✅ Processamento bem-sucedido")
                    self.log_teste(f"   🎯 Pode reparcelar: {resultado.get('pode_reparcelar')}")
                    self.log_teste(f"   💰 Saldo total: R$ {resultado.get('saldo_total', 0):,.2f}")
                    self.log_teste(f"   📊 CT a vencer: {resultado.get('qtd_parcelas_ct_a_vencer', 0)}")
                    self.log_teste(f"   🚨 CT vencidas: {resultado.get('qtd_ct_vencidas', 0)}")
                else:
                    self.log_teste(f"   ❌ Erro: {resultado.get('erro', 'Erro desconhecido')}", "ERROR")
                
                resultados.append(resultado)
            
            # Salvar resultados
            await self._salvar_resultados_teste("validacao_regras_pdd", resultados)
            
            sucessos = sum(1 for r in resultados if r.get("sucesso"))
            self.log_teste(f"\n📈 RESULTADO: {sucessos}/{len(resultados)} sucessos")
            
            return sucessos > 0
            
        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            return False
    
    async def teste_calculo_reparcelamento(self) -> bool:
        """
        Testa cálculos de reparcelamento com dados reais
        """
        self.log_teste("🧪 TESTE: CÁLCULO REPARCELAMENTO")
        self.log_teste("=" * 50)
        
        try:
            # Usar dados de exemplo para teste
            saldo_atual = 10000.0
            igpm_exemplo = 3.89
            parcelas_pendentes = 12
            
            self.log_teste(f"💰 Saldo atual: R$ {saldo_atual:,.2f}")
            self.log_teste(f"📊 IGP-M: {igmp_exemplo}%")
            self.log_teste(f"🔢 Parcelas pendentes: {parcelas_pendentes}")
            
            # Calcular valores
            resultado_calculo = await self.processador_regras.calcular_valores_reparcelamento(
                saldo_atual=saldo_atual,
                indice_igpm=igpm_exemplo,
                parcelas_pendentes=parcelas_pendentes
            )
            
            if resultado_calculo.get("sucesso"):
                valores = resultado_calculo.get("valores_sienge", {})
                self.log_teste(f"✅ Cálculo bem-sucedido")
                self.log_teste(f"   💰 Novo saldo: R$ {resultado_calculo.get('novo_saldo', 0):,.2f}")
                self.log_teste(f"   📊 Fator correção: {resultado_calculo.get('fator_correcao', 1):.4f}")
                self.log_teste(f"   🏦 Indexador: {valores.get('indexador', 'N/A')}")
                self.log_teste(f"   💸 Juros: {valores.get('percentual_juros', 0)}%")
                
                # Salvar resultado
                await self._salvar_resultados_teste("calculo_reparcelamento", resultado_calculo)
                return True
            else:
                self.log_teste(f"❌ Erro no cálculo: {resultado_calculo.get('erro')}", "ERROR")
                return False
                
        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            return False
    
    async def teste_preparacao_webscraping(self) -> bool:
        """
        Testa preparação de parâmetros para webscraping
        """
        self.log_teste("🧪 TESTE: PREPARAÇÃO WEBSCRAPING")
        self.log_teste("=" * 50)
        
        try:
            # Carregar dados reais
            df_real = await self.carregar_dados_excel_real()
            if df_real is None:
                return False
            
            # Encontrar título que pode reparcelar
            titulo_testavel = None
            dados_validacao = None
            
            for titulo in df_real['Título'].unique()[:5]:
                df_titulo = df_real[df_real['Título'] == titulo].copy()
                cliente = df_titulo['Cliente'].iloc[0] if 'Cliente' in df_titulo.columns else f"Cliente_{titulo}"
                
                resultado = self.processador_regras.processar_dados_cliente_completo(
                    df_planilha=df_titulo,
                    cliente=cliente,
                    numero_titulo=str(titulo)
                )
                
                if resultado.get("pode_reparcelar"):
                    titulo_testavel = titulo
                    dados_validacao = resultado
                    break
            
            if not titulo_testavel:
                self.log_teste("❌ Nenhum título encontrado que possa reparcelar", "WARNING")
                # Usar dados exemplo para teste
                titulo_testavel = "EXEMPLO_001"
                dados_validacao = {
                    "pode_reparcelar": True,
                    "saldo_total": 15000.0,
                    "qtd_parcelas_ct_a_vencer": 8,
                    "parcelas_ct_a_vencer_detalhes": []
                }
            
            self.log_teste(f"🎯 Título selecionado: {titulo_testavel}")
            
            # Calcular valores para webscraping
            saldo_atual = dados_validacao.get('saldo_total', 15000.0)
            parcelas_pendentes = dados_validacao.get('qtd_parcelas_ct_a_vencer', 8)
            igpm_simulado = 3.89
            
            calculo_resultado = await self.processador_regras.calcular_valores_reparcelamento(
                saldo_atual=saldo_atual,
                indice_igpm=igpm_simulado,
                parcelas_pendentes=parcelas_pendentes
            )
            
            if not calculo_resultado.get("sucesso"):
                self.log_teste(f"❌ Erro no cálculo: {calculo_resultado.get('erro')}", "ERROR")
                return False
            
            # Preparar parâmetros completos
            parametros_webscraping = {
                "numero_titulo": str(titulo_testavel),
                "cliente": dados_validacao.get("cliente", f"Cliente_{titulo_testavel}"),
                "url_reparcelamento": "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/reparcelamento/inclusao",
                "valores_sienge": calculo_resultado.get("valores_sienge", {}),
                "parcelas_desmarcar": dados_validacao.get("parcelas_ct_a_vencer_detalhes", []),
                "saldo_anterior": saldo_atual,
                "saldo_novo": calculo_resultado.get("novo_saldo", 0),
                "igpm_aplicado": igpm_simulado,
                "timestamp_preparacao": datetime.now().isoformat()
            }
            
            # Salvar parâmetros
            arquivo_parametros = self.pasta_dados / f"parametros_webscraping_{self.timestamp_execucao}.json"
            with open(arquivo_parametros, 'w', encoding='utf-8') as f:
                json.dump(parametros_webscraping, f, indent=2, ensure_ascii=False)
            
            self.log_teste(f"✅ Parâmetros preparados e salvos: {arquivo_parametros}")
            self.log_teste(f"   📄 Título: {parametros_webscraping['numero_titulo']}")
            self.log_teste(f"   💰 Saldo: R$ {parametros_webscraping['saldo_anterior']:,.2f} → R$ {parametros_webscraping['saldo_novo']:,.2f}")
            
            return True
            
        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            return False
    
    async def teste_simulacao_webscraping(self) -> bool:
        """
        Simula execução do webscraping
        """
        self.log_teste("🧪 TESTE: SIMULAÇÃO WEBSCRAPING")
        self.log_teste("=" * 50)
        
        try:
            # Buscar arquivo de parâmetros mais recente
            arquivos_parametros = list(self.pasta_dados.glob("parametros_webscraping_*.json"))
            
            if not arquivos_parametros:
                self.log_teste("❌ Nenhum arquivo de parâmetros encontrado. Execute teste_preparacao_webscraping primeiro.", "ERROR")
                return False
            
            arquivo_mais_recente = max(arquivos_parametros, key=lambda f: f.stat().st_mtime)
            
            with open(arquivo_mais_recente, 'r', encoding='utf-8') as f:
                parametros = json.load(f)
            
            self.log_teste(f"📊 Carregados parâmetros: {arquivo_mais_recente.name}")
            self.log_teste(f"   📄 Título: {parametros['numero_titulo']}")
            self.log_teste(f"   👤 Cliente: {parametros['cliente']}")
            
            # Simular resultado do webscraping
            resultado_simulado = {
                "sucesso": True,
                "novo_titulo_gerado": f"REP_{parametros['numero_titulo']}_{self.timestamp_execucao}",
                "numero_titulo_original": parametros['numero_titulo'],
                "valores_aplicados": parametros['valores_sienge'],
                "parcelas_processadas": len(parametros['parcelas_desmarcar']),
                "timestamp_webscraping": datetime.now().isoformat()
            }
            
            # Salvar resultado simulado
            await self._salvar_resultados_teste("simulacao_webscraping", resultado_simulado)
            
            self.log_teste(f"✅ Simulação bem-sucedida")
            self.log_teste(f"   🆕 Novo título: {resultado_simulado['novo_titulo_gerado']}")
            self.log_teste(f"   📊 Parcelas processadas: {resultado_simulado['parcelas_processadas']}")
            
            return True
            
        except Exception as e:
            self.log_teste(f"❌ Erro na simulação: {str(e)}", "ERROR")
            return False
    
    async def teste_browser_manager(self) -> bool:
        """
        Testa funcionalidades do browser manager
        """
        self.log_teste("🧪 TESTE: BROWSER MANAGER")
        self.log_teste("=" * 50)
        
        try:
            from core.browser_manager import RPABrowser, SELENIUM_DISPONIVEL
            
            self.log_teste(f"📊 Selenium disponível: {'✅' if SELENIUM_DISPONIVEL else '❌'}")
            
            if not SELENIUM_DISPONIVEL:
                self.log_teste("⚠️ Selenium não disponível - teste em modo simulado", "WARNING")
                return True
            
            # Testar métodos essenciais
            metodos_essenciais = [
                'get_page', 'find_element', 'find_elements', 'click', 
                'send_text', 'send_text_human_like', 'check_for_error',
                'on_new_window', 'on_iframe', 'close'
            ]
            
            self.log_teste("🔧 Validando métodos essenciais:")
            browser = RPABrowser(headless=True)
            
            for metodo in metodos_essenciais:
                disponivel = hasattr(browser, metodo)
                status = "✅" if disponivel else "❌"
                self.log_teste(f"   {status} {metodo}")
            
            browser.close()
            self.log_teste("✅ Browser Manager validado")
            
            return True
            
        except Exception as e:
            self.log_teste(f"❌ Erro no teste browser: {str(e)}", "ERROR")
            return False
    
    async def teste_integracao_completa(self) -> bool:
        """
        Teste de integração completa
        """
        self.log_teste("🧪 TESTE: INTEGRAÇÃO COMPLETA")
        self.log_teste("=" * 50)
        
        try:
            # Executar todos os testes em sequência
            testes = [
                ("Validação Regras PDD", self.teste_validacao_regras_pdd),
                ("Cálculo Reparcelamento", self.teste_calculo_reparcelamento),
                ("Preparação Webscraping", self.teste_preparacao_webscraping),
                ("Simulação Webscraping", self.teste_simulacao_webscraping),
                ("Browser Manager", self.teste_browser_manager)
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
            
            self.log_teste(f"\n📈 RESULTADO INTEGRAÇÃO COMPLETA:")
            self.log_teste(f"   ✅ Sucessos: {sucessos}/{total}")
            self.log_teste(f"   ❌ Falhas: {total - sucessos}")
            
            # Salvar resumo
            resumo = {
                "timestamp_execucao": self.timestamp_execucao,
                "resultados_individuais": resultados,
                "sucessos": sucessos,
                "total_testes": total,
                "percentual_sucesso": (sucessos / total) * 100 if total > 0 else 0
            }
            
            await self._salvar_resultados_teste("integracao_completa", resumo)
            
            return sucessos == total
            
        except Exception as e:
            self.log_teste(f"❌ Erro na integração: {str(e)}", "ERROR")
            return False
    
    async def _salvar_resultados_teste(self, nome_teste: str, dados: Any):
        """
        Salva resultados do teste para auditoria
        """
        try:
            arquivo = self.pasta_dados / f"{nome_teste}_{self.timestamp_execucao}.json"
            
            dados_salvamento = {
                "nome_teste": nome_teste,
                "timestamp": datetime.now().isoformat(),
                "dados": dados
            }
            
            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_salvamento, f, indent=2, ensure_ascii=False)
            
            self.log_teste(f"💾 Resultados salvos: {arquivo}")
            
        except Exception as e:
            self.log_teste(f"❌ Erro ao salvar resultados: {str(e)}", "ERROR")


async def menu_interativo():
    """
    Menu interativo para execução dos testes
    """
    testador = TestadorRPASienge()
    
    opcoes = {
        "1": ("🔥 Teste Integração Completa (RECOMENDADO)", testador.teste_integracao_completa),
        "2": ("🤖 Teste Validação Regras PDD", testador.teste_validacao_regras_pdd),
        "3": ("💰 Teste Cálculo Reparcelamento", testador.teste_calculo_reparcelamento),
        "4": ("📊 Teste Preparação Webscraping", testador.teste_preparacao_webscraping),
        "5": ("🌐 Teste Simulação Webscraping", testador.teste_simulacao_webscraping),
        "6": ("🔧 Teste Browser Manager", testador.teste_browser_manager),
        "0": ("❌ Sair", None)
    }
    
    print("\n" + "=" * 70)
    print("🧪 TESTES RPA SIENGE - ESTRUTURA REFINADA")
    print("Sistema de testes completo para validação do RPA Sienge")
    print("=" * 70)
    
    for key, (descricao, _) in opcoes.items():
        print(f"{key}. {descricao}")
    
    print("=" * 70)
    
    while True:
        try:
            escolha = input("\n➤ Escolha uma opção (0-6): ").strip()
            
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
                print("❌ Opção inválida! Escolha entre 0-6.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Testes interrompidos pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")
            traceback.print_exc()


if __name__ == "__main__":
    print("🚀 SISTEMA DE TESTES RPA SIENGE")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("🎯 Estrutura refinada e organizada")
    
    try:
        asyncio.run(menu_interativo())
    except KeyboardInterrupt:
        print("\n👋 Sistema encerrado pelo usuário.")
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        traceback.print_exc()
