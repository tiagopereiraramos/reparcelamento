#!/bin/bash

# deploy_producao.sh - Script de Deploy para Produção
# Uso: sudo ./deploy_producao.sh

set -e  # Para em caso de erro

echo "🚀 INICIANDO DEPLOY RPA PARA PRODUÇÃO"
echo "======================================"

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script deve ser executado como root (sudo)"
    exit 1
fi

# Configurações
RPA_USER="rpa"
RPA_HOME="/home/$RPA_USER"
APP_DIR="$RPA_HOME/app"
LOG_DIR="$RPA_HOME/logs"
DATA_DIR="$RPA_HOME/dados_processamento"
CREDENTIALS_DIR="$RPA_HOME/credentials"
BACKUP_DIR="$RPA_HOME/backups"

echo "📋 Configurações:"
echo "   Usuário: $RPA_USER"
echo "   App: $APP_DIR"
echo "   Logs: $LOG_DIR"
echo "   Dados: $DATA_DIR"

# 1. Atualizar sistema
echo "🔄 Atualizando sistema..."
apt update
apt upgrade -y

# 2. Instalar dependências do sistema
echo "📦 Instalando dependências do sistema..."
apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    curl \
    wget \
    unzip \
    git \
    htop \
    tree \
    docker.io \
    docker-compose \
    ufw \
    fail2ban

# 3. Instalar Google Chrome
echo "🌐 Instalando Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt update
apt install -y google-chrome-stable

# 4. Instalar UV
echo "⚡ Instalando UV..."
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 5. Criar usuário RPA
echo "👤 Criando usuário RPA..."
if id "$RPA_USER" &>/dev/null; then
    echo "   Usuário $RPA_USER já existe"
else
    useradd -m -s /bin/bash $RPA_USER
    usermod -aG sudo $RPA_USER
    echo "$RPA_USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
fi

# 6. Configurar diretórios
echo "📁 Configurando diretórios..."
mkdir -p $APP_DIR
mkdir -p $LOG_DIR
mkdir -p $DATA_DIR
mkdir -p $CREDENTIALS_DIR
mkdir -p $BACKUP_DIR
mkdir -p $RPA_HOME/mongo-init
mkdir -p $RPA_HOME/mongo-backups

# 7. Copiar código
echo "📋 Copiando código..."
cp -r . $APP_DIR/
chown -R $RPA_USER:$RPA_USER $RPA_HOME

# 8. Configurar ambiente Python
echo "🐍 Configurando ambiente Python..."
cd $APP_DIR
sudo -u $RPA_USER bash -c "
    source ~/.bashrc
    uv venv
    source .venv/bin/activate
    uv pip install -e .
"

# 9. Configurar variáveis de ambiente
echo "🔧 Configurando variáveis de ambiente..."
cat > $APP_DIR/.env << EOF
# Configurações do Sistema RPA
MONGODB_URI=mongodb://rpa_user:rpa_password_2024@localhost:27017/rpa_system
HEADLESS=true
WEBHOOK_NOTIFICACAO=
PLANILHA_CALCULO_ID=
PLANILHA_APOIO_ID=

# Configurações de Log
LOG_LEVEL=INFO
LOG_FILE=$LOG_DIR/rpa_system.log

# Configurações de Backup
BACKUP_DIR=$BACKUP_DIR
BACKUP_RETENTION_DAYS=30
EOF

chown $RPA_USER:$RPA_USER $APP_DIR/.env

# 10. Configurar systemd para agendador
echo "⏰ Configurando systemd para agendador..."
cat > /etc/systemd/system/rpa-agendador.service << EOF
[Unit]
Description=RPA Agendador Diário
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=$RPA_USER
Group=$RPA_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin
Environment=PYTHONPATH=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python agendador_diario.py
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/agendador.log
StandardError=append:$LOG_DIR/agendador_error.log

[Install]
WantedBy=multi-user.target
EOF

# 11. Configurar systemd para dashboard (opcional)
echo "📊 Configurando systemd para dashboard..."
cat > /etc/systemd/system/rpa-dashboard.service << EOF
[Unit]
Description=RPA Dashboard Streamlit
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=$RPA_USER
Group=$RPA_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin
Environment=PYTHONPATH=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/streamlit run dashboard_notificacoes.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10
StandardOutput=append:$LOG_DIR/dashboard.log
StandardError=append:$LOG_DIR/dashboard_error.log

[Install]
WantedBy=multi-user.target
EOF

