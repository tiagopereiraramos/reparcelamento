# 🚀 DEPLOY PARA PRODUÇÃO - SISTEMA RPA

## 📋 **VISÃO GERAL**

Este documento descreve o processo completo de deploy do sistema RPA em ambiente de produção Ubuntu.

## 🎯 **ARQUITETURA**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ubuntu 22.04  │    │   MongoDB 7.0   │    │   Dashboard     │
│   (Produção)    │◄──►│   (Docker)      │◄──►│   (Streamlit)   │
│                 │    │                 │    │                 │
│ • RPAs Nativos  │    │ • Dados         │    │ • Monitoramento │
│ • UV Package    │    │ • Logs          │    │ • Relatórios    │
│ • Systemd       │    │ • Configurações │    │ • Notificações  │
│ • Cron Jobs     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ **PRÉ-REQUISITOS**

### **Servidor Ubuntu 22.04 LTS**
- **CPU**: 4 cores mínimo (8 recomendado)
- **RAM**: 8GB mínimo (16GB recomendado)
- **Disco**: 100GB mínimo (SSD recomendado)
- **Rede**: Conexão estável com internet

### **Acesso Root**
```bash
sudo su -
```

## 🚀 **DEPLOY AUTOMATIZADO**

### **1. Preparar Servidor**
```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências básicas
sudo apt install -y curl wget git htop tree
```

### **2. Executar Script de Deploy**
```bash
# Baixar código (se necessário)
git clone <seu-repositorio> /tmp/rpa-deploy
cd /tmp/rpa-deploy

# Executar deploy
sudo chmod +x deploy_producao.sh
sudo ./deploy_producao.sh
```

## 📁 **ESTRUTURA DE DIRETÓRIOS**

Após o deploy, a estrutura será:

```
/home/rpa/
├── app/                    # Código da aplicação
│   ├── core/              # Módulos core
│   ├── rpa_sienge/        # RPA Sienge
│   ├── rpa_sicredi/       # RPA Sicredi
│   ├── scripts/           # Scripts de execução
│   └── .env              # Variáveis de ambiente
├── logs/                  # Logs do sistema
│   ├── agendador.log     # Log do agendador
│   ├── backup.log        # Log de backups
│   └── monitor.log       # Log de monitoramento
├── dados_processamento/   # Dados processados
├── credentials/           # Credenciais (configurar)
├── backups/              # Backups automáticos
└── mongo-init/           # Scripts de inicialização MongoDB
```

## ⚙️ **CONFIGURAÇÕES PÓS-DEPLOY**

### **1. Configurar Credenciais**
```bash
# Acessar diretório de credenciais
cd /home/rpa/credentials

# Criar arquivos de credenciais necessários
# (Sienge, Sicredi, etc.)
```

### **2. Configurar Variáveis de Ambiente**
```bash
# Editar arquivo .env
nano /home/rpa/app/.env

# Configurar:
# - MONGODB_URI
# - WEBHOOK_NOTIFICACAO
# - PLANILHA_CALCULO_ID
# - PLANILHA_APOIO_ID
```

### **3. Configurar Agendamento**
```bash
# Verificar cron jobs
crontab -l

# Editar agendamento (se necessário)
crontab -e
```

## 🔧 **SERVIÇOS SYSTEMD**

### **RPA Agendador**
```bash
# Status
systemctl status rpa-agendador

# Logs
journalctl -u rpa-agendador -f

# Reiniciar
systemctl restart rpa-agendador

# Habilitar/Desabilitar
systemctl enable rpa-agendador
systemctl disable rpa-agendador
```

### **RPA Dashboard** (Opcional)
```bash
# Status
systemctl status rpa-dashboard

# Logs
journalctl -u rpa-dashboard -f

# Reiniciar
systemctl restart rpa-dashboard
```

## 📊 **MONITORAMENTO**

### **Logs em Tempo Real**
```bash
# Todos os logs
tail -f /home/rpa/logs/*.log

# Log específico
tail -f /home/rpa/logs/agendador.log
```

### **Status do Sistema**
```bash
# Script de monitoramento
/home/rpa/app/scripts/monitor_system.sh

# Verificar recursos
htop
df -h
free -h
```

### **Dashboard Web**
```
http://localhost:8501
```

## 💾 **BACKUP E RESTORE**

### **Backup Automático**
- **Frequência**: Diário às 02:00
- **Local**: `/home/rpa/backups/`
- **Retenção**: 30 dias
- **Componentes**: MongoDB, dados, logs, configurações

