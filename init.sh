#!/bin/bash

# =============================================================================
# DATA PLATFORM INITIALIZATION SCRIPT
# =============================================================================
# Script para inicializar Airflow + Spark + MinIO + Jupyter + PostgreSQL
# =============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Função para printar com cor
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Função para printar header
print_header() {
    echo ""
    print_color "$CYAN" "============================================================================="
    print_color "$CYAN" " $1"
    print_color "$CYAN" "============================================================================="
    echo ""
}

# Função para verificar se comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================
print_header "PRE-FLIGHT CHECKS"

# Verificar Docker
if ! command_exists docker; then
    print_color "$RED" "❌ Docker não está instalado!"
    exit 1
fi
print_color "$GREEN" "✓ Docker instalado: $(docker --version)"

# Verificar Docker Compose
if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    print_color "$RED" "❌ Docker Compose não está instalado!"
    exit 1
fi
print_color "$GREEN" "✓ Docker Compose instalado"

# Verificar se arquivo .env existe
if [ ! -f .env ]; then
    print_color "$RED" "❌ Arquivo .env não encontrado!"
    exit 1
fi
print_color "$GREEN" "✓ Arquivo .env encontrado"

# =============================================================================
# CREATE DIRECTORY STRUCTURE
# =============================================================================
print_header "CREATING DIRECTORY STRUCTURE"

directories=("dags" "logs" "plugins" "data" "notebooks" "spark-apps")

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_color "$GREEN" "✓ Diretório criado: $dir/"
    else
        print_color "$YELLOW" "⚠ Diretório já existe: $dir/"
    fi
done

# Criar subdiretórios em data
mkdir -p data/raw data/processed data/output
print_color "$GREEN" "✓ Subdiretórios criados em data/"

# =============================================================================
# SET PERMISSIONS
# =============================================================================
print_header "SETTING PERMISSIONS"

# Obter AIRFLOW_UID do .env
source .env
AIRFLOW_UID=${AIRFLOW_UID:-50000}

print_color "$YELLOW" "→ Configurando permissões para AIRFLOW_UID: $AIRFLOW_UID"

for dir in "${directories[@]}"; do
    chmod -R 755 "$dir"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo chown -R $AIRFLOW_UID:$AIRFLOW_UID "$dir" 2>/dev/null || chown -R $AIRFLOW_UID:$AIRFLOW_UID "$dir"
    fi
done

print_color "$GREEN" "✓ Permissões configuradas"

# =============================================================================
# STOP EXISTING CONTAINERS
# =============================================================================
print_header "STOPPING EXISTING CONTAINERS"

if docker ps -a | grep -q "data-platform"; then
    print_color "$YELLOW" "→ Parando containers existentes..."
    docker-compose down -v 2>/dev/null || docker compose down -v 2>/dev/null || true
    print_color "$GREEN" "✓ Containers parados"
else
    print_color "$YELLOW" "⚠ Nenhum container em execução"
fi

# =============================================================================
# BUILD CUSTOM AIRFLOW IMAGE
# =============================================================================
print_header "BUILDING CUSTOM AIRFLOW IMAGE"

print_color "$YELLOW" "→ Construindo imagem customizada do Airflow..."
print_color "$YELLOW" "   (Isso pode levar alguns minutos na primeira execução)"

if docker-compose build 2>/dev/null || docker compose build 2>/dev/null; then
    print_color "$GREEN" "✓ Imagem construída com sucesso"
else
    print_color "$RED" "❌ Falha ao construir imagem"
    exit 1
fi

# =============================================================================
# START SERVICES
# =============================================================================
print_header "STARTING SERVICES"

print_color "$YELLOW" "→ Iniciando serviços..."
print_color "$YELLOW" "   (Isso pode levar alguns minutos...)"

if docker-compose up -d 2>/dev/null || docker compose up -d 2>/dev/null; then
    print_color "$GREEN" "✓ Serviços iniciados"
else
    print_color "$RED" "❌ Falha ao iniciar serviços"
    exit 1
fi

# =============================================================================
# WAIT FOR SERVICES TO BE HEALTHY
# =============================================================================
print_header "WAITING FOR SERVICES TO BE HEALTHY"

sleep 10

