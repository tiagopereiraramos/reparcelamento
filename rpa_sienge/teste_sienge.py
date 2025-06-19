#!/usr/bin/env python3
"""
Teste RPA Sienge - Baseado na Implementação Completa do rpa_sienge.py
Sistema de testes que utiliza toda a funcionalidade já implementada

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


class TestadorRPASiengeCompleto:
    """
    Testador RPA Sienge usando toda a implementação do rpa_sienge.py
    """

    def __init__(self):
        self.pasta_resultados = Path("rpa_sienge/dados_processamento/testes_completos")
        self.pasta_resultados.mkdir(parents=True, exist_ok=True)
        self.timestamp_execucao = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.rpa_sienge = RPASienge()

    def log_teste(self, mensagem: str, nivel: str = "INFO"):
        """Log estruturado para testes"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {nivel}: {mensagem}")

    def obter_credenciais_sienge(self) -> Dict[str, str]:
        """
        Obtém credenciais do Sienge (configure conforme necessário)
        """
        return {
            "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/8"),
            "usuario": os.getenv("SIENGE_USUARIO", "tc@trajetoriaconsultoria.com.br"),
            "senha": os.getenv("SIENGE_SENHA", "sua_senha_aqui"),
            "empresa": os.getenv("SIENGE_EMPRESA", "BVRB")
        }

    def criar_contrato_teste(self) -> Dict[str, Any]:
        """
        Cria contrato de teste baseado nos dados reais
        """
        return {
            "numero_titulo": "2239",
            "cliente": "SANDRO RIZZON VIEIRA",
            "empreendimento": "MARCELY"
        }

    async def teste_login_sienge(self) -> bool:
        """
        Testa apenas o login no Sienge
        """
        self.log_teste("🧪 TESTE: LOGIN SIENGE")
        self.log_teste("=" * 40)

        try:
            # Configurar credenciais
            credenciais = self.obter_credenciais_sienge()
            self.rpa_sienge._configurar_credenciais(credenciais)

            # Testar login
            self.log_teste("🔐 Testando login no Sienge...")
            await self.rpa_sienge._fazer_login_sienge()

            if self.rpa_sienge.logado_sienge:
                self.log_teste("✅ Login realizado com sucesso!")
                return True
            else:
                self.log_teste("❌ Login falhou", "ERROR")
                return False

        except Exception as e:
            self.log_teste(f"❌ Erro no teste de login: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_consulta_relatorios(self) -> bool:
        """
        Testa consulta de relatórios (etapa de consulta)
        """
        self.log_teste("🧪 TESTE: CONSULTA DE RELATÓRIOS")
        self.log_teste("=" * 40)

        try:
            contrato = self.criar_contrato_teste()
            credenciais = self.obter_credenciais_sienge()

            self.log_teste(f"📄 Testando consulta para: {contrato['numero_titulo']}")
            self.log_teste(f"👤 Cliente: {contrato['cliente']}")

            # Executar apenas etapa de consulta
            resultado = await self.rpa_sienge.executar(
                contrato=contrato,
                credenciais_sienge=credenciais,
                etapa="consulta"
            )

            if resultado.sucesso:
                self.log_teste("✅ Consulta realizada com sucesso!")

                # Analisar dados retornados
                dados_financeiros = resultado.dados.get("dados_financeiros", {})
                self.log_teste(f"📊 Status cliente: {dados_financeiros.get('status_cliente', 'N/A')}")
                self.log_teste(f"💰 Saldo total: R$ {dados_financeiros.get('saldo_total', 0):,.2f}")
                self.log_teste(f"🔢 Parcelas pendentes: {dados_financeiros.get('parcelas_pendentes', 0)}")

                # Salvar resultado
                await self._salvar_resultado_teste("consulta_relatorios", {
                    "contrato": contrato,
                    "resultado": resultado.dados,
                    "timestamp": datetime.now().isoformat()
                })

                return True
            else:
                self.log_teste(f"❌ Erro na consulta: {resultado.erro}", "ERROR")
                return False

        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_carregamento_dados_fila(self) -> bool:
        """
        Testa carregamento de dados da fila do MongoDB
        """
        self.log_teste("🧪 TESTE: CARREGAMENTO DADOS FILA")
        self.log_teste("=" * 40)

        try:
            # Testar carregamento da fila
            self.log_teste("📊 Carregando dados da fila de reparcelamento...")

            resultado_carga = await self.rpa_sienge.carregar_dados_fila_reparcelamento()

            if resultado_carga.get("sucesso", False):
                parametros = resultado_carga["parametros_navegacao"]

                self.log_teste("✅ Dados carregados com sucesso!")
                self.log_teste(f"📄 Título: {parametros['numero_titulo']}")
                self.log_teste(f"👤 Cliente: {parametros['cliente']}")
                self.log_teste(f"💰 Saldo: R$ {parametros['saldo_anterior']:,.2f} → R$ {parametros['saldo_novo']:,.2f}")
                self.log_teste(f"📊 IGP-M: {parametros['igpm_aplicado']}%")
                self.log_teste(f"❌ Parcelas a desmarcar: {parametros['total_parcelas_desmarcar']}")

                # Salvar dados completos
                await self._salvar_resultado_teste("carregamento_fila", {
                    "resultado_carga": resultado_carga,
                    "timestamp": datetime.now().isoformat()
                })

                return True
            else:
                erro = resultado_carga.get("erro", "Erro desconhecido")
                self.log_teste(f"❌ Erro no carregamento: {erro}", "ERROR")

                if resultado_carga.get("fila_vazia"):
                    self.log_teste("⚠️ Fila de reparcelamento vazia", "WARNING")
                elif "IGPM não disponível" in erro:
                    self.log_teste("⚠️ Execute o RPA de Coleta de Índices primeiro", "WARNING")

                return False

        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_reparcelamento_webscraping_mock(self) -> bool:
        """
        Testa execução de reparcelamento com webscraping (simulado)
        """
        self.log_teste("🧪 TESTE: REPARCELAMENTO WEBSCRAPING (SIMULADO)")
        self.log_teste("=" * 50)

        try:
            self.log_teste("🌐 Testando execução completa de reparcelamento...")

            # Executar reparcelamento completo
            resultado = await self.rpa_sienge.executar_reparcelamento_webscraping()

            if resultado.sucesso:
                self.log_teste("✅ Reparcelamento executado com sucesso!")

                dados = resultado.dados
                self.log_teste(f"📄 Título processado: {dados.get('numero_titulo')}")
                self.log_teste(f"👤 Cliente: {dados.get('cliente')}")
                self.log_teste(f"🆕 Novo título: {dados.get('novo_titulo_gerado')}")
                self.log_teste(f"💰 Saldo anterior: R$ {dados.get('saldo_anterior', 0):,.2f}")
                self.log_teste(f"💰 Saldo novo: R$ {dados.get('saldo_novo', 0):,.2f}")
                self.log_teste(f"❌ Parcelas desmarcadas: {dados.get('parcelas_desmarcadas', 0)}")

                # Salvar resultado
                await self._salvar_resultado_teste("reparcelamento_webscraping", {
                    "resultado": resultado.dados,
                    "timestamp": datetime.now().isoformat()
                })

                return True
            else:
                self.log_teste(f"❌ Erro no reparcelamento: {resultado.erro}", "ERROR")
                return False

        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_integracao_completa_fila(self) -> bool:
        """
        Teste de integração usando toda a funcionalidade da fila
        """
        self.log_teste("🧪 TESTE: INTEGRAÇÃO COMPLETA FILA")
        self.log_teste("=" * 50)

        try:
            testes = [
                ("Carregamento Fila", self.teste_carregamento_dados_fila),
                ("Consulta Relatórios", self.teste_consulta_relatorios),
                ("Reparcelamento Webscraping", self.teste_reparcelamento_webscraping_mock)
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
            self.log_teste(f"   📊 Taxa sucesso: {(sucessos/total)*100:.1f}%")

            # Salvar resumo
            resumo = {
                "timestamp_execucao": self.timestamp_execucao,
                "resultados_individuais": resultados,
                "sucessos": sucessos,
                "total_testes": total,
                "percentual_sucesso": (sucessos / total) * 100 if total > 0 else 0,
                "tipo_teste": "integracao_completa_baseada_rpa_sienge"
            }

            await self._salvar_resultado_teste("integracao_completa_fila", resumo)

            return sucessos == total

        except Exception as e:
            self.log_teste(f"❌ Erro na integração: {str(e)}", "ERROR")
            return False

    async def teste_processamento_etapa_completa(self) -> bool:
        """
        Teste da etapa completa do RPA (consulta + reparcelamento + carnê)
        """
        self.log_teste("🧪 TESTE: PROCESSAMENTO ETAPA COMPLETA")
        self.log_teste("=" * 45)

        try:
            contrato = self.criar_contrato_teste()
            credenciais = self.obter_credenciais_sienge()

            self.log_teste("🚀 Executando etapa completa...")

            # Executar etapa completa
            resultado = await self.rpa_sienge.executar(
                contrato=contrato,
                credenciais_sienge=credenciais,
                etapa="completa",
                autorizar_reparcelamento=True  # Para pular validação PDD em teste
            )

            if resultado.sucesso:
                self.log_teste("✅ Etapa completa executada com sucesso!")

                dados = resultado.dados
                self.log_teste(f"📋 Etapa executada: {dados.get('etapa_executada')}")

                # Dados financeiros
                dados_financeiros = dados.get("dados_financeiros", {})
                self.log_teste(f"💰 Saldo total: R$ {dados_financeiros.get('saldo_total', 0):,.2f}")

                # Reparcelamento
                reparcelamento = dados.get("reparcelamento", {})
                if reparcelamento:
                    self.log_teste(f"🆕 Novo título: {reparcelamento.get('novo_titulo_gerado')}")
                    self.log_teste(f"💰 Valor corrigido: R$ {reparcelamento.get('valor_corrigido', 0):,.2f}")

                # Carnê
                carne = dados.get("carne_gerado", {})
                if carne and carne.get("sucesso"):
                    self.log_teste(f"📄 Carnê gerado: {carne.get('nome_arquivo')}")

                # Salvar resultado
                await self._salvar_resultado_teste("etapa_completa", {
                    "contrato": contrato,
                    "resultado": resultado.dados,
                    "timestamp": datetime.now().isoformat()
                })

                return True
            else:
                self.log_teste(f"❌ Erro na etapa completa: {resultado.erro}", "ERROR")
                return False

        except Exception as e:
            self.log_teste(f"❌ Erro no teste: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_validacao_credenciais(self) -> bool:
        """
        Testa validação de credenciais
        """
        self.log_teste("🧪 TESTE: VALIDAÇÃO CREDENCIAIS")
        self.log_teste("=" * 35)

        try:
            credenciais = self.obter_credenciais_sienge()

            self.log_teste("🔍 Validando credenciais fornecidas...")
            self.log_teste(f"   URL: {credenciais.get('url', 'N/A')}")
            self.log_teste(f"   Usuário: {credenciais.get('usuario', 'N/A')}")
            self.log_teste(f"   Senha: {'***' if credenciais.get('senha') else 'N/A'}")
            self.log_teste(f"   Empresa: {credenciais.get('empresa', 'N/A')}")

            # Verificar se todas as credenciais estão presentes
            campos_obrigatorios = ["url", "usuario", "senha"]
            campos_faltando = [campo for campo in campos_obrigatorios if not credenciais.get(campo)]

            if campos_faltando:
                self.log_teste(f"❌ Campos obrigatórios faltando: {', '.join(campos_faltando)}", "ERROR")
                self.log_teste("💡 Configure as variáveis de ambiente ou edite o método obter_credenciais_sienge()")
                return False
            else:
                self.log_teste("✅ Todas as credenciais necessárias estão presentes")
                return True

        except Exception as e:
            self.log_teste(f"❌ Erro na validação: {str(e)}", "ERROR")
            return False

    async def _salvar_resultado_teste(self, nome_teste: str, dados: Any):
        """Salva resultados do teste"""
        try:
            arquivo = self.pasta_resultados / f"{nome_teste}_{self.timestamp_execucao}.json"

            dados_salvamento = {
                "nome_teste": nome_teste,
                "timestamp": datetime.now().isoformat(),
                "baseado_em": "rpa_sienge.py",
                "dados": dados
            }

            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_salvamento, f, indent=2, ensure_ascii=False)

            self.log_teste(f"💾 Resultado salvo: {arquivo}")

        except Exception as e:
            self.log_teste(f"❌ Erro ao salvar resultado: {str(e)}", "ERROR")


async def menu_interativo():
    """
    Menu interativo para execução dos testes baseados no rpa_sienge.py
    """
    testador = TestadorRPASiengeCompleto()

    opcoes = {
        "1": ("🔥 Teste Integração Completa (RECOMENDADO)", testador.teste_integracao_completa_fila),
        "2": ("🔐 Teste Login Sienge", testador.teste_login_sienge),
        "3": ("📊 Teste Consulta Relatórios", testador.teste_consulta_relatorios),
        "4": ("📁 Teste Carregamento Dados Fila", testador.teste_carregamento_dados_fila),
        "5": ("🌐 Teste Reparcelamento Webscraping", testador.teste_reparcelamento_webscraping_mock),
        "6": ("🚀 Teste Etapa Completa", testador.teste_processamento_etapa_completa),
        "7": ("🔍 Teste Validação Credenciais", testador.teste_validacao_credenciais),
        "0": ("❌ Sair", None)
    }

    print("\n" + "=" * 70)
    print("🧪 TESTES RPA SIENGE - BASEADO NA IMPLEMENTAÇÃO COMPLETA")
    print("Sistema de testes usando toda a funcionalidade do rpa_sienge.py")
    print("=" * 70)

    for key, (descricao, _) in opcoes.items():
        print(f"{key}. {descricao}")

    print("=" * 70)

    while True:
        try:
            escolha = input("\n➤ Escolha uma opção (0-7): ").strip()

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
                print("❌ Opção inválida! Escolha entre 0-7.")

        except KeyboardInterrupt:
            print("\n\n👋 Testes interrompidos pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")
            traceback.print_exc()


if __name__ == "__main__":
    print("🚀 SISTEMA DE TESTES RPA SIENGE - IMPLEMENTAÇÃO COMPLETA")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("🎯 Baseado em toda a funcionalidade do rpa_sienge.py")

    try:
        asyncio.run(menu_interativo())
    except KeyboardInterrupt:
        print("\n👋 Sistema encerrado pelo usuário.")
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        import traceback
        traceback.print_exc()