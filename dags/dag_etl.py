from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from airflow.models import Variable
from airflow.hooks.base import BaseHook

# Configurações padrão seguindo o padrão dos seus DAGs
default_args = {
    'depends_on_past': False,
    'start_date': datetime(2025, 8, 15),
    'email': ['sergio.palmiere@sc.senai.br'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(seconds=10)
}

dag = DAG('dag_etl', 
          description='Pipeline ETL com Spark - Bronze Silver Gold',
          default_args=default_args,
          schedule_interval=None,
          start_date=datetime(2025, 8, 15),
          catchup=False, 
          default_view='graph', 
          tags=['etl', 'spark', 'pipeline'],
          doc_md='''## DAG ETL com Apache Spark
          
          Este pipeline processa dados através das camadas:
          1. Bronze - Dados brutos
          2. Silver - Dados limpos e estruturados  
          3. Gold - Dados agregados para analytics
          ''')

def get_spark_config(**context):
    """Função para obter configurações do Spark de forma segura"""
    try:
        # Tentativa de obter conexão MinIO (se configurada)
        try:
            minio_conn = BaseHook.get_connection("minio_conn")
            minio_extras = minio_conn.extra_dejson
            
            spark_conf = {
                'spark.eventLog.enabled': 'true',
                'spark.eventLog.dir': 'file:/opt/spark/events',
                'spark.hadoop.fs.s3a.access.key': minio_extras.get('s3a.access.key', 'minioadmin'),
                'spark.hadoop.fs.s3a.secret.key': minio_extras.get('s3a.secret.key', 'minioadmin123'),
                'spark.hadoop.fs.s3a.endpoint': minio_extras.get('s3a.endpoint', 'http://minio:9000'),
                'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
                'spark.hadoop.fs.s3a.path.style.access': 'true',
                'spark.hadoop.com.amazonaws.services.s3.enableV4': 'true',
                'spark.hadoop.fs.s3a.aws.credentials.provider': 'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider',
                'spark.sql.adaptive.enabled': 'true',
                'spark.sql.adaptive.coalescePartitions.enabled': 'true'
            }
        except:
            # Configuração padrão se conexão MinIO não existir
            spark_conf = {
                'spark.eventLog.enabled': 'true',
                'spark.eventLog.dir': 'file:/opt/spark/events',
                'spark.sql.adaptive.enabled': 'true',
                'spark.sql.adaptive.coalescePartitions.enabled': 'true'
            }
        
        context['ti'].xcom_push(key='spark_config', value=spark_conf)
        print("Configurações do Spark preparadas com sucesso")
        
    except Exception as e:
        print(f"Erro ao preparar configurações: {e}")
        # Configuração mínima como fallback
        spark_conf = {
            'spark.eventLog.enabled': 'true',
            'spark.eventLog.dir': 'file:/opt/spark/events'
        }
        context['ti'].xcom_push(key='spark_config', value=spark_conf)

def get_postgres_config(**context):
    """Função para obter configurações do PostgreSQL de forma segura"""
    try:
        # Tentativa de obter conexão PostgreSQL
        try:
            postgres_conn = BaseHook.get_connection("postgres_conn")
            postgres_url = f"jdbc:postgresql://{postgres_conn.host}:{postgres_conn.port}/{postgres_conn.schema}"
            postgres_config = {
                'url': postgres_url,
                'user': postgres_conn.login,
                'password': postgres_conn.password
            }
        except:
            # Configuração padrão para pgDuckDB (do docker-compose)
            postgres_config = {
                'url': 'jdbc:postgresql://db:5432/postgres',
                'user': 'postgres',
                'password': 'postgres'
            }
        
        context['ti'].xcom_push(key='postgres_config', value=postgres_config)
        print("Configurações do PostgreSQL preparadas com sucesso")
        
    except Exception as e:
        print(f"Erro ao preparar configurações PostgreSQL: {e}")

# Task para verificar se arquivos de script existem
check_scripts = BashOperator(
    task_id='check_scripts',
    bash_command='''
    echo "Verificando scripts Spark..."
    ls -la /opt/airflow/scripts/
    
    if [ ! -f "/opt/airflow/scripts/01_bronze.py" ]; then
        echo "ERRO: Script 01_bronze.py não encontrado"
        exit 1
    fi
    
    if [ ! -f "/opt/airflow/scripts/02_silver.py" ]; then
        echo "ERRO: Script 02_silver.py não encontrado"
        exit 1
    fi
    
    if [ ! -f "/opt/airflow/scripts/03_consume.py" ]; then
        echo "ERRO: Script 03_consume.py não encontrado"
        exit 1
    fi
    
    echo "Todos os scripts encontrados!"
    ''',
    dag=dag
)

# Task para preparar configurações
prepare_configs = PythonOperator(
    task_id='prepare_configs',
    python_callable=get_spark_config,
    dag=dag
)

prepare_postgres = PythonOperator(
    task_id='prepare_postgres',
    python_callable=get_postgres_config,
    dag=dag
)

# Task 1 - Camada Bronze (dados brutos)
spark_bronze = SparkSubmitOperator(
    task_id='spark_bronze_layer',
    application='/opt/airflow/scripts/01_bronze.py',
    conn_id='spark_default',  # Usando conexão padrão
    conf={
        'spark.eventLog.enabled': 'true',
        'spark.eventLog.dir': 'file:/opt/spark/events',
        'spark.sql.adaptive.enabled': 'true',
        'spark.sql.adaptive.coalescePartitions.enabled': 'true'
    },
    verbose=True,
    dag=dag
)

# Task 2 - Camada Silver (dados limpos)
spark_silver = SparkSubmitOperator(
    task_id='spark_silver_layer',
    application='/opt/airflow/scripts/02_silver.py',
    conn_id='spark_default',
    conf={
        'spark.eventLog.enabled': 'true',
        'spark.eventLog.dir': 'file:/opt/spark/events',
        'spark.sql.adaptive.enabled': 'true',
        'spark.sql.adaptive.coalescePartitions.enabled': 'true'
    },
    verbose=True,
    dag=dag
)

# Task 3 - Camada Gold (dados para consumo)
spark_gold = SparkSubmitOperator(
    task_id='spark_gold_layer',
    application='/opt/airflow/scripts/03_consume.py',
    conn_id='spark_default',
    conf={
        'spark.eventLog.enabled': 'true',
        'spark.eventLog.dir': 'file:/opt/spark/events',
        'spark.sql.adaptive.enabled': 'true',
        'spark.sql.adaptive.coalescePartitions.enabled': 'true'
    },
    application_args=[
        'jdbc:postgresql://db:5432/postgres',
        'postgres',
        'postgres'
    ],
    verbose=True,
    dag=dag
)

# Task de verificação final
verify_pipeline = BashOperator(
    task_id='verify_pipeline',
    bash_command='''
    echo "Pipeline ETL executado com sucesso!"
    echo "Verificando logs do Spark..."
    ls -la /opt/spark/events/ | tail -5
    echo "Pipeline concluído."
    ''',
    dag=dag
)

# Definindo as dependências do pipeline
check_scripts >> [prepare_configs, prepare_postgres]
[prepare_configs, prepare_postgres] >> spark_bronze
spark_bronze >> spark_silver
spark_silver >> spark_gold
spark_gold >> verify_pipeline