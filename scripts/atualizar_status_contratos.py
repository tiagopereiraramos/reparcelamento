#!/usr/bin/env python3
"""
Script para atualizar status de contratos na fila.

Permite atualizar o status de um ou múltiplos contratos na fila_contratos.json
usando códigos de cliente ou números de título.

Uso:
    python scripts/atualizar_status_contratos.py --codigos 657,123 --status PENDENTE
    python scripts/atualizar_status_contratos.py --titulos 715,1234 --status ERRO
    python scripts/atualizar_status_contratos.py --codigo 657 --status PROCESSANDO
    python scripts/atualizar_status_contratos.py --titulo 715 --status APROVACAO_REALIZADA
"""

from core.status_enum import StatusContrato
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

# Adicionar o diretório raiz ao path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))


def carregar_fila_contratos(caminho_arquivo: str) -> List[dict]:
    """
    Carrega a fila de contratos do arquivo JSON.

    Args:
        caminho_arquivo: Caminho para o arquivo fila_contratos.json

    Returns:
        Lista de contratos

    Raises:
        FileNotFoundError: Se o arquivo não existir
        json.JSONDecodeError: Se o arquivo não for JSON válido
    """
    if not os.path.exists(caminho_arquivo):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)


def salvar_fila_contratos(caminho_arquivo: str, contratos: List[dict]) -> None:
    """
    Salva a fila de contratos no arquivo JSON.

    Args:
        caminho_arquivo: Caminho para o arquivo fila_contratos.json
        contratos: Lista de contratos atualizada
    """
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        json.dump(contratos, f, ensure_ascii=False, indent=2)


def encontrar_contratos_por_codigo(contratos: List[dict], codigos: List[str]) -> List[dict]:
    """
    Encontra contratos pelo código do cliente.

    Args:
        contratos: Lista de contratos
        codigos: Lista de códigos de cliente

    Returns:
        Lista de contratos encontrados
    """
    encontrados = []
    codigos_str = [str(codigo).strip() for codigo in codigos]

    for contrato in contratos:
        codigo_cliente = str(contrato.get("Código Cliente", "")).strip()
        if codigo_cliente in codigos_str:
            encontrados.append(contrato)

    return encontrados


def encontrar_contratos_por_titulo(contratos: List[dict], titulos: List[str]) -> List[dict]:
    """
    Encontra contratos pelo número do título.

    Args:
        contratos: Lista de contratos
        titulos: Lista de números de título

    Returns:
        Lista de contratos encontrados
    """
    encontrados = []
    titulos_str = [str(titulo).strip() for titulo in titulos]

    for contrato in contratos:
        titulo = str(contrato.get("Titulo", "")).strip()
        if titulo in titulos_str:
            encontrados.append(contrato)

    return encontrados


def atualizar_status_contratos(
    contratos: List[dict],
    contratos_encontrados: List[dict],
    novo_status: StatusContrato,
    adicionar_metadata: bool = True
) -> int:
    """
    Atualiza o status dos contratos encontrados.

    Args:
        contratos: Lista completa de contratos
        contratos_encontrados: Contratos a serem atualizados
        novo_status: Novo status a ser aplicado
        adicionar_metadata: Se deve adicionar metadados de atualização

    Returns:
        Número de contratos atualizados
    """
    atualizados = 0

    for contrato_encontrado in contratos_encontrados:
        # Encontrar o contrato na lista original
        for i, contrato in enumerate(contratos):
            if contrato == contrato_encontrado:
                # Atualizar status
                contratos[i]["status"] = novo_status.value

                # Adicionar metadados se solicitado
                if adicionar_metadata:
                    contratos[i]["status_atualizado_em"] = datetime.now(
                    ).isoformat()
                    contratos[i]["status_anterior"] = contrato.get(
                        "status", "N/A")

                atualizados += 1
                break

    return atualizados


