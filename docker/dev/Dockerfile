FROM python:3.12

ENV PYTHON_ENV DEV

WORKDIR /workspace

COPY . .
RUN apt -y update
RUN pip install -U pip
RUN pip3 install -r requirements.txt -r test-requirements.txt
RUN pip install alembic
