#!/bin/bash

# backup_mongodb.sh - Script de Backup do Sistema RPA
# Executa backup do MongoDB e dados processados

set -e

# Configurações
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/rpa/backups"
LOG_FILE="/home/rpa/logs/backup.log"
RETENTION_DAYS=30

# Criar diretórios se não existirem
mkdir -p $BACKUP_DIR
mkdir -p $(dirname $LOG_FILE)

# Função de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "🚀 INICIANDO BACKUP DO SISTEMA RPA"

# 1. Backup MongoDB
log "🗄️ Iniciando backup do MongoDB..."
cd /home/rpa/app

# Backup usando mongodump
if docker exec rpa_mongodb mongodump --out /tmp/backup_$DATE; then
    docker cp rpa_mongodb:/tmp/backup_$DATE $BACKUP_DIR/mongodb_$DATE
    log "✅ Backup MongoDB concluído: mongodb_$DATE"
else
    log "❌ Erro no backup do MongoDB"
    exit 1
fi

# 2. Backup dados processados
log "📁 Iniciando backup dos dados processados..."
DATA_DIR="/home/rpa/dados_processamento"
if [ -d "$DATA_DIR" ]; then
    tar -czf $BACKUP_DIR/dados_$DATE.tar.gz -C /home/rpa dados_processamento
    log "✅ Backup dados processados concluído: dados_$DATE.tar.gz"
else
    log "⚠️ Diretório de dados não encontrado"
fi

# 3. Backup logs importantes
log "📝 Iniciando backup dos logs..."
LOG_DIR="/home/rpa/logs"
if [ -d "$LOG_DIR" ]; then
    tar -czf $BACKUP_DIR/logs_$DATE.tar.gz -C /home/rpa logs
    log "✅ Backup logs concluído: logs_$DATE.tar.gz"
else
    log "⚠️ Diretório de logs não encontrado"
fi

# 4. Backup configurações
log "⚙️ Iniciando backup das configurações..."
CONFIG_FILES="/home/rpa/app/.env /home/rpa/credentials"
if [ -f "/home/rpa/app/.env" ]; then
    tar -czf $BACKUP_DIR/config_$DATE.tar.gz -C /home/rpa app/.env credentials 2>/dev/null || true
    log "✅ Backup configurações concluído: config_$DATE.tar.gz"
else
    log "⚠️ Arquivo .env não encontrado"
fi

# 5. Criar arquivo de metadados
log "📋 Criando metadados do backup..."
cat > $BACKUP_DIR/metadata_$DATE.json << EOF
{
    "timestamp": "$(date -Iseconds)",
    "backup_id": "$DATE",
    "components": {
        "mongodb": "mongodb_$DATE",
        "dados": "dados_$DATE.tar.gz",
        "logs": "logs_$DATE.tar.gz",
        "config": "config_$DATE.tar.gz"
    },
    "system_info": {
        "disk_usage": "$(df /home/rpa | tail -1 | awk '{print $5}')",
        "memory_usage": "$(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')",
        "uptime": "$(uptime -p)"
    }
}
EOF

# 6. Limpar backups antigos
log "🧹 Limpando backups antigos..."
find $BACKUP_DIR -name "mongodb_*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find $BACKUP_DIR -name "metadata_*.json" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# 7. Verificar espaço em disco
DISK_USAGE=$(df $BACKUP_DIR | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    log "⚠️ ATENÇÃO: Disco com $DISK_USAGE% de uso!"
fi

# 8. Estatísticas do backup
BACKUP_SIZE=$(du -sh $BACKUP_DIR/mongodb_$DATE 2>/dev/null | cut -f1 || echo "0")
log "📊 Estatísticas do backup:"
log "   Tamanho MongoDB: $BACKUP_SIZE"
log "   Total de backups: $(find $BACKUP_DIR -name "mongodb_*" | wc -l)"
log "   Espaço usado: $(du -sh $BACKUP_DIR | cut -f1)"

# 9. Notificação de sucesso
log "🎉 BACKUP CONCLUÍDO COM SUCESSO!"
log "   Local: $BACKUP_DIR"
log "   ID: $DATE"
log "   Retenção: $RETENTION_DAYS dias"

# 10. Limpar arquivos temporários do container
docker exec rpa_mongodb rm -rf /tmp/backup_$DATE 2>/dev/null || true

log "✅ Backup finalizado com sucesso!" 