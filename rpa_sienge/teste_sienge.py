#!/usr/bin/env python3
"""
Teste RPA Sienge - Focado na Implementação Real
Sistema de testes que utiliza exclusivamente o rpa_sienge.py já implementado

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import traceback

# Adiciona o diretório raiz ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import do RPA Sienge real
from rpa_sienge.rpa_sienge import RPASienge
from core.base_rpa import ResultadoRPA


class TestadorRPASiengeReal:
    """
    Testador focado exclusivamente no rpa_sienge.py já implementado
    """

    def __init__(self):
        self.pasta_resultados = Path("rpa_sienge/dados_processamento/testes_reais")
        self.pasta_resultados.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def log(self, mensagem: str, nivel: str = "INFO"):
        """Log estruturado"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {nivel}: {mensagem}")

    def obter_credenciais_teste(self) -> Dict[str, str]:
        """Credenciais para teste (configure conforme necessário)"""
        return {
            "url": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/8"),
            "usuario": os.getenv("SIENGE_USUARIO", "tc@trajetoriaconsultoria.com.br"),
            "senha": os.getenv("SIENGE_SENHA", "sua_senha_aqui"),
            "empresa": os.getenv("SIENGE_EMPRESA", "BVRB")
        }

    def criar_dados_teste(self) -> Dict[str, Any]:
        """Dados de teste baseados no contrato real validado"""
        return {
            "numero_titulo": "2239",
            "cliente": "SANDRO RIZZON VIEIRA",
            "empreendimento": "MARCELY"
        }

    async def teste_carregamento_fila_real(self) -> bool:
        """Testa carregamento da fila usando dados reais do banco"""
        self.log("🧪 TESTE: CARREGAMENTO FILA REAL")
        self.log("=" * 40)

        try:
            rpa = RPASienge()

            self.log("📊 Carregando dados da fila de reparcelamento...")
            resultado = await rpa.carregar_dados_fila_reparcelamento()

            if resultado.get("sucesso", False):
                parametros = resultado["parametros_navegacao"]

                self.log("✅ Dados carregados com sucesso!")
                self.log(f"📄 Título: {parametros['numero_titulo']}")
                self.log(f"👤 Cliente: {parametros['cliente']}")
                self.log(f"💰 Saldo anterior: R$ {parametros['saldo_anterior']:,.2f}")
                self.log(f"💰 Saldo novo: R$ {parametros['saldo_novo']:,.2f}")
                self.log(f"📊 IGP-M aplicado: {parametros['igpm_aplicado']}%")
                self.log(f"❌ Parcelas a desmarcar: {parametros['total_parcelas_desmarcar']}")

                await self._salvar_resultado("carregamento_fila", resultado)
                return True
            else:
                erro = resultado.get("erro", "Erro desconhecido")
                self.log(f"❌ Erro: {erro}", "ERROR")

                if "Fila vazia" in erro:
                    self.log("💡 Configure dados na fila de reparcelamento", "WARNING")
                elif "IGPM não disponível" in erro:
                    self.log("💡 Execute o RPA de Coleta de Índices primeiro", "WARNING")

                return False

        except Exception as e:
            self.log(f"❌ Erro no teste: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_execucao_webscraping(self) -> bool:
        """Testa execução completa do webscraping"""
        self.log("🧪 TESTE: EXECUÇÃO WEBSCRAPING COMPLETA")
        self.log("=" * 45)

        try:
            rpa = RPASienge()

            self.log("🌐 Executando reparcelamento com webscraping...")
            resultado = await rpa.executar_reparcelamento_webscraping()

            if resultado.sucesso:
                dados = resultado.dados

                self.log("✅ Webscraping executado com sucesso!")
                self.log(f"📄 Título processado: {dados.get('numero_titulo')}")
                self.log(f"👤 Cliente: {dados.get('cliente')}")
                self.log(f"🆕 Novo título gerado: {dados.get('novo_titulo_gerado')}")
                self.log(f"💰 Valor corrigido: R$ {dados.get('saldo_novo', 0):,.2f}")
                self.log(f"❌ Parcelas processadas: {dados.get('parcelas_desmarcadas', 0)}")

                await self._salvar_resultado("webscraping_completo", resultado.dados)
                return True
            else:
                self.log(f"❌ Erro no webscraping: {resultado.erro}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Erro no teste: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_etapa_consulta(self) -> bool:
        """Testa apenas a etapa de consulta"""
        self.log("🧪 TESTE: ETAPA CONSULTA")
        self.log("=" * 30)

        try:
            rpa = RPASienge()
            contrato = self.criar_dados_teste()
            credenciais = self.obter_credenciais_teste()

            self.log(f"🔍 Consultando título: {contrato['numero_titulo']}")
            self.log(f"👤 Cliente: {contrato['cliente']}")

            resultado = await rpa.executar(
                contrato=contrato,
                credenciais_sienge=credenciais,
                etapa="consulta"
            )

            if resultado.sucesso:
                dados_financeiros = resultado.dados.get("dados_financeiros", {})

                self.log("✅ Consulta realizada com sucesso!")
                self.log(f"📊 Status: {dados_financeiros.get('status_cliente', 'N/A')}")
                self.log(f"💰 Saldo total: R$ {dados_financeiros.get('saldo_total', 0):,.2f}")
                self.log(f"🔢 Parcelas pendentes: {dados_financeiros.get('parcelas_pendentes', 0)}")

                await self._salvar_resultado("consulta", resultado.dados)
                return True
            else:
                self.log(f"❌ Erro na consulta: {resultado.erro}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Erro no teste: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    async def teste_integracao_completa(self) -> bool:
        """Teste de integração completa usando funcionalidade real"""
        self.log("🧪 TESTE: INTEGRAÇÃO COMPLETA")
        self.log("=" * 35)

        testes = [
            ("Carregamento Fila Real", self.teste_carregamento_fila_real),
            ("Consulta Relatórios", self.teste_etapa_consulta),
            ("Webscraping Completo", self.teste_execucao_webscraping)
        ]

        resultados = {}

        for nome, funcao in testes:
            self.log(f"\n🔄 Executando: {nome}")
            try:
                resultado = await funcao()
                resultados[nome] = resultado
                status = "✅ SUCESSO" if resultado else "❌ FALHA"
                self.log(f"{status}: {nome}")
            except Exception as e:
                self.log(f"❌ ERRO em {nome}: {str(e)}", "ERROR")
                resultados[nome] = False

        # Resumo final
        sucessos = sum(1 for r in resultados.values() if r)
        total = len(resultados)

        self.log(f"\n📈 RESUMO FINAL:")
        self.log(f"   ✅ Sucessos: {sucessos}/{total}")
        self.log(f"   ❌ Falhas: {total - sucessos}")
        self.log(f"   📊 Taxa sucesso: {(sucessos/total)*100:.1f}%")

        # Salvar resumo completo
        resumo = {
            "timestamp": self.timestamp,
            "resultados": resultados,
            "taxa_sucesso": (sucessos / total) * 100 if total > 0 else 0,
            "arquivo_testado": "rpa_sienge/rpa_sienge.py"
        }

        await self._salvar_resultado("integracao_completa", resumo)

        return sucessos == total

    async def _salvar_resultado(self, nome_teste: str, dados: Any):
        """Salva resultado do teste"""
        try:
            arquivo = self.pasta_resultados / f"{nome_teste}_{self.timestamp}.json"

            dados_salvamento = {
                "nome_teste": nome_teste,
                "timestamp": datetime.now().isoformat(),
                "arquivo_testado": "rpa_sienge/rpa_sienge.py",
                "dados": dados
            }

            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_salvamento, f, indent=2, ensure_ascii=False, default=str)

            self.log(f"💾 Resultado salvo: {arquivo.name}")

        except Exception as e:
            self.log(f"❌ Erro ao salvar: {str(e)}", "ERROR")


async def menu_principal():
    """Menu principal para execução dos testes"""
    testador = TestadorRPASiengeReal()

    opcoes = {
        "1": ("🔥 Teste Integração Completa", testador.teste_integracao_completa),
        "2": ("📊 Teste Carregamento Fila Real", testador.teste_carregamento_fila_real),
        "3": ("🔍 Teste Consulta Relatórios", testador.teste_etapa_consulta),
        "4": ("🌐 Teste Webscraping Completo", testador.teste_execucao_webscraping),
        "0": ("❌ Sair", None)
    }

    print("\n" + "=" * 60)
    print("🧪 TESTES RPA SIENGE - IMPLEMENTAÇÃO REAL")
    print("Focado exclusivamente no rpa_sienge.py já desenvolvido")
    print("=" * 60)

    for key, (descricao, _) in opcoes.items():
        print(f"{key}. {descricao}")
    print("=" * 60)

    while True:
        try:
            escolha = input("\n➤ Escolha (0-4): ").strip()

            if escolha == "0":
                print("👋 Encerrando...")
                break
            elif escolha in opcoes and opcoes[escolha][1]:
                nome_teste = opcoes[escolha][0]
                print(f"\n🔄 Executando: {nome_teste}")
                print("-" * 50)

                inicio = datetime.now()
                sucesso = await opcoes[escolha][1]()
                fim = datetime.now()

                tempo = (fim - inicio).total_seconds()
                resultado = "✅ SUCESSO" if sucesso else "❌ FALHA"

                print("-" * 50)
                print(f"{resultado} em {tempo:.1f}s")

                input("\n⏳ Pressione ENTER para continuar...")

                # Reexibir menu
                print("\n" + "=" * 60)
                for key, (descricao, _) in opcoes.items():
                    print(f"{key}. {descricao}")
                print("=" * 60)
            else:
                print("❌ Opção inválida!")

        except KeyboardInterrupt:
            print("\n👋 Interrompido pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro: {str(e)}")


if __name__ == "__main__":
    print("🚀 SISTEMA DE TESTES RPA SIENGE")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("🎯 Testando rpa_sienge.py real e funcional")

    try:
        asyncio.run(menu_principal())
    except KeyboardInterrupt:
        print("\n👋 Sistema encerrado.")
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        traceback.print_exc()