# Development Guide

Local development setup and workflows for ExamEngine.

## Prerequisites

- **Node.js 20+** and npm
- **Python 3.12+**
- **Docker & Docker Compose**
- **Git**

## Installation

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/shuklashreyas/ExamEngine.git
cd ExamEngine

# Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Start all services (dev profile)
docker-compose --profile dev up -d

# View logs
docker-compose --profile dev logs -f
```

Services will be available at:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- API Docs: <http://localhost:8000/docs>

### Option 2: Local Development

```bash
# Install all dependencies
npm run install:all

# Start both frontend and backend with hot reload
npm run dev
```

Or run services separately:

```bash
# Terminal 1: Backend
cd backend && uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

## Environment Variables

### Backend (`backend/.env`)

```env
DATABASE_URL=postgresql://user:password@localhost:5432/examengine
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=examengine-datasets
JWT_SECRET_KEY=your_secret_key
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Available Scripts

From the root directory:

| Command                | Description                     |
| ---------------------- | ------------------------------- |
| `npm run dev`          | Start both frontend and backend |
| `npm run dev:backend`  | Start backend only              |
| `npm run dev:frontend` | Start frontend only             |
| `npm run format`       | Format all code                 |
| `npm run lint`         | Lint all code                   |
| `npm run test`         | Run all tests                   |
| `npm run build`        | Build frontend for production   |

## Docker Commands

The project uses Docker Compose profiles to separate dev and prod environments.

```bash
# Development (--profile dev)
docker-compose --profile dev up -d              # Start all dev services
docker-compose --profile dev down               # Stop dev services
docker-compose --profile dev logs -f            # View all logs
docker-compose --profile dev logs -f backend-dev # View backend logs
docker-compose --profile dev restart backend-dev # Restart backend
docker-compose --profile dev up -d --build      # Rebuild and start
docker-compose --profile dev down -v            # Remove containers and volumes

# Production (--profile prod)
docker-compose --profile prod up -d             # Start prod services
docker-compose --profile prod down              # Stop prod services
```

## Code Style

### Backend (Python)

- Follow PEP 8
- Use type hints everywhere
- Run `ruff` for linting and formatting

```bash
cd backend
ruff format .
ruff check --fix .
```

### Frontend (TypeScript)

- Follow ESLint rules
- Use TypeScript strictly
- Format with Biome

```bash
cd frontend
npm run format
npm run lint
```

### Commit Messages

Use conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

## Project Architecture

### Backend Structure

```
backend/src/
├── domain/         # Domain models and logic (algorithms)
├── api/
│   ├── routes/     # FastAPI route handlers
│   └── deps.py     # Dependency injection
├── core/           # Config, database, exceptions
├── services/       # Business logic
├── repo/           # Database repositories
└── schemas/        # Pydantic models
```

### Frontend Structure

```
frontend/src/
├── app/            # Next.js app router pages
├── components/     # React components
│   ├── ui/         # Shadcn/ui components
│   └── ...         # Feature components
└── lib/
    ├── api/        # API client
    ├── store/      # Zustand state
    └── hooks/      # Custom hooks
```

## Troubleshooting

### Port Conflicts

```bash
# Check what's using a port
lsof -i :3000
lsof -i :8000

# Kill process on port
kill -9 $(lsof -t -i:3000)
```

### Database Issues

```bash
# Reset database
docker-compose --profile dev down -v
docker-compose --profile dev up -d db

# If db fails to reset, run this (Optional)
python backend/src/schema/reset_database.py

# Wait for db to be healthy, then start other services
docker-compose --profile dev up -d
```

### Python Import Errors

```bash
# Ensure you're in the correct directory
cd backend
pip install -e ".[dev]"
```
