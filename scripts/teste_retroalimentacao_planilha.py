import sys
import os
import pandas as pd
from core.processador_regras_pdd import ProcessadorRegrasNegocio

if __name__ == "__main__":
    print("\n=== Teste de Retroalimentação da Planilha (Simulação) ===\n")
    caminho_arquivo = input(
        "Caminho do arquivo Excel (ex: planilhas_sienge/arquivo.xlsx): ").strip()
    cliente = input("Nome do cliente (exatamente como no relatório): ").strip()
    numero_titulo = input(
        "Número do título (exatamente como no relatório): ").strip()

    if not os.path.exists(caminho_arquivo):
        print(f"❌ Arquivo não encontrado: {caminho_arquivo}")
        sys.exit(1)

    try:
        df = pd.read_excel(caminho_arquivo)
    except Exception as e:
        print(f"❌ Erro ao carregar o arquivo: {e}")
        sys.exit(1)

    processador = ProcessadorRegrasNegocio()
    resultado = processador.processar_dados_cliente_completo(
        df, cliente, numero_titulo)

    print("\n--- Dados extraídos para retroalimentação ---")
    if not resultado.get("sucesso"):
        print(f"❌ Erro: {resultado.get('erro', 'Processamento falhou')}")
        sys.exit(1)

    campos = [
        ("Valor da Parcela Base", resultado.get("valor_parcela_atual")),
        ("Parcelas a vencer", resultado.get("qtd_parcelas_ct_a_vencer")),
        ("Saldo total", resultado.get("saldo_total")),
        ("Dia de vencimento", resultado.get("dia_vencimento")),
        ("1º vencimento carnê", resultado.get("primeiro_vencimento_carne")),
        ("Status do cliente", resultado.get("status_cliente")),
        ("Pode reparcelar?", resultado.get("pode_reparcelar")),
    ]
    for nome, valor in campos:
        print(f"{nome:25}: {valor}")

    print("\n--- Fim do teste ---\n")
