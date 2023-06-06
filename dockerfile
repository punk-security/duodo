FROM python:3.11-alpine as builder

RUN apk update

# Create app directory
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-alpine
RUN apk update
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir -p /app/results
WORKDIR /app

COPY . .

# Exports
ENV ADMIN_IKEY=""
ENV ADMIN_SKEY=""
ENV AUTH_IKEY=""
ENV AUTH_SKEY=""

ENTRYPOINT [ "python3", "/app/main.py" ]
