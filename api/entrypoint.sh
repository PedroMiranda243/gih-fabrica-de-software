#!/bin/sh
# Aplica as migrações antes de servir.
#
# Isso é o que faz `docker compose up` entregar um sistema pronto em vez de uma
# API apontando para um banco vazio (RNF07). O compose já espera o Postgres
# ficar saudável, então aqui o banco existe — mas pode ainda não ter esquema.
set -e

echo "Aplicando migrações..."
alembic upgrade head

echo "Subindo a API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
