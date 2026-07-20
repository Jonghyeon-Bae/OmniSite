# Production Dockerfile for Next.js Frontend (v1.2.0-stable)
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json /app/
RUN npm ci

COPY . /app

# Disable telemetry and build the production bundle
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Copy built assets and public folder from builder
COPY --from=builder /app/public /app/public
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/package.json /app/package.json
COPY --from=builder /app/node_modules /app/node_modules

EXPOSE 3000

CMD ["npm", "run", "start"]
