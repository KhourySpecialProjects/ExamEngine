FROM node:20-bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy frontend package.json
COPY frontend/package.json ./package.json

# Install dependencies directly (this will create package-lock.json automatically)
RUN npm install

# Copy the rest of the frontend code
COPY frontend/ .

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=20s --timeout=5s --start-period=60s --retries=5 \
  CMD node -e "require('http').get('http://localhost:3000', r => process.exit(r.statusCode===200?0:1)).on('error', ()=>process.exit(1))"

# Need to change to npm run build
# Run development server with Turbopack
CMD ["npm", "run", "dev"]
