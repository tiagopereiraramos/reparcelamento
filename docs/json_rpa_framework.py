# JSON RPA Framework - Controlador Transacional
# Framework para gerenciamento transacional de arquivos JSON para automação (RPA)
# Autor: Framework desenvolvido para controle robusto de filas de processamento

import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field, make_dataclass
from filelock import FileLock
from copy import deepcopy
import hashlib

class JSONRPAException(Exception):
    """Exceção base para o framework JSON RPA"""
    pass

class TransactionException(JSONRPAException):
    """Exceção para operações transacionais"""
    pass

class ValidationException(JSONRPAException):
    """Exceção para validação de dados"""
    pass

@dataclass
class WALEntry:
    """Entrada do Write-Ahead Log"""
    timestamp: str
    operation: str  # INSERT, UPDATE, DELETE, SET_STATUS
    record_id: Optional[str]
    data: Dict[str, Any]
    checksum: str = field(default="")
    
    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calcula checksum para integridade"""
        content = f"{self.timestamp}{self.operation}{self.record_id}{json.dumps(self.data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'operation': self.operation,
            'record_id': self.record_id,
            'data': self.data,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WALEntry':
        return cls(**data)

class QueryBuilder:
    """Construtor de queries para busca flexível"""
    
    @staticmethod
    def match_record(record: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Verifica se um registro corresponde à query"""
        for key, value in query.items():
            if key not in record:
                return False
            
            if isinstance(value, dict):
                # Operadores especiais
                if '$eq' in value:
                    if record[key] != value['$eq']:
                        return False
                elif '$ne' in value:
                    if record[key] == value['$ne']:
                        return False
                elif '$in' in value:
                    if record[key] not in value['$in']:
                        return False
                elif '$nin' in value:
                    if record[key] in value['$nin']:
                        return False
                elif '$gt' in value:
                    if not (record[key] > value['$gt']):
                        return False
                elif '$gte' in value:
                    if not (record[key] >= value['$gte']):
                        return False
                elif '$lt' in value:
                    if not (record[key] < value['$lt']):
                        return False
                elif '$lte' in value:
                    if not (record[key] <= value['$lte']):
                        return False
                elif '$regex' in value:
                    import re
                    if not re.search(value['$regex'], str(record[key])):
                        return False
                elif '$exists' in value:
                    exists = key in record and record[key] is not None
                    if exists != value['$exists']:
                        return False
            else:
                # Comparação direta
                if record[key] != value:
                    return False
        
        return True

class IndexManager:
    """Gerenciador de índices para busca otimizada"""
    
    def __init__(self):
        self.indexes: Dict[str, Dict[Any, List[str]]] = {}
        self._lock = threading.RLock()
    
    def build_index(self, field: str, records: List[Dict[str, Any]]):
        """Constrói índice para um campo específico"""
        with self._lock:
            self.indexes[field] = {}
            for i, record in enumerate(records):
                if field in record:
                    value = record[field]
                    record_id = record.get('_id', str(i))
                    
                    if value not in self.indexes[field]:
                        self.indexes[field][value] = []
                    self.indexes[field][value].append(record_id)
    
    def update_index(self, field: str, old_value: Any, new_value: Any, record_id: str):
        """Atualiza índice após modificação"""
        with self._lock:
            if field not in self.indexes:
                return
            
            # Remove da posição antiga
            if old_value in self.indexes[field]:
                if record_id in self.indexes[field][old_value]:
                    self.indexes[field][old_value].remove(record_id)
                    if not self.indexes[field][old_value]:
                        del self.indexes[field][old_value]
            
            # Adiciona na nova posição
            if new_value not in self.indexes[field]:
                self.indexes[field][new_value] = []
            if record_id not in self.indexes[field][new_value]:
                self.indexes[field][new_value].append(record_id)
    
    def find_by_index(self, field: str, value: Any) -> List[str]:
        """Busca IDs usando índice"""
        with self._lock:
            if field in self.indexes and value in self.indexes[field]:
                return self.indexes[field][value].copy()
            return []
    
    def get_indexed_fields(self) -> List[str]:
        """Retorna campos indexados"""
        with self._lock:
            return list(self.indexes.keys())

