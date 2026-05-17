FROM node:22-alpine AS deps
WORKDIR /repo
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --filter @solo/web --frozen-lockfile

FROM node:22-alpine AS builder
WORKDIR /repo
RUN corepack enable
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules
COPY . .
RUN pnpm --filter @solo/web build

FROM node:22-alpine
WORKDIR /repo
ENV NODE_ENV=production
RUN corepack enable
COPY --from=builder /repo/package.json /repo/pnpm-lock.yaml /repo/pnpm-workspace.yaml ./
COPY --from=builder /repo/apps/web ./apps/web
COPY --from=builder /repo/node_modules ./node_modules
COPY --from=builder /repo/apps/web/node_modules ./apps/web/node_modules
EXPOSE 3000
CMD ["pnpm", "--filter", "@solo/web", "exec", "next", "start", "-H", "0.0.0.0"]
