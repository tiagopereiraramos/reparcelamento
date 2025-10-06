# Exemplo de Uso Avançado - JSON RPA Framework
# Demonstra casos de uso práticos para RPA com o framework transacional

from json_rpa_framework import JSONRPAFramework
from datetime import datetime, timedelta
import time
import threading
import random

class RPAContratosManager:
    """Gerenciador especializado para processamento de contratos via RPA"""
    
    def __init__(self, data_dir: str = "data"):
        self.framework = JSONRPAFramework(
            data_dir=data_dir,
            auto_index_fields=['status', 'codigo_cliente', 'empresa', 'tipo_contrato']
        )
    
    def importar_contratos_lote(self, contratos: list) -> dict:
        """Importa lote de contratos com validação"""
        resultado = {
            'importados': 0,
            'erros': 0,
            'duplicados': 0,
            'ids_criados': []
        }
        
        for contrato in contratos:
            try:
                # Verifica duplicatas
                existente = self.framework.find_one({
                    'codigo_cliente': contrato.get('codigo_cliente'),
                    'empresa': contrato.get('empresa')
                })
                
                if existente:
                    resultado['duplicados'] += 1
                    continue
                
                # Padroniza status inicial
                contrato['status'] = contrato.get('status', 'aguardando_processamento')
                contrato['data_importacao'] = datetime.now().isoformat()
                
                # Insere contrato
                record_id = self.framework.insert(contrato)
                resultado['ids_criados'].append(record_id)
                resultado['importados'] += 1
                
            except Exception as e:
                print(f"Erro ao importar contrato {contrato.get('codigo_cliente', 'N/A')}: {e}")
                resultado['erros'] += 1
        
        return resultado
    
    def processar_fila_contratos(self, status_origem: str = "aguardando_processamento", 
                                limite: int = 10) -> dict:
        """Processa fila de contratos alterando status para 'processando'"""
        contratos = self.framework.find(
            {"status": status_origem}, 
            limit=limite
        )
        
        resultado = {
            'processados': 0,
            'erros': 0,
            'contratos_ids': []
        }
        
        for contrato in contratos:
            try:
                record_id = contrato['_id']
                
                # Marca como processando
                sucesso = self.framework.set_status(
                    record_id, 
                    "processando",
                    {
                        'data_inicio_processamento': datetime.now().isoformat(),
                        'worker_id': threading.get_ident()
                    }
                )
                
                if sucesso:
                    resultado['processados'] += 1
                    resultado['contratos_ids'].append(record_id)
                
            except Exception as e:
                print(f"Erro ao processar contrato {record_id}: {e}")
                resultado['erros'] += 1
        
        return resultado
    
    def finalizar_processamento(self, record_id: str, sucesso: bool = True, 
                               observacoes: str = "") -> bool:
        """Finaliza processamento de um contrato"""
        status_final = "concluido" if sucesso else "erro"
        
        dados_finalizacao = {
            'data_fim_processamento': datetime.now().isoformat(),
            'observacoes': observacoes
        }
        
        return self.framework.set_status(record_id, status_final, dados_finalizacao)
    
    def obter_dashboard_status(self) -> dict:
        """Gera dashboard com estatísticas dos contratos"""
        todos_status = self.framework.distinct('status')
        dashboard = {}
        
        for status in todos_status:
            count = self.framework.count({'status': status})
            dashboard[status] = count
        
        # Estatísticas adicionais
        dashboard['total_contratos'] = self.framework.count()
        dashboard['empresas_ativas'] = len(self.framework.distinct('empresa'))
        
        return dashboard
    
    def buscar_contratos_avancado(self, filtros: dict) -> list:
        """Busca avançada com múltiplos filtros"""
        query = {}
        
        # Filtro por empresa
        if 'empresa' in filtros:
            query['empresa'] = filtros['empresa']
        
        # Filtro por status múltiplos
        if 'status_lista' in filtros:
            query['status'] = {'$in': filtros['status_lista']}
        
        # Filtro por código cliente (regex)
        if 'codigo_cliente_parcial' in filtros:
            query['codigo_cliente'] = {'$regex': filtros['codigo_cliente_parcial']}
        
        # Filtro por data de criação
        if 'data_inicio' in filtros and 'data_fim' in filtros:
            query['_created_at'] = {
                '$gte': filtros['data_inicio'],
                '$lte': filtros['data_fim']
            }
        
        return self.framework.find(query)
    
    def executar_manutencao(self) -> dict:
        """Executa rotinas de manutenção do sistema"""
        resultado = {
            'backup_criado': False,
            'wal_compactado': False,
            'indices_reconstruidos': False,
            'estatisticas': {}
        }
        
        try:
            # Backup
            backup_path = self.framework.backup()
            resultado['backup_criado'] = True
            resultado['backup_path'] = backup_path
            
            # Compacta WAL
            self.framework.compact_wal()
            resultado['wal_compactado'] = True
            
            # Reconstrói índices principais
            for field in ['status', 'empresa', 'codigo_cliente']:
                self.framework.create_index(field)
            resultado['indices_reconstruidos'] = True
            
            # Coleta estatísticas
            resultado['estatisticas'] = self.framework.get_stats()
            
        except Exception as e:
            resultado['erro'] = str(e)
        
        return resultado

