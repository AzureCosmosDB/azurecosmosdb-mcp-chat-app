FROM python:3.13-slim

COPY . app

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD [ "python", "app/chat_app.py" ]