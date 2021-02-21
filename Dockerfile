FROM python:3.9-slim
LABEL org.opencontainers.image.source https://github.com/ihaveamac/discord-mod-mail
ENV MODMAIL_DATA_DIR=data
ENV IS_DOCKER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOME /home/modmail
RUN useradd -m -d $HOME -s /bin/sh -u 3913 modmail
WORKDIR $HOME
COPY ./requirements.txt .
RUN pip install --no-compile --no-cache-dir -r requirements.txt
USER modmail
COPY --chown=3913:3913 . .
ARG BRANCH="unknown"
ENV COMMIT_BRANCH=${BRANCH}
ARG COMMIT="unknown"
ENV COMMIT_SHA=${COMMIT}
CMD ["python3", "run.py"]
