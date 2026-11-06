# Build from the repository root so the pnpm workspace is in the context:
#   docker buildx build --platform linux/arm64 -f apps/web/Dockerfile .
#
# Staging runs on ARM64 Fargate, so the published image must be linux/arm64.

ARG NODE_VERSION=24.20.0
ARG PNPM_VERSION=10.11.0

FROM node:${NODE_VERSION}-bookworm-slim AS base
ARG PNPM_VERSION
ENV PNPM_HOME=/pnpm
ENV PATH=${PNPM_HOME}:${PATH}
RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate
WORKDIR /workspace

# Install dependencies first so source edits do not invalidate this layer.
FROM base AS dependencies
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/studio/package.json packages/studio/package.json
COPY packages/email/package.json packages/email/package.json
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --ignore-scripts --filter web...

FROM dependencies AS build
# VITE_ variables are read at build time and baked into the browser bundle, so the
# image is tied to the server URL that the browser will call. There is no safe
# default: an empty value breaks the app and a localhost value hides a mistake.
ARG VITE_SHIFU_SERVER_URL
RUN test -n "${VITE_SHIFU_SERVER_URL}" \
    || (echo "Set --build-arg VITE_SHIFU_SERVER_URL to the public server URL." >&2; exit 1)
ENV VITE_SHIFU_SERVER_URL=${VITE_SHIFU_SERVER_URL}
COPY apps/web apps/web
COPY packages/studio/public/projects packages/studio/public/projects
RUN pnpm --filter web build \
    && pnpm --filter web deploy --prod --legacy --ignore-scripts /deploy

FROM node:${NODE_VERSION}-bookworm-slim AS runtime
ENV NODE_ENV=production
ENV SHIFU_WEB_APP_PORT=7000
WORKDIR /app

COPY --from=build --chown=node:node /deploy/node_modules ./node_modules
COPY --from=build --chown=node:node /workspace/apps/web/package.json ./package.json
COPY --from=build --chown=node:node /workspace/apps/web/server.production.mjs ./server.production.mjs
COPY --from=build --chown=node:node /workspace/apps/web/dist ./dist

USER node
EXPOSE 7000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:' + (process.env.SHIFU_WEB_APP_PORT || 7000) + '/api/health').then((r) => process.exit(r.ok ? 0 : 1), () => process.exit(1))"

CMD ["node", "server.production.mjs"]