def simular_processamento_concorrente():
    """Simula múltiplas RPAs processando contratos simultaneamente"""
    
    def worker_rpa(worker_id: int, manager: RPAContratosManager):
        """Simula uma RPA processando contratos"""
        print(f"Worker {worker_id} iniciado")
        
        for _ in range(5):  # Processa 5 contratos
            # Pega contratos para processar
            resultado = manager.processar_fila_contratos(limite=1)
            
            if resultado['processados'] > 0:
                record_id = resultado['contratos_ids'][0]
                print(f"Worker {worker_id} processando contrato {record_id}")
                
                # Simula tempo de processamento
                time.sleep(random.uniform(0.5, 2.0))
                
                # Finaliza com sucesso (90% das vezes)
                sucesso = random.random() > 0.1
                observacao = "Processado com sucesso" if sucesso else "Erro no processamento"
                
                manager.finalizar_processamento(record_id, sucesso, observacao)
                print(f"Worker {worker_id} finalizou contrato {record_id} - Sucesso: {sucesso}")
            else:
                print(f"Worker {worker_id} - Nenhum contrato disponível")
                time.sleep(0.5)
    
    # Inicializa manager
    manager = RPAContratosManager()
    
    # Cria contratos de exemplo
    contratos_exemplo = []
    for i in range(20):
        contrato = {
            "empresa": f"Empresa {(i % 3) + 1}",
            "loteamento": f"Loteamento {chr(65 + (i % 5))}",
            "codigo_cliente": f"{1000 + i:04d}",
            "cliente": f"Cliente Exemplo {i + 1}",
            "tipo_contrato": "residencial" if i % 2 == 0 else "comercial",
            "valor_contrato": round(random.uniform(50000, 500000), 2),
            "status": "aguardando_processamento"
        }
        contratos_exemplo.append(contrato)
    
    # Importa contratos
    print("Importando contratos...")
    resultado_import = manager.importar_contratos_lote(contratos_exemplo)
    print(f"Importação: {resultado_import}")
    
    # Cria threads simulando RPAs concorrentes
    print("\nIniciando processamento concorrente...")
    threads = []
    for i in range(3):  # 3 RPAs trabalhando simultaneamente
        thread = threading.Thread(target=worker_rpa, args=(i + 1, manager))
        threads.append(thread)
        thread.start()
    
    # Aguarda conclusão
    for thread in threads:
        thread.join()
    
    # Mostra dashboard final
    print("\n=== Dashboard Final ===")
    dashboard = manager.obter_dashboard_status()
    for status, count in dashboard.items():
        print(f"{status}: {count}")
    
    # Estatísticas do framework
    print("\n=== Estatísticas do Framework ===")
    stats = manager.framework.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    return manager

if __name__ == "__main__":
    # Executa simulação
    manager = simular_processamento_concorrente()
    
    # Exemplo de busca avançada
    print("\n=== Exemplo de Busca Avançada ===")
    filtros = {
        'status_lista': ['concluido', 'erro'],
        'empresa': 'Empresa 1'
    }
    
    resultados = manager.buscar_contratos_avancado(filtros)
    print(f"Contratos encontrados: {len(resultados)}")
    
    for contrato in resultados[:3]:  # Mostra apenas os primeiros 3
        print(f"- {contrato['codigo_cliente']}: {contrato['status']}")
    
    # Executa manutenção
    print("\n=== Executando Manutenção ===")
    manutencao = manager.executar_manutencao()
    print(f"Manutenção: {manutencao}")