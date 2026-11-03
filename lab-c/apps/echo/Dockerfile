FROM python:3.12-slim
WORKDIR /app
COPY app.py .
RUN useradd --uid 10001 --no-create-home echo
USER echo
EXPOSE 5007
CMD ["python", "app.py"]
