# =============================================================================
# CUSTOM AIRFLOW IMAGE WITH SPARK INTEGRATION
# =============================================================================
# Base Image: Apache Airflow 2.8.1 with Python 3.11
# Additional: Spark 3.5.0, Java 11, Data Engineering Libraries
# =============================================================================

FROM apache/airflow:2.8.1-python3.11

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================
ENV SPARK_VERSION=3.5.0
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/usr/local/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# =============================================================================
# SWITCH TO ROOT USER FOR SYSTEM INSTALLATIONS
# =============================================================================
USER root

# =============================================================================
# INSTALL SYSTEM DEPENDENCIES
# =============================================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-17-jdk \
    procps \
    curl \
    wget \
    vim \
    git \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# INSTALL APACHE SPARK
# =============================================================================
RUN cd /tmp && \
    wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    rm -rf ${SPARK_HOME} && \
    mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_HOME} && \
    rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    chown -R airflow:root ${SPARK_HOME}

# =============================================================================
# INSTALL AWS SDK FOR MINIO/S3 INTEGRATION
# =============================================================================
RUN cd ${SPARK_HOME}/jars && \
    wget -q https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    wget -q https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar

# =============================================================================
# CREATE NECESSARY DIRECTORIES
# =============================================================================
RUN mkdir -p /opt/airflow/spark-apps \
    /opt/airflow/notebooks \
    /opt/airflow/data && \
    chown -R airflow:root /opt/airflow/spark-apps \
    /opt/airflow/notebooks \
    /opt/airflow/data

# =============================================================================
# SWITCH BACK TO AIRFLOW USER
# =============================================================================
USER airflow

# Set PYTHONPATH for PySpark
ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

# =============================================================================
# INSTALL PYTHON DEPENDENCIES
# =============================================================================
COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

# =============================================================================
# VERIFY INSTALLATIONS
# =============================================================================
RUN java -version && \
    python --version && \
    pip list | grep -E "pyspark|boto3|pandas"

# =============================================================================
# HEALTHCHECK
# =============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import airflow; import pyspark; print('OK')" || exit 1

# =============================================================================
# EXPOSE PORTS (Documentation only)
# =============================================================================
# 8080: Airflow Webserver
# 8793: Airflow Worker Log Server

WORKDIR /opt/airflow