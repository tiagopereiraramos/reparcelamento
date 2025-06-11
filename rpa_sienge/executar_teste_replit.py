import asyncio
import sys
import argparse
from pathlib import Path

# Adiciona o diretório pai ao path para importar módulos core
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from teste_replit_detalhado import main

def parse_args():
    """Analisa argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description="Teste Replit Detalhado - RPA Sienge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Arquivo Excel padrão
  python executar_teste_replit.py

  # Arquivo Excel específico
  python executar_teste_replit.py --arquivo /caminho/para/planilha.xlsx

  # Google Sheets (com retroalimentação conforme PDD)
  python executar_teste_replit.py --sheets 1ABC123DEF456GHI789JKL012MNO345PQR678STU

  # Google Sheets com arquivo Excel local para comparação
  python executar_teste_replit.py --arquivo planilha.xlsx --sheets PLANILHA_ID
        """
    )

    parser.add_argument(
        '--arquivo', 
        type=str, 
        help='Caminho para arquivo Excel'
    )

    parser.add_argument(
        '--sheets', 
        type=str, 
        help='ID da planilha Google Sheets (habilita retroalimentação PDD)'
    )

    return parser.parse_args()

if __name__ == "__main__":
    print("🚀 Executando Teste Replit Detalhado...")
    print("=" * 50)

    try:
        args = parse_args()

        # Validações
        if args.arquivo and not Path(args.arquivo).exists():
            print(f"❌ Arquivo não encontrado: {args.arquivo}")
            sys.exit(1)

        if args.sheets:
            print("📊 Modo Google Sheets ATIVADO")
            print("🔄 Retroalimentação conforme PDD será executada")

        # Executa teste com parâmetros
        resultado = asyncio.run(main(
            arquivo_fonte=args.arquivo,
            planilha_id=args.sheets
        ))

        if resultado:
            print("\n✅ Teste executado com sucesso!")
            if args.sheets:
                print("📊 Planilha Google Sheets atualizada com resultados")
        else:
            print("\n❌ Teste falhou!")

    except KeyboardInterrupt:
        print("\n👋 Teste cancelado pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro: {str(e)}")
        sys.exit(1)