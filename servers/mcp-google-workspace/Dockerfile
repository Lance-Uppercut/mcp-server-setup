FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY dist/ ./dist/
COPY src/ ./src/
COPY .gauth.json ./
COPY .accounts.json ./
COPY .oauth2.*.json ./

ENV NODE_ENV=production

CMD ["node", "dist/server.js"]
