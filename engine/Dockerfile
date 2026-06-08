FROM python:3.11-alpine

RUN addgroup -S cherenkov && adduser -S cherenkov -G cherenkov

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py spec_loader.py validator.py ./

RUN chown -R cherenkov:cherenkov /app

USER cherenkov

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
