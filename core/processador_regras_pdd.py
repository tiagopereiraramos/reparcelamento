"""
PROCESSADOR REGRAS PDD - CENTRALIZADO
Implementação completa de todas as regras de negócio PDD para reparcelamento Sienge
Centralizado na pasta core para acesso por todos os RPAs

Desenvolvido em Português Brasileiro
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import logging


class ProcessadorRegrasNegocio:
    """
    Processador centralizado de todas as regras PDD para reparcelamento

    RESPONSABILIDADES:
    - Validação rigorosa de inadimplência (≥3 CT vencidas = INADIMPLENTE)
    - Implementação das 8 regras PDD seção 9.1.1
    - Cálculos financeiros de reparcelamento
    - Determinação de parcelas para desmarcar
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.limite_inadimplencia = 3  # REGRA CRÍTICA PDD

    def processar_dados_cliente_completo(self, df_planilha: pd.DataFrame, cliente: str,
                                         numero_titulo: str, dados_validacao_base: Optional[Dict[str, Any]] = None,
                                         data_limite_inadimplencia: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Processa todos os dados do cliente aplicando TODAS as regras PDD 9.1.1
        (Aderente ao input.md: extração e retroalimentação)
        """
        try:
            import unicodedata

            self.logger.info(f"🔍 [PDD] INÍCIO DO PROCESSAMENTO")
            self.logger.info(f"   - Cliente: {cliente}")
            self.logger.info(f"   - Título: {numero_titulo}")
            self.logger.info(
                f"   - Dados validação base: {list(dados_validacao_base.keys()) if dados_validacao_base else 'None'}")

            # Forçar output para aparecer nos logs
            import sys
            print(
                f"🔍 [PDD] INÍCIO DO PROCESSAMENTO - Cliente: {cliente}", flush=True)
            sys.stdout.flush()

            def norm(x):
                if pd.isna(x):
                    return ''
                return unicodedata.normalize('NFKD', str(x)).encode('ASCII', 'ignore').decode('ASCII').strip().upper()

            self.logger.info(
                f"🔍 [PDD] Processando extração fiel para cliente: {cliente} | título: {numero_titulo}")
            self.logger.info(
                f"🔍 [PDD] Colunas originais: {list(df_planilha.columns)}")

            # Renomear colunas para padrão PDD
            col_map = {norm(c): c for c in df_planilha.columns}

            def col(nome):
                return col_map.get(norm(nome), nome)
            # ✅ CORREÇÃO: Mapear colunas reais do relatório Sienge
            # Nomes reais das colunas do relatório Sienge:
            # Título, Parcela/Sequencial, Parcela/Condição, Cód. empresa, Empresa, Cód. centro de custo,
            # Centro de custo, Documento, Nº documento, Cód. cliente, Cliente, Status da parcela,
            # Tipo condição, Data vencimento, Valor original, Indexador, Correção monetária,
            # Juros contratuais, Valor atualizado, Taxa administrativa, Seguro, Valor corrigido,
            # Data base de juros, Juros %, Tipo de juros, Data base correção, Data correção,
            # Dias para desconto VP, Juros VP %, Valor presente, Valor desconto comercial,
            # Dias de atraso, Multa %, Juros de mora, Valor de acréscimo, Valor a receber,
            # Data da baixa, Valor da baixa, Recebimento líquido

            # Mapeamento das colunas reais para os nomes esperados pelo código
            mapeamento_colunas = {
                "TÍTULO": ["Título", "TITULO"],
                "STATUS DA PARCELA": ["Status da parcela", "STATUS DA PARCELA"],
                "DOCUMENTO": ["Documento", "DOCUMENTO"],
                "DATA VENCIMENTO": ["Data vencimento", "DATA VENCIMENTO"],
                "VALOR ORIGINAL": ["Valor original", "VALOR ORIGINAL"],
                "CLIENTE": ["Cliente", "CLIENTE"],
                "TIPO CONDIÇÃO": ["Tipo condição", "TIPO CONDIÇÃO"],
                "CÓD. CLIENTE": ["Cód. cliente", "COD. CLIENTE", "Código cliente"]
            }
            # ✅ CORREÇÃO: Tratamento robusto para coluna 'Valor original'

            def obter_coluna_valor_original(df):
                """Obtém a coluna de valor original com fallbacks"""
                possiveis_nomes = [
                    'Valor original', 'VALOR ORIGINAL', 'Valor Original',
                    'valor original', 'Valor a receber', 'VALOR A RECEBER'
                ]

                for nome in possiveis_nomes:
                    if nome in df.columns:
                        return nome

                # Se não encontrar, procurar por colunas similares
                colunas_similares = [col for col in df.columns
                                     if 'valor' in col.lower() and 'original' in col.lower()]
                if colunas_similares:
                    return colunas_similares[0]

                # Último recurso: procurar por qualquer coluna com 'valor'
                colunas_valor = [
                    col for col in df.columns if 'valor' in col.lower()]
                if colunas_valor:
                    return colunas_valor[0]

                return None

            # Usar função de obtenção da coluna
            coluna_valor_original = obter_coluna_valor_original(df_planilha)
            print(
                f"🔍 [PDD] Coluna valor original encontrada: {coluna_valor_original}", flush=True)
            if not coluna_valor_original:
                print(
                    f"❌ [PDD] RETORNANDO ERRO - Coluna de valor não encontrada", flush=True)
                return self._retorno_erro("Coluna de valor não encontrada", cliente, numero_titulo)

            # Atualizar mapeamento de colunas
            mapeamento_colunas["VALOR ORIGINAL"] = [coluna_valor_original]
            print(f"🔍 [PDD] Mapeamento de colunas atualizado", flush=True)

            # Verificar se as colunas existem com os nomes reais
            print(f"🔍 [PDD] Verificando colunas obrigatórias...", flush=True)
            colunas_encontradas = {}
            for nome_esperado, possiveis_nomes in mapeamento_colunas.items():
                encontrada = False
                for nome_real in possiveis_nomes:
                    if nome_real in df_planilha.columns:
                        colunas_encontradas[nome_esperado] = nome_real
                        encontrada = True
                        break

                if not encontrada:
                    self.logger.error(
                        f"❌ [PDD] Coluna obrigatória ausente: {nome_esperado}")
                    self.logger.error(
                        f"   Colunas disponíveis: {list(df_planilha.columns)}")
                    print(
                        f"❌ [PDD] RETORNANDO ERRO - Coluna obrigatória ausente: {nome_esperado}", flush=True)
                    return self._retorno_erro(f"Coluna obrigatória ausente: {nome_esperado}", cliente, numero_titulo)

            # Atualizar função col() para usar o mapeamento real
            def col(nome):
                return colunas_encontradas.get(nome, nome)

            print(
                f"🔍 [PDD] Colunas encontradas: {list(colunas_encontradas.keys())}", flush=True)

            # ✅ CORREÇÃO PDD: Obter mês base dos dados de validação base (planilha) - MOVIDO PARA O INÍCIO
            print(f"🔍 [PDD] Processando dados de validação base...", flush=True)
            mes_base = None
            ano_base = None
            tipo_reajuste = "ANUAL"  # Valor padrão
            data_assinatura = datetime.now()  # Valor padrão

            if dados_validacao_base:
                # Obter mês base da planilha
                mes_reajuste_str = str(
                    dados_validacao_base.get('Mês reajuste', '')).strip()
                if mes_reajuste_str and mes_reajuste_str not in ['', '#N/A', 'N/A', '#REF!', '#VALUE!', 'null', 'None']:
                    try:
                        # ✅ CORREÇÃO: Tentar formatos incluindo "ago.-25"
                        formatos = ["%d/%m/%Y", "%Y-%m-%d",
                                    "%d-%m-%Y", "%m/%d/%Y"]
                        mes_base = None
                        ano_base = None

                        # Primeiro tentar formato especial "ago.-25"
                        if '.' in mes_reajuste_str and '-' in mes_reajuste_str:
                            try:
                                mes_str = mes_reajuste_str.split('.')[0]
                                ano_str = mes_reajuste_str.split('-')[1]
                                meses = {
                                    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                                    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
                                }
                                mes_base = meses.get(mes_str.lower())
                                ano_base = 2000 + int(ano_str)
                                self.logger.info(
                                    f"✅ Mês base processado (formato especial): {mes_base:02d}/{ano_base}")
                            except (ValueError, IndexError, KeyError):
                                pass

                        # Se não conseguiu, tentar formatos padrão
                        if not mes_base or not ano_base:
                            for formato in formatos:
                                try:
                                    data_base = datetime.strptime(
                                        mes_reajuste_str, formato)
                                    mes_base = data_base.month
                                    ano_base = data_base.year
                                    self.logger.info(
                                        f"✅ Mês base processado (formato padrão): {mes_base:02d}/{ano_base}")
                                    break
                                except ValueError:
                                    continue

                    except Exception as e:
                        self.logger.warning(
                            f"Não foi possível interpretar o mês base do reparcelamento: {e}")

                # Obter tipo de reajuste da planilha
                tipo_reajuste_original = str(dados_validacao_base.get(
                    'Tipo reajuste', '')).strip()

                # ✅ CORREÇÃO: Se tipo_reajuste estiver vazio, usar o valor fornecido nos dados_validacao_base
                if not tipo_reajuste_original or tipo_reajuste_original == '':
                    tipo_reajuste_original = str(
                        dados_validacao_base.get('tipo_reajuste', '')).strip()

                # ✅ CORREÇÃO: Se ainda estiver vazio, tentar extrair do relatório
                if not tipo_reajuste_original or tipo_reajuste_original == '':
                    # Tentar extrair da coluna 'Tipo condição' do relatório
                    if 'Tipo condição' in df_planilha.columns:
                        tipos_unicos = df_planilha['Tipo condição'].unique()
                        for tipo in tipos_unicos:
                            if pd.notna(tipo) and str(tipo).strip() != '':
                                tipo_str = str(tipo).lower()
                                if 'anivers' in tipo_str:
                                    tipo_reajuste_original = 'ANIVERSÁRIO'
                                    break
                                elif 'anual' in tipo_str:
                                    tipo_reajuste_original = 'ANUAL'
                                    break

                tipo_reajuste = tipo_reajuste_original.lower()
                print(
                    f"🔍 [PDD] Tipo reajuste extraído: '{tipo_reajuste_original}' -> '{tipo_reajuste}'", flush=True)

                # ✅ NOVO: Log visual do tipo de reajuste
                if 'anivers' in tipo_reajuste:
                    print(
                        f"🎂 [PDD] TIPO REAJUSTE: ANIVERSÁRIO | Regra: Vencimento pode ser jogado para mês seguinte", flush=True)
                    self.logger.info(
                        f"🎂 [PDD] TIPO REAJUSTE: ANIVERSÁRIO | Regra: Vencimento pode ser jogado para mês seguinte")
                else:
                    print(
                        f"📅 [PDD] TIPO REAJUSTE: ANUAL | Regra: Vencimento sempre no mês de reparcelamento", flush=True)
                    self.logger.info(
                        f"📅 [PDD] TIPO REAJUSTE: ANUAL | Regra: Vencimento sempre no mês de reparcelamento")

                # Obter data de assinatura da planilha
                assinatura_str = str(dados_validacao_base.get(
                    'Assinatura ultimo Contrato', '')).strip()
                if assinatura_str and assinatura_str not in ['', '#N/A', 'N/A', '#REF!', '#VALUE!', 'null', 'None']:
                    formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]
                    for formato in formatos:
                        try:
                            data_assinatura = datetime.strptime(
                                assinatura_str, formato)
                            break
                        except ValueError:
                            continue

            # ✅ CORREÇÃO: Definir valores padrão se não encontrados
            print(f"🔍 [PDD] Verificando valores padrão...", flush=True)
            if not mes_base or not ano_base:
                hoje = datetime.now()
                mes_base = hoje.month
                ano_base = hoje.year
                self.logger.warning(
                    f"⚠️ [PDD] Mês base não encontrado - usando mês atual: {mes_base:02d}/{ano_base}")
                print(
                    f"⚠️ [PDD] Usando mês atual: {mes_base:02d}/{ano_base}", flush=True)

            # Log das informações obtidas
            print(f"🔍 [PDD] Log das informações obtidas...", flush=True)
            self.logger.info(
                f"🔍 [PDD] Mês base: {mes_base:02d}/{ano_base}")
            self.logger.info(f"🔍 [PDD] Tipo reajuste: '{tipo_reajuste}'")
            self.logger.info(
                f"🔍 [PDD] Tipo reajuste (lower): '{tipo_reajuste.lower()}'")
            self.logger.info(
                f"🔍 [PDD] Contém 'anivers': {'anivers' in tipo_reajuste.lower()}")
            self.logger.info(
                f"🔍 [PDD] Data assinatura: {data_assinatura.strftime('%d/%m/%Y')}")
            print(f"🔍 [PDD] Mês base: {mes_base:02d}/{ano_base}", flush=True)
            print(f"🔍 [PDD] Tipo reajuste: '{tipo_reajuste}'", flush=True)
            print(
                f"🔍 [PDD] Contém 'anivers': {'anivers' in tipo_reajuste.lower()}", flush=True)

            # Normalizar colunas de filtro
            print(f"🔍 [PDD] Normalizando colunas de filtro...", flush=True)
            df = df_planilha.copy()
            df["_TITULO"] = df[col("TÍTULO")].apply(norm)
            df["_STATUS"] = df[col("STATUS DA PARCELA")].apply(norm)
            df["_DOCUMENTO"] = df[col("DOCUMENTO")].apply(norm)
            df["_CLIENTE"] = df[col("CLIENTE")].apply(norm)
            print(f"🔍 [PDD] Colunas normalizadas criadas", flush=True)

            # Filtrar linhas do título (CORRIGIDO: lidar com float vs string)
            print(f"🔍 [PDD] Filtrando por título: {numero_titulo}", flush=True)
            titulo_norm = norm(numero_titulo)
            print(f"🔍 [PDD] Título normalizado: '{titulo_norm}'", flush=True)

            # Criar múltiplas máscaras para diferentes formatos
            mask_titulo = df["_TITULO"] == titulo_norm  # Formato exato

            # Tentar conversões numéricas
            try:
                titulo_float = float(numero_titulo)
                titulo_int = int(titulo_float)

                # Formato float com .0
                mask_titulo |= df["_TITULO"] == norm(str(titulo_float))
                # Formato int sem .0
                mask_titulo |= df["_TITULO"] == norm(str(titulo_int))
                # Comparação numérica direta se a coluna contém floats
                if df["Título"].dtype in ['float64', 'int64']:
                    mask_titulo |= df["Título"] == titulo_float
                    mask_titulo |= df["Título"] == titulo_int
            except (ValueError, TypeError):
                pass

            df_titulo = df[mask_titulo].copy()
            print(
                f"🔍 [PDD] Linhas após filtro por título: {len(df_titulo)}", flush=True)
            self.logger.info(
                f"🔍 [PDD] Linhas após filtro por título: {len(df_titulo)}")
            if df_titulo.empty:
                print(
                    f"❌ [PDD] RETORNANDO ERRO - Nenhuma linha encontrada para o título {numero_titulo}", flush=True)
                self.logger.error(
                    f"❌ [PDD] Nenhuma linha encontrada para o título {numero_titulo}")
                return self._retorno_erro(f"Título {numero_titulo} não encontrado", cliente, numero_titulo)

            # --- EXTRAÇÃO FIEL AO PDD ---
            print(f"🔍 [PDD] Iniciando extração fiel ao PDD...", flush=True)
            # 1. TODAS as parcelas CT (sem filtro inicial - será filtrado depois)
            mask_ct = df_titulo["_DOCUMENTO"].str.contains("CT")
            parcelas_ct_todas = df_titulo[mask_ct].copy()
            print(
                f"🔍 [PDD] TODAS as parcelas CT encontradas: {len(parcelas_ct_todas)}", flush=True)

            # Se não houver parcelas CT, ERRO explícito
            if parcelas_ct_todas.empty:
                self.logger.error(
                    f"❌ [PDD] Nenhuma parcela CT a vencer encontrada para o título {numero_titulo}")
                return {
                    "status_cliente": "ERRO",
                    "sucesso": False,
                    "pode_reparcelar": True,
                    "qtd_parcelas_ct_a_vencer": 0,
                    "qtd_ct_vencidas": 0,
                    "dia_vencimento": None,
                    "valor_parcela_atual": None,
                    "saldo_total": None,
                    "primeiro_vencimento_carne": None,
                    "erro": "Nenhuma parcela CT a vencer encontrada no relatório do Sienge"
                }

            print(f"🔍 [PDD] Iniciando regras PDD 9.1.1...", flush=True)

            # 2. Dia de vencimento (moda dos dias das parcelas CT)
            dias_venc = parcelas_ct_todas[col("DATA VENCIMENTO")].dropna().apply(lambda x: pd.to_datetime(
                x, errors='coerce', dayfirst=True).day if pd.to_datetime(x, errors='coerce', dayfirst=True) is not pd.NaT else None)
            dias_venc = dias_venc.dropna().tolist()
            if not dias_venc:
                self.logger.error(
                    f"❌ [PDD] Não foi possível extrair o dia de vencimento das parcelas CT a vencer para o título {numero_titulo}")
                return {
                    "status_cliente": "ERRO",
                    "sucesso": False,
                    "pode_reparcelar": True,
                    "qtd_parcelas_ct_a_vencer": len(parcelas_ct_todas),
                    "qtd_ct_vencidas": 0,
                    "dia_vencimento": None,
                    "valor_parcela_atual": None,
                    "saldo_total": None,
                    "primeiro_vencimento_carne": None,
                    "erro": "Não foi possível extrair o dia de vencimento das parcelas CT a vencer do relatório do Sienge"
                }
            dia_vencimento = max(
                set(dias_venc), key=dias_venc.count) if dias_venc else None
            self.logger.info(
                f"🔍 [PDD] Dia de vencimento extraído: {dia_vencimento}")

            # ✅ CORREÇÃO CRÍTICA: A contagem de parcelas será feita APÓS calcular o primeiro vencimento
            # Por enquanto, manter todas as parcelas para processamento posterior
            parcelas_ct_a_vencer_filtradas = parcelas_ct_todas
            self.logger.info(
                f"🔍 [PDD] Parcelas CT para filtro: {len(parcelas_ct_a_vencer_filtradas)} (filtro será aplicado após calcular primeiro vencimento)")

            # 3. Valor da parcela atual (CONFORME PDD EXATO)
            # ✅ CORREÇÃO: PDD não especifica moda - usar primeiro valor válido encontrado
            coluna_valor = colunas_encontradas.get(
                "VALOR ORIGINAL", "Valor original")
            if coluna_valor not in parcelas_ct_a_vencer_filtradas.columns:
                self.logger.error(
                    f"❌ [PDD] Coluna '{coluna_valor}' não encontrada nas parcelas filtradas")
                return self._retorno_erro(f"Coluna de valor não encontrada: {coluna_valor}", cliente, numero_titulo)

            # ✅ CORREÇÃO PDD: Pega o primeiro valor válido encontrado (não moda)
            valor_parcela_atual = 0.0
            for _, row in parcelas_ct_a_vencer_filtradas.iterrows():
                try:
                    valor_str = str(row[coluna_valor]).replace(
                        ',', '.').replace('R$', '').strip()
                    if valor_str.replace('.', '', 1).replace('-', '').isdigit():
                        valor_parcela_atual = float(valor_str)
                        if valor_parcela_atual > 0:
                            self.logger.info(
                                f"🔍 [PDD] Valor parcela atual extraído: R$ {valor_parcela_atual:,.2f}")
                            break  # ✅ Pega o primeiro valor válido
                except (ValueError, TypeError):
                    continue

            # 4. Parcelas a vencer (contagem será feita APÓS calcular o primeiro vencimento)
            # Por enquanto, usar todas as parcelas
            qtd_parcelas_ct_a_vencer = len(parcelas_ct_a_vencer_filtradas)
            self.logger.info(
                f"🔍 [PDD] Parcelas CT a vencer (temporário): {qtd_parcelas_ct_a_vencer} (filtro será aplicado após calcular primeiro vencimento)")

            # 5. Parcelas vencidas (CT)
            mask_vencida = df_titulo["_STATUS"].str.contains(
                "VENCIDA", na=False)
            parcelas_ct_vencidas = df_titulo[mask_vencida & mask_ct].copy()
            qtd_ct_vencidas = len(parcelas_ct_vencidas)
            self.logger.info(
                f"🔍 [PDD] Quantidade de parcelas CT vencidas: {qtd_ct_vencidas}")

            # 6. Pendências Sienge (REC/FAT vencidas)
            mask_rec_fat = df_titulo["_DOCUMENTO"].str.contains(
                "REC", na=False) | df_titulo["_DOCUMENTO"].str.contains("FAT", na=False)
            pendencias_sienge = "Sim" if not df_titulo[mask_rec_fat &
                                                       mask_vencida].empty else ""
            self.logger.info(f"🔍 [PDD] Pendências Sienge: {pendencias_sienge}")

            # 7. Pendências Sienge Inad (CT vencidas > 60 dias antes do 1º vencimento do novo carnê)
            inadimplente = False
            pendencias_sienge_inad = ""
            if not parcelas_ct_vencidas.empty and dia_vencimento:
                # ✅ CORREÇÃO: Calcular primeiro vencimento do carnê usando as mesmas regras PDD
                data_primeiro_venc = None

                # ✅ CORREÇÃO CRÍTICA: O mês de reparcelamento É o mês de reajuste (não o próximo)
                # O mês base JÁ É o mês de reajuste (ex: out.-25 = outubro/2025)
                mes_reparcelamento = mes_base if mes_base else datetime.now().month
                ano_reparcelamento = ano_base if ano_base else datetime.now().year

                if tipo_reajuste and 'anivers' in tipo_reajuste and data_assinatura and mes_base and ano_base:
                    # Regra aniversário
                    dia_aniversario = data_assinatura.day
                    if dia_vencimento < dia_aniversario:
                        # Vencimento antes do aniversário: mês seguinte ao mês de reparcelamento
                        mes_venc = mes_reparcelamento + 1
                        ano_venc = ano_reparcelamento
                        if mes_venc > 12:
                            mes_venc = 1
                            ano_venc += 1
                        data_primeiro_venc = datetime(
                            ano_venc, mes_venc, dia_vencimento)
                    else:
                        # Vencimento após ou igual ao aniversário: mês de reparcelamento
                        data_primeiro_venc = datetime(
                            ano_reparcelamento, mes_reparcelamento, dia_vencimento)
                else:
                    # Regra padrão (anual ou fallback)
                    if mes_base and ano_base:
                        data_primeiro_venc = datetime(
                            ano_reparcelamento, mes_reparcelamento, dia_vencimento)
                    else:
                        # Fallback: próximo mês
                        hoje = pd.Timestamp.now()
                        proximo_mes = (hoje + pd.offsets.MonthBegin(1)
                                       ).replace(day=dia_vencimento)
                        data_primeiro_venc = proximo_mes

                # Verificar inadimplência usando o primeiro vencimento calculado
                if data_primeiro_venc:
                    self.logger.info(
                        f"🔍 [PDD] Primeiro vencimento para verificação de inadimplência: {data_primeiro_venc.strftime('%d/%m/%Y')}")

                    for _, row in parcelas_ct_vencidas.iterrows():
                        data_venc = pd.to_datetime(
                            row[col("DATA VENCIMENTO")], errors='coerce', dayfirst=True)
                        if data_venc is not pd.NaT and (data_primeiro_venc - data_venc).days > 60:
                            inadimplente = True
                            pendencias_sienge_inad = "OK"
                            self.logger.info(
                                f"🔍 [PDD] Cliente inadimplente detectado: parcela vencida em {data_venc.strftime('%d/%m/%Y')} ({data_primeiro_venc - data_venc} dias antes)")
                            break

            self.logger.info(
                f"🔍 [PDD] Pendências Sienge Inad: {pendencias_sienge_inad}")

            # 8. Saldo total (não especificado no PDD, manter 0 ou calcular se houver campo)
            saldo_total = 0.0
            if "SALDO DEVEDOR BASE" in [norm(c) for c in df_titulo.columns]:
                saldo_col = col("SALDO DEVEDOR BASE")
                saldo_vals = df_titulo[saldo_col].dropna().apply(lambda x: float(str(x).replace(',', '.').replace('R$', '').strip(
                )) if str(x).replace(',', '.').replace('R$', '').replace('.', '', 1).replace('-', '').isdigit() else 0)
                saldo_vals = [v for v in saldo_vals if v > 0]
                saldo_total = max(
                    set(saldo_vals), key=saldo_vals.count) if saldo_vals else 0.0
            self.logger.info(f"🔍 [PDD] Saldo total extraído: {saldo_total}")

            # 9. 1º vencimento carnê (aplicar regras PDD conforme tipo de reajuste)
            print(
                f"🔍 [PDD] CALCULANDO 1º VENCIMENTO CARNÊ - MÉTODO PRINCIPAL", flush=True)
            print(f"   - mes_base: {mes_base}", flush=True)
            print(f"   - ano_base: {ano_base}", flush=True)
            print(f"   - dia_vencimento: {dia_vencimento}", flush=True)
            print(f"   - tipo_reajuste: '{tipo_reajuste}'", flush=True)
            print(
                f"   - data_assinatura: {data_assinatura.strftime('%d/%m/%Y') if data_assinatura else 'N/A'}", flush=True)

            # ✅ CORREÇÃO CRÍTICA: O mês de reparcelamento É o mês de reajuste (não o próximo)
            # O mês base JÁ É o mês de reajuste (ex: set.-25 = setembro/2025)
            mes_reparcelamento = mes_base if mes_base else datetime.now().month
            ano_reparcelamento = ano_base if ano_base else datetime.now().year

            print(
                f"🔍 [PDD] Mês de reajuste: {mes_reparcelamento:02d}/{ano_reparcelamento}", flush=True)
            print(
                f"🔍 [PDD] Mês de reparcelamento: {mes_reparcelamento:02d}/{ano_reparcelamento} (mesmo mês)", flush=True)

            if tipo_reajuste and 'anivers' in tipo_reajuste and data_assinatura and mes_base and ano_base:
                # ✅ REGRA ANIVERSÁRIO PDD
                dia_aniversario = data_assinatura.day
                print(f"🎂 [PDD] APLICANDO REGRA ANIVERSÁRIO:", flush=True)
                print(f"   - Dia aniversário: {dia_aniversario}", flush=True)
                print(f"   - Dia vencimento: {dia_vencimento}", flush=True)
                print(
                    f"   - Comparação: {dia_vencimento} < {dia_aniversario} = {dia_vencimento < dia_aniversario}", flush=True)

                if dia_vencimento < dia_aniversario:
                    # Vencimento antes do aniversário: mês seguinte ao mês de reparcelamento
                    mes_venc = mes_reparcelamento + 1
                    ano_venc = ano_reparcelamento
                    if mes_venc > 12:
                        mes_venc = 1
                        ano_venc += 1
                    primeiro_vencimento_data = datetime(
                        ano_venc, mes_venc, dia_vencimento)
                    primeiro_vencimento_carne = primeiro_vencimento_data.strftime(
                        "%d/%m/%Y")
                    print(
                        f"✅ [PDD] Aniversário - vencimento antes do aniversário: {primeiro_vencimento_carne} (mês seguinte ao reparcelamento)", flush=True)
                else:
                    # Vencimento após ou igual ao aniversário: mês de reparcelamento
                    primeiro_vencimento_data = datetime(
                        ano_reparcelamento, mes_reparcelamento, dia_vencimento)
                    primeiro_vencimento_carne = primeiro_vencimento_data.strftime(
                        "%d/%m/%Y")
                    print(
                        f"✅ [PDD] Aniversário - após/igual: {primeiro_vencimento_carne} (mês de reparcelamento)", flush=True)
            else:
                # Regra padrão (anual ou fallback)
                if mes_base and ano_base:
                    primeiro_vencimento_data = datetime(
                        ano_reparcelamento, mes_reparcelamento, dia_vencimento)
                    primeiro_vencimento_carne = primeiro_vencimento_data.strftime(
                        "%d/%m/%Y")
                    print(
                        f"📅 [PDD] APLICANDO REGRA ANUAL: {primeiro_vencimento_carne} (mês de reparcelamento)", flush=True)
                else:
                    # Fallback: próximo mês
                    hoje = pd.Timestamp.now()
                    proximo_mes = (hoje + pd.offsets.MonthBegin(1)
                                   ).replace(day=dia_vencimento)
                    primeiro_vencimento_carne = proximo_mes.strftime(
                        "%d/%m/%Y")
                    print(
                        f"⚠️ [PDD] Fallback: {primeiro_vencimento_carne}", flush=True)

            self.logger.info(
                f"🔍 [PDD] 1º vencimento carnê FINAL: {primeiro_vencimento_carne} (dia {dia_vencimento} extraído do relatório)")

            # ✅ NOVO: Log visual do resultado final
            print(
                f"🎯 [PDD] RESULTADO FINAL: {primeiro_vencimento_carne} | Dia: {dia_vencimento} | Tipo: {tipo_reajuste.upper()}", flush=True)

            # ✅ CORREÇÃO CRÍTICA: Contagem de parcelas A PARTIR do primeiro vencimento do carnê
            print(
                f"🔍 [PDD] APLICANDO FILTRO DE PARCELAS A PARTIR DO PRIMEIRO VENCIMENTO", flush=True)

            # Converter primeiro vencimento para datetime para comparação
            try:
                data_primeiro_vencimento = datetime.strptime(
                    primeiro_vencimento_carne, "%d/%m/%Y")
                print(
                    f"   📅 Data do primeiro vencimento: {data_primeiro_vencimento.strftime('%d/%m/%Y')}", flush=True)

                # Filtrar parcelas que vencem A PARTIR do primeiro vencimento do carnê
                parcelas_filtradas_final = []
                for _, parcela in parcelas_ct_todas.iterrows():
                    try:
                        # Processar data de vencimento da parcela
                        data_venc_str = None
                        for col_name in ["Data vencimento", "DATA VENCIMENTO", "data_vencimento"]:
                            if col_name in parcela:
                                data_venc_str = str(
                                    parcela.get(col_name, "")).strip()
                                break

                        if not data_venc_str or data_venc_str in ['', '#N/A', 'N/A', '#REF!', '#VALUE!', 'null', 'None']:
                            continue

                        # Tentar diferentes formatos de data
                        data_vencimento_parcela = None
                        formatos = ["%d/%m/%Y", "%Y-%m-%d",
                                    "%d-%m-%Y", "%m/%d/%Y"]

                        for formato in formatos:
                            try:
                                data_vencimento_parcela = datetime.strptime(
                                    data_venc_str, formato)
                                break
                            except ValueError:
                                continue

                        if not data_vencimento_parcela:
                            continue

                        # ✅ CORREÇÃO: Incluir parcelas A PARTIR do primeiro vencimento do carnê
                        # E também considerar a data limite de inadimplência se fornecida
                        incluir_parcela = data_vencimento_parcela >= data_primeiro_vencimento

                        if data_limite_inadimplencia:
                            # Aplicar filtro de inadimplência: parcelas devem vencer >= data limite inadimplência
                            incluir_parcela = incluir_parcela and data_vencimento_parcela >= data_limite_inadimplencia

                        if incluir_parcela:
                            parcelas_filtradas_final.append(parcela)
                            motivo = f"(>= {data_primeiro_vencimento.strftime('%d/%m/%Y')}"
                            if data_limite_inadimplencia:
                                motivo += f" e >= {data_limite_inadimplencia.strftime('%d/%m/%Y')}"
                            motivo += ")"
                            print(
                                f"   ✅ Incluindo parcela: {data_vencimento_parcela.strftime('%d/%m/%Y')} {motivo}", flush=True)
                        else:
                            motivo = f"(< {data_primeiro_vencimento.strftime('%d/%m/%Y')}"
                            if data_limite_inadimplencia and data_vencimento_parcela < data_limite_inadimplencia:
                                motivo = f"(< {data_limite_inadimplencia.strftime('%d/%m/%Y')} - inadimplência)"
                            print(
                                f"   ❌ Excluindo parcela: {data_vencimento_parcela.strftime('%d/%m/%Y')} {motivo}", flush=True)

                    except Exception as e:
                        print(
                            f"   ⚠️ Erro ao processar parcela: {str(e)}", flush=True)
                        continue

                # Atualizar quantidade de parcelas com o filtro correto
                qtd_parcelas_ct_a_vencer = len(parcelas_filtradas_final)
                filtro_info = f"a partir de {data_primeiro_vencimento.strftime('%d/%m/%Y')}"
                if data_limite_inadimplencia:
                    filtro_info += f" e >= {data_limite_inadimplencia.strftime('%d/%m/%Y')} (inadimplência)"
                print(
                    f"🔍 [PDD] QUANTIDADE FINAL DE PARCELAS: {qtd_parcelas_ct_a_vencer} ({filtro_info})", flush=True)
                print(
                    f"🔍 [PDD] Total original: {len(parcelas_ct_todas)} | Filtradas: {qtd_parcelas_ct_a_vencer}", flush=True)

            except Exception as e:
                print(
                    f"❌ Erro ao aplicar filtro de parcelas: {str(e)}", flush=True)
                # Em caso de erro, manter a contagem original
                qtd_parcelas_ct_a_vencer = len(parcelas_ct_a_vencer_filtradas)

            # ✅ CORREÇÃO: Usar código cliente dos dados de validação base (planilha)
            codigo_cliente = ""
            if dados_validacao_base and dados_validacao_base.get('codigo_cliente'):
                codigo_cliente = str(
                    dados_validacao_base.get('codigo_cliente')).strip()
                self.logger.info(
                    f"🔍 [PDD] Código cliente obtido dos dados de validação base: '{codigo_cliente}'")
            else:
                # Fallback: tentar extrair do relatório
                if 'Cód. cliente' in df_titulo.columns:
                    codigos = df_titulo['Cód. cliente'].dropna().unique()
                    if len(codigos) > 0:
                        codigo_cliente = str(codigos[0]).strip()
                        self.logger.info(
                            f"🔍 [PDD] Código cliente extraído do relatório: '{codigo_cliente}'")

                    # 10. Determinar se pode reparcelar (regra PDD)
            # ✅ CORREÇÃO PDD: TODOS os contratos podem ser reparcelados
            # Apenas a geração de carnê é restrita a adimplentes
            pode_reparcelar = True  # Todos os contratos podem reparcelar
            status_cliente = "adimplente"

            # Verificar se há parcelas a vencer
            if qtd_parcelas_ct_a_vencer == 0:
                pode_reparcelar = False
                status_cliente = "sem_parcelas_vencer"

            # ✅ CORREÇÃO PDD: Pendências NÃO bloqueiam reparcelamento
            # Apenas determinam se pode gerar carnê
            if inadimplente:
                status_cliente = "inadimplente"  # Pode reparcelar, mas não gerar carnê

            if pendencias_sienge:
                status_cliente = "com_pendencias"  # Pode reparcelar, mas não gerar carnê

            # Montar dict final
            resultado = {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "codigo_cliente": codigo_cliente,  # ✅ NOVA COLUNA
                "dia_vencimento": dia_vencimento,
                "valor_parcela_atual": valor_parcela_atual,
                "qtd_parcelas_ct_a_vencer": qtd_parcelas_ct_a_vencer,
                "qtd_ct_vencidas": qtd_ct_vencidas,
                "pendencias_sienge": pendencias_sienge,
                "pendencias_sienge_inad": pendencias_sienge_inad,
                "cliente_inadimplente": inadimplente,
                "saldo_total": saldo_total,
                "primeiro_vencimento_carne": primeiro_vencimento_carne,
                "pode_reparcelar": pode_reparcelar,  # ✅ CORREÇÃO: Adicionar campo
                "status_cliente": status_cliente,  # ✅ CORREÇÃO: Adicionar campo
                "sucesso": True,
                "timestamp_processamento": pd.Timestamp.now().isoformat(),
            }
            self.logger.info(
                f"🔍 [PDD] Resultado final extração fiel: {resultado}")
            return resultado

        except Exception as e:
            self.logger.error(
                f"❌ [PDD] Erro inesperado na extração fiel: {str(e)}")
            return self._retorno_erro(f"Erro inesperado: {str(e)}", cliente, numero_titulo)

    def _validar_estrutura_planilha_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Valida se a planilha CSV tem a estrutura esperada do Sienge"""
        try:
            if df.empty:
                return {"valida": False, "motivo": "Planilha vazia"}

            # Colunas obrigatórias conforme CSV real do Sienge (cabeçalho atualizado)
            colunas_obrigatorias = [
                "Título", "Parcela/Condição", "Documento", "Cliente",
                "Status da parcela", "Data vencimento", "Valor a receber"
            ]

            # Verificar se existem variações nos nomes das colunas
            colunas_disponíveis = list(df.columns)
            mapeamento_colunas = {}

            for col_obrigatoria in colunas_obrigatorias:
                if col_obrigatoria in colunas_disponíveis:
                    mapeamento_colunas[col_obrigatoria] = col_obrigatoria
                else:
                    # Buscar variações comuns
                    if col_obrigatoria == "Documento" and "Nº documento" in colunas_disponíveis:
                        mapeamento_colunas[col_obrigatoria] = "Nº documento"
                    elif col_obrigatoria == "Valor a receber" and "Valor a receber" in colunas_disponíveis:
                        mapeamento_colunas[col_obrigatoria] = "Valor a receber"
                    # Adicionar outras variações conforme necessário

            colunas_faltantes = [
                col for col in colunas_obrigatorias if col not in df.columns]
            if colunas_faltantes:
                return {
                    "valida": False,
                    "motivo": f"Colunas ausentes: {colunas_faltantes}"
                }

            return {"valida": True, "total_registros": len(df)}

        except Exception as e:
            return {"valida": False, "motivo": f"Erro na validação: {str(e)}"}

    def _aplicar_regra_inadimplencia_csv(self, df: pd.DataFrame, mes_base: int = None, ano_base: int = None, tipo_reajuste: str = None, data_assinatura: datetime = None) -> Dict[str, Any]:
        """
        REGRA PDD CRÍTICA: Identificação de Cliente Inadimplente

        CONFORME PDD SEÇÃO 9.1.1:
        - Considerar TODAS as parcelas CT (independente do status)
        - Verificar se vencimento < data limite (60 dias antes do novo carnê)
        - Status "Vencida" ou "A vencer" não importa para esta análise
        """
        try:
            hoje = date.today()

            # 1. IDENTIFICAR DIA DE VENCIMENTO REAL DO RELATÓRIO
            resultado_regra_1 = self._regra_1_dia_vencimento_csv(
                df, dados_validacao_base)
            dia_vencimento_extraido = resultado_regra_1.get("dia_vencimento")
            if resultado_regra_1.get("sucesso", False) and dia_vencimento_extraido is not None:
                dia_vencimento = int(dia_vencimento_extraido)
                self.logger.info(
                    f"📈 ✅ Dia de vencimento extraído do relatório: {dia_vencimento}")
            else:
                # ❌ ERRO: Dia de vencimento não encontrado no relatório
                self.logger.error(
                    f"📈 ❌ Dia de vencimento não encontrado no relatório - PROCESSAMENTO INTERROMPIDO")
                return {
                    "status_cliente": "ERRO",
                    "pode_reparcelar": True,
                    "qtd_parcelas_ct_vencidas": 0,
                    "parcelas_problematicas": [],
                    "erro": "Dia de vencimento não encontrado no relatório do Sienge",
                    "data_limite_inadimplencia": None,
                    "primeiro_vencimento_carne": None,
                    "dia_vencimento": None
                }

            # 2. CALCULAR 1º VENCIMENTO DO NOVO CARNÊ CONFORME PDD
            primeiro_vencimento_novo_carne = None

            # ✅ CORREÇÃO CRÍTICA: Verificar se as variáveis estão definidas
            print(f"🔍 [PDD] INICIANDO CÁLCULO DO 1º VENCIMENTO CARNÊ", flush=True)
            print(
                f"   - mes_base: {mes_base} (tipo: {type(mes_base)})", flush=True)
            print(
                f"   - ano_base: {ano_base} (tipo: {type(ano_base)})", flush=True)
            print(
                f"   - dia_vencimento: {dia_vencimento} (tipo: {type(dia_vencimento)})", flush=True)
            print(f"   - mes_base bool: {bool(mes_base)}", flush=True)
            print(f"   - ano_base bool: {bool(ano_base)}", flush=True)
            print(
                f"   - dia_vencimento bool: {bool(dia_vencimento)}", flush=True)
            print(
                f"   - Condição if: {bool(mes_base) and bool(ano_base) and bool(dia_vencimento)}", flush=True)

            # ✅ CORREÇÃO: Definir valores padrão se necessário
            if not mes_base or not ano_base:
                hoje = datetime.now()
                mes_base = mes_base or hoje.month
                ano_base = ano_base or hoje.year
                print(
                    f"⚠️ [PDD] Valores padrão definidos: mes_base={mes_base}, ano_base={ano_base}", flush=True)

            if mes_base and ano_base and dia_vencimento:
                self.logger.info(f"🔍 [PDD] Calculando 1º vencimento carnê:")
                self.logger.info(f"   - Mês base: {mes_base}")
                self.logger.info(f"   - Ano base: {ano_base}")
                self.logger.info(f"   - Dia vencimento: {dia_vencimento}")
                self.logger.info(f"   - Tipo reajuste: '{tipo_reajuste}'")
                self.logger.info(
                    f"   - Contém 'anivers': {'anivers' in tipo_reajuste}")
                self.logger.info(
                    f"   - Data assinatura: {data_assinatura.strftime('%d/%m/%Y') if data_assinatura else 'N/A'}")

                if tipo_reajuste and 'anivers' in tipo_reajuste and data_assinatura:
                    # Reajuste Aniversário
                    dia_aniversario = data_assinatura.day
                    self.logger.info(
                        f"   - Dia aniversário: {dia_aniversario}")
                    self.logger.info(
                        f"   - Comparação: {dia_vencimento} < {dia_aniversario} = {dia_vencimento < dia_aniversario}")

                    if dia_vencimento < dia_aniversario:
                        # Vencimento antes do aniversário: mês seguinte ao mês base
                        mes_venc = mes_base + 1
                        ano_venc = ano_base
                        if mes_venc > 12:
                            mes_venc = 1
                            ano_venc += 1
                        primeiro_vencimento_novo_carne = datetime(
                            ano_venc, mes_venc, dia_vencimento)
                        self.logger.info(
                            f"📈 Reajuste Aniversário: vencimento antes do aniversário. 1º vencimento: {primeiro_vencimento_novo_carne.strftime('%d/%m/%Y')}")
                    else:
                        # Vencimento após ou igual ao aniversário: mês base
                        primeiro_vencimento_novo_carne = datetime(
                            ano_base, mes_base, dia_vencimento)
                        self.logger.info(
                            f"📈 Reajuste Aniversário: vencimento após/aniversário. 1º vencimento: {primeiro_vencimento_novo_carne.strftime('%d/%m/%Y')}")
                else:
                    # Reajuste Anual ou padrão
                    primeiro_vencimento_novo_carne = datetime(
                        ano_base, mes_base, dia_vencimento)
                    self.logger.info(
                        f"📈 Reajuste Anual/padrão. 1º vencimento: {primeiro_vencimento_novo_carne.strftime('%d/%m/%Y')}")
            else:
                # Fallback: próximo mês disponível
                proximo_mes = hoje.replace(day=1) + timedelta(days=31)
                proximo_mes = proximo_mes.replace(day=1)
                primeiro_vencimento_novo_carne = proximo_mes.replace(
                    day=dia_vencimento)
                self.logger.info(
                    f"📈 Fallback: próximo mês. 1º vencimento: {primeiro_vencimento_novo_carne.strftime('%d/%m/%Y')}")

            # 3. CALCULAR DATA LIMITE (60 DIAS ANTES)
            data_limite = primeiro_vencimento_novo_carne - timedelta(days=60)

            # 4. FILTRAR APENAS PARCELAS CT (todas, independente do status)
            parcelas_ct = df[
                df["Documento"].str.contains("CT", case=False, na=False)
            ].copy()

            if parcelas_ct.empty:
                self.logger.info(
                    "📈 ⚠️ Nenhuma parcela CT encontrada no relatório")
                return {
                    "status_cliente": "ADIMPLENTE",
                    "pode_reparcelar": True,
                    "qtd_parcelas_ct_vencidas": 0,
                    "parcelas_problematicas": [],
                    "data_limite_inadimplencia": data_limite.strftime("%d/%m/%Y"),
                    "primeiro_vencimento_carne": primeiro_vencimento_novo_carne.strftime("%Y-%m-%d")
                }

            # 5. PROCESSAR DATAS DE VENCIMENTO
            def processar_data_vencimento(data_str):
                try:
                    if pd.isna(data_str) or str(data_str).strip() == "":
                        return None

                    data_str = str(data_str).strip()

                    # Tentar diferentes formatos
                    formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]

                    for formato in formatos:
                        try:
                            return datetime.strptime(data_str, formato).date()
                        except ValueError:
                            continue

                    return None
                except Exception:
                    return None

            # 6. APLICAR PROCESSAMENTO DE DATAS
            parcelas_ct = pd.DataFrame(parcelas_ct)
            parcelas_ct["Data_vencimento_processada"] = parcelas_ct["Data vencimento"].apply(
                processar_data_vencimento)

            # 7. FILTRAR PARCELAS COM DATAS VÁLIDAS
            parcelas_validas = parcelas_ct[parcelas_ct["Data_vencimento_processada"].notna(
            )].copy()
            parcelas_validas = pd.DataFrame(parcelas_validas)

            if parcelas_validas.empty:
                self.logger.warning(
                    "📈 ⚠️ Nenhuma parcela CT com data válida encontrada")
                return {
                    "status_cliente": "ADIMPLENTE",
                    "pode_reparcelar": True,
                    "qtd_parcelas_ct_vencidas": 0,
                    "parcelas_problematicas": [],
                    "data_limite_inadimplencia": data_limite.strftime("%d/%m/%Y"),
                    "primeiro_vencimento_carne": primeiro_vencimento_novo_carne.strftime("%Y-%m-%d")
                }

            # 8. IDENTIFICAR PARCELAS VENCIDAS ANTES DA DATA LIMITE
            parcelas_inadimplentes = parcelas_validas[
                parcelas_validas["Data_vencimento_processada"] < data_limite
            ]
            parcelas_inadimplentes = pd.DataFrame(parcelas_inadimplentes)

            qtd_parcelas_inadimplentes = len(parcelas_inadimplentes)

            # 9. DETERMINAR STATUS DO CLIENTE (CONFORME PDD - NÃO BLOQUEIA REPARCELAMENTO)
            if qtd_parcelas_inadimplentes > 0:
                status_cliente = "INADIMPLENTE"
                # ✅ CORREÇÃO PDD: Reparcelamento deve ser realizado mesmo para inadimplentes
                pode_reparcelar = True
                self.logger.info(
                    f"📈 ⚠️ Cliente INADIMPLENTE: {qtd_parcelas_inadimplentes} parcelas vencidas antes da data limite")
                self.logger.info(
                    "📈 ✅ CONFORME PDD: Reparcelamento será realizado, mas carnê não será gerado (pode_reparcelar=True, bloqueio apenas no carnê)")
            else:
                status_cliente = "ADIMPLENTE"
                pode_reparcelar = True
                self.logger.info(
                    "📈 ✅ Cliente ADIMPLENTE: Nenhuma parcela vencida antes da data limite (pode_reparcelar=True)")

            # 10. PREPARAR LISTA DE PARCELAS PROBLEMÁTICAS
            parcelas_problematicas = []
            for _, parcela in parcelas_inadimplentes.iterrows():
                vencimento_proc = parcela.get("Data_vencimento_processada")
                if vencimento_proc is None:
                    vencimento_proc = ''
                if not hasattr(vencimento_proc, 'strftime') and vencimento_proc != '':
                    try:
                        vencimento_proc = pd.to_datetime(vencimento_proc)
                    except Exception:
                        vencimento_proc = ''
                vencimento_str = vencimento_proc.strftime(
                    "%d/%m/%Y") if hasattr(vencimento_proc, 'strftime') else str(vencimento_proc)
                parcelas_problematicas.append({
                    "parcela": parcela.get("Parcela/Condição", "N/A"),
                    "vencimento": vencimento_str,
                    "valor": parcela.get("Valor a receber", 0),
                    "status": parcela.get("Status da parcela", "N/A")
                })

            # 11. RESULTADO FINAL
            resultado = {
                "status_cliente": status_cliente,
                "pode_reparcelar": pode_reparcelar,
                "qtd_parcelas_ct_vencidas": qtd_parcelas_inadimplentes,
                "parcelas_problematicas": parcelas_problematicas,
                "data_limite_inadimplencia": data_limite.strftime("%d/%m/%Y"),
                "primeiro_vencimento_carne": primeiro_vencimento_novo_carne.strftime("%Y-%m-%d"),
                "dia_vencimento": dia_vencimento,
                "tipo_reajuste": tipo_reajuste,
                "data_assinatura": data_assinatura.strftime("%d/%m/%Y") if data_assinatura else None
            }

            # LOG FINAL RESUMIDO
            self.logger.info("📈 ✅ Validação PDD 9.1.1 concluída:")
            self.logger.info(f"📈   📊 Status: {status_cliente}")
            self.logger.info(
                f"📈   🔢 Parcelas CT vencidas: {qtd_parcelas_inadimplentes}")
            self.logger.info(f"📈   ✔️ Pode reparcelar: {pode_reparcelar}")
            self.logger.info(f"📈   🎂 Tipo reajuste: {tipo_reajuste}")
            self.logger.info(
                f"📈   📅 Data assinatura: {data_assinatura.strftime('%d/%m/%Y') if data_assinatura else 'N/A'}")
            self.logger.info(
                f"📈   📅 1º vencimento carnê: {primeiro_vencimento_novo_carne.strftime('%d/%m/%Y')}")

            return resultado

        except Exception as e:
            self.logger.error(
                f"📈 ❌ Erro na validação de inadimplência: {str(e)}")
            return {
                "status_cliente": "ERRO",
                "pode_reparcelar": True,  # ✅ CORREÇÃO PDD: Sempre permite reparcelamento
                "qtd_parcelas_ct_vencidas": 0,
                "parcelas_problematicas": [],
                "erro": str(e)
            }

    # ============= REGRAS 9.1.1 COMPLETAS ADAPTADAS PARA CSV =============

    def _regra_1_dia_vencimento_csv(self, df: pd.DataFrame, dados_validacao_base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        REGRA 1 PDD: Identificação do Dia de Vencimento
        ✅ CORREÇÃO CRÍTICA: O dia DEVE vir da coluna "Data vencimento" do relatório Sienge
        """
        try:
            print("🔍 📋 Extraindo dia do primeiro vencimento...")
            self.logger.info("🔍 📋 Extraindo dia do primeiro vencimento...")

            # ✅ CORREÇÃO CRÍTICA: O dia DEVE vir da coluna "Data vencimento" do relatório Sienge
            print(
                "🔍 📋 Extraindo dia do primeiro vencimento das parcelas futuras do Sienge...")
            self.logger.info(
                "🔍 📋 Extraindo dia do primeiro vencimento das parcelas futuras do Sienge...")

            # Filtrar apenas parcelas que ainda não foram baixadas (futuras)
            mask_nao_baixadas = df["Data da baixa"].isna()
            parcelas_futuras = df[mask_nao_baixadas].copy()

            if len(parcelas_futuras) == 0:
                print("🔍 ❌ Nenhuma parcela futura encontrada!")
                self.logger.info("🔍 ❌ Nenhuma parcela futura encontrada!")
                return {
                    "sucesso": False,
                    "motivo": "Nenhuma parcela futura encontrada no relatório",
                    "dia_vencimento": None
                }

            # Ordenar por data de vencimento para pegar o primeiro vencimento
            parcelas_futuras = parcelas_futuras.sort_values("Data vencimento")

            # Pegar a primeira parcela futura (primeiro vencimento)
            primeira_parcela = parcelas_futuras.iloc[0]

            try:
                data_venc_str = str(primeira_parcela["Data vencimento"])
                data_venc = pd.to_datetime(
                    data_venc_str, errors='coerce', dayfirst=True)

                if pd.isna(data_venc):
                    print(f"🔍 ❌ Data de vencimento inválida: {data_venc_str}")
                    self.logger.info(
                        f"🔍 ❌ Data de vencimento inválida: {data_venc_str}")
                    return {
                        "sucesso": False,
                        "motivo": f"Data de vencimento inválida: {data_venc_str}",
                        "dia_vencimento": None
                    }

                dia_vencimento = data_venc.day

                if not (1 <= dia_vencimento <= 31):
                    print(f"🔍 ❌ Dia de vencimento inválido: {dia_vencimento}")
                    self.logger.info(
                        f"🔍 ❌ Dia de vencimento inválido: {dia_vencimento}")
                    return {
                        "sucesso": False,
                        "motivo": f"Dia de vencimento inválido: {dia_vencimento}",
                        "dia_vencimento": None
                    }

                print(
                    f"🔍 ✅ Dia do primeiro vencimento extraído do Sienge: {dia_vencimento} (Data: {data_venc_str})")
                self.logger.info(
                    f"🔍 ✅ Dia do primeiro vencimento extraído do Sienge: {dia_vencimento} (Data: {data_venc_str})")

                return {
                    "sucesso": True,
                    "dia_vencimento": dia_vencimento,
                    "fonte": "relatorio_sienge",
                    "data_primeiro_vencimento": data_venc_str,
                    "observacao": f"Dia {dia_vencimento} extraído do primeiro vencimento futuro do Sienge ({data_venc_str})"
                }

            except Exception as e:
                print(f"🔍 ❌ Erro ao processar data de vencimento: {e}")
                self.logger.info(
                    f"🔍 ❌ Erro ao processar data de vencimento: {e}")
                return {
                    "sucesso": False,
                    "erro": str(e),
                    "dia_vencimento": None
                }

        except Exception as e:
            print(f"🔍 ❌ Erro geral na extração do dia de vencimento: {e}")
            self.logger.info(
                f"🔍 ❌ Erro geral na extração do dia de vencimento: {e}")
            return {
                "sucesso": False,
                "erro": str(e),
                "dia_vencimento": None
            }

    def _regra_2_primeiro_vencimento_csv(self, df: pd.DataFrame, tipo_reajuste: str = "ANUAL", mes_base: int = None, ano_base: int = None, data_assinatura: datetime = None, dados_validacao_base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        REGRA 2 PDD: Cálculo do 1º Vencimento do Novo Carnê
        ✅ CORREÇÃO: Agora aplica regras de aniversário conforme PDD
        """
        try:
            hoje = date.today()

            # Obter dia de vencimento extraído do relatório do Sienge
            regra_1 = self._regra_1_dia_vencimento_csv(
                df, dados_validacao_base)
            # ✅ CORREÇÃO: Agora extrai o dia diretamente do relatório, conforme PDD
            if not regra_1.get("sucesso", False) or not regra_1.get("dia_vencimento"):
                return {
                    "sucesso": False,
                    "erro": "Dia de vencimento não encontrado no relatório do Sienge",
                    "data_primeiro_vencimento": None
                }

            dia_vencimento = regra_1.get("dia_vencimento")

            # Garantir que é um número válido
            if not isinstance(dia_vencimento, int) or dia_vencimento < 1 or dia_vencimento > 31:
                return {
                    "sucesso": False,
                    "erro": f"Dia de vencimento inválido extraído do relatório: {dia_vencimento}",
                    "data_primeiro_vencimento": None
                }

            # ✅ CORREÇÃO CRÍTICA: Aplicar regras PDD para primeiro vencimento
            # Se mes_base e ano_base não foram fornecidos, usar valores padrão
            if not mes_base or not ano_base:
                hoje = datetime.now()
                mes_base = mes_base or hoje.month
                ano_base = ano_base or hoje.year

            primeiro_vencimento = None

            # ✅ CORREÇÃO CRÍTICA: O mês de reparcelamento É o mês de reajuste (não o próximo)
            # O mês base JÁ É o mês de reajuste (ex: out.-25 = outubro/2025)
            mes_reparcelamento = mes_base if mes_base else datetime.now().month
            ano_reparcelamento = ano_base if ano_base else datetime.now().year

            if tipo_reajuste and 'anivers' in tipo_reajuste and data_assinatura and mes_base and ano_base:
                # ✅ REGRA ANIVERSÁRIO PDD
                dia_aniversario = data_assinatura.day

                if dia_vencimento < dia_aniversario:
                    # Vencimento antes do aniversário: mês seguinte ao mês de reparcelamento
                    mes_venc = mes_reparcelamento + 1
                    ano_venc = ano_reparcelamento
                    if mes_venc > 12:
                        mes_venc = 1
                        ano_venc += 1
                    primeiro_vencimento = datetime(
                        ano_venc, mes_venc, dia_vencimento)
                else:
                    # Vencimento após ou igual ao aniversário: mês de reparcelamento
                    primeiro_vencimento = datetime(
                        ano_reparcelamento, mes_reparcelamento, dia_vencimento)
            else:
                # ✅ REGRA ANUAL PDD
                if mes_base and ano_base:
                    primeiro_vencimento = datetime(
                        ano_reparcelamento, mes_reparcelamento, dia_vencimento)
                else:
                    # Fallback: próximo mês disponível
                    proximo_mes = hoje.replace(day=1) + timedelta(days=31)
                    primeiro_vencimento = proximo_mes.replace(
                        day=dia_vencimento)

            # Se a data já passou, usar o mês seguinte
            if primeiro_vencimento.date() < hoje:
                primeiro_vencimento = (primeiro_vencimento.replace(
                    day=1) + timedelta(days=31)).replace(day=dia_vencimento)

            return {
                "sucesso": True,
                "data_primeiro_vencimento": primeiro_vencimento.isoformat(),
                "data_primeiro_vencimento_formatada": primeiro_vencimento.strftime("%d/%m/%Y"),
                "tipo_reajuste": tipo_reajuste,
                "dia_vencimento_usado": dia_vencimento,
                "observacao_regra": f"Primeiro vencimento no dia {dia_vencimento} aplicando regras PDD",
                "dias_ate_vencimento": (primeiro_vencimento.date() - hoje).days
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "data_primeiro_vencimento": None
            }

    def _regra_3_valor_parcela_atual_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 3 PDD: Valor da Parcela Atual CT (CONFORME PDD EXATO)

        CONFORME PDD (linhas 525-575):
        - Filtrar por Status da parcela = "a vencer"
        - Filtrar por Documento = "CT"  
        - Pegar o valor unitário da coluna "Valor original" (NÃO calcular média)
        - Valor mais comum (moda) das parcelas individuais
        """
        try:
            # Filtrar parcelas CT a vencer CONFORME PDD
            parcelas_ct = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ].copy()

            if parcelas_ct.empty:
                return {
                    "sucesso": False,
                    "motivo": "Nenhuma parcela CT a vencer encontrada",
                    "valor_parcela_base": 0
                }

            # PDD: Usar "Valor original" (valor unitário da parcela)
            # ✅ CORREÇÃO: Verificar coluna com fallbacks
            coluna_valor_original = None
            possiveis_nomes = [
                'Valor original', 'VALOR ORIGINAL', 'Valor Original', 'valor original']
            for nome in possiveis_nomes:
                if nome in parcelas_ct.columns:
                    coluna_valor_original = nome
                    break

            if not coluna_valor_original:
                return {
                    "sucesso": False,
                    "motivo": "Coluna obrigatória ausente: VALOR ORIGINAL",
                    "valor_parcela_base": 0
                }

            valores_unitarios = []
            for _, row in parcelas_ct.iterrows():
                try:
                    valor_str = str(
                        row.get(coluna_valor_original, "0")).replace(",", ".")
                    valor_unitario = float(valor_str)
                    if valor_unitario > 0:
                        valores_unitarios.append(valor_unitario)
                except Exception:
                    continue

            if not valores_unitarios:
                return {
                    "sucesso": False,
                    "motivo": "Valores de parcela unitários inválidos",
                    "valor_parcela_base": 0
                }

            valor_base = max(set(valores_unitarios),
                             key=valores_unitarios.count)

            self.logger.info(f"🎯 REGRA 3 PDD - Valor da Parcela Atual:")
            self.logger.info(
                f"   📊 Filtros aplicados: Status='a vencer' + Documento='CT'")
            self.logger.info(
                f"   📄 Parcelas CT encontradas: {len(parcelas_ct)}")
            self.logger.info(
                f"   💰 Valores unitários válidos: {len(valores_unitarios)}")
            self.logger.info(
                f"   💵 Valor mais comum (moda): R$ {valor_base:,.2f}")
            self.logger.info(
                f"   📈 Valores únicos encontrados: {len(set(valores_unitarios))}")

            if len(set(valores_unitarios)) > 1:
                self.logger.warning(
                    f"⚠️ Múltiplos valores encontrados: {set(valores_unitarios)}")
                self.logger.warning(
                    f"   Usando valor mais comum: R$ {valor_base:,.2f}")

            return {
                "sucesso": True,
                "valor_parcela_base": valor_base,
                "total_parcelas_analisadas": len(valores_unitarios),
                "valor_minimo": min(valores_unitarios),
                "valor_maximo": max(valores_unitarios),
                "valores_unicos": len(set(valores_unitarios)),
                "valor_mais_comum": valor_base,
                "metodo_calculo": "valor_unitario_moda_conforme_pdd"
            }

        except Exception as e:
            self.logger.error(f"❌ Erro na Regra 3 PDD: {str(e)}")
            return {
                "sucesso": False,
                "erro": str(e),
                "valor_parcela_base": 0
            }

    def _regra_4_parcelas_irregulares_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 4 PDD: Verificação de Parcelas CT com Valores Irregulares
        """
        try:
            valor_base_info = self._regra_3_valor_parcela_atual_csv(df)
            valor_base = valor_base_info.get("valor_parcela_base", 0)

            if valor_base == 0:
                return {
                    "sucesso": False,
                    "motivo": "Valor base não determinado",
                    "parcelas_irregulares": []
                }

            # Filtrar parcelas CT a vencer
            parcelas_ct = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ].copy()

            parcelas_irregulares = []
            for _, row in parcelas_ct.iterrows():
                try:
                    valor_original = float(
                        str(row.get(coluna_valor_original, "0")).replace(",", "."))

                    tipo_condicao = str(row.get("Tipo condição", "")).strip()

                    # Tolerância de 1% para diferenças
                    if valor_base > 0:
                        diferenca_percentual = abs(
                            valor_original - valor_base) / valor_base * 100

                        if diferenca_percentual > 1:
                            parcelas_irregulares.append({
                                "documento": row.get("Documento"),
                                "parcela_condicao": row.get("Parcela/Condição"),
                                "data_vencimento": row.get("Data vencimento"),
                                "valor_original": valor_original,
                                "valor_base": valor_base,
                                "tipo_condicao": tipo_condicao,
                                "diferenca_absoluta": valor_original - valor_base,
                                "diferenca_percentual": diferenca_percentual
                            })
                except:
                    continue

            return {
                "sucesso": True,
                "tem_irregularidades": len(parcelas_irregulares) > 0,
                "quantidade_irregulares": len(parcelas_irregulares),
                "parcelas_irregulares": parcelas_irregulares,
                "valor_base_referencia": valor_base
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "parcelas_irregulares": []
            }

    def _regra_5_parcelas_a_vencer_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 5 PDD: Quantidade de Parcelas a Vencer (CT e IPTU)
        """
        try:
            # Parcelas CT a vencer
            mask_vencer = df["Status da parcela"].str.upper(
            ).str.contains("VENCER", na=False)
            mask_ct = df["Documento"].str.contains("CT", case=False, na=False)
            parcelas_ct = df[mask_vencer & mask_ct]

            # Parcelas IPTU a vencer
            mask_iptu = df["Documento"].str.contains(
                "IPTU", case=False, na=False)
            parcelas_iptu = df[mask_vencer & mask_iptu]

            # Calcular valores
            valor_ct = 0
            # ✅ CORREÇÃO: Verificar coluna com fallbacks
            coluna_valor_original = None
            possiveis_nomes = [
                'Valor original', 'VALOR ORIGINAL', 'Valor Original', 'valor original']
            for nome in possiveis_nomes:
                if nome in parcelas_ct.columns:
                    coluna_valor_original = nome
                    break

            if not coluna_valor_original:
                return {
                    "sucesso": False,
                    "motivo": "Coluna obrigatória ausente: VALOR ORIGINAL",
                    "quantidade_ct_a_vencer": len(parcelas_ct),
                    "quantidade_iptu_a_vencer": len(parcelas_iptu),
                    "valor_total_ct": 0,
                    "valor_total_iptu": 0,
                    "saldo_total": 0,
                    "parcelas_ct_detalhes": [] if parcelas_ct.empty else parcelas_ct.to_dict('records'),
                    "parcelas_iptu_detalhes": [] if parcelas_iptu.empty else parcelas_iptu.to_dict('records')
                }
            for _, row in parcelas_ct.iterrows():
                try:
                    valor = float(
                        str(row.get(coluna_valor_original, "0")).replace(",", "."))
                    valor_ct += valor
                except:
                    continue

            valor_iptu = 0
            for _, row in parcelas_iptu.iterrows():
                try:
                    valor = float(
                        str(row.get("Valor a receber", "0")).replace(",", "."))
                    valor_iptu += valor
                except:
                    continue

            return {
                "sucesso": True,
                "quantidade_ct_a_vencer": len(parcelas_ct),
                "quantidade_iptu_a_vencer": len(parcelas_iptu),
                "valor_total_ct": valor_ct,
                "valor_total_iptu": valor_iptu,
                "saldo_total": valor_ct + valor_iptu,
                "parcelas_ct_detalhes": [] if parcelas_ct.empty else parcelas_ct.to_dict('records'),
                "parcelas_iptu_detalhes": [] if parcelas_iptu.empty else parcelas_iptu.to_dict('records')
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "quantidade_ct_a_vencer": 0,
                "quantidade_iptu_a_vencer": 0
            }

    def _regra_6_parcelas_vencidas_ct_csv(self, df: pd.DataFrame, mes_base: int = None, ano_base: int = None, tipo_reajuste: str = None, data_assinatura: datetime = None) -> Dict[str, Any]:
        """
        REGRA 6 PDD: Quantidade de Parcelas Vencidas CT (já implementada no método de inadimplência)
        """
        return self._aplicar_regra_inadimplencia_csv(df, mes_base, ano_base, tipo_reajuste, data_assinatura)

    def _regra_7_pendencias_rec_fat_iptu_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 7 PDD: Pendências IPTU e outros tipos (REC/FAT se existirem)
        """
        try:
            hoje = date.today()

            # Filtrar parcelas IPTU vencidas
            parcelas_iptu_vencidas = []
            parcelas_iptu = df[df["Documento"].str.contains(
                "IPTU", case=False, na=False)]

            for _, row in parcelas_iptu.iterrows():
                try:

                    try:
                        data_venc_str = str(row["Data vencimento"])
                        data_venc = pd.to_datetime(
                            data_venc_str, errors='coerce', dayfirst=True)
                        if pd.isna(data_venc):
                            continue
                        data_venc_date = data_venc.date()
                    except:
                        continue

                    status = str(row.get("Status da parcela", "")
                                 ).strip().upper()

                    # Vencida e não paga
                    vencida = data_venc_date < hoje
                    quitada = status in [
                        "PAGA", "QUITADA", "LIQUIDADA", "BAIXADA"]

                    if vencida and not quitada:
                        valor = 0
                        try:
                            valor = float(
                                str(row.get("Valor a receber", "0")).replace(",", "."))
                        except:
                            pass

                        parcelas_iptu_vencidas.append({
                            "documento": row.get("Documento"),
                            "data_vencimento": data_venc_date.isoformat(),
                            "status": status,
                            "valor": valor,
                            "tipo": "IPTU"
                        })
                except:
                    continue

            return {
                "sucesso": True,
                "quantidade_pendencias_iptu": len(parcelas_iptu_vencidas),
                "pendencias_iptu_detalhes": parcelas_iptu_vencidas,
                "valor_total_pendencias": sum(p["valor"] for p in parcelas_iptu_vencidas),
                "observacao": "Pendências IPTU não impedem reparcelamento (PDD 7.3.2)"
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "quantidade_pendencias_iptu": 0
            }

    def _consolidar_resultados_completos(self, regras_aplicadas: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consolida resultados de todas as regras 9.1.1 em formato estruturado
        """
        try:
            # ✅ EXTRAIR DADOS PRINCIPAIS SEM FALLBACKS
            dia_vencimento = regras_aplicadas["regra_1"].get("dia_vencimento")
            if not isinstance(dia_vencimento, int) or dia_vencimento < 1 or dia_vencimento > 31:
                return {
                    "sucesso": False,
                    "erro": "Dia de vencimento inválido ou ausente no relatório do Sienge"
                }
            primeiro_vencimento = regras_aplicadas["regra_2"].get(
                "data_primeiro_vencimento_formatada")
            valor_parcela_base = regras_aplicadas["regra_3"].get(
                "valor_parcela_base", 0)

            irregularidades = regras_aplicadas["regra_4"]
            parcelas_info = regras_aplicadas["regra_5"]
            ct_vencidas_info = regras_aplicadas["regra_6"]
            pendencias_info = regras_aplicadas["regra_7"]

            return {
                "sucesso": True,
                "dia_vencimento": dia_vencimento,
                "valor_parcela_atual": valor_parcela_base,
                "primeiro_vencimento_carne": primeiro_vencimento,
                "tem_parcelas_irregulares": irregularidades.get("tem_irregularidades", False),
                "quantidade_irregulares": irregularidades.get("quantidade_irregulares", 0),
                "parcelas_divergentes": irregularidades.get("parcelas_irregulares", []),
                "qtd_parcelas_ct_a_vencer": parcelas_info.get("quantidade_ct_a_vencer", 0),
                "qtd_parcelas_iptu_a_vencer": parcelas_info.get("quantidade_iptu_a_vencer", 0),
                "qtd_pendencias_iptu": pendencias_info.get("quantidade_pendencias_iptu", 0),
                "saldo_total": parcelas_info.get("saldo_total", 0),
                "valor_total_ct": parcelas_info.get("valor_total_ct", 0),
                "valor_total_iptu": parcelas_info.get("valor_total_iptu", 0),
                "valor_total_vencido": ct_vencidas_info.get("valor_total_vencido", 0),
                "parcelas_ct_vencidas_detalhes": ct_vencidas_info.get("ct_vencidas_detalhes", []),
                "pendencias_iptu_detalhes": pendencias_info.get("pendencias_iptu_detalhes", []),
                "parcelas_ct_a_vencer_detalhes": parcelas_info.get("parcelas_ct_detalhes", []),
                "parcelas_iptu_a_vencer_detalhes": parcelas_info.get("parcelas_iptu_detalhes", []),
                "tipo_reajuste": "ANUAL",
                "indexador": "IGP-M",
                "juros_fixo": 8.0,
                "tipo_condicao": "PM",
                "regras_pdd_aplicadas": "REGRAS_COMPLETAS_9_1_1",
                "total_regras_aplicadas": 8,
                "todas_regras_sucesso": all(
                    regra.get("sucesso", False) for regra in regras_aplicadas.values()
                ),
                "timestamp_processamento": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro na consolidação: {str(e)}"
            }

    # ============= CÁLCULOS FINANCEIROS =============

    async def calcular_valores_reparcelamento(self, saldo_atual: float, indice_igpm: Optional[float] = None,
                                              parcelas_pendentes: int = 0) -> Dict[str, Any]:
        """
        Calcula valores para reparcelamento conforme regras PDD
        """
        try:
            # Se IGPM não foi fornecido, tentar buscar no MongoDB
            if indice_igpm is None:
                from core.data_manager import data_manager
                indice_igpm = await data_manager.obter_indice_mais_recente("igpm")

                if indice_igpm is None:
                    return {
                        "sucesso": False,
                        "erro": "IGPM não disponível",
                        "acao_requerida": "EXECUTAR_RPA_COLETA_INDICES"
                    }

            # Aplicar correção IGP-M
            fator_correcao = 1 + (indice_igpm / 100)
            novo_saldo = saldo_atual * fator_correcao
            novo_saldo = float(Decimal(str(novo_saldo)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP))

            # Data primeiro vencimento (próximo mês, dia 15)
            hoje = date.today()
            primeiro_vencimento = (hoje.replace(
                day=1) + timedelta(days=31)).replace(day=15)

            # REGRA PDD: Quantidade de parcelas deve ser 12 (não todas as pendentes)
            quantidade_parcelas_reparcelamento = min(parcelas_pendentes, 12)

            # Valores para preenchimento no Sienge
            valores_sienge = {
                "detalhamento": f"CORREÇÃO {hoje.strftime('%m/%y')}",
                "tipo_condicao": "PM",
                "valor_total": novo_saldo,
                "quantidade_parcelas": quantidade_parcelas_reparcelamento,
                "data_primeiro_vencimento": primeiro_vencimento.strftime("%d/%m/%Y"),
                "indexador": "1 IGP-M",
                "tipo_juros": "Fixo",
                "percentual_juros": 8.0
            }

            return {
                "sucesso": True,
                "valores_sienge": valores_sienge,
                "novo_saldo": novo_saldo,
                "fator_correcao": fator_correcao,
                "diferenca_correcao": novo_saldo - saldo_atual,
                "igpm_utilizado": indice_igpm
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro no cálculo: {str(e)}"
            }

    def determinar_parcelas_desmarcar(self, parcelas_ct_a_vencer: List[Dict]) -> List[Dict]:
        """
        Determina quais parcelas devem ser desmarcadas conforme regras PDD

        MOMENTO DE DISPARO:
        1. Durante processamento de dados (RPA Análise Planilhas)
        2. Durante webscraping (RPA Sienge - Passo 23)

        DADOS BUSCADOS:
        - Data vencimento (campo obrigatório)
        - Documento (ex: CT-12/84)
        - Valor a receber
        - Motivo da desmarcação (para auditoria)

        REGRA CRÍTICA PDD:
        - DESMARCAR se Data vencimento <= Data atual
        - MANTER MARCADAS se Data vencimento > Data atual
        """
        try:
            hoje = date.today()
            parcelas_desmarcar = []

            # Usar estratégia conservadora (apenas vencidas)
            estrategia = "CONSERVADORA"
            data_limite = hoje
            descricao_limite = "já vencidas"

            self.logger.info(
                f"🎯 Aplicando estratégia {estrategia} - limite: {data_limite.strftime('%d/%m/%Y')}")
            for parcela in parcelas_ct_a_vencer:
                data_vencimento = parcela.get("Data vencimento")

                # Converter data com validação robusta
                if isinstance(data_vencimento, str):
                    data_obj = pd.to_datetime(
                        data_vencimento, errors='coerce', dayfirst=True)
                    if pd.notna(data_obj) and isinstance(data_obj, pd.Timestamp):
                        data_obj = data_obj.date()
                    else:
                        self.logger.warning(
                            f"Data inválida ignorada: {data_vencimento}")
                        continue
                elif isinstance(data_vencimento, (date, datetime)):
                    data_obj = data_vencimento.date() if isinstance(
                        data_vencimento, datetime) else data_vencimento
                else:
                    self.logger.warning(
                        f"Formato de data não reconhecido: {type(data_vencimento)}")
                    continue

                # APLICAR REGRA CONFORME ESTRATÉGIA
                if data_obj <= data_limite:
                    # Calcular informações adicionais
                    dias_diferenca = (data_obj - hoje).days
                    status_vencimento = "VENCIDA" if dias_diferenca < 0 else "MES_ATUAL" if dias_diferenca == 0 else "FUTURA"

                    # Determinar motivo específico
                    if dias_diferenca < 0:
                        motivo = f"Parcela vencida há {abs(dias_diferenca)} dias"
                    elif dias_diferenca == 0:
                        motivo = f"Parcela vence hoje"
                    else:
                        motivo = f"Parcela {descricao_limite}"

                    parcela_info = {
                        "documento": parcela.get("Documento"),
                        "parcela_condicao": parcela.get("Parcela/Condição", "N/A"),
                        "data_vencimento": data_obj.strftime("%d/%m/%Y"),
                        "valor": float(parcela.get("Valor a receber", 0)),
                        "motivo": motivo,
                        "estrategia_aplicada": "CONSERVADORA",
                        "status_vencimento": status_vencimento,
                        "dias_diferenca": dias_diferenca,
                        "prioridade": 1 if dias_diferenca < 0 else 2 if dias_diferenca == 0 else 3
                    }

                    parcelas_desmarcar.append(parcela_info)

            # Ordenar por prioridade (vencidas primeiro)
            parcelas_desmarcar.sort(key=lambda x: (
                x["prioridade"], x["data_vencimento"]))

            # REGRA PDD: Limitar a 12 parcelas para reparcelamento
            parcelas_para_reparcelamento = 12
            parcelas_restantes = len(
                parcelas_ct_a_vencer) - len(parcelas_desmarcar)

            # Se há mais de 12 parcelas restantes, desmarcar as excedentes
            if parcelas_restantes > parcelas_para_reparcelamento:
                parcelas_excedentes = parcelas_restantes - parcelas_para_reparcelamento
                # Pegar as últimas parcelas (mais distantes) para desmarcar
                parcelas_futuras = [
                    p for p in parcelas_ct_a_vencer if p not in parcelas_desmarcar]
                parcelas_futuras.sort(
                    key=lambda x: x.get("Data vencimento", ""))

                for i in range(parcelas_excedentes):
                    if i < len(parcelas_futuras):
                        parcela = parcelas_futuras[-(i+1)]  # Pegar as últimas
                        parcela_info = {
                            "documento": parcela.get("Documento"),
                            "parcela_condicao": parcela.get("Parcela/Condição", "N/A"),
                            "data_vencimento": parcela.get("Data vencimento", "N/A"),
                            "valor": float(parcela.get("Valor a receber", 0)),
                            "motivo": f"Parcela excedente - limite PDD de {parcelas_para_reparcelamento} parcelas",
                            "estrategia_aplicada": "LIMITE_PDD_12",
                            "status_vencimento": "FUTURA_EXCEDENTE",
                            "dias_diferenca": 0,
                            "prioridade": 4
                        }
                        parcelas_desmarcar.append(parcela_info)

            # Log de auditoria
            total_valor = sum(p["valor"] for p in parcelas_desmarcar)
            self.logger.info(f"📋 Parcelas para desmarcar: {len(parcelas_desmarcar)} "
                             f"(R$ {total_valor:,.2f}) - Estratégia: CONSERVADORA + LIMITE_PDD_12")
            self.logger.info(
                f"📊 Parcelas restantes para reparcelamento: {parcelas_para_reparcelamento}")

            if parcelas_desmarcar:
                self.logger.info(f"📊 Distribuição:")
                vencidas = len(
                    [p for p in parcelas_desmarcar if p["status_vencimento"] == "VENCIDA"])
                mes_atual = len(
                    [p for p in parcelas_desmarcar if p["status_vencimento"] == "MES_ATUAL"])
                futuras = len(
                    [p for p in parcelas_desmarcar if p["status_vencimento"] == "FUTURA"])
                self.logger.info(
                    f"   - Vencidas: {vencidas}, Mês atual: {mes_atual}, Futuras: {futuras}")

            return parcelas_desmarcar

        except Exception as e:
            self.logger.error(
                f"Erro ao determinar parcelas para desmarcar: {str(e)}")
            import traceback
            self.logger.error(f"Detalhes: {traceback.format_exc()}")
            return []

    def _filtrar_parcelas_por_mes_base_pdd(self, parcelas_ct_todas: pd.DataFrame, mes_base: int, ano_base: int,
                                           tipo_reajuste: str, data_assinatura: datetime) -> pd.DataFrame:
        """
        ✅ CORREÇÃO PDD: Filtra parcelas conforme regra PDD de "parcelas a partir do mês base do reparcelamento"

        Regras PDD:
        - Anual: apenas parcelas com vencimento dentro do mês base da correção
        - Aniversário: considerar regra do aniversário (mês seguinte se após aniversário)

        Args:
            parcelas_ct_todas: DataFrame com todas as parcelas CT
            mes_base: Mês base do reparcelamento
            ano_base: Ano base do reparcelamento
            tipo_reajuste: Tipo de reajuste ('anual' ou 'aniversário')
            data_assinatura: Data de assinatura do contrato

        Returns:
            DataFrame com parcelas filtradas conforme regra PDD
        """
        try:
            if parcelas_ct_todas.empty:
                self.logger.info(
                    "🔍 [PDD] Nenhuma parcela CT para filtrar")
                return parcelas_ct_todas

            # Converter para DataFrame se necessário
            if not isinstance(parcelas_ct_todas, pd.DataFrame):
                parcelas_ct_todas = pd.DataFrame(parcelas_ct_todas)

            parcelas_filtradas = []
            tipo_reajuste_lower = str(
                tipo_reajuste).lower() if tipo_reajuste else "anual"

            self.logger.info(
                f"🔍 [PDD] Filtrando parcelas por mês base: {mes_base:02d}/{ano_base}")
            self.logger.info(
                f"🔍 [PDD] Tipo de reajuste: {tipo_reajuste_lower}")

            for _, parcela in parcelas_ct_todas.iterrows():
                try:
                    # Processar data de vencimento (tentar diferentes nomes de coluna)
                    data_venc_str = None
                    for col_name in ["DATA VENCIMENTO", "Data vencimento", "data_vencimento"]:
                        if col_name in parcela:
                            data_venc_str = str(
                                parcela.get(col_name, "")).strip()
                            break

                    if not data_venc_str or data_venc_str in ['', '#N/A', 'N/A', '#REF!', '#VALUE!', 'null', 'None']:
                        self.logger.debug(
                            f"🔍 [PDD] Parcela sem data válida: {data_venc_str}")
                        continue

                    # Tentar diferentes formatos de data
                    data_vencimento = None
                    formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]

                    for formato in formatos:
                        try:
                            data_vencimento = datetime.strptime(
                                data_venc_str, formato)
                            break
                        except ValueError:
                            continue

                    if not data_vencimento:
                        self.logger.debug(
                            f"🔍 [PDD] Não foi possível processar data: {data_venc_str}")
                        continue

                    self.logger.debug(
                        f"🔍 [PDD] Processando parcela: {data_vencimento.strftime('%d/%m/%Y')}")

                    # Aplicar regras PDD conforme tipo de reajuste
                    incluir_parcela = False

                    if 'anivers' in tipo_reajuste_lower and data_assinatura:
                        # ✅ REGRA ANIVERSÁRIO PDD
                        dia_aniversario = data_assinatura.day
                        dia_vencimento = data_vencimento.day

                        self.logger.debug(
                            f"🔍 [PDD] Aniversário dia {dia_aniversario}, vencimento dia {dia_vencimento}")

                        if dia_vencimento < dia_aniversario:
                            # Vencimento antes do aniversário: mês base
                            if data_vencimento.month == mes_base and data_vencimento.year == ano_base:
                                incluir_parcela = True
                                self.logger.debug(
                                    f"🔍 [PDD] Aniversário - antes: {data_vencimento.strftime('%d/%m/%Y')} (mês base)")
                            else:
                                self.logger.debug(
                                    f"🔍 [PDD] Aniversário - antes: {data_vencimento.strftime('%d/%m/%Y')} (fora do mês base)")
                        else:
                            # Vencimento após aniversário: mês seguinte
                            mes_venc = mes_base + 1
                            ano_venc = ano_base
                            if mes_venc > 12:
                                mes_venc = 1
                                ano_venc += 1

                            if data_vencimento.month == mes_venc and data_vencimento.year == ano_venc:
                                incluir_parcela = True
                                self.logger.debug(
                                    f"🔍 [PDD] Aniversário - após: {data_vencimento.strftime('%d/%m/%Y')} (mês seguinte)")
                            else:
                                self.logger.debug(
                                    f"🔍 [PDD] Aniversário - após: {data_vencimento.strftime('%d/%m/%Y')} (fora do mês seguinte)")
                    else:
                        # ✅ REGRA ANUAL PDD
                        if data_vencimento.month == mes_base and data_vencimento.year == ano_base:
                            incluir_parcela = True
                            self.logger.debug(
                                f"🔍 [PDD] Anual: {data_vencimento.strftime('%d/%m/%Y')} (mês base)")
                        else:
                            self.logger.debug(
                                f"🔍 [PDD] Anual: {data_vencimento.strftime('%d/%m/%Y')} (fora do mês base)")

                    if incluir_parcela:
                        parcelas_filtradas.append(parcela)
                        self.logger.debug(
                            f"🔍 [PDD] Parcela incluída: {data_vencimento.strftime('%d/%m/%Y')}")
                    else:
                        self.logger.debug(
                            f"🔍 [PDD] Parcela excluída: {data_vencimento.strftime('%d/%m/%Y')}")

                except Exception as e:
                    self.logger.warning(
                        f"🔍 [PDD] Erro ao processar parcela: {str(e)}")
                    continue

            # Criar DataFrame com parcelas filtradas
            if parcelas_filtradas:
                df_filtrado = pd.DataFrame(parcelas_filtradas)
                self.logger.info(
                    f"🔍 [PDD] Parcelas filtradas: {len(df_filtrado)} de {len(parcelas_ct_todas)}")
                return df_filtrado
            else:
                self.logger.warning(
                    f"🔍 [PDD] Nenhuma parcela atende aos critérios de filtro PDD")
                return pd.DataFrame()  # Retorna DataFrame vazio

        except Exception as e:
            self.logger.error(
                f"🔍 [PDD] Erro ao filtrar parcelas por mês base: {str(e)}")
            # Em caso de erro, retorna todas as parcelas (comportamento anterior)
            return parcelas_ct_todas

    def _retorno_erro(self, erro: str, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """Helper para retornos de erro padronizados"""
        return {
            "cliente": cliente,
            "numero_titulo": numero_titulo,
            "sucesso": False,
            "erro": erro,
            "pode_reparcelar": False,
            "status_cliente": "ERRO_PROCESSAMENTO",
            "data_processamento": datetime.now().isoformat()
        }


# ============= CLASSES LEGACY PARA COMPATIBILIDADE =============

class ValidadorInadimplenciaPDD:
    """Wrapper de compatibilidade - usa ProcessadorRegrasNegocio"""

    def __init__(self):
        self.processador = ProcessadorRegrasNegocio()

    def validar_cliente(self, df_planilha: pd.DataFrame, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        return self.processador._aplicar_regra_inadimplencia_csv(df_planilha)


class CalculadoraReparcelamentoPDD:
    """Wrapper de compatibilidade - usa ProcessadorRegrasNegocio"""

    def __init__(self):
        self.processador = ProcessadorRegrasNegocio()

    async def calcular_valores_sienge(self, saldo_atual: float, indice_igpm: float, parcelas_pendentes: int) -> Dict[str, Any]:
        return await self.processador.calcular_valores_reparcelamento(saldo_atual, indice_igpm, parcelas_pendentes)

    def determinar_parcelas_desmarcar(self, parcelas_ct_a_vencer: List[Dict]) -> List[Dict]:
        return self.processador.determinar_parcelas_desmarcar(parcelas_ct_a_vencer)
