
"""
Teste Workflow RPA Sienge
Testa workflow completo com os 3 cenários principais do PDD

Desenvolvido em Português Brasileiro
Separado da lógica de produção
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Adiciona o diretório pai ao path
sys.path.append(str(Path(__file__).parent.parent))

from rpa_sienge.simulador_sienge import executar_simulacao_sienge


class TesteWorkflowSienge:
    """
    Testa workflow completo do RPA Sienge com 3 cenários principais
    """

    def __init__(self):
        self.resultados = []

    def criar_cenarios_teste(self) -> List[Dict[str, Any]]:
        """Cria os 3 cenários principais de teste"""
        timestamp = datetime.now().strftime("%m%d")
        
        return [
            # Cenário 1: Cliente Adimplente (DEVE reparcelar)
            {
                "nome": "Cliente Adimplente",
                "contrato": {
                    "numero_titulo": f"PDDADIMPLENTE{timestamp}",
                    "cliente": "CLIENTE TESTE ADIMPLENTE LTDA",
                    "empreendimento": "TESTE ADIMPLENTE",
                    "cnpj_unidade": "12.345.678/0001-01"
                },
                "esperado": True,
                "descricao": "Cliente sem parcelas CT vencidas"
            },
            
            # Cenário 2: Cliente Inadimplente (NÃO DEVE reparcelar)
            {
                "nome": "Cliente Inadimplente", 
                "contrato": {
                    "numero_titulo": f"PDDINADIMPLENTE{timestamp}",
                    "cliente": "CLIENTE TESTE INADIMPLENTE LTDA",
                    "empreendimento": "TESTE INADIMPLENTE",
                    "cnpj_unidade": "12.345.678/0001-02"
                },
                "esperado": False,
                "descricao": "Cliente com 3+ parcelas CT vencidas"
            },
            
            # Cenário 3: Cliente Limite (DEVE reparcelar)
            {
                "nome": "Cliente Limite",
                "contrato": {
                    "numero_titulo": f"PDDLIMITE{timestamp}",
                    "cliente": "CLIENTE TESTE LIMITE LTDA", 
                    "empreendimento": "TESTE LIMITE",
                    "cnpj_unidade": "12.345.678/0001-03"
                },
                "esperado": True,
                "descricao": "Cliente com 2 parcelas CT vencidas (< 3)"
            }
        ]

    def criar_indices_teste(self) -> Dict[str, Any]:
        """Cria índices econômicos para teste"""
        return {
            "ipca": {
                "valor": 4.62,
                "tipo": "IPCA",
                "periodo": "Dezembro/2024"
            },
            "igpm": {
                "valor": 3.89,
                "tipo": "IGP-M",
                "periodo": "Dezembro/2024"
            }
        }

    def criar_credenciais_teste(self) -> Dict[str, str]:
        """Cria credenciais de teste"""
        return {
            "url": "https://sienge-teste.com",
            "usuario": "usuario_teste",
            "senha": "senha_teste",
            "empresa": "EMPRESA TESTE"
        }

    async def executar_cenario(
        self,
        cenario: Dict[str, Any],
        indices: Dict[str, Any],
        credenciais: Dict[str, str]
    ) -> Dict[str, Any]:
        """Executa um cenário específico"""
        
        print(f"\n🧪 TESTANDO CENÁRIO: {cenario['nome']}")
        print("-" * 50)
        print(f"📋 Contrato: {cenario['contrato']['numero_titulo']}")
        print(f"👤 Cliente: {cenario['contrato']['cliente']}")
        print(f"📝 Descrição: {cenario['descricao']}")
        print(f"📊 Resultado esperado: {'✅ DEVE reparcelar' if cenario['esperado'] else '❌ NÃO deve reparcelar'}")

        try:
            # Executa simulação
            resultado = await executar_simulacao_sienge(
                contrato=cenario["contrato"],
                indices_economicos=indices,
                credenciais_sienge=credenciais
            )

            # Verifica se resultado está conforme esperado
            sucesso_obtido = resultado.sucesso
            sucesso_esperado = cenario["esperado"]
            
            teste_passou = sucesso_obtido == sucesso_esperado

            # Monta resultado do teste
            resultado_teste = {
                "cenario": cenario["nome"],
                "contrato": cenario["contrato"]["numero_titulo"],
                "esperado": sucesso_esperado,
                "obtido": sucesso_obtido,
                "teste_passou": teste_passou,
                "resultado_rpa": resultado.dados if resultado.sucesso else None,
                "erro_rpa": resultado.erro if not resultado.sucesso else None,
                "mensagem": resultado.mensagem,
                "timestamp": datetime.now().isoformat()
            }

            # Log do resultado
            if teste_passou:
                print("✅ TESTE PASSOU - Comportamento conforme esperado")
                if resultado.sucesso:
                    dados_reparcelamento = resultado.dados.get("reparcelamento", {})
                    detalhes = dados_reparcelamento.get("detalhes_reparcelamento", {})
                    print(f"   📋 Novo título: {dados_reparcelamento.get('novo_titulo_gerado', 'N/A')}")
                    print(f"   💰 Novo saldo: R$ {detalhes.get('valor_total', 0):,.2f}")
                    print(f"   📈 Índice IGP-M: {detalhes.get('indice_aplicado', 0)}%")
                else:
                    print(f"   📋 Motivo bloqueio: {resultado.mensagem}")
            else:
                print("❌ TESTE FALHOU - Comportamento inesperado")
                print(f"   📊 Esperado: {sucesso_esperado}, Obtido: {sucesso_obtido}")

            return resultado_teste

        except Exception as e:
            print(f"💥 ERRO NO TESTE: {str(e)}")
            return {
                "cenario": cenario["nome"],
                "contrato": cenario["contrato"]["numero_titulo"],
                "esperado": cenario["esperado"],
                "obtido": None,
                "teste_passou": False,
                "erro_teste": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def executar_workflow_completo(self) -> Dict[str, Any]:
        """Executa workflow completo com os 3 cenários"""
        
        print("🎯 TESTE WORKFLOW COMPLETO - RPA SIENGE")
        print("=" * 60)
        print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("📝 Testando 3 cenários principais do PDD")
        print("=" * 60)

        # Preparar dados
        cenarios = self.criar_cenarios_teste()
        indices = self.criar_indices_teste()
        credenciais = self.criar_credenciais_teste()

        print(f"🔧 Configuração:")
        print(f"   📈 IPCA: {indices['ipca']['valor']}%")
        print(f"   📈 IGP-M: {indices['igpm']['valor']}%")
        print(f"   🏢 URL: {credenciais['url']}")

        # Executar todos os cenários
        for cenario in cenarios:
            resultado_cenario = await self.executar_cenario(cenario, indices, credenciais)
            self.resultados.append(resultado_cenario)

        # Resumo final
        print("\n📊 RESUMO DO WORKFLOW")
        print("=" * 40)

        testes_passaram = 0
        total_testes = len(self.resultados)

        for resultado in self.resultados:
            status = "✅ PASSOU" if resultado["teste_passou"] else "❌ FALHOU"
            nome = resultado["cenario"]
            print(f"{nome:20} {status}")
            
            if resultado["teste_passou"]:
                testes_passaram += 1

        print(f"\n🎯 RESULTADO FINAL: {testes_passaram}/{total_testes} testes passaram")

        if testes_passaram == total_testes:
            print("🎉 WORKFLOW COMPLETO - TODOS OS TESTES PASSARAM!")
            resultado_final = True
        else:
            print("⚠️ WORKFLOW COM FALHAS - Verificar cenários que falharam")
            resultado_final = False

        # Monta resultado completo
        return {
            "sucesso": resultado_final,
            "total_cenarios": total_testes,
            "cenarios_passaram": testes_passaram,
            "cenarios_falharam": total_testes - testes_passaram,
            "detalhes_cenarios": self.resultados,
            "timestamp_execucao": datetime.now().isoformat(),
            "duracao_estimada": "~15 segundos (simulado)"
        }

    async def executar_cenario_isolado(self, nome_cenario: str) -> Dict[str, Any]:
        """Executa apenas um cenário específico"""
        cenarios = self.criar_cenarios_teste()
        indices = self.criar_indices_teste()
        credenciais = self.criar_credenciais_teste()

        # Busca cenário específico
        cenario_encontrado = None
        for cenario in cenarios:
            if nome_cenario.lower() in cenario["nome"].lower():
                cenario_encontrado = cenario
                break

        if not cenario_encontrado:
            print(f"❌ Cenário '{nome_cenario}' não encontrado")
            print("Cenários disponíveis:")
            for cenario in cenarios:
                print(f"  - {cenario['nome']}")
            return {"sucesso": False, "erro": "Cenário não encontrado"}

        # Executa cenário
        resultado = await self.executar_cenario(cenario_encontrado, indices, credenciais)
        return {"sucesso": resultado["teste_passou"], "resultado": resultado}


async def main():
    """Função principal do teste"""
    
    print("🤖 TESTE WORKFLOW RPA SIENGE")
    print("Teste completo com 3 cenários principais")
    print("Desenvolvido em Python")
    print()

    teste = TesteWorkflowSienge()

    # Verifica argumentos
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando in ["adimplente", "inadimplente", "limite"]:
            resultado = await teste.executar_cenario_isolado(comando)
            return resultado["sucesso"]
        elif comando in ["completo", "all", "workflow"]:
            resultado = await teste.executar_workflow_completo()
            return resultado["sucesso"]
        else:
            print(f"❌ Comando inválido: {comando}")
            print("Comandos disponíveis:")
            print("  - adimplente: Testa apenas cenário adimplente")
            print("  - inadimplente: Testa apenas cenário inadimplente") 
            print("  - limite: Testa apenas cenário limite")
            print("  - completo: Executa workflow completo")
            return False
    else:
        # Execução completa por padrão
        resultado = await teste.executar_workflow_completo()
        return resultado["sucesso"]


if __name__ == "__main__":
    # Configurar event loop
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        resultado = asyncio.run(main())
        sys.exit(0 if resultado else 1)
    except KeyboardInterrupt:
        print("\n👋 Teste cancelado pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro fatal: {str(e)}")
        sys.exit(1)
