from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.email_operator import EmailOperator
from datetime import datetime, timedelta

default_args = {
    'depends_on_past': False,
    'start_date': datetime(2025,8,8),
    'email': ['sergio.palmiere@sc.senai.br'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(seconds=10)
}

dag = DAG('sendemail', description = "DAG para enviar email",
          default_args = default_args,
          schedule_interval=None,
          catchup = False, default_view='graph', tags=['processo', 'tag', 'pipeline'])

task1  = BashOperator(task_id='tsk1',bash_command="sleep 1", dag=dag)
task2  = BashOperator(task_id='tsk2',bash_command="sleep 1", dag=dag)
task3  = BashOperator(task_id='tsk3',bash_command="sleep 1", dag=dag)
task4  = BashOperator(task_id='tsk4',bash_command="exit 1", dag=dag)
task6  = BashOperator(task_id='tsk6',bash_command="sleep 1", dag=dag, trigger_rule='none_failed')
task7  = BashOperator(task_id='tsk7',bash_command="sleep 1", dag=dag, trigger_rule='none_failed')

send_email = EmailOperator(task_id="send_email",
                           to="sergio.palmiere@sc.senai.br",
                           subject="Erro no processamento do Airflow",
                           html_content="""<h3> Ocorreu um erro no processamento da Dag. </h3>
                                            <p>Dag: send_email </p>
                                            """,
                           dag=dag, trigger_rule="one_failed")

[task1,task2] >> task3 >> task4
task4 >> [send_email, task6, task7]