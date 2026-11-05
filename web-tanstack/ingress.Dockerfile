FROM nginx:1.28-alpine
COPY web-tanstack/ingress.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=755 web-tanstack/15-resolver.envsh /docker-entrypoint.d/15-resolver.envsh
ENV PORT=8080 API_UPSTREAM=api-gw:8000
EXPOSE 8080
