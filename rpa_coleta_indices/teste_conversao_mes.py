#!/usr/bin/env python3
"""
Teste da função _converter_formato_mes
Verifica se a conversão de datas está funcionando corretamente
"""

from rpa_coleta_indices import RPAColetaIndices
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def testar_conversao_mes():
    """Testa a função _converter_formato_mes com diferentes formatos"""

    # Cria instância do RPA
    rpa = RPAColetaIndices()

    # Casos de teste
    casos_teste = [
        ("25/06/2025", "jun.-25"),
        ("15/01/2025", "jan.-25"),
        ("30/12/2024", "dez.-24"),
        ("Abr/2025", "abr.-25"),
        ("junho de 2025", "jun.-25"),
        ("jan.-25", "jan.-25"),
        ("dez.-24", "dez.-24"),
        ("25/06/2025", "jun.-25"),  # Duplicado para verificar consistência
    ]

    print("🧪 Testando função _converter_formato_mes")
    print("=" * 50)

    sucessos = 0
    total = len(casos_teste)

    for entrada, esperado in casos_teste:
        try:
            resultado = rpa._converter_formato_mes(entrada)
            status = "✅" if resultado == esperado else "❌"
            print(f"{status} '{entrada}' -> '{resultado}' (esperado: '{esperado}')")

            if resultado == esperado:
                sucessos += 1
            else:
                print(f"   ⚠️  Diferente do esperado!")

        except Exception as e:
            print(f"❌ '{entrada}' -> ERRO: {str(e)}")

    print("=" * 50)
    print(f"📊 Resultado: {sucessos}/{total} testes passaram")

    if sucessos == total:
        print("🎉 Todos os testes passaram!")
    else:
        print("⚠️  Alguns testes falharam. Verificar a função.")

    return sucessos == total


if __name__ == "__main__":
    sucesso = testar_conversao_mes()
    sys.exit(0 if sucesso else 1)
