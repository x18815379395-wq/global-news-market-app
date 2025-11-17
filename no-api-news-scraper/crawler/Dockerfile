FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install -r requirements.txt && \
    python -m playwright install --with-deps firefox
COPY . .
CMD ["python", "tools/doctor.py"]
