FROM node:22-alpine AS build
WORKDIR /app/web-tanstack
COPY web-tanstack/package*.json ./
RUN npm ci
COPY web-tanstack/ ./
COPY web/src/ ../web/src/
RUN npm run build && npm run check
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /app/web-tanstack/.output ./.output
USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
