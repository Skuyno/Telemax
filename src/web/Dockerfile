FROM node:22-alpine AS builder

WORKDIR /code

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN npm run build

FROM node:22-alpine

WORKDIR /code

ENV NODE_ENV=production
ENV NUXT_HOST=0.0.0.0
ENV NUXT_PORT=3000

COPY --from=builder /code/.output ./.output

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
