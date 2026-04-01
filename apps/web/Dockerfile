FROM node:22-alpine

WORKDIR /app

RUN corepack enable
RUN pnpm config set registry https://registry.npmmirror.com

COPY . .

RUN pnpm install --frozen-lockfile

RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]