services=("postgres" "redis" "minio" "spark-master" "spark-worker" "airflow-webserver" "jupyter")
total_services=${#services[@]}
healthy_count=0

for service in "${services[@]}"; do
    print_color "$YELLOW" "→ Verificando $service..."
    
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker ps | grep -q "data-platform-$service" && docker ps --filter "name=data-platform-$service" --filter "health=healthy" | grep -q "data-platform-$service" 2>/dev/null; then
            print_color "$GREEN" "  ✓ $service está saudável"
            ((healthy_count++))
            break
        elif docker ps | grep -q "data-platform-$service"; then
            print_color "$YELLOW" "  ⏳ $service está iniciando... (tentativa $((attempt+1))/$max_attempts)"
            sleep 5
            ((attempt++))
        else
            print_color "$YELLOW" "  ⏳ $service está iniciando... (tentativa $((attempt+1))/$max_attempts)"
            sleep 5
            ((attempt++))
        fi
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_color "$YELLOW" "  ⚠ $service pode não estar totalmente pronto"
    fi
done

echo ""
print_color "$CYAN" "Status: $healthy_count/$total_services serviços verificados"

# =============================================================================
# DISPLAY ACCESS INFORMATION
# =============================================================================
print_header "ACCESS INFORMATION"

echo ""
print_color "$GREEN" "🚀 PLATAFORMA DE DADOS INICIADA COM SUCESSO!"
echo ""

print_color "$CYAN" "📊 AIRFLOW WEBSERVER"
print_color "$BLUE" "   URL: http://localhost:8080"
print_color "$BLUE" "   Username: airflow"
print_color "$BLUE" "   Password: airflow"
echo ""

print_color "$CYAN" "⚡ SPARK MASTER UI"
print_color "$BLUE" "   URL: http://localhost:8081"
echo ""

print_color "$CYAN" "⚡ SPARK WORKER UI"
print_color "$BLUE" "   URL: http://localhost:8082"
echo ""

print_color "$CYAN" "📦 MINIO CONSOLE (S3)"
print_color "$BLUE" "   URL: http://localhost:9001"
print_color "$BLUE" "   Username: minioadmin"
print_color "$BLUE" "   Password: minioadmin123"
print_color "$BLUE" "   API Endpoint: http://localhost:9000"
echo ""

print_color "$CYAN" "📓 JUPYTER NOTEBOOK"
print_color "$BLUE" "   URL: http://localhost:8888"
print_color "$BLUE" "   Token: jupyter123"
echo ""

print_color "$CYAN" "🐘 POSTGRESQL"
print_color "$BLUE" "   Host: localhost"
print_color "$BLUE" "   Port: 5432"
print_color "$BLUE" "   Database: airflow"
print_color "$BLUE" "   Username: airflow"
print_color "$BLUE" "   Password: airflow"
echo ""

print_color "$CYAN" "🌸 FLOWER (Celery Monitor) - Opcional"
print_color "$BLUE" "   Executar: docker-compose --profile flower up -d"
print_color "$BLUE" "   URL: http://localhost:5555"
echo ""

# =============================================================================
# USEFUL COMMANDS
# =============================================================================
print_header "USEFUL COMMANDS"

print_color "$YELLOW" "📝 Ver logs de todos os serviços:"
print_color "$BLUE" "   docker-compose logs -f"
echo ""

print_color "$YELLOW" "📝 Ver logs de um serviço específico:"
print_color "$BLUE" "   docker-compose logs -f airflow-webserver"
print_color "$BLUE" "   docker-compose logs -f spark-master"
echo ""

print_color "$YELLOW" "📝 Parar todos os serviços:"
print_color "$BLUE" "   docker-compose down"
echo ""

print_color "$YELLOW" "📝 Parar e remover volumes:"
print_color "$BLUE" "   docker-compose down -v"
echo ""

print_color "$YELLOW" "📝 Verificar status dos containers:"
print_color "$BLUE" "   docker-compose ps"
echo ""

print_color "$YELLOW" "📝 Reiniciar um serviço específico:"
print_color "$BLUE" "   docker-compose restart airflow-scheduler"
echo ""

# =============================================================================
# DIRECTORY STRUCTURE INFO
# =============================================================================
print_header "DIRECTORY STRUCTURE"

print_color "$YELLOW" "📁 dags/          → Coloque seus DAGs do Airflow aqui"
print_color "$YELLOW" "📁 logs/          → Logs do Airflow"
print_color "$YELLOW" "📁 plugins/       → Plugins customizados do Airflow"
print_color "$YELLOW" "📁 data/          → Dados para processamento"
print_color "$YELLOW" "📁 notebooks/     → Notebooks Jupyter"
print_color "$YELLOW" "📁 spark-apps/    → Aplicações Spark"
echo ""

print_color "$GREEN" "✨ Plataforma pronta para uso!"
print_color "$CYAN" "============================================================================="
echo ""

