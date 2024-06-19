FROM python:3.7-bullseye

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir --progress-bar=off -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]