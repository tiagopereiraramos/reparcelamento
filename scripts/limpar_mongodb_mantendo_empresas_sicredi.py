import pymongo
import sys

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "sistema_rpa"  # Altere se necessário
KEEP_COLLECTION = "empresas_sicredi"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]

collections = db.list_collection_names()

print(f"Collections encontradas: {collections}")
collections_to_drop = [c for c in collections if c != KEEP_COLLECTION]

if not collections_to_drop:
    print(f"Nada a apagar. Apenas '{KEEP_COLLECTION}' existe.")
    sys.exit(0)

print(f"As seguintes collections serão APAGADAS: {collections_to_drop}")
confirm = input(
    "Tem certeza que deseja continuar? (digite 'SIM' para confirmar): ")

if confirm.strip().upper() == 'SIM':
    for col in collections_to_drop:
        db.drop_collection(col)
        print(f"Collection '{col}' apagada.")
    print("Limpeza concluída. Apenas 'empresas_sicredi' foi mantida.")
else:
    print("Operação cancelada.")
