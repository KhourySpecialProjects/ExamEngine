FROM node:20-bookworm-slim

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
# Copy application code
COPY . .

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=20s --timeout=5s --start-period=60s --retries=5 \
  CMD node -e "require('http').get('http://localhost:3000', r => process.exit(r.statusCode===200?0:1)).on('error', ()=>process.exit(1))"

# Need to change to npm run build
# Run development server with Turbopack
CMD ["npm", "run", "dev"]
