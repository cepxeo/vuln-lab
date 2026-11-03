FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends imagemagick \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV SHOP_DB=/data/shop.db PORT=5001
RUN mkdir -p /data /tmp/shop-exports

EXPOSE 5001
CMD ["sh", "-c", "python seed.py && gunicorn -b 0.0.0.0:5001 -w 2 app:app || python app.py"]
