
#!/usr/bin/env python3
"""
Script de Execução Simplificada do RPA Sienge
Execute este arquivo para testar o sistema
"""

import asyncio
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def main():
    """Executa teste do RPA Sienge"""
    print("🚀 EXECUTANDO RPA SIENGE")
    print("=" * 50)
    
    try:
        from rpa_sienge.teste_sienge import teste_rapido_sistema
        await teste_rapido_sistema()
        
    except ImportError as e:
        print(f"❌ Erro de importação: {str(e)}")
        print("Verifique se todos os módulos estão instalados")
        
    except Exception as e:
        print(f"❌ Erro na execução: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
