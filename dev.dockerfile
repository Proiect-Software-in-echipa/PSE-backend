FROM python:3.11-slim-bullseye

RUN apt-get update \
    && apt-get install gcc git ssh curl unzip -y \
    && apt-get clean \
    && pip install aws-sam-cli

RUN python3 -m venv /opt/venv

COPY . .
CMD . /opt/venv/bin/activate