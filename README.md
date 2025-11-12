 # 🚀 Plataforma de Dados Completa - Docker

[![Airflow](https://img.shields.io/badge/Airflow-2.8.1-017CEE?logo=apache-airflow)](https://airflow.apache.org/)
[![Spark](https://img.shields.io/badge/Spark-3.5.0-E25A1C?logo=apache-spark)](https://spark.apache.org/)
[![MLflow](https://img.shields.io/badge/MLflow-Latest-0194E2?logo=mlflow)](https://mlflow.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)](https://www.postgresql.org/)

Plataforma completa de dados, analytics e machine learning com **16 serviços integrados** rodando em containers Docker.

---

## 📋 **Índice**

- [Arquitetura](#-arquitetura)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação Rápida](#-instalação-rápida)
- [Instalação Detalhada](#-instalação-detalhada)
- [Serviços e Acessos](#-serviços-e-acessos)
- [Estrutura de Diretórios](#-estrutura-de-diretórios)
- [Uso](#-uso)
- [Troubleshooting](#-troubleshooting)
- [Manutenção](#-manutenção)

---

## 🏗️ **Arquitetura**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PLATAFORMA DE DADOS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Airflow    │  │    Spark     │  │    MinIO     │          │
│  │ Orquestração │◄─┤ Processamento│◄─┤  Storage S3  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
│         │                  │                                      │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────────────┐          │
│  │   MLflow     │  │   Jupyter    │  │   Metabase   │          │
│  │ ML Tracking  │  │  Notebooks   │  │  Analytics   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Grafana +   │  │  PostgreSQL  │  │   pgAdmin    │          │
│  │  Prometheus  │  │   Database   │  │  DB Manager  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💻 **Pré-requisitos**

### **Hardware Recomendado:**
- **CPU**: 4+ cores
- **RAM**: 8GB+ (16GB recomendado)
- **Disco**: 50GB+ livres
- **SO**: Linux (Ubuntu 20.04+), macOS, Windows + WSL2

### **Software Necessário:**

#### **Ubuntu/Debian:**
```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install docker-compose -y

# Reiniciar sessão
newgrp docker
```

#### **Windows:**
1. Instalar [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Habilitar WSL2
3. Instalar [Ubuntu no WSL2](https://ubuntu.com/wsl)

#### **macOS:**
```bash
# Instalar Docker Desktop
brew install --cask docker

# Ou via Homebrew
brew install docker docker-compose
```

### **Verificar Instalação:**
```bash
docker --version
docker-compose --version
```

---

## ⚡ **Instalação Rápida**

```bash
# 1. Clonar/Criar diretório do projeto
mkdir -p ~/projects/Airflow_Tool
cd ~/projects/Airflow_Tool

# 2. Criar estrutura de diretórios
mkdir -p dags logs plugins data notebooks spark-apps prometheus grafana/provisioning/{datasources,dashboards}

# 3. Copiar arquivos de configuração
# - .env
# - docker-compose.yaml
# - Dockerfile
# - requirements.txt
# - prometheus/prometheus.yml
# - grafana/provisioning/datasources/prometheus.yml

# 4. Configurar permissões
chmod -R 755 dags logs plugins data notebooks spark-apps
sudo chown -R 50000:0 dags logs plugins

# 5. Build e inicialização
docker-compose build
docker-compose up -d

# 6. Aguardar inicialização (2-3 minutos)
watch docker-compose ps

# 7. Criar bancos de dados adicionais
docker exec -it data-platform-postgres psql -U airflow -d postgres -c "CREATE DATABASE metabase;"

# 8. Criar bucket MLflow no MinIO
docker run --rm --network data-platform-network minio/mc:latest /bin/sh -c "
mc alias set myminio http://minio:9000 minioadmin minioadmin123;
mc mb myminio/mlflow-artifacts --ignore-existing;
"
```

**Pronto! Acesse:** http://localhost:8080

---

## 📖 **Instalação Detalhada**

### **Passo 1: Preparar Ambiente**

```bash
# Criar diretório do projeto
mkdir -p ~/projects/Airflow_Tool
cd ~/projects/Airflow_Tool

# Criar estrutura de pastas
mkdir -p {dags,logs,plugins,data,notebooks,spark-apps}
mkdir -p data/{raw,processed,output}
mkdir -p prometheus
mkdir -p grafana/provisioning/{datasources,dashboards}

# Verificar estrutura
tree -L 2
```

### **Passo 2: Criar Arquivos de Configuração**

#### **2.1 - Arquivo `.env`**

Criar arquivo `.env` na raiz do projeto:

```env
# Airflow
AIRFLOW_IMAGE_NAME=apache/airflow:2.8.1-python3.11
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow

# SMTP (opcional - configurar com suas credenciais)
AIRFLOW_SMTP_HOST=smtp.gmail.com
AIRFLOW_SMTP_USER=seu-email@gmail.com
AIRFLOW_SMTP_PASSWORD=sua-senha-app
AIRFLOW_SMTP_PORT=587
AIRFLOW_MAIL_FROM=Airflow

# PostgreSQL
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
POSTGRES_PORT=5433

# Redis
REDIS_PORT=6379

# Spark
SPARK_VERSION=3.5.0
SPARK_IMAGE=apache/spark:3.5.0
SPARK_MASTER_PORT=7077
SPARK_MASTER_WEBUI_PORT=8090
SPARK_WORKER_WEBUI_PORT=8091
SPARK_WORKER_CORES=2
SPARK_WORKER_MEMORY=2g

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_API_PORT=9002
MINIO_CONSOLE_PORT=9001

# Jupyter
JUPYTER_PORT=8888
JUPYTER_TOKEN=jupyter123
JUPYTER_ENABLE_LAB=yes

# Flower
FLOWER_PORT=5555
```

#### **2.2 - Arquivo `prometheus/prometheus.yml`**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'airflow'
    static_configs:
      - targets: ['airflow-webserver:8080']

  - job_name: 'spark-master'
    static_configs:
      - targets: ['spark-master:8080']

  - job_name: 'minio'
    metrics_path: /minio/v2/metrics/cluster
    static_configs:
      - targets: ['minio:9000']
```

#### **2.3 - Arquivo `grafana/provisioning/datasources/prometheus.yml`**

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true

  - name: PostgreSQL
    type: postgres
    url: postgres:5432
    database: airflow
    user: airflow
    secureJsonData:
      password: airflow
    jsonData:
      sslmode: disable
      postgresVersion: 1500
    editable: true
```

#### **2.4 - Copiar `docker-compose.yaml`, `Dockerfile` e `requirements.txt`**

Copie os arquivos dos artefatos fornecidos anteriormente.

### **Passo 3: Configurar Permissões**

```bash
# Permissões para Airflow (UID 50000)
sudo chown -R 50000:0 dags logs plugins

# Permissões gerais
chmod -R 755 dags logs plugins data notebooks spark-apps

# Permissões completas para desenvolvimento
chmod -R 777 notebooks data
```

### **Passo 4: Build e Inicialização**

```bash
# Build das imagens customizadas
docker-compose build --no-cache

# Subir infraestrutura base
docker-compose up -d postgres redis minio

# Aguardar 15 segundos
sleep 15

# Subir demais serviços
docker-compose up -d

# Monitorar inicialização
watch -n 2 docker-compose ps
```

### **Passo 5: Configuração Pós-Instalação**

```bash
# Criar database para Metabase
docker exec -it data-platform-postgres psql -U airflow -d postgres -c "CREATE DATABASE metabase;"

# Criar bucket para MLflow
docker run --rm --network data-platform-network minio/mc:latest /bin/sh -c "
mc alias set myminio http://minio:9000 minioadmin minioadmin123;
mc mb myminio/mlflow-artifacts --ignore-existing;
mc ls myminio/;
"

# Configurar conexão PostgreSQL no Airflow
docker exec -it data-platform-airflow-webserver airflow connections add 'postgres_default' \
    --conn-type 'postgres' \
    --conn-host 'postgres' \
    --conn-schema 'airflow' \
    --conn-login 'airflow' \
    --conn-password 'airflow' \
    --conn-port 5432
```

---

## 🌐 **Serviços e Acessos**

| Serviço | URL | Usuário | Senha | Descrição |
|---------|-----|---------|-------|-----------|
| **📊 Airflow** | http://localhost:8080 | `airflow` | `airflow` | Orquestração de workflows |
| **⚡ Spark Master** | http://localhost:8090 | - | - | Interface do Spark Master |
| **⚡ Spark Worker** | http://localhost:8091 | - | - | Interface do Spark Worker |
| **📦 MinIO Console** | http://localhost:9001 | `minioadmin` | `minioadmin123` | Storage S3-compatible |
| **📓 Jupyter Lab** | http://localhost:8888 | - | `jupyter123` | Notebooks interativos |
| **🤖 MLflow** | http://localhost:5001 | - | - | ML experiment tracking |
| **📈 Metabase** | http://localhost:3000 | *criar* | *criar* | Business Intelligence |
| **📊 Grafana** | http://localhost:3001 | `admin` | `admin` | Dashboards e monitoring |
| **📈 Prometheus** | http://localhost:9090 | - | - | Métricas e alertas |
| **🔧 pgAdmin** | http://localhost:5050 | `admin@admin.com` | `admin` | PostgreSQL manager |
| **🐘 PostgreSQL** | `localhost:5433` | `airflow` | `airflow` | Database principal |
| **🌸 Flower** | http://localhost:5555 | - | - | Celery monitoring (opcional) |

### **Notas Importantes:**

- **Metabase**: Requer configuração inicial na primeira vez
- **Jupyter**: Token = `jupyter123` (configurável no `.env`)
- **PostgreSQL**: Porta externa `5433` (interna `5432`)
- **MinIO API**: Porta `9002` (Console `9001`)
- **Flower**: Executar com `docker-compose --profile flower up -d`

---

## 📁 **Estrutura de Diretórios**

```
Airflow_Tool/
├── dags/                      # DAGs do Airflow
│   ├── dag_carga_cursos.py
│   └── example_dag.py
├── logs/                      # Logs do Airflow
├── plugins/                   # Plugins customizados
├── data/                      # Dados para processamento
│   ├── raw/                   # Dados brutos
│   ├── processed/             # Dados processados
│   └── output/                # Resultados
├── notebooks/                 # Notebooks Jupyter
│   └── dados/                 # Datasets
├── spark-apps/                # Aplicações Spark
├── prometheus/
│   └── prometheus.yml         # Config Prometheus
├── grafana/
│   └── provisioning/
│       ├── datasources/       # Datasources Grafana
│       └── dashboards/        # Dashboards Grafana
├── .env                       # Variáveis de ambiente
├── docker-compose.yaml        # Orquestração Docker
├── Dockerfile                 # Imagem customizada Airflow
├── requirements.txt           # Dependências Python
└── README.md                  # Este arquivo
```

---

## 🎯 **Uso**

### **Criar uma DAG no Airflow**

1. Criar arquivo `dags/minha_dag.py`:

```python
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

def hello_world():
    print("Hello from Airflow!")

with DAG(
    dag_id='hello_world',
    start_date=datetime(2025, 1, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:
    
    task = PythonOperator(
        task_id='say_hello',
        python_callable=hello_world
    )
```

2. Aguardar 30 segundos
3. Acessar http://localhost:8080
4. Ativar a DAG
5. Executar manualmente

### **Usar Spark via Jupyter**

1. Acessar http://localhost:8888 (token: `jupyter123`)
2. Criar novo notebook
3. Código de exemplo:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Exemplo") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

df = spark.read.csv("/home/jovyan/data/dados.csv", header=True)
df.show()
```

### **Tracking ML com MLflow**

```python
import mlflow

mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("meu_experimento")

with mlflow.start_run():
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("accuracy", 0.95)
```

### **Upload de Dados no MinIO**

1. Acessar http://localhost:9001
2. Login: `minioadmin` / `minioadmin123`
3. Ir em **Buckets** → Selecionar bucket
4. Clicar em **Upload** → Escolher arquivo

---

## 🔧 **Troubleshooting**

### **Container não inicia**

```bash
# Ver logs
docker-compose logs [nome-do-servico]

# Reiniciar serviço específico
docker-compose restart [nome-do-servico]

# Recriar container
docker-compose up -d --force-recreate [nome-do-servico]
```

### **Porta já em uso**

```bash
# Verificar o que está usando a porta
sudo lsof -i :8080

# Matar processo
sudo kill -9 [PID]

# Ou alterar porta no .env
```

### **Erro de permissão**

```bash
# Corrigir permissões Airflow
sudo chown -R 50000:0 dags logs plugins

# Corrigir permissões Jupyter
chmod -R 777 notebooks data
```

### **Serviço "unhealthy"**

```bash
# Ver healthcheck
docker inspect [container-name] | grep -A 10 Health

# Aguardar mais tempo (alguns serviços demoram)
sleep 60
docker-compose ps
```

### **Limpeza completa**

```bash
# Parar tudo
docker-compose down

# Remover volumes (⚠️ APAGA DADOS!)
docker-compose down -v

# Limpar sistema
docker system prune -af

# Rebuild completo
docker-compose build --no-cache
docker-compose up -d
```

---

## 🛠️ **Manutenção**

### **Comandos Úteis**

```bash
# Ver status de todos os serviços
docker-compose ps

# Ver logs em tempo real
docker-compose logs -f [servico]

# Parar todos os serviços
docker-compose stop

# Iniciar todos os serviços
docker-compose start

# Reiniciar serviço específico
docker-compose restart airflow-scheduler

# Ver uso de recursos
docker stats

# Backup de volumes
docker run --rm -v data-platform_postgres-db-volume:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres-backup.tar.gz /data
```

### **Atualizar Versões**

```bash
# Pull de novas imagens
docker-compose pull

# Rebuild
docker-compose build --no-cache

# Recriar containers
docker-compose up -d --force-recreate
```

### **Monitoramento**

- **Grafana**: http://localhost:3001
  - Importar dashboards: 1860, 7362, 10991
- **Prometheus**: http://localhost:9090
  - Verificar targets em Status → Targets
- **Flower** (Celery): `docker-compose --profile flower up -d`

---

## 📚 **Recursos Adicionais**

- [Documentação Airflow](https://airflow.apache.org/docs/)
- [Documentação Spark](https://spark.apache.org/docs/latest/)
- [Documentação MLflow](https://mlflow.org/docs/latest/index.html)
- [Documentação MinIO](https://min.io/docs/minio/linux/index.html)
- [Dashboards Grafana](https://grafana.com/grafana/dashboards/)

---

## 📝 **Licença**

Este projeto é open source e está sob a licença MIT.

---

## 👥 **Contribuindo**

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 🆘 **Suporte**

Para questões e suporte:
- Abra uma issue no GitHub
- Consulte a documentação oficial de cada ferramenta
- Verifique a seção [Troubleshooting](#-troubleshooting)

---

**🎉 Desenvolvido com ❤️ para a comunidade de Data Engineering**
