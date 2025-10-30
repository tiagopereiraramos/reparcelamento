#!/usr/bin/env python3
"""
Ajusta o status para CARNE_GERADO dos contratos da empresa 9 - SPE PARQUE DA LAGOA
Cria backup automático antes de salvar.
"""

import json
import os
from datetime import datetime
from pathlib import Path

ARQUIVO = Path("data/fila_contratos.json")
EMPRESA_ALVO = "9 - SPE PARQUE DA LAGOA"


def log(msg: str) -> None:
    from datetime import datetime as _dt
    print(f"[{_dt.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def main() -> int:
    if not ARQUIVO.exists():
        log(f"Arquivo não encontrado: {ARQUIVO}")
        return 1

    # Backup
    backup_dir = ARQUIVO.parent
    backup_name = f"fila_contratos.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = backup_dir / backup_name
    try:
        with open(ARQUIVO, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        log(f"📦 Backup criado: {backup_path}")
    except Exception as e:
        log(f"Falha ao criar backup: {e}")
        return 1

    # Ajuste
    alterados = 0
    total_emp = 0
    for item in dados:
        if item.get("Empresa") == EMPRESA_ALVO:
            total_emp += 1
            if item.get("status") != "CARNE_GERADO":
                item["status"] = "CARNE_GERADO"
                item["status_timestamp"] = datetime.now().isoformat()
                item["status_anterior"] = item.get("status_anterior", "")
                alterados += 1

    try:
        with open(ARQUIVO, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        log(f"✅ Salvo com sucesso: {ARQUIVO}")
        log(f"📊 Empresa alvo: {EMPRESA_ALVO} | Total: {total_emp} | Alterados para CARNE_GERADO: {alterados}")
        return 0
    except Exception as e:
        log(f"❌ Erro ao salvar arquivo: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


