# =============================================================================
# Frontend image: SvelteKit built with adapter-node, served by Node.
# =============================================================================

FROM node:20-bookworm-slim AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build


FROM node:20-bookworm-slim AS runtime

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0 \
    LANG=C.UTF-8

WORKDIR /app

# Only production dependencies and the compiled server are shipped.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=builder /app/build ./build

USER node
EXPOSE 3000
CMD ["node", "build/index.js"]
