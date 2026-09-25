FROM python:3.11-slim

WORKDIR /app

# Dependências primeiro: cada camada só é reconstruída quando o requirements
# dela muda. As do modelo vêm antes das da API porque o PyTorch é a maior de
# todas e a que menos muda.
#
# O modelo preditivo chega como **contexto adicional** de build (`modelo`, no
# docker-compose.yml — ADR-010). Construir a partir da raiz do repositório
# resolveria o mesmo problema e levaria web/node_modules e docs/ para dentro
# do build.
COPY --from=modelo requirements.txt /modelo/requirements.txt
RUN pip install --no-cache-dir -r /modelo/requirements.txt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# `--no-deps`: as dependências do pacote já estão acima, com a versão fixa e a
# roda CPU. Deixar o pip resolvê-las pelo pyproject traria o PyTorch do PyPI.
COPY --from=modelo pyproject.toml /modelo/pyproject.toml
COPY --from=modelo gih_modelo /modelo/gih_modelo
RUN pip install --no-cache-dir --no-deps /modelo

COPY alembic.ini .
COPY app ./app
COPY migrations ./migrations
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
