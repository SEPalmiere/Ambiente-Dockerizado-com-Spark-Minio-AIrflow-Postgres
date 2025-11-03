"""
=============================================================================
SCRIPT PARA POPULAR TABELA CURSOS A PARTIR DE CSV
=============================================================================
Lê o arquivo carga_amostra.csv e insere os dados na tabela cursos
=============================================================================
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

# Caminho do arquivo CSV
CSV_FILE = '/opt/airflow/notebooks/dados/carga_amostra.csv'

# Configurações do PostgreSQL
DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'airflow',
    'user': 'airflow',
    'password': 'airflow'
}

# =============================================================================
# FUNÇÕES
# =============================================================================

def connect_db():
    """Conecta ao banco de dados PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logging.info("✅ Conexão com PostgreSQL estabelecida")
        return conn
    except Exception as e:
        logging.error(f"❌ Erro ao conectar ao banco: {e}")
        raise


def read_csv(file_path):
    """Lê o arquivo CSV"""
    try:
        # Ler CSV
        df = pd.read_csv(file_path)
        logging.info(f"✅ Arquivo CSV lido: {len(df)} registros encontrados")
        logging.info(f"📋 Colunas: {list(df.columns)}")
        
        # Mostrar primeiras linhas
        logging.info(f"\n📊 Primeiras linhas do CSV:\n{df.head()}")
        
        return df
    except FileNotFoundError:
        logging.error(f"❌ Arquivo não encontrado: {file_path}")
        raise
    except Exception as e:
        logging.error(f"❌ Erro ao ler CSV: {e}")
        raise


def process_data(df):
    """Processa os dados do CSV para o formato da tabela"""
    try:
        # Verificar se coluna course_id existe
        if 'course_id' not in df.columns:
            raise ValueError("Coluna 'course_id' não encontrada no CSV")
        
        # Se a coluna course_id contém formato "NÚMERO,LETRA" (ex: "1070968,U")
        if df['course_id'].dtype == 'object' and ',' in str(df['course_id'].iloc[0]):
            logging.info("🔄 Processando format: NÚMERO,LETRA")
            # Separar course_id e course_type
            df[['course_id', 'course_type']] = df['course_id'].str.split(',', expand=True)
            df['course_id'] = df['course_id'].astype(int)
        
        # Se já existem colunas separadas
        elif 'course_type' in df.columns:
            logging.info("✅ Colunas já separadas")
            df['course_id'] = df['course_id'].astype(int)
        
        else:
            raise ValueError("Formato de dados não reconhecido")
        
        # Selecionar apenas as colunas necessárias
        df_clean = df[['course_id', 'course_type']].copy()
        
        # Remover duplicatas
        df_clean = df_clean.drop_duplicates()
        
        # Remover valores nulos
        df_clean = df_clean.dropna()
        
        logging.info(f"✅ Dados processados: {len(df_clean)} registros válidos")
        
        return df_clean
        
    except Exception as e:
        logging.error(f"❌ Erro ao processar dados: {e}")
        raise


def insert_data(conn, df):
    """Insere dados na tabela cursos"""
    try:
        cursor = conn.cursor()
        
        # Query de inserção (ignora duplicatas)
        insert_query = """
            INSERT INTO cursos (course_id, course_type)
            VALUES (%s, %s)
            ON CONFLICT (course_id, course_type) DO NOTHING
        """
        
        # Preparar dados para inserção
        data = [(row['course_id'], row['course_type']) for _, row in df.iterrows()]
        
        # Executar inserção em lote
        execute_batch(cursor, insert_query, data, page_size=1000)
        
        # Commit
        conn.commit()
        
        # Verificar quantos foram inseridos
        cursor.execute("SELECT COUNT(*) FROM cursos")
        total = cursor.fetchone()[0]
        
        logging.info(f"✅ Dados inseridos com sucesso!")
        logging.info(f"📊 Total de registros na tabela: {total}")
        
        cursor.close()
        
    except Exception as e:
        conn.rollback()
        logging.error(f"❌ Erro ao inserir dados: {e}")
        raise


def verify_data(conn):
    """Verifica os dados inseridos"""
    try:
        cursor = conn.cursor()
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM cursos")
        total = cursor.fetchone()[0]
        
        # Mostrar primeiros 10 registros
        cursor.execute("""
            SELECT id, course_id, course_type, created_at 
            FROM cursos 
            ORDER BY id 
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        logging.info(f"\n📊 VERIFICAÇÃO DOS DADOS")
        logging.info(f"Total de registros: {total}")
        logging.info(f"\n🔍 Primeiros 10 registros:")
        
        for row in results:
            logging.info(f"  ID: {row[0]}, Course: {row[1]}, Type: {row[2]}, Created: {row[3]}")
        
        # Estatísticas por tipo
        cursor.execute("""
            SELECT course_type, COUNT(*) as total
            FROM cursos
            GROUP BY course_type
            ORDER BY total DESC
        """)
        
        stats = cursor.fetchall()
        
        logging.info(f"\n📈 Estatísticas por tipo:")
        for stat in stats:
            logging.info(f"  Tipo {stat[0]}: {stat[1]} cursos")
        
        cursor.close()
        
    except Exception as e:
        logging.error(f"❌ Erro ao verificar dados: {e}")
        raise


# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================

def main():
    """Função principal"""
    conn = None
    
    try:
        logging.info("🚀 Iniciando processo de carga de dados...")
        
        # 1. Ler CSV
        df = read_csv(CSV_FILE)
        
        # 2. Processar dados
        df_processed = process_data(df)
        
        # 3. Conectar ao banco
        conn = connect_db()
        
        # 4. Inserir dados
        insert_data(conn, df_processed)
        
        # 5. Verificar dados
        verify_data(conn)
        
        logging.info("🎉 Processo concluído com sucesso!")
        
    except Exception as e:
        logging.error(f"💥 Erro fatal: {e}")
        raise
        
    finally:
        if conn:
            conn.close()
            logging.info("🔌 Conexão com banco fechada")


if __name__ == "__main__":
    main()

