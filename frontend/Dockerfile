# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=secret,id=host_ca_bundle \
    if [ -f /run/secrets/host_ca_bundle ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/host_ca_bundle; fi; \
    npm ci

FROM node:22-alpine AS builder
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v2
ARG NEXT_PUBLIC_VID_CLIENT_KEY=local-vid-client-key
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_VID_CLIENT_KEY=$NEXT_PUBLIC_VID_CLIENT_KEY
RUN --mount=type=secret,id=host_ca_bundle \
    if [ -f /run/secrets/host_ca_bundle ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/host_ca_bundle; fi; \
    npm run build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
