FROM python:3.10-slim AS base

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1

FROM base AS python-deps

RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc libzbar0

COPY Pipfile .
COPY Pipfile.lock .
COPY pyzbar/ /pyzbar/
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libzbar0 wget
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

RUN useradd --create-home movableq
WORKDIR /home/movableq
USER movableq

COPY . .

ENTRYPOINT ["python", "server.py"]