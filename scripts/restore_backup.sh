#!/bin/bash

# restore_backup.sh - Script de Restore do Sistema RPA
# Restaura backup do MongoDB e dados processados

set -e

# Configurações
BACKUP_DIR="/home/rpa/backups"
LOG_FILE="/home/rpa/logs/restore.log"

# Função de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Função de ajuda
show_help() {
    echo "Uso: $0 [OPÇÕES] BACKUP_ID"
    echo ""
    echo "OPÇÕES:"
    echo "  -h, --help     Mostra esta ajuda"
    echo "  -l, --list     Lista backups disponíveis"
    echo "  -f, --force    Força restore sem confirmação"
    echo ""
    echo "EXEMPLOS:"
    echo "  $0 20241201_143022    # Restaura backup específico"
    echo "  $0 --list             # Lista backups disponíveis"
    echo "  $0 --force 20241201_143022  # Restaura sem confirmação"
    echo ""
    echo "BACKUP_ID: ID do backup (formato: YYYYMMDD_HHMMSS)"
}

# Função para listar backups
list_backups() {
    echo "📋 BACKUPS DISPONÍVEIS:"
    echo "========================"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        echo "❌ Diretório de backup não encontrado: $BACKUP_DIR"
        exit 1
    fi
    
    # Listar backups MongoDB
    echo "🗄️ Backups MongoDB:"
    for backup in $(find $BACKUP_DIR -name "mongodb_*" -type d | sort -r); do
        backup_id=$(basename $backup | sed 's/mongodb_//')
        backup_date=$(echo $backup_id | sed 's/_/ /' | sed 's/_/:/')
        backup_size=$(du -sh $backup 2>/dev/null | cut -f1 || echo "0")
        echo "   📁 $backup_id ($backup_date) - $backup_size"
    done
    
    echo ""
    echo "📦 Backups de Dados:"
    for backup in $(find $BACKUP_DIR -name "dados_*.tar.gz" | sort -r); do
        backup_id=$(basename $backup | sed 's/dados_//' | sed 's/.tar.gz//')
        backup_date=$(echo $backup_id | sed 's/_/ /' | sed 's/_/:/')
        backup_size=$(du -sh $backup 2>/dev/null | cut -f1 || echo "0")
        echo "   📦 $backup_id ($backup_date) - $backup_size"
    done
    
    echo ""
    echo "📝 Backups de Logs:"
    for backup in $(find $BACKUP_DIR -name "logs_*.tar.gz" | sort -r); do
        backup_id=$(basename $backup | sed 's/logs_//' | sed 's/.tar.gz//')
        backup_date=$(echo $backup_id | sed 's/_/ /' | sed 's/_/:/')
        backup_size=$(du -sh $backup 2>/dev/null | cut -f1 || echo "0")
        echo "   📝 $backup_id ($backup_date) - $backup_size"
    done
}

# Verificar argumentos
FORCE=false
BACKUP_ID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        *)
            BACKUP_ID="$1"
            shift
            ;;
    esac
done

# Verificar se backup ID foi fornecido
if [ -z "$BACKUP_ID" ]; then
    echo "❌ ERRO: Backup ID é obrigatório"
    echo ""
    show_help
    exit 1
fi

# Verificar se backup existe
MONGODB_BACKUP="$BACKUP_DIR/mongodb_$BACKUP_ID"
DADOS_BACKUP="$BACKUP_DIR/dados_$BACKUP_ID.tar.gz"
LOGS_BACKUP="$BACKUP_DIR/logs_$BACKUP_ID.tar.gz"
CONFIG_BACKUP="$BACKUP_DIR/config_$BACKUP_ID.tar.gz"

if [ ! -d "$MONGODB_BACKUP" ]; then
    echo "❌ ERRO: Backup MongoDB não encontrado: $MONGODB_BACKUP"
    echo ""
    list_backups
    exit 1
fi

log "🚀 INICIANDO RESTORE DO BACKUP: $BACKUP_ID"

# Confirmar restore (se não for forçado)
if [ "$FORCE" != "true" ]; then
    echo ""
    echo "⚠️  ATENÇÃO: Esta operação irá sobrescrever dados atuais!"
    echo "   Backup: $BACKUP_ID"
    echo "   MongoDB: $MONGODB_BACKUP"
    [ -f "$DADOS_BACKUP" ] && echo "   Dados: $DADOS_BACKUP"
    [ -f "$LOGS_BACKUP" ] && echo "   Logs: $LOGS_BACKUP"
    [ -f "$CONFIG_BACKUP" ] && echo "   Config: $CONFIG_BACKUP"
    echo ""
    read -p "   Confirma o restore? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "❌ Restore cancelado"
        exit 1
    fi
fi

