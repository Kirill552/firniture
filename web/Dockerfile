FROM node:20-alpine AS builder

WORKDIR /app

# Копируем package files
COPY package*.json ./

# Устанавливаем зависимости (--legacy-peer-deps для three-dxf-loader)
RUN npm ci --legacy-peer-deps

# Копируем исходники
COPY . .

# Собираем приложение
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Production образ
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Создаём пользователя
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Копируем собранное приложение
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
