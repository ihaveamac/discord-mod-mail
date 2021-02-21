FROM python:3.9-slim
LABEL org.opencontainers.image.source https://github.com/ihaveamac/discord-mod-mail

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV IS_DOCKER=1
ENV MODMAIL_DATA_DIR=data

ENV HOME /home/modmail
RUN useradd -m -d $HOME -s /bin/sh -u 3913 modmail
WORKDIR $HOME

COPY ./requirements.txt .
RUN pip install --no-compile --no-cache-dir -r requirements.txt

USER modmail

COPY LICENSE.md LICENSE.md
COPY README.md README.md
COPY schema.sql schema.sql
COPY run.py run.py

ARG BRANCH="unknown"
ENV COMMIT_BRANCH=${BRANCH}
ARG COMMIT="unknown"
ENV COMMIT_SHA=${COMMIT}

CMD ["python3", "run.py"]