class JSONRPAFramework:
    """Framework principal para controle transacional de JSON para RPAs"""
    
    def __init__(self, 
                 data_dir: str = "data",
                 main_file: str = "fila_contratos.json",
                 wal_file: str = "fila_contratos.wal",
                 index_file: str = "index_status.json",
                 auto_index_fields: List[str] = None):
        
        self.data_dir = data_dir
        self.main_file = os.path.join(data_dir, main_file)
        self.wal_file = os.path.join(data_dir, wal_file)
        self.index_file = os.path.join(data_dir, index_file)
        
        # Locks para concorrência
        self.main_lock = FileLock(f"{self.main_file}.lock")
        self.wal_lock = FileLock(f"{self.wal_file}.lock")
        
        # Gerenciador de índices
        self.index_manager = IndexManager()
        self.auto_index_fields = auto_index_fields or ['status', 'codigo_cliente', 'empresa']
        
        # Cache e estado
        self._data_cache: List[Dict[str, Any]] = []
        self._cache_dirty = True
        self._cache_lock = threading.RLock()
        
        # Estatísticas
        self.stats = {
            'operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'wal_recoveries': 0
        }
        
        # Inicialização
        self._ensure_directories()
        self._initialize_data()
        self._recover_from_wal()
        self._build_indexes()
    
    def _ensure_directories(self):
        """Garante que os diretórios existam"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _generate_id(self) -> str:
        """Gera ID único para registros"""
        return f"{int(time.time() * 1000)}_{threading.get_ident()}"
    
    def _get_timestamp(self) -> str:
        """Retorna timestamp atual formatado"""
        return datetime.now().isoformat()
    
    def _initialize_data(self):
        """Inicializa arquivo de dados se não existir"""
        if not os.path.exists(self.main_file):
            with self.main_lock:
                with open(self.main_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
    
    def _load_data(self) -> List[Dict[str, Any]]:
        """Carrega dados do arquivo principal"""
        try:
            with open(self.main_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_data(self, data: List[Dict[str, Any]]):
        """Salva dados no arquivo principal"""
        with open(self.main_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _write_wal_entry(self, entry: WALEntry):
        """Escreve entrada no Write-Ahead Log"""
        with self.wal_lock:
            with open(self.wal_file, 'a', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False)
                f.write('\n')
    
    def _recover_from_wal(self):
        """Recupera estado a partir do WAL após falha"""
        if not os.path.exists(self.wal_file):
            return
        
        wal_entries = []
        try:
            with self.wal_lock:
                with open(self.wal_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entry_data = json.loads(line)
                                entry = WALEntry.from_dict(entry_data)
                                # Verifica integridade
                                if entry.checksum == entry._calculate_checksum():
                                    wal_entries.append(entry)
                            except json.JSONDecodeError:
                                continue
        except FileNotFoundError:
            return
        
        if not wal_entries:
            return
        
        # Aplica entradas do WAL
        with self.main_lock:
            data = self._load_data()
            
            for entry in wal_entries:
                try:
                    if entry.operation == 'INSERT':
                        data.append(entry.data)
                    elif entry.operation == 'UPDATE':
                        for i, record in enumerate(data):
                            if record.get('_id') == entry.record_id:
                                data[i].update(entry.data)
                                break
                    elif entry.operation == 'DELETE':
                        data = [r for r in data if r.get('_id') != entry.record_id]
                    elif entry.operation == 'SET_STATUS':
                        for i, record in enumerate(data):
                            if record.get('_id') == entry.record_id:
                                data[i].update(entry.data)
                                break
                except Exception as e:
                    print(f"Erro ao aplicar entrada WAL: {e}")
                    continue
            
            self._save_data(data)
            self.stats['wal_recoveries'] += len(wal_entries)
        
        # Limpa WAL após recuperação
        with self.wal_lock:
            open(self.wal_file, 'w').close()
    
    def _build_indexes(self):
        """Constrói índices para campos configurados"""
        with self._cache_lock:
            if self._cache_dirty:
                self._refresh_cache()
            
            for field in self.auto_index_fields:
                self.index_manager.build_index(field, self._data_cache)
    
    def _refresh_cache(self):
        """Atualiza cache dos dados"""
        with self.main_lock:
            self._data_cache = self._load_data()
            self._cache_dirty = False
    
    def _get_cached_data(self) -> List[Dict[str, Any]]:
        """Retorna dados do cache"""
        with self._cache_lock:
            if self._cache_dirty:
                self._refresh_cache()
                self.stats['cache_misses'] += 1
            else:
                self.stats['cache_hits'] += 1
            
            return deepcopy(self._data_cache)
    
    # CRUD Operations
    
    def insert(self, record: Dict[str, Any]) -> str:
        """Insere um novo registro"""
        record = deepcopy(record)
        record_id = record.get('_id', self._generate_id())
        record['_id'] = record_id
        record['_created_at'] = self._get_timestamp()
        record['_updated_at'] = record['_created_at']
        
        # WAL entry
        wal_entry = WALEntry(
            timestamp=self._get_timestamp(),
            operation='INSERT',
            record_id=record_id,
            data=record
        )
        
        with self.main_lock:
            # Escreve WAL primeiro
            self._write_wal_entry(wal_entry)
            
            # Carrega, modifica e salva dados
            data = self._load_data()
            data.append(record)
            self._save_data(data)
            
            # Atualiza cache e índices
            with self._cache_lock:
                self._data_cache.append(record)
                for field in self.auto_index_fields:
                    if field in record:
                        self.index_manager.update_index(field, None, record[field], record_id)
            
            self.stats['operations'] += 1
            return record_id
    
    def find(self, query: Dict[str, Any] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Busca registros baseado em query"""
        query = query or {}
        data = self._get_cached_data()
        
        # Otimização com índices para queries simples
        if len(query) == 1:
            field, value = next(iter(query.items()))
            if field in self.index_manager.get_indexed_fields() and not isinstance(value, dict):
                record_ids = self.index_manager.find_by_index(field, value)
                results = [r for r in data if r.get('_id') in record_ids]
                return results[:limit] if limit else results
        
        # Busca completa
        results = []
        for record in data:
            if QueryBuilder.match_record(record, query):
                results.append(record)
                if limit and len(results) >= limit:
                    break
        
        return results
    
    def find_one(self, query: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Busca um único registro"""
        results = self.find(query, limit=1)
        return results[0] if results else None
    
    def update(self, query: Dict[str, Any], update_data: Dict[str, Any], multi: bool = False) -> int:
        """Atualiza registros baseado em query"""
        update_data = deepcopy(update_data)
        update_data['_updated_at'] = self._get_timestamp()
        
        updated_count = 0
        
        with self.main_lock:
            data = self._load_data()
            
            for i, record in enumerate(data):
                if QueryBuilder.match_record(record, query):
                    record_id = record.get('_id')
                    old_record = deepcopy(record)
                    
                    # WAL entry
                    wal_entry = WALEntry(
                        timestamp=self._get_timestamp(),
                        operation='UPDATE',
                        record_id=record_id,
                        data=update_data
                    )
                    self._write_wal_entry(wal_entry)
                    
                    # Atualiza registro
                    data[i].update(update_data)
                    updated_count += 1
                    
                    # Atualiza índices
                    for field in self.auto_index_fields:
                        old_value = old_record.get(field)
                        new_value = data[i].get(field)
                        if old_value != new_value:
                            self.index_manager.update_index(field, old_value, new_value, record_id)
                    
                    if not multi:
                        break
            
            if updated_count > 0:
                self._save_data(data)
                with self._cache_lock:
                    self._cache_dirty = True
            
            self.stats['operations'] += 1
            return updated_count
    
    def delete(self, query: Dict[str, Any], multi: bool = False) -> int:
        """Remove registros baseado em query"""
        deleted_count = 0
        
        with self.main_lock:
            data = self._load_data()
            new_data = []
            
            for record in data:
                if QueryBuilder.match_record(record, query):
                    record_id = record.get('_id')
                    
                    # WAL entry
                    wal_entry = WALEntry(
                        timestamp=self._get_timestamp(),
                        operation='DELETE',
                        record_id=record_id,
                        data=record
                    )
                    self._write_wal_entry(wal_entry)
                    
                    # Remove dos índices
                    for field in self.auto_index_fields:
                        if field in record:
                            self.index_manager.update_index(field, record[field], None, record_id)
                    
                    deleted_count += 1
                    
                    if not multi:
                        continue
                else:
                    new_data.append(record)
            
            if deleted_count > 0:
                self._save_data(new_data)
                with self._cache_lock:
                    self._cache_dirty = True
            
            self.stats['operations'] += 1
            return deleted_count
    
    def set_status(self, record_id: str, status: str, additional_data: Dict[str, Any] = None) -> bool:
        """Atualiza status de um registro específico (operação otimizada)"""
        update_data = {'status': status}
        if additional_data:
            update_data.update(additional_data)
        update_data['_updated_at'] = self._get_timestamp()
        
        with self.main_lock:
            # WAL entry específica para SET_STATUS
            wal_entry = WALEntry(
                timestamp=self._get_timestamp(),
                operation='SET_STATUS',
                record_id=record_id,
                data=update_data
            )
            self._write_wal_entry(wal_entry)
            
            # Atualiza dados
            data = self._load_data()
            updated = False
            
            for i, record in enumerate(data):
                if record.get('_id') == record_id:
                    old_status = record.get('status')
                    data[i].update(update_data)
                    
                    # Atualiza índice de status
                    if 'status' in self.auto_index_fields:
                        self.index_manager.update_index('status', old_status, status, record_id)
                    
                    updated = True
                    break
            
            if updated:
                self._save_data(data)
                with self._cache_lock:
                    self._cache_dirty = True
            
            self.stats['operations'] += 1
            return updated
    
    def bulk_update_status(self, query: Dict[str, Any], status: str, additional_data: Dict[str, Any] = None) -> int:
        """Atualiza status de múltiplos registros em operação atômica"""
        update_data = {'status': status}
        if additional_data:
            update_data.update(additional_data)
        
        return self.update(query, update_data, multi=True)
    
    def count(self, query: Dict[str, Any] = None) -> int:
        """Conta registros que correspondem à query"""
        return len(self.find(query))
    
    def distinct(self, field: str, query: Dict[str, Any] = None) -> List[Any]:
        """Retorna valores únicos de um campo"""
        records = self.find(query)
        values = set()
        for record in records:
            if field in record:
                values.add(record[field])
        return list(values)
    
    # Utility Methods
    
    def create_index(self, field: str):
        """Cria índice para um campo específico"""
        if field not in self.auto_index_fields:
            self.auto_index_fields.append(field)
        
        data = self._get_cached_data()
        self.index_manager.build_index(field, data)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do framework"""
        stats = self.stats.copy()
        stats['total_records'] = len(self._get_cached_data())
        stats['indexed_fields'] = self.index_manager.get_indexed_fields()
        stats['cache_hit_ratio'] = (
            stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses'])
            if (stats['cache_hits'] + stats['cache_misses']) > 0 else 0
        )
        return stats
    
    def compact_wal(self):
        """Compacta o Write-Ahead Log (remove entradas redundantes)"""
        with self.wal_lock:
            if os.path.exists(self.wal_file):
                # Simplesmente limpa o WAL já que os dados estão salvos
                open(self.wal_file, 'w').close()
    
    def export_data(self, filename: str = None) -> str:
        """Exporta todos os dados para arquivo JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.json"
        
        data = self._get_cached_data()
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def backup(self, backup_dir: str = None) -> str:
        """Cria backup completo (dados + WAL + índices)"""
        if not backup_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"backup_{timestamp}"
        
        backup_path = os.path.join(self.data_dir, backup_dir)
        os.makedirs(backup_path, exist_ok=True)
        
        # Copia arquivos
        import shutil
        shutil.copy2(self.main_file, backup_path)
        if os.path.exists(self.wal_file):
            shutil.copy2(self.wal_file, backup_path)
        
        return backup_path

# Exemplo de uso e testes
if __name__ == "__main__":
    # Inicializa o framework
    framework = JSONRPAFramework()
    
    # Exemplo de inserção
    contrato_exemplo = {
        "empresa": "18 - URUCUI SCP 2",
        "loteamento": "OLIVEIRA IV",
        "codigo_cliente": "6616",
        "cliente": "ALEXANDRA DA PAZ RODRIGUES",
        "status": "pendente",
        "proximo_reajuste": "",
        "data_migracao": ""
    }
    
    # Insere registro
    record_id = framework.insert(contrato_exemplo)
    print(f"Registro inserido com ID: {record_id}")
    
    # Busca registros
    contratos_pendentes = framework.find({"status": "pendente"})
    print(f"Contratos pendentes: {len(contratos_pendentes)}")
    
    # Atualiza status
    framework.set_status(record_id, "processando", {"data_inicio": datetime.now().isoformat()})
    
    # Busca avançada
    contratos_empresa = framework.find({
        "empresa": "18 - URUCUI SCP 2",
        "status": {"$in": ["processando", "concluido"]}
    })
    
    # Estatísticas
    print("Estatísticas:", framework.get_stats())