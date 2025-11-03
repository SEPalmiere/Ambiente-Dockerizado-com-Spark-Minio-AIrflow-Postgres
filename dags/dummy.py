from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime
from airflow.operators.dummy_operator import DummyOperator

dag = DAG('dummy', description = "DAG com dummy",
          schedule_interval=None,start_date=datetime(2024,8,22),
          catchup = False)

task1  = BashOperator(task_id='tsk1',bash_command="sleep 1", dag=dag)
task2  = BashOperator(task_id='tsk2',bash_command="sleep 1", dag=dag)
task3  = BashOperator(task_id='tsk3',bash_command="sleep 1", dag=dag)
dummy = DummyOperator(task_id="dummy", dag=dag)
task4  = BashOperator(task_id='tsk4',bash_command="sleep 1", dag=dag)
task5  = BashOperator(task_id='tsk5',bash_command="sleep 1", dag=dag)

[task1, task2, task3] >> dummy 
dummy >> [task4,task5]