FROM python:3.12

ENV PYTHON_ENV DEV

WORKDIR /workspace

COPY . .
RUN pip install -U pip
RUN --mount=type=ssh pip3 install -r requirements.txt -r test-requirements.txt --target "/workspace"
RUN pip install alembic
