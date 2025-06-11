#!/bin/bash
# Deploy Script - Sistema RPA de Reparcelamento v2.0
# Script automatizado para deploy self-hosted

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SISTEMA RPA DE REPARCELAMENTO - DEPLOY SELF-HOSTED${NC}"
echo "=================================================================="

# Verificar se está sendo executado como root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Não execute este script como root!${NC}"
    exit 1
fi

# Função para imprimir com cores
print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar dependências
print_step "Verificando dependências..."

if ! command -v docker &> /dev/null; then
    print_error "Docker não está instalado. Instale com: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose não está instalado. Instale com: pip install docker-compose"
    exit 1
fi

print_success "Dependências verificadas"

# Criar diretórios necessários
print_step "Criando estrutura de diretórios..."
mkdir -p {logs,temp,deploy/credentials,deploy/ssl,backups}
chmod 700 deploy/credentials
print_success "Diretórios criados"

# Verificar arquivo .env
if [ ! -f "deploy/.env" ]; then
    print_warning "Arquivo .env não encontrado. Copiando exemplo..."
    cp deploy/.env.example deploy/.env
    print_warning "⚠️ IMPORTANTE: Edite o arquivo deploy/.env com suas configurações reais!"
    echo ""
    echo -e "${YELLOW}Você precisa configurar:${NC}"
    echo "- IDs das planilhas Google Sheets"
    echo "- Credenciais do Sienge"  
    echo "- Credenciais do Sicredi"
    echo "- Senha do MongoDB"
    echo ""
    read -p "Pressione Enter após configurar o arquivo .env..."
fi

# Verificar credenciais Google
if [ ! -f "deploy/credentials/google_service_account.json" ]; then
    print_error "Arquivo de credenciais Google não encontrado!"
    echo "Coloque o arquivo JSON do Service Account em: deploy/credentials/google_service_account.json"
    exit 1
fi

print_success "Credenciais verificadas"

# Escolher ambiente
echo ""
echo -e "${BLUE}Escolha o ambiente de deploy:${NC}"
echo "1) Desenvolvimento (local)"
echo "2) Produção (servidor)"
read -p "Digite sua opção (1-2): " ambiente

case $ambiente in
    1)
        COMPOSE_FILE="docker-compose.yml"
        ENV_FILE=".env"
        print_step "Deploy em ambiente de desenvolvimento..."
        ;;
    2)
        COMPOSE_FILE="deploy/docker-compose.production.yml"
        ENV_FILE="deploy/.env"
        print_step "Deploy em ambiente de produção..."
        ;;
    *)
        print_error "Opção inválida!"
        exit 1
        ;;
esac

# Parar containers existentes
print_step "Parando containers existentes..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down || true

# Build das imagens
print_step "Construindo imagens Docker..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE build

# Iniciar sistema
print_step "Iniciando sistema..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d

# Aguardar inicialização
print_step "Aguardando inicialização dos serviços..."
sleep 30

# Health checks
print_step "Verificando saúde dos serviços..."

# Verificar MongoDB
if docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T mongodb mongosh --eval "db.adminCommand('ping')" &> /dev/null; then
    print_success "MongoDB: OK"
else
    print_warning "MongoDB: Aguardando..."
    sleep 10
fi

# Verificar API
if curl -f http://localhost:5000/health &> /dev/null; then
    print_success "API: OK"
else
    print_error "API: Falha na verificação"
    docker-compose -f $COMPOSE_FILE logs rpa-api | tail -20
fi

# Verificar Dashboard
if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
    print_success "Dashboard: OK"
else
    print_warning "Dashboard: Aguardando inicialização..."
fi

# Mostrar status final
echo ""
echo "=================================================================="
print_success "DEPLOY CONCLUÍDO!"
echo ""
echo -e "${BLUE}🔗 URLs de Acesso:${NC}"
echo "📊 Dashboard: http://localhost:8501"
echo "🔗 API: http://localhost:5000"
echo "📖 Documentação: http://localhost:5000/docs"

if [ "$ambiente" = "2" ]; then
    echo "🗄️ MongoDB Admin: mongodb://localhost:27017"
fi

echo ""
echo -e "${BLUE}📋 Comandos Úteis:${NC}"
echo "• Ver logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "• Parar sistema: docker-compose -f $COMPOSE_FILE down"
echo "• Reiniciar: docker-compose -f $COMPOSE_FILE restart"
echo "• Status: docker-compose -f $COMPOSE_FILE ps"

echo ""
print_success "Sistema RPA rodando com sucesso! 🎉"