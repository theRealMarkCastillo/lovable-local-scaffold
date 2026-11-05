FROM node:22-alpine AS build
WORKDIR /app
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
FROM nginx:1.28-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY web/default.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=755 web/15-config.envsh /docker-entrypoint.d/15-config.envsh
ENV PORT=8080 API_UPSTREAM=api-gw:8000
EXPOSE 8080
