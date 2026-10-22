# =============================================================================
# Frontend image: SvelteKit built with adapter-node, served by Node.
#
# Build context is the REPO ROOT (see docker-compose.yml): the editor preview
# compiles the renderer's Remotion composition ($renderer -> ../renderer/src)
# and serves its music and sound effects (static/studio -> renderer/public).
# The layout below keeps those relative paths valid inside the image.
# =============================================================================

FROM node:20-bookworm-slim AS builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY renderer/src /app/renderer/src
COPY renderer/public/studio /app/renderer/public/studio
COPY frontend/ ./
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
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=builder /app/frontend/build ./build

USER node
EXPOSE 3000
CMD ["node", "build/index.js"]
