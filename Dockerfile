FROM python:3.11

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="/app"

RUN apt-get update
RUN apt install -y python-dev-is-python3 

WORKDIR /conf
COPY logger.conf ./

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip 
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install 'uvicorn[standard]' gunicorn

# Скопировать выполняемый код
COPY ./src/. ./

# # Перейти в рабочий директорий
# WORKDIR /app/tests
# # Скопировать выполняемый код
# COPY ./tests/ ./

WORKDIR /app

RUN dir

#CMD gunicorn main:app --timeout 86400 --workers 1 --worker-class uvicorn.workers.UvicornWorker --log-config /conf/logger.conf --bind 0.0.0.0:8001