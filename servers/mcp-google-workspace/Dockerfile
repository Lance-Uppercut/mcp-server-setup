FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY dist/ ./dist/
COPY src/ ./src/

RUN touch .gauth.json .accounts.json || true

ENV NODE_ENV=production

CMD ["node", "dist/server.js"]
