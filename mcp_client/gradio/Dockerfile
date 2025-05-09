FROM python:3.13-slim

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD [ "python", "app.py" ]