def exibir_contratos_encontrados(contratos: List[dict]) -> None:
    """
    Exibe informações dos contratos encontrados.

    Args:
        contratos: Lista de contratos encontrados
    """
    if not contratos:
        print("❌ Nenhum contrato encontrado.")
        return

    print(f"📋 {len(contratos)} contrato(s) encontrado(s):")
    print("-" * 80)

    for i, contrato in enumerate(contratos, 1):
        codigo = contrato.get("Código Cliente", "N/A")
        cliente = contrato.get("Cliente", "N/A")
        titulo = contrato.get("Titulo", "N/A")
        status_atual = contrato.get("status", "N/A")

        print(
            f"{i:2d}. Código: {codigo} | Cliente: {cliente} | Título: {titulo} | Status: {status_atual}")


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Atualiza status de contratos na fila",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Atualizar por códigos de cliente
  python scripts/atualizar_status_contratos.py --codigos 657,123 --status PENDENTE
  
  # Atualizar por números de título
  python scripts/atualizar_status_contratos.py --titulos 715,1234 --status ERRO
  
  # Atualizar um único contrato
  python scripts/atualizar_status_contratos.py --codigo 657 --status PROCESSANDO
  
  # Listar status disponíveis
  python scripts/atualizar_status_contratos.py --listar-status
        """
    )

    # Argumentos para busca
    grupo_busca = parser.add_mutually_exclusive_group(required=False)
    grupo_busca.add_argument(
        "--codigo",
        type=str,
        help="Código único do cliente"
    )
    grupo_busca.add_argument(
        "--codigos",
        type=str,
        help="Códigos do cliente separados por vírgula (ex: 657,123,456)"
    )
    grupo_busca.add_argument(
        "--titulo",
        type=str,
        help="Número único do título"
    )
    grupo_busca.add_argument(
        "--titulos",
        type=str,
        help="Números de título separados por vírgula (ex: 715,1234,5678)"
    )

    # Argumentos para status
    parser.add_argument(
        "--status",
        type=str,
        help=f"Novo status para os contratos. Status válidos: {', '.join(StatusContrato.list_all())}"
    )

    # Argumentos opcionais
    parser.add_argument(
        "--arquivo",
        type=str,
        default="data/fila_contratos.json",
        help="Caminho para o arquivo fila_contratos.json (padrão: data/fila_contratos.json)"
    )
    parser.add_argument(
        "--sem-metadata",
        action="store_true",
        help="Não adicionar metadados de atualização (status_atualizado_em, status_anterior)"
    )
    parser.add_argument(
        "--listar-status",
        action="store_true",
        help="Lista todos os status disponíveis e sai"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria feito sem fazer as alterações"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostra informações detalhadas"
    )

    args = parser.parse_args()

    # Listar status se solicitado
    if args.listar_status:
        print("📋 Status disponíveis:")
        for status in StatusContrato:
            print(f"  - {status.value}")
        return

    # Validar argumentos obrigatórios
    if not any([args.codigo, args.codigos, args.titulo, args.titulos]):
        print("❌ Erro: É necessário especificar --codigo, --codigos, --titulo ou --titulos")
        parser.print_help()
        sys.exit(1)

    if not args.status:
        print("❌ Erro: É necessário especificar --status")
        parser.print_help()
        sys.exit(1)

    # Validar status
    try:
        novo_status = StatusContrato.from_string(args.status)
    except ValueError as e:
        print(f"❌ Erro: {e}")
        print(f"Status válidos: {', '.join(StatusContrato.list_all())}")
        sys.exit(1)

    try:
        # Carregar fila de contratos
        print(f"📂 Carregando fila de contratos: {args.arquivo}")
        contratos = carregar_fila_contratos(args.arquivo)
        print(f"✅ {len(contratos)} contratos carregados")

        # Encontrar contratos
        contratos_encontrados = []

        if args.codigo:
            codigos = [args.codigo]
            contratos_encontrados = encontrar_contratos_por_codigo(
                contratos, codigos)
            print(f"🔍 Buscando por código: {args.codigo}")

        elif args.codigos:
            codigos = [c.strip() for c in args.codigos.split(',')]
            contratos_encontrados = encontrar_contratos_por_codigo(
                contratos, codigos)
            print(f"🔍 Buscando por códigos: {', '.join(codigos)}")

        elif args.titulo:
            titulos = [args.titulo]
            contratos_encontrados = encontrar_contratos_por_titulo(
                contratos, titulos)
            print(f"🔍 Buscando por título: {args.titulo}")

        elif args.titulos:
            titulos = [t.strip() for t in args.titulos.split(',')]
            contratos_encontrados = encontrar_contratos_por_titulo(
                contratos, titulos)
            print(f"🔍 Buscando por títulos: {', '.join(titulos)}")

        # Exibir contratos encontrados
        exibir_contratos_encontrados(contratos_encontrados)

        if not contratos_encontrados:
            print("❌ Nenhum contrato encontrado com os critérios especificados.")
            sys.exit(1)

        # Confirmar atualização
        if args.dry_run:
            print(f"\n🔍 DRY RUN - O que seria feito:")
            print(
                f"   Status atual: {contratos_encontrados[0].get('status', 'N/A')}")
            print(f"   Novo status: {novo_status.value}")
            print(
                f"   Contratos a serem atualizados: {len(contratos_encontrados)}")
            return

        # Atualizar status
        print(f"\n🔄 Atualizando status para: {novo_status.value}")
        atualizados = atualizar_status_contratos(
            contratos,
            contratos_encontrados,
            novo_status,
            adicionar_metadata=not args.sem_metadata
        )

        # Salvar arquivo
        print(f"💾 Salvando alterações...")
        salvar_fila_contratos(args.arquivo, contratos)

        print(
            f"✅ Sucesso! {atualizados} contrato(s) atualizado(s) para status '{novo_status.value}'")

        if args.verbose:
            print(f"\n📊 Resumo da operação:")
            print(f"   - Contratos encontrados: {len(contratos_encontrados)}")
            print(f"   - Contratos atualizados: {atualizados}")
            print(f"   - Novo status: {novo_status.value}")
            print(f"   - Arquivo: {args.arquivo}")

    except FileNotFoundError as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao ler arquivo JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
