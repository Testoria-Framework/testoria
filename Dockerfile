# Testoria CLI image: docker run --rm -v "$PWD:/work" testoria run
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/opt/testoria
WORKDIR /opt/testoria
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY testoria ./testoria
RUN useradd --create-home --uid 1000 testoria
USER testoria
WORKDIR /work
EXPOSE 8080
ENTRYPOINT ["python", "-m", "testoria"]
CMD ["--help"]
