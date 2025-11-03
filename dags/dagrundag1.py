from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime
from airflow.operators.dagrun_operator import TriggerDagRunOperator

dag = DAG('dagrundag1', description = "Dag run Dags",
          schedule_interval=None,start_date=datetime(2024,8,22),
          catchup = False)

task1  = BashOperator(task_id='tsk1',bash_command="sleep 5", dag=dag)
task2  = TriggerDagRunOperator(task_id='tsk2', trigger_dag_id="dagrundag2", dag=dag)

task1 >> task2