# 12. Configurar firewall
echo "🛡️ Configurando firewall..."
ufw --force enable
ufw allow ssh
ufw allow 27017/tcp  # MongoDB
ufw allow 8501/tcp   # Dashboard
ufw allow 22/tcp     # SSH

# 13. Configurar fail2ban
echo "🔒 Configurando fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

# 14. Subir MongoDB
echo "🗄️ Iniciando MongoDB..."
cd $APP_DIR
docker-compose up -d mongodb

# Aguardar MongoDB estar pronto
echo "⏳ Aguardando MongoDB estar pronto..."
sleep 30

# 15. Habilitar e iniciar serviços
echo "🚀 Habilitando e iniciando serviços..."
systemctl daemon-reload
systemctl enable rpa-agendador
systemctl start rpa-agendador

# 16. Configurar cron para backups
echo "💾 Configurando backups automáticos..."
cat > /etc/cron.d/rpa-backup << EOF
# Backup diário do MongoDB e dados
0 2 * * * $RPA_USER $APP_DIR/scripts/backup_mongodb.sh >> $LOG_DIR/backup.log 2>&1

# Limpeza de logs antigos
0 3 * * * $RPA_USER find $LOG_DIR -name "*.log" -mtime +7 -delete
EOF

# 17. Configurar logrotate
echo "📝 Configurando rotação de logs..."
cat > /etc/logrotate.d/rpa << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $RPA_USER $RPA_USER
    postrotate
        systemctl reload rpa-agendador
    endscript
}
EOF

# 18. Criar script de monitoramento
echo "📊 Criando script de monitoramento..."
cat > $APP_DIR/scripts/monitor_system.sh << 'EOF'
#!/bin/bash

# Script de monitoramento do sistema RPA

LOG_FILE="/home/rpa/logs/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] === MONITORAMENTO RPA ===" >> $LOG_FILE

# Verificar serviços
if systemctl is-active --quiet rpa-agendador; then
    echo "[$DATE] ✅ RPA Agendador: ATIVO" >> $LOG_FILE
else
    echo "[$DATE] ❌ RPA Agendador: INATIVO" >> $LOG_FILE
    systemctl restart rpa-agendador
fi

# Verificar MongoDB
if docker ps | grep -q rpa_mongodb; then
    echo "[$DATE] ✅ MongoDB: ATIVO" >> $LOG_FILE
else
    echo "[$DATE] ❌ MongoDB: INATIVO" >> $LOG_FILE
    docker-compose up -d mongodb
fi

# Verificar espaço em disco
DISK_USAGE=$(df /home/rpa | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "[$DATE] ⚠️ DISCO: $DISK_USAGE% usado" >> $LOG_FILE
fi

# Verificar memória
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEM_USAGE -gt 80 ]; then
    echo "[$DATE] ⚠️ MEMÓRIA: $MEM_USAGE% usado" >> $LOG_FILE
fi

echo "[$DATE] === FIM MONITORAMENTO ===" >> $LOG_FILE
EOF

chmod +x $APP_DIR/scripts/monitor_system.sh

# Adicionar monitoramento ao cron
echo "*/5 * * * * $RPA_USER $APP_DIR/scripts/monitor_system.sh" >> /etc/cron.d/rpa-backup

# 19. Configurar permissões finais
echo "🔐 Configurando permissões..."
chown -R $RPA_USER:$RPA_USER $RPA_HOME
chmod +x $APP_DIR/scripts/*.sh

# 20. Testar conectividade
echo "🧪 Testando conectividade..."
if curl -s http://localhost:27017 > /dev/null; then
    echo "✅ MongoDB respondendo"
else
    echo "❌ MongoDB não está respondendo"
fi

echo ""
echo "🎉 DEPLOY CONCLUÍDO COM SUCESSO!"
echo "=================================="
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Configure as credenciais em $CREDENTIALS_DIR"
echo "2. Edite as variáveis de ambiente em $APP_DIR/.env"
echo "3. Verifique os logs: tail -f $LOG_DIR/agendador.log"
echo "4. Acesse o dashboard: http://localhost:8501"
echo ""
echo "🔧 COMANDOS ÚTEIS:"
echo "   Status: systemctl status rpa-agendador"
echo "   Logs: journalctl -u rpa-agendador -f"
echo "   Restart: systemctl restart rpa-agendador"
echo "   Backup: $APP_DIR/scripts/backup_mongodb.sh"
echo ""
echo "📊 MONITORAMENTO:"
echo "   Logs em tempo real: tail -f $LOG_DIR/*.log"
echo "   Status do sistema: $APP_DIR/scripts/monitor_system.sh"
echo "" 