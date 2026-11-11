FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────────────
# unixodbc-dev   : pyodbc build headers
# odbc-postgresql: "PostgreSQL Unicode" / "PostgreSQL ANSI" ODBC drivers
# curl, gnupg    : needed to add the Microsoft package repo for MSSQL driver
RUN apt-get update && apt-get install -y --no-install-recommends \
        unixodbc \
        unixodbc-dev \
        odbc-postgresql \
        curl \
        gnupg2 \
        apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# ── Microsoft ODBC Driver 17 for SQL Server ───────────────────────────────────
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
        -o /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# ── MySQL ODBC driver (Community) ─────────────────────────────────────────────
# Installed via the debian package; driver name: "MySQL ODBC 8.0 Unicode Driver"
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmyodbc \
    && rm -rf /var/lib/apt/lists/* || true   # non-fatal: may not be in slim repo

# ── Python dependencies ───────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

EXPOSE 5006

# allow-websocket-origin=* lets the browser connect from any host
CMD ["panel", "serve", "app.py", \
     "--address", "0.0.0.0", \
     "--port", "5006", \
     "--allow-websocket-origin=*"]
