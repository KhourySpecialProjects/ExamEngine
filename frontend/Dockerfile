FROM node:20-bookworm-slim

WORKDIR /app

ARG NODE_ENV
# Next.js pass environment variables at build time
ARG NEXT_PUBLIC_API_URL 
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY frontend/package*.json ./

# Install dependencies directly (this will create package-lock.json automatically)
RUN npm ci

# Copy the rest of the frontend code
COPY frontend/ .

RUN npm run build

# Set Node.js environment to production
ENV NODE_ENV=production

EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=5s --start-period=60s --retries=5 \
  CMD node -e "require('http').get('http://localhost:3000', r => process.exit(r.statusCode===200?0:1)).on('error', ()=>process.exit(1))"

# Run the production server
CMD ["npm", "run", "start"]
