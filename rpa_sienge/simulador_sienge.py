
"""
Simulador RPA Sienge
Simula comportamento do RPA Sienge para testes e desenvolvimento

Desenvolvido em Português Brasileiro
Separado do código de produção para evitar confusão
"""

import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any
from core.base_rpa import ResultadoRPA


class SimuladorSienge:
    """
    Simulador do RPA Sienge para testes e desenvolvimento
    Replica exatamente as regras do PDD sem acessar o sistema real
    """

    def __init__(self):
        self.pasta_exemplos = Path(__file__).parent / "planilhas_exemplo"

    async def executar_simulacao(
        self,
        contrato: Dict[str, Any],
        credenciais_sienge: Dict[str, str],
        indices: Dict[str, Any] = None
    ) -> ResultadoRPA:
        """
        Executa simulação completa do processamento Sienge
        """
        try:
            print(f"🧪 SIMULAÇÃO SIENGE - Contrato: {contrato.get('numero_titulo', '')}")

            # Simula login
            await self._simular_login(credenciais_sienge)

            # Simula consulta de relatórios
            dados_financeiros = await self._simular_consulta_relatorios(contrato)

            # Valida contrato
            pode_reparcelar = await self._validar_contrato_simulado(dados_financeiros)

            if not pode_reparcelar["pode_reparcelar"]:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=f"Contrato não pode ser reparcelado: {pode_reparcelar['motivo']}",
                    dados={
                        "contrato": contrato,
                        "validacao": pode_reparcelar,
                        "dados_financeiros": dados_financeiros
                    }
                )

            # Simula processamento
            resultado_reparcelamento = await self._simular_processamento(contrato, indices, dados_financeiros)

            # Simula geração de carnê
            carne_gerado = await self._simular_geracao_carne(contrato)

            # Monta resultado
            resultado_dados = {
                "contrato_processado": contrato,
                "dados_financeiros": dados_financeiros,
                "reparcelamento": resultado_reparcelamento,
                "carne_gerado": carne_gerado,
                "timestamp_processamento": datetime.now().isoformat(),
                "tipo_execucao": "simulado"
            }

            return ResultadoRPA(
                sucesso=resultado_reparcelamento["sucesso"],
                mensagem=f"SIMULAÇÃO - Reparcelamento processado - Cliente: {contrato.get('cliente', '')}",
                dados=resultado_dados
            )

        except Exception as e:
            return ResultadoRPA(
                sucesso=False,
                mensagem="Falha na simulação Sienge",
                erro=str(e)
            )

    async def _simular_login(self, credenciais: Dict[str, str]):
        """Simula login no Sienge"""
        print(f"🔐 SIMULAÇÃO - Login Sienge: {credenciais.get('url', '')}")
        await asyncio.sleep(0.5)
        print("✅ Login simulado realizado")

    async def _simular_consulta_relatorios(self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """Simula consulta de relatórios usando planilhas exemplo"""
        try:
            numero_titulo = contrato.get("numero_titulo", "")
            print(f"📊 SIMULAÇÃO - Consultando relatórios para: {numero_titulo}")

            # Mapeia títulos para arquivos
            mapeamento_arquivos = {
                "PDDADIMPLENTE": "saldo_devedor_adimplente.xlsx",
                "PDDINADIMPLENTE": "saldo_devedor_inadimplente.xlsx",
                "PDDLIMITE": "saldo_devedor_limite_inadimplencia.xlsx",
                "PDDCUSTAS": "saldo_devedor_custas_honorarios.xlsx",
                "PDD001": "saldo_devedor_adimplente.xlsx",
                "PDD002": "saldo_devedor_inadimplente.xlsx",
                "PDD003": "saldo_devedor_limite_inadimplencia.xlsx",
                "PDD004": "saldo_devedor_custas_honorarios.xlsx",
                "PDD005": "saldo_devedor_situacao_mista.xlsx"
            }

            # Determina arquivo baseado no título
            arquivo = None
            for titulo_key, arquivo_nome in mapeamento_arquivos.items():
                if titulo_key in numero_titulo:
                    arquivo = self.pasta_exemplos / arquivo_nome
                    break

            # Se não encontrou correspondência, usa arquivo adimplente como padrão
            if not arquivo or not arquivo.exists():
                arquivo = self.pasta_exemplos / "saldo_devedor_adimplente.xlsx"

            if not arquivo.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")

            # Lê planilha Excel
            df = pd.read_excel(arquivo)

            # Processa dados conforme estrutura esperada
            dados_processados = self._processar_dados_planilha_simulado(df, contrato)

            print(f"✅ SIMULAÇÃO - Relatório consultado - {len(df)} registros")
            await asyncio.sleep(1.0)

            return dados_processados

        except Exception as e:
            print(f"❌ SIMULAÇÃO - Erro na consulta: {str(e)}")
            return {"erro": str(e), "sucesso": False}

    def _processar_dados_planilha_simulado(self, df: pd.DataFrame, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados da planilha conforme regras do PDD"""
        try:
            # Calcula saldo total
            saldo_total = df['Saldo'].sum() if 'Saldo' in df.columns else 0.0

            # Identifica parcelas vencidas
            data_atual = date.today()
            parcelas_vencidas = []
            parcelas_ct_vencidas = []
            parcelas_rec_fat = []

            for _, row in df.iterrows():
                data_venc_str = str(row.get('Data de vencimento', ''))
                tipo_documento = str(row.get('Tipo documento', ''))

                try:
                    if '/' in data_venc_str:
                        data_venc = datetime.strptime(data_venc_str, '%d/%m/%Y').date()
                    else:
                        continue
                except:
                    continue

                if data_venc < data_atual:
                    parcela_info = {
                        "numero_parcela": str(row.get('Número da parcela', '')),
                        "data_vencimento": data_venc,
                        "valor": float(row.get('Saldo', 0)),
                        "tipo_documento": tipo_documento
                    }

                    parcelas_vencidas.append(parcela_info)

                    if tipo_documento == "CT":
                        parcelas_ct_vencidas.append(parcela_info)
                    elif tipo_documento in ["REC", "FAT"]:
                        parcelas_rec_fat.append(parcela_info)

            # Determina status do cliente
            qtd_ct_vencidas = len(parcelas_ct_vencidas)

            if qtd_ct_vencidas >= 3:
                status_cliente = "inadimplente"
            elif qtd_ct_vencidas > 0 or len(parcelas_rec_fat) > 0:
                status_cliente = "pendencias"
            else:
                status_cliente = "adimplente"

            total_parcelas = len(df)
            parcelas_pendentes = total_parcelas - len(parcelas_vencidas)

            return {
                "sucesso": True,
                "cliente": contrato.get("cliente", ""),
                "numero_titulo": contrato.get("numero_titulo", ""),
                "saldo_total": saldo_total,
                "total_parcelas": total_parcelas,
                "parcelas_pendentes": parcelas_pendentes,
                "parcelas_vencidas": parcelas_vencidas,
                "parcelas_ct_vencidas": parcelas_ct_vencidas,
                "parcelas_rec_fat": parcelas_rec_fat,
                "status_cliente": status_cliente,
                "data_consulta": data_atual.isoformat()
            }

        except Exception as e:
            return {"erro": str(e), "sucesso": False}

    async def _validar_contrato_simulado(self, dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
        """Valida contrato conforme regras PDD"""
        try:
            if not dados_financeiros.get("sucesso", False):
                return {
                    "pode_reparcelar": False,
                    "motivo": "Erro na consulta de dados financeiros",
                    "status": "erro"
                }

            parcelas_ct_vencidas = dados_financeiros.get("parcelas_ct_vencidas", [])
            qtd_ct_vencidas = len(parcelas_ct_vencidas)

            # Regra principal do PDD
            if qtd_ct_vencidas >= 3:
                pode_reparcelar = False
                motivo = f"Cliente inadimplente - {qtd_ct_vencidas} parcelas CT vencidas (>= 3)"
                status = "inadimplente"
            else:
                pode_reparcelar = True
                motivo = f"Cliente apto para reparcelamento - {qtd_ct_vencidas} parcelas CT vencidas (< 3)"
                status = "apto"

            parcelas_rec_fat = dados_financeiros.get("parcelas_rec_fat", [])
            if len(parcelas_rec_fat) > 0 and pode_reparcelar:
                motivo += f" + {len(parcelas_rec_fat)} pendências REC/FAT (não impedem)"

            return {
                "pode_reparcelar": pode_reparcelar,
                "motivo": motivo,
                "status": status,
                "detalhes": {
                    "qtd_ct_vencidas": qtd_ct_vencidas,
                    "qtd_rec_fat": len(parcelas_rec_fat),
                    "cliente": dados_financeiros.get("cliente", ""),
                    "saldo_total": dados_financeiros.get("saldo_total", 0)
                }
            }

        except Exception as e:
            return {
                "pode_reparcelar": False,
                "motivo": f"Erro na validação: {str(e)}",
                "status": "erro"
            }

    async def _simular_processamento(
        self,
        contrato: Dict[str, Any],
        indices: Dict[str, Any],
        dados_financeiros: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simula processamento de reparcelamento"""
        try:
            numero_titulo = contrato.get("numero_titulo", "")
            print(f"🔄 SIMULAÇÃO - Processando reparcelamento: {numero_titulo}")

            # Simula as 5 etapas do PDD
            print("🧭 Etapa 1: Navegação (SIMULADO)")
            await asyncio.sleep(0.5)

            print(f"🔍 Etapa 2: Consulta título {numero_titulo} (SIMULADO)")
            await asyncio.sleep(1.0)

            print("📋 Etapa 3: Seleção documentos (SIMULADO)")
            await asyncio.sleep(0.8)

            print("⚙️ Etapa 4: Configuração detalhes (SIMULADO)")
            detalhes = self._calcular_detalhes_simulado(contrato, indices, dados_financeiros)
            await asyncio.sleep(1.2)

            print("💾 Etapa 5: Confirmação (SIMULADO)")
            novo_titulo = f"NOVO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            await asyncio.sleep(0.8)

            return {
                "sucesso": True,
                "numero_titulo_original": numero_titulo,
                "novo_titulo_gerado": novo_titulo,
                "detalhes_reparcelamento": detalhes,
                "timestamp_processamento": datetime.now().isoformat(),
                "tipo_processamento": "simulado"
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "numero_titulo": numero_titulo,
                "tipo_processamento": "erro_simulado"
            }

    def _calcular_detalhes_simulado(
        self,
        contrato: Dict[str, Any],
        indices: Dict[str, Any],
        dados_financeiros: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula detalhes conforme PDD"""
        try:
            saldo_atual = dados_financeiros.get("saldo_total", 0.0)
            parcelas_pendentes = dados_financeiros.get("parcelas_pendentes", 1)

            # SEMPRE usar IGP-M conforme PDD
            indices = indices or {}
            indice_igpm = indices.get("igpm", {}).get("valor", 3.89)

            # Cálculo
            fator_correcao = (1 + indice_igpm / 100)
            novo_saldo = saldo_atual * fator_correcao

            # Data primeiro vencimento (próximo mês, dia 15)
            hoje = date.today()
            if hoje.month == 12:
                data_primeiro_vencimento = date(hoje.year + 1, 1, 15)
            else:
                data_primeiro_vencimento = date(hoje.year, hoje.month + 1, 15)

            return {
                "detalhamento": f"CORREÇÃO {datetime.now().strftime('%m/%y')}",
                "tipo_condicao": "PM",
                "valor_total": novo_saldo,
                "quantidade_parcelas": parcelas_pendentes,
                "data_primeiro_vencimento": data_primeiro_vencimento.strftime("%d/%m/%Y"),
                "indexador": "IGP-M",
                "tipo_juros": "Fixo",
                "percentual_juros": 8.0,
                "indice_aplicado": indice_igpm,
                "fator_correcao": fator_correcao,
                "saldo_anterior": saldo_atual
            }

        except Exception as e:
            return {
                "erro": str(e),
                "tipo_condicao": "PM",
                "indexador": "IGP-M",
                "tipo_juros": "Fixo",
                "percentual_juros": 8.0
            }

    async def _simular_geracao_carne(self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """Simula geração de carnê"""
        print("🎯 SIMULAÇÃO - Gerando carnê...")
        await asyncio.sleep(1.0)

        nome_arquivo = f"carne_{contrato.get('numero_titulo', 'TITULO')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        print(f"✅ SIMULAÇÃO - Carnê gerado: {nome_arquivo}")

        return {
            "sucesso": True,
            "arquivo_gerado": nome_arquivo,
            "tipo": "simulado",
            "timestamp": datetime.now().isoformat()
        }


# ========================
# FUNÇÃO DE EXECUÇÃO SIMULADA
# ========================

async def executar_simulacao_sienge(
    contrato: Dict[str, Any],
    indices_economicos: Dict[str, Any],
    credenciais_sienge: Dict[str, str]
) -> ResultadoRPA:
    """
    Função para executar simulação do RPA Sienge
    Usado para testes e desenvolvimento
    """
    simulador = SimuladorSienge()
    return await simulador.executar_simulacao(contrato, credenciais_sienge, indices_economicos)
