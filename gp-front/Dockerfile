# 构建上下文应为 acid 仓库根目录：docker build -f gp-front/Dockerfile .
FROM node:22-alpine AS build
WORKDIR /web

COPY gp-front/package.json gp-front/package-lock.json* ./
RUN npm ci

COPY gp-front/ ./
ARG VITE_API_BASE_URL=/api
ARG VITE_FLDCF_BASE_URL=/fldcf-api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_FLDCF_BASE_URL=$VITE_FLDCF_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /web/dist /usr/share/nginx/html
COPY gp-front/nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