### **Backup Manual**
```bash
# Executar backup manual
/home/rpa/app/scripts/backup_mongodb.sh
```

### **Restore**
```bash
# Listar backups disponíveis
/home/rpa/app/scripts/restore_backup.sh --list

# Restaurar backup específico
/home/rpa/app/scripts/restore_backup.sh 20241201_143022

# Restaurar sem confirmação
/home/rpa/app/scripts/restore_backup.sh --force 20241201_143022
```

## 🔒 **SEGURANÇA**

### **Firewall (UFW)**
```bash
# Status
ufw status

# Regras configuradas:
# - SSH (22)
# - MongoDB (27017)
# - Dashboard (8501)
```

### **Fail2Ban**
```bash
# Status
systemctl status fail2ban

# Logs
tail -f /var/log/fail2ban.log
```

### **Permissões**
```bash
# Verificar permissões
ls -la /home/rpa/

# Corrigir permissões (se necessário)
chown -R rpa:rpa /home/rpa/
chmod 600 /home/rpa/credentials/*
```

## 🚨 **TROUBLESHOOTING**

### **Problemas Comuns**

#### **1. RPA Agendador não inicia**
```bash
# Verificar logs
journalctl -u rpa-agendador -n 50

# Verificar dependências
systemctl status docker
systemctl status mongodb

# Verificar ambiente Python
/home/rpa/app/.venv/bin/python --version
```

#### **2. MongoDB não conecta**
```bash
# Verificar container
docker ps | grep mongodb

# Verificar logs
docker logs rpa_mongodb

# Reiniciar MongoDB
docker-compose restart mongodb
```

#### **3. Chrome não funciona**
```bash
# Verificar instalação
google-chrome --version

# Verificar permissões
ls -la /usr/bin/google-chrome

# Reinstalar Chrome
apt remove google-chrome-stable
apt install google-chrome-stable
```

#### **4. Espaço em disco**
```bash
# Verificar uso
df -h

# Limpar logs antigos
find /home/rpa/logs -name "*.log" -mtime +7 -delete

# Limpar backups antigos
find /home/rpa/backups -mtime +30 -delete
```

## 📈 **ESCALABILIDADE**

### **Para Alta Demanda**
1. **Aumentar recursos do servidor**
2. **Configurar múltiplas instâncias**
3. **Implementar load balancer**
4. **Usar MongoDB cluster**

### **Para Múltiplos Ambientes**
1. **Desenvolvimento**: Docker local
2. **Homologação**: Servidor dedicado
3. **Produção**: Servidor otimizado

## 🔄 **ATUALIZAÇÕES**

### **Atualizar Código**
```bash
# Parar serviços
systemctl stop rpa-agendador

# Backup atual
/home/rpa/app/scripts/backup_mongodb.sh

# Atualizar código
cd /home/rpa/app
git pull origin main

# Atualizar dependências
source .venv/bin/activate
uv pip install -e .

# Reiniciar serviços
systemctl start rpa-agendador
```

### **Atualizar Sistema**
```bash
# Atualizar Ubuntu
apt update && apt upgrade -y

# Reiniciar se necessário
reboot
```

## 📞 **SUPORTE**

### **Logs Importantes**
- `/home/rpa/logs/agendador.log` - Log principal
- `/home/rpa/logs/backup.log` - Log de backups
- `/home/rpa/logs/monitor.log` - Log de monitoramento
- `journalctl -u rpa-agendador` - Log systemd

### **Comandos Úteis**
```bash
# Status geral
systemctl status rpa-agendador rpa-dashboard

# Logs em tempo real
tail -f /home/rpa/logs/*.log

# Monitoramento
/home/rpa/app/scripts/monitor_system.sh

# Backup manual
/home/rpa/app/scripts/backup_mongodb.sh

# Restart completo
systemctl restart rpa-agendador && systemctl restart rpa-dashboard
```

---

## ✅ **CHECKLIST PÓS-DEPLOY**

- [ ] Servidor Ubuntu 22.04 configurado
- [ ] Docker e MongoDB funcionando
- [ ] UV e Python 3.11 instalados
- [ ] Google Chrome instalado
- [ ] Credenciais configuradas
- [ ] Variáveis de ambiente definidas
- [ ] RPA Agendador rodando
- [ ] Dashboard acessível (opcional)
- [ ] Backups automáticos configurados
- [ ] Monitoramento ativo
- [ ] Firewall configurado
- [ ] Logs sendo gerados
- [ ] Teste de funcionamento realizado

**🎉 SISTEMA PRONTO PARA PRODUÇÃO!** 