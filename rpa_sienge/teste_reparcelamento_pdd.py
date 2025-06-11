
#!/usr/bin/env python3
"""
Teste Específico - Reparcelamento Sienge PDD
Testa especificamente o processamento de reparcelamento conforme regras do PDD

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, date
import json

# Adiciona o diretório pai ao path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from rpa_sienge.simulador_sienge import executar_simulacao_sienge
except ImportError:
    from simulador_sienge import executar_simulacao_sienge


class TesteReparcelamentoPDD:
    """
    Classe para testar reparcelamento seguindo rigorosamente as regras do PDD
    """
    
    def __init__(self):
        self.rpa = None
        
    def criar_credenciais_teste(self):
        """Cria credenciais de teste"""
        return {
            "url": "https://sienge-teste.com",
            "usuario": "usuario_teste", 
            "senha": "senha_teste"
        }

    def criar_contrato_teste(self, tipo_contrato: str = "adimplente") -> dict:
        """
        Cria contrato de teste conforme tipo especificado
        
        Args:
            tipo_contrato: 'adimplente', 'inadimplente', 'limite', 'custas', 'misto'
        """
        base_contrato = {
            "numero_titulo": f"PDD{tipo_contrato.upper()}{datetime.now().strftime('%m%d')}",
            "cliente": f"CLIENTE TESTE {tipo_contrato.upper()}",
            "empreendimento": "EMPREENDIMENTO TESTE PDD",
            "cnpj_unidade": "12.345.678/0001-90",
            "indexador": "IPCA",
            "ultimo_reajuste": "01/01/2023"
        }
        
        return base_contrato

    def criar_dados_financeiros_teste(self, tipo_cenario: str = "adimplente") -> dict:
        """
        Cria dados financeiros de teste para diferentes cenários
        
        Args:
            tipo_cenario: Tipo do cenário conforme PDD
        """
        data_atual = date.today()
        
        cenarios = {
            "adimplente": {
                "cliente": "CLIENTE ADIMPLENTE TESTE",
                "numero_titulo": "PDD001",
                "saldo_total": 150000.00,
                "total_parcelas": 60,
                "parcelas_pendentes": 48,
                "parcelas_vencidas": [],
                "parcelas_ct_vencidas": [],
                "parcelas_rec_fat": [],
                "status_cliente": "adimplente",
                "pode_reparcelar": True,
                "motivo_validacao": "Cliente apto para reparcelamento - sem pendências CT"
            },
            
            "inadimplente": {
                "cliente": "CLIENTE INADIMPLENTE TESTE",
                "numero_titulo": "PDD002",
                "saldo_total": 100000.00,
                "total_parcelas": 60,
                "parcelas_pendentes": 40,
                "parcelas_vencidas": [
                    {"numero_parcela": "001", "data_vencimento": date(2024, 10, 15), "valor": 2500.00, "tipo_documento": "CT"},
                    {"numero_parcela": "002", "data_vencimento": date(2024, 11, 15), "valor": 2500.00, "tipo_documento": "CT"},
                    {"numero_parcela": "003", "data_vencimento": date(2024, 12, 15), "valor": 2500.00, "tipo_documento": "CT"},
                ],
                "parcelas_ct_vencidas": [
                    {"numero_parcela": "001", "data_vencimento": date(2024, 10, 15), "valor": 2500.00, "tipo_documento": "CT"},
                    {"numero_parcela": "002", "data_vencimento": date(2024, 11, 15), "valor": 2500.00, "tipo_documento": "CT"},
                    {"numero_parcela": "003", "data_vencimento": date(2024, 12, 15), "valor": 2500.00, "tipo_documento": "CT"},
                ],
                "parcelas_rec_fat": [],
                "status_cliente": "inadimplente",
                "pode_reparcelar": False,
                "motivo_validacao": "Cliente inadimplente - 3 parcelas CT vencidas"
            },
            
            "limite": {
                "cliente": "CLIENTE LIMITE TESTE",
                "numero_titulo": "PDD003",
                "saldo_total": 120000.00,
                "total_parcelas": 50,
                "parcelas_pendentes": 42,
                "parcelas_vencidas": [
                    {"numero_parcela": "001", "data_vencimento": date(2024, 11, 15), "valor": 2400.00, "tipo_documento": "CT"},
                    {"numero_parcela": "002", "data_vencimento": date(2024, 12, 15), "valor": 2400.00, "tipo_documento": "CT"},
                ],
                "parcelas_ct_vencidas": [
                    {"numero_parcela": "001", "data_vencimento": date(2024, 11, 15), "valor": 2400.00, "tipo_documento": "CT"},
                    {"numero_parcela": "002", "data_vencimento": date(2024, 12, 15), "valor": 2400.00, "tipo_documento": "CT"},
                ],
                "parcelas_rec_fat": [],
                "status_cliente": "adimplente",  # Limite ainda é adimplente
                "pode_reparcelar": True,
                "motivo_validacao": "Cliente apto - apenas 2 parcelas CT (< 3)"
            },
            
            "custas": {
                "cliente": "CLIENTE CUSTAS TESTE",
                "numero_titulo": "PDD004",
                "saldo_total": 90000.00,
                "total_parcelas": 45,
                "parcelas_pendentes": 40,
                "parcelas_vencidas": [
                    {"numero_parcela": "REC001", "data_vencimento": date(2024, 10, 15), "valor": 1500.00, "tipo_documento": "REC"},
                    {"numero_parcela": "FAT001", "data_vencimento": date(2024, 11, 15), "valor": 2000.00, "tipo_documento": "FAT"},
                ],
                "parcelas_ct_vencidas": [],
                "parcelas_rec_fat": [
                    {"numero_parcela": "REC001", "data_vencimento": date(2024, 10, 15), "valor": 1500.00, "tipo_documento": "REC"},
                    {"numero_parcela": "FAT001", "data_vencimento": date(2024, 11, 15), "valor": 2000.00, "tipo_documento": "FAT"},
                ],
                "status_cliente": "pendencias_custas",
                "pode_reparcelar": True,
                "motivo_validacao": "Cliente com 2 pendências de custas/honorários"
            }
        }
        
        return cenarios.get(tipo_cenario, cenarios["adimplente"])

    def criar_indices_teste(self) -> dict:
        """Cria índices econômicos de teste"""
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

    async def teste_cenario_adimplente(self):
        """
        Testa cenário cliente adimplente - DEVE PODER reparcelar
        """
        print("\n🧪 TESTE CENÁRIO: Cliente Adimplente")
        print("-" * 50)
        
        try:
            # Preparar dados de teste
            contrato = self.criar_contrato_teste("adimplente")
            dados_financeiros = self.criar_dados_financeiros_teste("adimplente")
            indices = self.criar_indices_teste()
            
            print(f"📋 Contrato: {contrato['numero_titulo']}")
            print(f"👤 Cliente: {contrato['cliente']}")
            print(f"💰 Saldo: R$ {dados_financeiros['saldo_total']:,.2f}")
            print(f"📊 Parcelas pendentes: {dados_financeiros['parcelas_pendentes']}")
            print(f"⚠️ Parcelas CT vencidas: {len(dados_financeiros['parcelas_ct_vencidas'])}")
            
            # Executar processamento
            resultado = await self.rpa._processar_reparcelamento(
                contrato, indices, dados_financeiros
            )
            
            # Verificar resultado
            if resultado["sucesso"]:
                print("✅ TESTE PASSOU - Cliente adimplente processado com sucesso")
                print(f"   📋 Novo título: {resultado.get('novo_titulo_gerado', 'N/A')}")
                
                detalhes = resultado.get("detalhes_reparcelamento", {})
                print(f"   💰 Novo saldo: R$ {detalhes.get('valor_total', 0):,.2f}")
                print(f"   📈 Índice aplicado: {detalhes.get('indice_aplicado', 0)}%")
                print(f"   📊 Parcelas: {detalhes.get('quantidade_parcelas', 0)}")
                print(f"   📅 1º vencimento: {detalhes.get('data_primeiro_vencimento', 'N/A')}")
                print(f"   ⚙️ Configuração: {detalhes.get('tipo_condicao', 'N/A')}, {detalhes.get('indexador', 'N/A')}, {detalhes.get('tipo_juros', 'N/A')} {detalhes.get('percentual_juros', 0)}%")
                return True
            else:
                print(f"❌ TESTE FALHOU - Erro: {resultado.get('erro', 'Desconhecido')}")
                return False
                
        except Exception as e:
            print(f"❌ ERRO NO TESTE: {str(e)}")
            return False

    async def teste_cenario_inadimplente(self):
        """
        Testa cenário cliente inadimplente - NÃO DEVE PODER reparcelar
        """
        print("\n🧪 TESTE CENÁRIO: Cliente Inadimplente")
        print("-" * 50)
        
        try:
            # Preparar dados de teste
            contrato = self.criar_contrato_teste("inadimplente")
            dados_financeiros = self.criar_dados_financeiros_teste("inadimplente")
            indices = self.criar_indices_teste()
            
            print(f"📋 Contrato: {contrato['numero_titulo']}")
            print(f"👤 Cliente: {contrato['cliente']}")
            print(f"💰 Saldo: R$ {dados_financeiros['saldo_total']:,.2f}")
            print(f"⚠️ Parcelas CT vencidas: {len(dados_financeiros['parcelas_ct_vencidas'])}")
            
            # Primeiro valida se não pode reparcelar
            validacao = await self.rpa._validar_contrato_reparcelamento(dados_financeiros)
            
            if not validacao["pode_reparcelar"]:
                print("✅ TESTE PASSOU - Cliente inadimplente bloqueado corretamente")
                print(f"   📋 Motivo: {validacao['motivo']}")
                return True
            else:
                print("❌ TESTE FALHOU - Cliente inadimplente não foi bloqueado")
                return False
                
        except Exception as e:
            print(f"❌ ERRO NO TESTE: {str(e)}")
            return False

    async def teste_cenario_limite(self):
        """
        Testa cenário cliente no limite - DEVE PODER reparcelar (2 CT < 3)
        """
        print("\n🧪 TESTE CENÁRIO: Cliente Limite (2 CT)")
        print("-" * 50)
        
        try:
            # Preparar dados de teste
            contrato = self.criar_contrato_teste("limite")
            dados_financeiros = self.criar_dados_financeiros_teste("limite")
            indices = self.criar_indices_teste()
            
            print(f"📋 Contrato: {contrato['numero_titulo']}")
            print(f"👤 Cliente: {contrato['cliente']}")
            print(f"⚠️ Parcelas CT vencidas: {len(dados_financeiros['parcelas_ct_vencidas'])} (limite: < 3)")
            
            # Executar processamento
            resultado = await self.rpa._processar_reparcelamento(
                contrato, indices, dados_financeiros
            )
            
            # Verificar resultado
            if resultado["sucesso"]:
                print("✅ TESTE PASSOU - Cliente no limite processado com sucesso")
                print(f"   📋 Regra aplicada: {len(dados_financeiros['parcelas_ct_vencidas'])} CT < 3 (permitido)")
                
                detalhes = resultado.get("detalhes_reparcelamento", {})
                print(f"   💰 Novo saldo: R$ {detalhes.get('valor_total', 0):,.2f}")
                return True
            else:
                print(f"❌ TESTE FALHOU - Erro: {resultado.get('erro', 'Desconhecido')}")
                return False
                
        except Exception as e:
            print(f"❌ ERRO NO TESTE: {str(e)}")
            return False

    async def teste_cenario_custas(self):
        """
        Testa cenário cliente com custas/honorários - DEVE PODER reparcelar
        """
        print("\n🧪 TESTE CENÁRIO: Cliente com Custas/Honorários")
        print("-" * 50)
        
        try:
            # Preparar dados de teste
            contrato = self.criar_contrato_teste("custas")
            dados_financeiros = self.criar_dados_financeiros_teste("custas")
            indices = self.criar_indices_teste()
            
            print(f"📋 Contrato: {contrato['numero_titulo']}")
            print(f"👤 Cliente: {contrato['cliente']}")
            print(f"💰 Saldo: R$ {dados_financeiros['saldo_total']:,.2f}")
            print(f"📋 Parcelas REC/FAT: {len(dados_financeiros['parcelas_rec_fat'])}")
            print(f"⚠️ Parcelas CT vencidas: {len(dados_financeiros['parcelas_ct_vencidas'])} (OK)")
            
            # Executar processamento
            resultado = await self.rpa._processar_reparcelamento(
                contrato, indices, dados_financeiros
            )
            
            # Verificar resultado
            if resultado["sucesso"]:
                print("✅ TESTE PASSOU - Cliente com custas processado com sucesso")
                print(f"   📋 Regra aplicada: REC/FAT não impede reparcelamento")
                return True
            else:
                print(f"❌ TESTE FALHOU - Erro: {resultado.get('erro', 'Desconhecido')}")
                return False
                
        except Exception as e:
            print(f"❌ ERRO NO TESTE: {str(e)}")
            return False

    async def teste_calculos_pdd(self):
        """
        Testa especificamente os cálculos conforme regras do PDD
        """
        print("\n🧪 TESTE CÁLCULOS PDD")
        print("-" * 50)
        
        try:
            # Dados de teste específicos para cálculo
            contrato = {
                "numero_titulo": "CALC001",
                "cliente": "TESTE CÁLCULOS",
                "indexador": "IPCA"  # Note: PDD sempre usa IGP-M
            }
            
            dados_financeiros = {
                "saldo_total": 100000.00,  # R$ 100.000,00
                "parcelas_pendentes": 48
            }
            
            indices = {
                "ipca": {"valor": 4.62},
                "igpm": {"valor": 3.89}
            }
            
            print(f"💰 Saldo base: R$ {dados_financeiros['saldo_total']:,.2f}")
            print(f"📊 Parcelas pendentes: {dados_financeiros['parcelas_pendentes']}")
            print(f"📈 IPCA: {indices['ipca']['valor']}%")
            print(f"📈 IGP-M: {indices['igpm']['valor']}%")
            
            # Testa cálculo dos detalhes
            detalhes = await self.rpa._calcular_detalhes_reparcelamento_simulado(
                contrato, indices, dados_financeiros
            )
            
            # Verificações PDD
            testes_passaram = True
            
            # 1. Deve sempre usar IGP-M (não IPCA do contrato)
            if detalhes.get("indexador") != "IGP-M":
                print("❌ ERRO: Não está usando IGP-M (obrigatório PDD)")
                testes_passaram = False
            else:
                print("✅ IGP-M aplicado corretamente")
            
            # 2. Tipo condição deve ser PM
            if detalhes.get("tipo_condicao") != "PM":
                print("❌ ERRO: Tipo condição não é PM")
                testes_passaram = False
            else:
                print("✅ Tipo condição PM correto")
            
            # 3. Juros deve ser Fixo 8%
            if detalhes.get("tipo_juros") != "Fixo" or detalhes.get("percentual_juros") != 8.0:
                print("❌ ERRO: Juros não é Fixo 8%")
                testes_passaram = False
            else:
                print("✅ Juros Fixo 8% correto")
            
            # 4. Cálculo do novo saldo
            saldo_esperado = 100000.00 * (1 + 3.89/100)  # IGP-M
            saldo_calculado = detalhes.get("valor_total", 0)
            
            if abs(saldo_calculado - saldo_esperado) > 0.01:
                print(f"❌ ERRO: Cálculo saldo incorreto. Esperado: {saldo_esperado:,.2f}, Calculado: {saldo_calculado:,.2f}")
                testes_passaram = False
            else:
                print(f"✅ Cálculo saldo correto: R$ {saldo_calculado:,.2f}")
            
            # 5. Data primeiro vencimento
            data_venc = detalhes.get("data_primeiro_vencimento", "")
            if not data_venc or "/" not in data_venc:
                print("❌ ERRO: Data primeiro vencimento inválida")
                testes_passaram = False
            else:
                print(f"✅ Data primeiro vencimento: {data_venc}")
            
            return testes_passaram
            
        except Exception as e:
            print(f"❌ ERRO NO TESTE DE CÁLCULOS: {str(e)}")
            return False

    async def executar_suite_completa(self):
        """
        Executa todos os testes de reparcelamento PDD
        """
        print("🧪 SUITE COMPLETA DE TESTES - REPARCELAMENTO PDD")
        print("=" * 60)
        print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 60)
        
        # Inicializar RPA
        await self.inicializar()
        
        try:
            resultados = []
            
            # Executar todos os testes
            print("🎯 EXECUTANDO TESTES CONFORME REGRAS DO PDD...")
            
            # Teste 1: Cliente Adimplente
            resultado1 = await self.teste_cenario_adimplente()
            resultados.append(("Adimplente", resultado1))
            
            # Teste 2: Cliente Inadimplente 
            resultado2 = await self.teste_cenario_inadimplente()
            resultados.append(("Inadimplente", resultado2))
            
            # Teste 3: Cliente Limite
            resultado3 = await self.teste_cenario_limite()
            resultados.append(("Limite", resultado3))
            
            # Teste 4: Cliente com Custas
            resultado4 = await self.teste_cenario_custas()
            resultados.append(("Custas", resultado4))
            
            # Teste 5: Cálculos PDD
            resultado5 = await self.teste_calculos_pdd()
            resultados.append(("Cálculos PDD", resultado5))
            
            # Resumo final
            print("\n📊 RESUMO DOS TESTES")
            print("=" * 40)
            
            sucessos = 0
            for nome, passou in resultados:
                status = "✅ PASSOU" if passou else "❌ FALHOU"
                print(f"{nome:20} {status}")
                if passou:
                    sucessos += 1
            
            print(f"\n🎯 RESULTADO FINAL: {sucessos}/{len(resultados)} testes passaram")
            
            if sucessos == len(resultados):
                print("🎉 TODOS OS TESTES PASSARAM - RPA SIENGE CONFORME PDD!")
                return True
            else:
                print("⚠️ ALGUNS TESTES FALHARAM - Verificar implementação")
                return False
                
        finally:
            # Finalizar RPA
            await self.finalizar()


async def main():
    """Função principal do teste"""
    
    print("🤖 TESTE REPARCELAMENTO SIENGE - REGRAS PDD")
    print("Desenvolvido em Python")
    print("Testa processamento de reparcelamento conforme documento PDD")
    print()
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        teste = TesteReparcelamentoPDD()
        
        if comando == "adimplente":
            await teste.inicializar()
            resultado = await teste.teste_cenario_adimplente()
            await teste.finalizar()
        elif comando == "inadimplente":
            await teste.inicializar()
            resultado = await teste.teste_cenario_inadimplente()
            await teste.finalizar()
        elif comando == "limite":
            await teste.inicializar()
            resultado = await teste.teste_cenario_limite()
            await teste.finalizar()
        elif comando == "custas":
            await teste.inicializar()
            resultado = await teste.teste_cenario_custas()
            await teste.finalizar()
        elif comando == "calculos":
            await teste.inicializar()
            resultado = await teste.teste_calculos_pdd()
            await teste.finalizar()
        elif comando == "completo" or comando == "all":
            teste = TesteReparcelamentoPDD()
            resultado = await teste.executar_suite_completa()
        else:
            print(f"❌ Comando inválido: {comando}")
            print("Comandos disponíveis: adimplente, inadimplente, limite, custas, calculos, completo")
            return False
            
        return resultado
    else:
        # Execução completa por padrão
        teste = TesteReparcelamentoPDD()
        return await teste.executar_suite_completa()


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
