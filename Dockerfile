FROM python:3.12-slim-bookworm

ARG version
COPY ./dist/gitlabstudentsmonitoring-${version}-py3-none-any.whl /tmp
ENV DEBIAN_FRONTEND=noninteractive
RUN pip3 install gunicorn /tmp/gitlabstudentsmonitoring-${version}-py3-none-any.whl
VOLUME ["/data"]
ENV FLASK_APP=gsm
ENV GSM_CONFIG_FILE=/data/gsm_config.toml
ENV GSM_SQLITE_DATABASE_FILE=/data/gsm.sqlite
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-w", "4", "gsm:create_app()"]
