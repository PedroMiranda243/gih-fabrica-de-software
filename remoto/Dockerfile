# A borda do acesso remoto (ADR-014, RNF30, H102): a interface **empacotada**,
# servida por nginx, com o `/api` repassado à API.
#
# Quem chega de fora da máquina não recebe o servidor de desenvolvimento do Vite
# (o de `web/Dockerfile`): ele entrega o código-fonte, módulo a módulo, e não foi
# feito para sair dela. Aqui a interface é a do `vite build` — os mesmos arquivos
# que a CI confere a cada Pull Request —, comprimida e com cache.
#
# O contexto do build é `web/`, para valer o `.dockerignore` dela (o
# `node_modules` do Windows não pode entrar). O `nginx.conf` vem pelo contexto
# adicional `remoto`, como o modelo e o núcleo entram no build da API.

FROM node:22-alpine AS interface

WORKDIR /app

# Dependências primeiro, em camada própria: mudar uma tela não reinstala tudo.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Sem root: a `nginx-unprivileged` (BSD-2) roda como o usuário 101 e escuta na
# 8080. Um processo que só entrega arquivo e repassa requisição não precisa de
# mais que isso.
FROM nginxinc/nginx-unprivileged:1.30.5-alpine

COPY --from=remoto nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=interface /app/dist /usr/share/nginx/html

EXPOSE 8080
