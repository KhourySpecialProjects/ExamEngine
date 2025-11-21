FROM node:20-bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY frontend/package*.json ./

# Install dependencies directly (this will create package-lock.json automatically)
RUN npm install

# Copy the rest of the frontend code
COPY frontend/ .

RUN npm run build

EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=5s --start-period=60s --retries=5 \
  CMD node -e "require('http').get('http://localhost:3000', r => process.exit(r.statusCode===200?0:1)).on('error', ()=>process.exit(1))"

# Run the production server
CMD ["npm", "run", "start"]
