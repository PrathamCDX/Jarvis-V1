FROM python:3.14-slim

# Docker will create this folder INSIDE the container automatically
WORKDIR /app

# COPY . . means: "Take everything from my CURRENT local folder 
# and put it into the WORKDIR (/app) inside the container."
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m app && \
    mkdir -p logs/client logs/server && \
    chown -R app:app /app

COPY --chown=app:app . .

USER app
EXPOSE 8000

CMD ["python3", "server_v2.py"]