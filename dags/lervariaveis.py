from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
from airflow.models import Variable

dag = DAG('lervaiaveis', description = "DAG com leitura de variavel",
          schedule_interval=None,start_date=datetime(2024,8,22),
          catchup = False)

def print_variable(**context):
    minha_var = Variable.get('pi')
    print(f"O Valor da variável é: {minha_var}")

task1  = PythonOperator(task_id='tsk1',python_callable=print_variable, dag=dag)



task1