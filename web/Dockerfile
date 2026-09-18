# Interface do GIH, servida pelo servidor de desenvolvimento do Vite.
#
# É ambiente de desenvolvimento, como o da API: o objetivo é `docker compose up`
# subir tudo a partir de um clone limpo (H09), não publicar em produção.
FROM node:22-alpine

WORKDIR /app

# Dependências primeiro, em camada própria: mudar uma tela não reinstala tudo.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# O proxy de `/api` aponta para o serviço `api` pela rede do compose — ver
# `vite.config.js` para o porquê de a interface e a API dividirem a origem.
ENV GIH_API_URL=http://api:8000

CMD ["npm", "run", "dev"]
