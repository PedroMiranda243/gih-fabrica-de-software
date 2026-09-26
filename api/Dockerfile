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

# O otimizador serial (ADR-011) chega do mesmo jeito, como contexto `nucleo`.
# Só o pacote Python: `spike/` e o `requirements.txt` da pasta são do spike de
# GPU, e trariam o CuPy para uma imagem que não o usa.
COPY --from=nucleo pyproject.toml /nucleo/pyproject.toml
COPY --from=nucleo gih_nucleo /nucleo/gih_nucleo
RUN pip install --no-cache-dir --no-deps /nucleo

COPY alembic.ini .
COPY app ./app
COPY migrations ./migrations
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
