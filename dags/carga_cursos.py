"""
=============================================================================
DAG - CARGA DE CURSOS NO POSTGRESQL
=============================================================================
Pipeline ETL para carregar dados do arquivo carga_prim.csv na tabela cursos
=============================================================================
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import logging

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

# Caminho do arquivo CSV
CSV_FILE = '/opt/airflow/notebooks/dados/carga_prim.csv'

# =============================================================================
# DEFAULT ARGS
# =============================================================================

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email': ['sergio.palmiere@sc.senai.br'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
}

# =============================================================================
# FUNÇÕES PYTHON
# =============================================================================

def extract_data(**context):
    """
    Task 1: Extrair dados do CSV
    """
    try:
        logging.info(f"📂 Lendo arquivo: {CSV_FILE}")
        
        # Ler CSV com configurações robustas
        df = pd.read_csv(
            CSV_FILE,
            sep=',',
            quotechar='"',
            escapechar='\\',
            encoding='utf-8',
            on_bad_lines='warn'
        )
        
        logging.info(f"✅ Arquivo lido com sucesso!")
        logging.info(f"   Registros encontrados: {len(df)}")
        logging.info(f"   Colunas: {list(df.columns)}")
        
        # Salvar informações no XCom
        context['ti'].xcom_push(key='total_rows', value=len(df))
        context['ti'].xcom_push(key='columns', value=list(df.columns))
        
        # Mostrar amostra
        logging.info(f"\n📊 Primeiras 5 linhas:\n{df.head()}")
        logging.info(f"\n🔍 Info do DataFrame:\n{df.info()}")
        
        return CSV_FILE
        
    except FileNotFoundError:
        logging.error(f"❌ Arquivo não encontrado: {CSV_FILE}")
        raise
    except Exception as e:
        logging.error(f"❌ Erro ao ler arquivo: {e}")
        raise


def transform_data(**context):
    """
    Task 2: Transformar dados
    """
    try:
        logging.info("🔄 Iniciando transformação dos dados...")
        
        # Ler CSV novamente com configurações robustas
        df = pd.read_csv(
            CSV_FILE,
            sep=',',
            quotechar='"',
            escapechar='\\',
            encoding='utf-8',
            on_bad_lines='warn'
        )
        
        # Verificar estrutura
        logging.info(f"Colunas originais: {list(df.columns)}")
        logging.info(f"Total de registros: {len(df)}")
        
        # Verificar se course_id é numérico
        logging.info(f"Tipo de course_id: {df['course_id'].dtype}")
        logging.info(f"Amostra de course_id: {df['course_id'].head()}")
        
        # Selecionar apenas as colunas que existem e são necessárias
        columns_to_keep = ['course_id', 'course_title', 'url', 'is_paid', 'price', 
                          'num_subscribers', 'num_reviews', 'num_lectures', 'level', 
                          'content_duration', 'published_timestamp', 'subject']
        
        # Manter apenas colunas que existem
        available_columns = [col for col in columns_to_keep if col in df.columns]
        df_clean = df[available_columns].copy()
        
        logging.info(f"Colunas selecionadas: {available_columns}")
        
        # Remover duplicatas baseado em course_id
        initial_count = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=['course_id'])
        duplicates_removed = initial_count - len(df_clean)
        
        # Remover valores nulos em course_id
        df_clean = df_clean.dropna(subset=['course_id'])
        
        # Converter tipos de dados com tratamento de erros
        if 'course_id' in df_clean.columns:
            try:
                df_clean['course_id'] = pd.to_numeric(df_clean['course_id'], errors='coerce')
                # Remover linhas onde course_id não pôde ser convertido
                df_clean = df_clean.dropna(subset=['course_id'])
                df_clean['course_id'] = df_clean['course_id'].astype('Int64')
            except Exception as e:
                logging.error(f"Erro ao converter course_id: {e}")
                raise
        
        if 'is_paid' in df_clean.columns:
            df_clean['is_paid'] = df_clean['is_paid'].astype(bool)
        
        if 'price' in df_clean.columns:
            df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce')
        
        if 'published_timestamp' in df_clean.columns:
            df_clean['published_timestamp'] = pd.to_datetime(df_clean['published_timestamp'], errors='coerce')
        
        logging.info(f"✅ Transformação concluída!")
        logging.info(f"   Duplicatas removidas: {duplicates_removed}")
        logging.info(f"   Registros finais: {len(df_clean)}")
        
        # Salvar dados transformados temporariamente
        temp_file = '/opt/airflow/data/cursos_transformed.csv'
        df_clean.to_csv(temp_file, index=False)
        
        # Passar informações via XCom
        context['ti'].xcom_push(key='transformed_file', value=temp_file)
        context['ti'].xcom_push(key='records_to_load', value=len(df_clean))
        context['ti'].xcom_push(key='duplicates_removed', value=duplicates_removed)
        
        return temp_file
        
    except Exception as e:
        logging.error(f"❌ Erro na transformação: {e}")
        raise


def load_data(**context):
    """
    Task 3: Carregar dados no PostgreSQL
    """
    try:
        logging.info("💾 Iniciando carga no banco de dados...")
        
        # Obter arquivo transformado do XCom
        temp_file = context['ti'].xcom_pull(key='transformed_file', task_ids='transform_data')
        
        # Ler dados transformados
        df = pd.read_csv(temp_file)
        
        logging.info(f"📊 Registros a carregar: {len(df)}")
        logging.info(f"📋 Colunas: {list(df.columns)}")
        
        # Conectar ao PostgreSQL usando Airflow Hook
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        
        # Obter conexão SQLAlchemy
        engine = pg_hook.get_sqlalchemy_engine()
        
        # Carregar dados usando pandas to_sql (mais eficiente e automático)
        try:
            df.to_sql(
                name='cursos',
                con=engine,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=1000
            )
            
            records_inserted = len(df)
            
        except Exception as e:
            logging.warning(f"⚠️ Erro ao inserir em lote, tentando registro por registro...")
            records_inserted = 0
            
            # Se falhar, tentar registro por registro (mais lento mas ignora duplicatas)
            with engine.begin() as conn:
                for idx, row in df.iterrows():
                    try:
                        # Converter row para dict
                        row_dict = row.to_dict()
                        
                        # Criar query dinâmica baseada nas colunas disponíveis
                        columns = ', '.join(row_dict.keys())
                        placeholders = ', '.join(['%s'] * len(row_dict))
                        values = tuple(row_dict.values())
                        
                        query = f"""
                            INSERT INTO cursos ({columns})
                            VALUES ({placeholders})
                            ON CONFLICT (course_id) DO NOTHING
                        """
                        
                        conn.execute(query, values)
                        records_inserted += 1
                        
                    except Exception as row_error:
                        logging.warning(f"⚠️ Erro no registro {idx}: {str(row_error)[:100]}")
                        continue
        
        logging.info(f"✅ Carga concluída!")
        logging.info(f"   Registros inseridos: {records_inserted}")
        
        # Salvar estatísticas no XCom
        context['ti'].xcom_push(key='records_inserted', value=records_inserted)
        
        return records_inserted
        
    except Exception as e:
        logging.error(f"❌ Erro ao carregar dados: {e}")
        raise


def validate_data(**context):
    """
    Task 4: Validar dados carregados
    """
    try:
        logging.info("🔍 Validando dados carregados...")
        
        # Conectar ao PostgreSQL
        pg_hook = PostgresHook(postgres_conn_id='postgres_default')
        
        # Contar registros
        result = pg_hook.get_first("SELECT COUNT(*) FROM cursos")
        total_records = result[0]
        
        # Obter estatísticas por subject (top 10)
        stats = pg_hook.get_records("""
            SELECT subject, COUNT(*) as total
            FROM cursos
            WHERE subject IS NOT NULL
            GROUP BY subject
            ORDER BY total DESC
            LIMIT 10
        """)
        
        # Estatísticas por level
        level_stats = pg_hook.get_records("""
            SELECT level, COUNT(*) as total
            FROM cursos
            WHERE level IS NOT NULL
            GROUP BY level
            ORDER BY total DESC
        """)
        
        # Estatísticas de preço
        price_stats = pg_hook.get_first("""
            SELECT 
                COUNT(CASE WHEN is_paid = true THEN 1 END) as paid_courses,
                COUNT(CASE WHEN is_paid = false THEN 1 END) as free_courses,
                ROUND(AVG(CASE WHEN is_paid = true THEN price END), 2) as avg_price,
                ROUND(MAX(price), 2) as max_price
            FROM cursos
        """)
        
        logging.info(f"✅ Validação concluída!")
        logging.info(f"   Total de cursos na tabela: {total_records}")
        
        if stats:
            logging.info(f"\n📈 Top 10 assuntos:")
            for stat in stats:
                logging.info(f"   {stat[0]}: {stat[1]} cursos")
        
        if level_stats:
            logging.info(f"\n📊 Distribuição por nível:")
            for stat in level_stats:
                logging.info(f"   {stat[0]}: {stat[1]} cursos")
        
        if price_stats:
            logging.info(f"\n💰 Estatísticas de preço:")
            logging.info(f"   Cursos pagos: {price_stats[0]}")
            logging.info(f"   Cursos gratuitos: {price_stats[1]}")
            logging.info(f"   Preço médio: ${price_stats[2]}")
            logging.info(f"   Preço máximo: ${price_stats[3]}")
        
        # Obter dados do XCom
        records_inserted = context['ti'].xcom_pull(key='records_inserted', task_ids='load_data')
        duplicates_removed = context['ti'].xcom_pull(key='duplicates_removed', task_ids='transform_data')
        
        # Resumo final
        summary = {
            'total_in_table': total_records,
            'records_inserted': records_inserted,
            'duplicates_removed': duplicates_removed
        }
        
        context['ti'].xcom_push(key='summary', value=summary)
        
        return summary
        
    except Exception as e:
        logging.error(f"❌ Erro na validação: {e}")
        raise


# =============================================================================
# DAG DEFINITION
# =============================================================================

with DAG(
    dag_id='dag_carga_cursos',
    default_args=default_args,
    description='Pipeline ETL: Carga de cursos do CSV para PostgreSQL',
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['etl', 'cursos', 'postgresql', 'csv'],
    doc_md=__doc__
) as dag:
    
    # -------------------------------------------------------------------------
    # TASK 1: Verificar se tabela existe, criar se necessário
    # -------------------------------------------------------------------------
    create_table = PostgresOperator(
        task_id='create_table_if_not_exists',
        postgres_conn_id='postgres_default',
        sql="""
        CREATE TABLE IF NOT EXISTS cursos (
            id SERIAL PRIMARY KEY,
            course_id BIGINT NOT NULL UNIQUE,
            course_title TEXT,
            url TEXT,
            is_paid BOOLEAN,
            price DECIMAL(10,2),
            num_subscribers INTEGER,
            num_reviews INTEGER,
            num_lectures INTEGER,
            level VARCHAR(50),
            content_duration DECIMAL(10,2),
            published_timestamp TIMESTAMP,
            subject VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_cursos_course_id ON cursos(course_id);
        CREATE INDEX IF NOT EXISTS idx_cursos_subject ON cursos(subject);
        CREATE INDEX IF NOT EXISTS idx_cursos_level ON cursos(level);
        CREATE INDEX IF NOT EXISTS idx_cursos_is_paid ON cursos(is_paid);
        """,
        doc_md="""
        ### Criar Tabela Cursos
        Cria a tabela cursos com todas as colunas do CSV.
        """
    )
    
    # -------------------------------------------------------------------------
    # TASK 2: Extrair dados do CSV
    # -------------------------------------------------------------------------
    extract = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        doc_md="""
        ### Extrair Dados
        Lê o arquivo carga_prim.csv e valida a estrutura.
        """
    )
    
    # -------------------------------------------------------------------------
    # TASK 3: Transformar dados
    # -------------------------------------------------------------------------
    transform = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        doc_md="""
        ### Transformar Dados
        - Remove duplicatas
        - Remove valores nulos
        - Converte tipos de dados
        """
    )
    
    # -------------------------------------------------------------------------
    # TASK 4: Carregar dados no PostgreSQL
    # -------------------------------------------------------------------------
    load = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
        doc_md="""
        ### Carregar Dados
        Insere dados na tabela cursos (ignora duplicatas).
        """
    )
    
    # -------------------------------------------------------------------------
    # TASK 5: Validar dados carregados
    # -------------------------------------------------------------------------
    validate = PythonOperator(
        task_id='validate_data',
        python_callable=validate_data,
        doc_md="""
        ### Validar Dados
        Verifica integridade e gera estatísticas dos dados carregados.
        """
    )
    
    # -------------------------------------------------------------------------
    # DEFINIR ORDEM DE EXECUÇÃO
    # -------------------------------------------------------------------------
    create_table >> extract >> transform >> load >> validate