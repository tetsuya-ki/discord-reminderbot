FROM python:3.8-buster as builder

ARG POETRY_VERSION=1.1.13
ARG POETRY_HOME=/opt/poetry

# poetry導入
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=${POETRY_HOME} python3 - --version=${POETRY_VERSION}
ENV PATH ${PATH}:${POETRY_HOME}/bin

COPY ./ /app
WORKDIR /app

RUN poetry install

CMD ["poetry", "run", "python", "discord-reminderbot.py"] 
VOLUME [ "/app/cogs/modules/files" ]