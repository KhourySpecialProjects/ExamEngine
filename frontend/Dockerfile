FROM node:20-bookworm-slim

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install --no-optional --no-audit --verbose

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