# 1. Parar serviços
log "⏹️ Parando serviços..."
systemctl stop rpa-agendador 2>/dev/null || true
systemctl stop rpa-dashboard 2>/dev/null || true

# 2. Backup do estado atual (safety)
log "💾 Criando backup de segurança do estado atual..."
SAFETY_DATE=$(date +%Y%m%d_%H%M%S)
SAFETY_DIR="$BACKUP_DIR/safety_$SAFETY_DATE"
mkdir -p $SAFETY_DIR

# Backup MongoDB atual
if docker exec rpa_mongodb mongodump --out /tmp/safety_$SAFETY_DATE 2>/dev/null; then
    docker cp rpa_mongodb:/tmp/safety_$SAFETY_DATE $SAFETY_DIR/mongodb
    log "✅ Backup de segurança MongoDB criado"
fi

# 3. Restore MongoDB
log "🗄️ Restaurando MongoDB..."
cd /home/rpa/app

# Limpar dados atuais
docker exec rpa_mongodb mongosh --eval "db.dropDatabase()" rpa_system 2>/dev/null || true

# Restaurar backup
if docker cp $MONGODB_BACKUP rpa_mongodb:/tmp/restore_$BACKUP_ID; then
    if docker exec rpa_mongodb mongorestore /tmp/restore_$BACKUP_ID; then
        log "✅ MongoDB restaurado com sucesso"
    else
        log "❌ Erro ao restaurar MongoDB"
        exit 1
    fi
else
    log "❌ Erro ao copiar backup para container"
    exit 1
fi

# 4. Restore dados processados
if [ -f "$DADOS_BACKUP" ]; then
    log "📁 Restaurando dados processados..."
    DATA_DIR="/home/rpa/dados_processamento"
    mkdir -p $DATA_DIR
    tar -xzf $DADOS_BACKUP -C /home/rpa
    log "✅ Dados processados restaurados"
else
    log "⚠️ Backup de dados não encontrado"
fi

# 5. Restore logs
if [ -f "$LOGS_BACKUP" ]; then
    log "📝 Restaurando logs..."
    LOG_DIR="/home/rpa/logs"
    mkdir -p $LOG_DIR
    tar -xzf $LOGS_BACKUP -C /home/rpa
    log "✅ Logs restaurados"
else
    log "⚠️ Backup de logs não encontrado"
fi

# 6. Restore configurações
if [ -f "$CONFIG_BACKUP" ]; then
    log "⚙️ Restaurando configurações..."
    tar -xzf $CONFIG_BACKUP -C /home/rpa
    log "✅ Configurações restauradas"
else
    log "⚠️ Backup de configurações não encontrado"
fi

# 7. Limpar arquivos temporários
docker exec rpa_mongodb rm -rf /tmp/restore_$BACKUP_ID 2>/dev/null || true

# 8. Reiniciar serviços
log "🚀 Reiniciando serviços..."
systemctl start rpa-agendador
systemctl start rpa-dashboard 2>/dev/null || true

# 9. Verificar integridade
log "🔍 Verificando integridade do restore..."
sleep 10

# Verificar se MongoDB está respondendo
if docker exec rpa_mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    log "✅ MongoDB respondendo corretamente"
else
    log "❌ MongoDB não está respondendo"
    exit 1
fi

# Verificar se agendador está rodando
if systemctl is-active --quiet rpa-agendador; then
    log "✅ RPA Agendador ativo"
else
    log "❌ RPA Agendador não está ativo"
fi

# 10. Estatísticas do restore
log "📊 Estatísticas do restore:"
log "   Backup ID: $BACKUP_ID"
log "   MongoDB: $(du -sh $MONGODB_BACKUP | cut -f1)"
[ -f "$DADOS_BACKUP" ] && log "   Dados: $(du -sh $DADOS_BACKUP | cut -f1)"
[ -f "$LOGS_BACKUP" ] && log "   Logs: $(du -sh $LOGS_BACKUP | cut -f1)"
[ -f "$CONFIG_BACKUP" ] && log "   Config: $(du -sh $CONFIG_BACKUP | cut -f1)"

log "🎉 RESTORE CONCLUÍDO COM SUCESSO!"
log "   Backup ID: $BACKUP_ID"
log "   Safety backup: safety_$SAFETY_DATE"

echo ""
echo "✅ RESTORE FINALIZADO!"
echo "   Backup: $BACKUP_ID"
echo "   Safety: safety_$SAFETY_DATE"
echo ""
echo "🔧 PRÓXIMOS PASSOS:"
echo "1. Verifique os logs: tail -f /home/rpa/logs/agendador.log"
echo "2. Teste o sistema: systemctl status rpa-agendador"
echo "3. Acesse o dashboard: http://localhost:8501"
echo "" 