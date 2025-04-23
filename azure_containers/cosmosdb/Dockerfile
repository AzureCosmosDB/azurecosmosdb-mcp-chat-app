FROM python:3.13-slim

# Copy the application into the container.
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

# Run the application.
CMD ["/app/.venv/bin/fastapi", "run", "/app/main.py", "--port", "8000", "--host", "0.0.0.0"]