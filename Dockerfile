FROM python:3.10-slim


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY . .

VOLUME ["/repo", "/output"]


WORKDIR /output


ENTRYPOINT ["/app/boomer.py"]


CMD ["version"]