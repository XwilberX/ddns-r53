FROM python:3.11.8-alpine3.19 as base

# Build-time metadata as defined at https://github.com/opencontainers/image-spec/blob/master/annotations.md
ARG BUILD_DATE
ARG DOCKER_TAG
ARG GIT_SHA

RUN apk update && apk add --no-cache tzdata

LABEL org.opencontainers.image.created=$BUILD_DATE \
  org.opencontainers.image.authors="Wilber Alegria" \
  org.opencontainers.image.url="https://github.com/XwilberX/ddns-r53" \
  org.opencontainers.image.documentation="https://github.com/XwilberX/ddns-r53" \
  org.opencontainers.image.source="https://github.com/XwilberX/ddns-r53" \
  org.opencontainers.image.version=$DOCKER_TAG \
  org.opencontainers.image.revision=$GIT_SHA \
  org.opencontainers.image.vendor="walegria99" \
  org.opencontainers.image.licenses="MIT" \
  org.opencontainers.image.ref.name="" \
  org.opencontainers.image.title="ddns-r53" \
  org.opencontainers.image.description="Update AWS Route 53 with your current public ip at a specified time interval."

ENV PYTHONFAULTHANDLER=1 \
  PYTHONHASHSEED=random \
  PYTHONUNBUFFERED=1

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# update pip
RUN pip install --upgrade pip

# install poetry
RUN pip install "poetry==1.7.1"

# copy only the dependencies definition
COPY pyproject.toml poetry.lock ./

# export the poetry environment to requirements.txt
RUN poetry self add poetry-plugin-export
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM base as builder

# copy the dependencies file
COPY --from=base /app/requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# copy main.py and .env
COPY main.py .
COPY .env .

# Run the application with cron
RUN echo "${CRON_SCHEDULE} /usr/local/bin/python /app/main.py >> /var/log/cron.log 2>&1" > /etc/crontabs/root

# Run the cron
CMD ["crond", "-f", "-d", "8"]