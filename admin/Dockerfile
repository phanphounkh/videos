# =============================================================================
# Admin panel image: SvelteKit built with adapter-node. It talks only to the
# backend (BACKEND_URL) and the telemetry service (TELEMETRY_URL), through its own
# server-side proxy, so neither address reaches the browser.
# =============================================================================

FROM node:20-bookworm-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-bookworm-slim AS runtime
ENV NODE_ENV=production PORT=3000 HOST=0.0.0.0 LANG=C.UTF-8
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=builder /app/build ./build
USER node
EXPOSE 3000
CMD ["node", "build/index.js"]
