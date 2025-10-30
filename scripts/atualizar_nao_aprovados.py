#!/usr/bin/env python3
"""
Script para atualizar todos os contratos não aprovados para APROVACAO_REALIZADA.

Este script identifica todos os contratos que NÃO estão com status APROVACAO_REALIZADA
e os atualiza para esse status, permitindo que sejam processados novamente.

Uso:
    python scripts/atualizar_nao_aprovados.py [--dry-run] [--verbose]
"""

from core.status_enum import StatusContrato
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Adicionar o diretório raiz ao path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))


def carregar_fila_contratos(caminho_arquivo: str) -> List[Dict[str, Any]]:
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
    if not Path(caminho_arquivo).exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)


def salvar_fila_contratos(caminho_arquivo: str, contratos: List[Dict[str, Any]]) -> None:
    """
    Salva a fila de contratos no arquivo JSON.

    Args:
        caminho_arquivo: Caminho para o arquivo fila_contratos.json
        contratos: Lista de contratos atualizada
    """
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        json.dump(contratos, f, ensure_ascii=False, indent=2)


def analisar_status_contratos(contratos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analisa a distribuição de status dos contratos.

    Args:
        contratos: Lista de contratos

    Returns:
        Dicionário com estatísticas dos status
    """
    from collections import Counter

    status_count = Counter(contrato.get('status', 'N/A')
                           for contrato in contratos)

    # Identificar contratos não aprovados
    nao_aprovados = [
        contrato for contrato in contratos
        if contrato.get('status') != StatusContrato.APROVACAO_REALIZADA.value
    ]

    return {
        'total_contratos': len(contratos),
        'status_distribuicao': dict(status_count),
        'nao_aprovados': nao_aprovados,
        'total_nao_aprovados': len(nao_aprovados),
        'aprovados': len(contratos) - len(nao_aprovados)
    }


def exibir_estatisticas(estatisticas: Dict[str, Any]) -> None:
    """
    Exibe estatísticas dos contratos.

    Args:
        estatisticas: Estatísticas dos contratos
    """
    print("📊 ANÁLISE DA FILA DE CONTRATOS")
    print("=" * 60)
    print(f"📋 Total de contratos: {estatisticas['total_contratos']}")
    print(f"✅ Contratos aprovados: {estatisticas['aprovados']}")
    print(f"❌ Contratos NÃO aprovados: {estatisticas['total_nao_aprovados']}")

    print("\n📈 DISTRIBUIÇÃO DE STATUS:")
    print("-" * 40)
    for status, count in sorted(estatisticas['status_distribuicao'].items(),
                                key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count} contratos")

    if estatisticas['total_nao_aprovados'] > 0:
        print(f"\n🔍 CONTRATOS QUE SERÃO ATUALIZADOS:")
        print("-" * 60)
        for i, contrato in enumerate(estatisticas['nao_aprovados'][:10], 1):
            codigo = contrato.get('Código Cliente', 'N/A')
            cliente = contrato.get('Cliente', 'N/A')
            titulo = contrato.get('Titulo', 'N/A')
            status = contrato.get('status', 'N/A')
            print(
                f"{i:2d}. Código: {codigo} | Cliente: {cliente} | Título: {titulo} | Status: {status}")

        if len(estatisticas['nao_aprovados']) > 10:
            print(
                f"    ... e mais {len(estatisticas['nao_aprovados']) - 10} contratos")


def atualizar_contratos_nao_aprovados(
    contratos: List[Dict[str, Any]],
    adicionar_metadata: bool = True
) -> int:
    """
    Atualiza todos os contratos não aprovados para APROVACAO_REALIZADA.

    Args:
        contratos: Lista completa de contratos
        adicionar_metadata: Se deve adicionar metadados de atualização

    Returns:
        Número de contratos atualizados
    """
    atualizados = 0

    for contrato in contratos:
        status_atual = contrato.get('status', 'N/A')

        if status_atual != StatusContrato.APROVACAO_REALIZADA.value:
            # Salvar status anterior
            status_anterior = status_atual

            # Atualizar para APROVACAO_REALIZADA
            contrato['status'] = StatusContrato.APROVACAO_REALIZADA.value

            # Adicionar metadados se solicitado
            if adicionar_metadata:
                contrato['status_atualizado_em'] = datetime.now().isoformat()
                contrato['status_anterior'] = status_anterior
                contrato['atualizado_por_script'] = 'atualizar_nao_aprovados.py'

            atualizados += 1

    return atualizados


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Atualiza todos os contratos não aprovados para APROVACAO_REALIZADA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Análise sem alterações
  python scripts/atualizar_nao_aprovados.py --dry-run
  
  # Atualização real
  python scripts/atualizar_nao_aprovados.py
  
  # Com informações detalhadas
  python scripts/atualizar_nao_aprovados.py --verbose
  
  # Sem metadados de atualização
  python scripts/atualizar_nao_aprovados.py --sem-metadata
        """
    )

    parser.add_argument(
        "--arquivo",
        type=str,
        default="data/fila_contratos.json",
        help="Caminho para o arquivo fila_contratos.json (padrão: data/fila_contratos.json)"
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
    parser.add_argument(
        "--sem-metadata",
        action="store_true",
        help="Não adicionar metadados de atualização"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Criar backup do arquivo antes da atualização"
    )

    args = parser.parse_args()

    try:
        # Carregar fila de contratos
        print(f"📂 Carregando fila de contratos: {args.arquivo}")
        contratos = carregar_fila_contratos(args.arquivo)
        print(f"✅ {len(contratos)} contratos carregados")

        # Analisar status
        estatisticas = analisar_status_contratos(contratos)
        exibir_estatisticas(estatisticas)

        # Verificar se há contratos para atualizar
        if estatisticas['total_nao_aprovados'] == 0:
            print("\n✅ Todos os contratos já estão com status APROVACAO_REALIZADA!")
            print("🎯 Nenhuma atualização necessária.")
            return

        # Dry run
        if args.dry_run:
            print(f"\n🔍 DRY RUN - O que seria feito:")
            print(
                f"   📊 Contratos a serem atualizados: {estatisticas['total_nao_aprovados']}")
            print(
                f"   📝 Novo status: {StatusContrato.APROVACAO_REALIZADA.value}")
            print(f"   📁 Arquivo: {args.arquivo}")
            return

        # Criar backup se solicitado
        if args.backup:
            backup_path = f"{args.arquivo}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"💾 Criando backup: {backup_path}")
            salvar_fila_contratos(backup_path, contratos)

        # Confirmar atualização
        print(
            f"\n⚠️  ATENÇÃO: Você está prestes a atualizar {estatisticas['total_nao_aprovados']} contratos!")
        print(f"📝 Novo status: {StatusContrato.APROVACAO_REALIZADA.value}")

        if not args.verbose:
            resposta = input("\n🤔 Deseja continuar? (s/N): ").strip().lower()
            if resposta not in ['s', 'sim', 'y', 'yes']:
                print("❌ Operação cancelada pelo usuário.")
                return

        # Atualizar contratos
        print(
            f"\n🔄 Atualizando contratos para: {StatusContrato.APROVACAO_REALIZADA.value}")
        atualizados = atualizar_contratos_nao_aprovados(
            contratos,
            adicionar_metadata=not args.sem_metadata
        )

        # Salvar arquivo
        print(f"💾 Salvando alterações...")
        salvar_fila_contratos(args.arquivo, contratos)

        print(
            f"✅ Sucesso! {atualizados} contrato(s) atualizado(s) para status '{StatusContrato.APROVACAO_REALIZADA.value}'")

        if args.verbose:
            print(f"\n📊 Resumo da operação:")
            print(
                f"   - Total de contratos: {estatisticas['total_contratos']}")
            print(f"   - Contratos atualizados: {atualizados}")
            print(f"   - Contratos já aprovados: {estatisticas['aprovados']}")
            print(
                f"   - Novo status: {StatusContrato.APROVACAO_REALIZADA.value}")
            print(f"   - Arquivo: {args.arquivo}")
            if args.backup:
                print(f"   - Backup criado: {backup_path}")

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
