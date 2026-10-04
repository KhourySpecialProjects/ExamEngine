<p align="center">
  <img src="frontend/public/github.svg" alt="Exam Engine" width="250"/>
  <p align="center"><em>Schedule Smarter</em></p>
</p>

An intelligent exam scheduling system that models final-exam scheduling as graph coloring and generates exam schedules with one of two engines: **Classic** (DSATUR greedy) or **Optimized** (saturation construction + simulated annealing). Built for Northeastern University's Office of the Vice Provost and Office of the University Registrar to assist final exam scheduling processes.

## Quick Links

| Document                                   | Description                                 |
| ------------------------------------------ | ------------------------------------------- |
| [Development Guide](./docs/DEVELOPMENT.md) | Local setup, running the app, code style    |
| [Infrastructure](./docs/INFRASTRUCTURE.md) | AWS/Terraform setup (not in use, likely out of date) |
| [Testing](./docs/TESTING.md)               | Running tests, CI/CD workflows              |
| [Data Guide](./docs/DATA.md)                | CSV formats, validation, database schema    |
| [Algorithm](./docs/ALGORITHM.md)           | Scheduling engines and constraints          |

## Overview

ExamEngine solves the complex problem of creating conflict-free exam timetables by analyzing student enrollment data, classroom capacities, and scheduling constraints.

**Key Capabilities:**

- Tested with schedules of more than 15,000 students and 1,500 exams
- Exam days (up to 7) and exam blocks per day (4 or 5) are set per run
- Generates schedules in minutes (vs. weeks manually)
- Minimizes student conflicts and back-to-back exams, and never seats more students in a room than it holds
- Configurable per-day exam limits for students and instructors
- Supports combined exams (same block and room), common exams (same block), and room blockouts
- Validates any saved schedule independently against its uploaded data

## Tech Stack

| Layer          | Technology                                                                 |
| -------------- | -------------------------------------------------------------------------- |
| Frontend       | Next.js 15, React 19, TypeScript, Tailwind CSS, Shadcn/ui                  |
| Backend        | FastAPI, Python 3.12, SQLAlchemy                                           |
| Database       | PostgreSQL (15 locally, 16 on Coolify)                                     |
| File storage   | S3-compatible: LocalStack (local), MinIO (Coolify), S3 (AWS)               |
| Deployment     | Docker Compose on Coolify (`develop` → dev, `staging` → staging). The AWS Terraform config (ECS Fargate, RDS, S3, ALB) is not in use and likely out of date |
| CI             | GitHub Actions (runs on `main`/`master` only)                              |

## Project Structure

```
ExamEngine/
├── frontend/                          # Next.js React application
├── backend/                           # FastAPI Python server and scheduling engines
├── infrastructure/                    # Terraform IaC (AWS): not in use, kept for reference
├── docs/                              # Documentation
│   ├── DEVELOPMENT.md
│   ├── INFRASTRUCTURE.md
│   ├── TESTING.md
│   ├── DATA.md
│   └── ALGORITHM.md
├── docker-compose.yml                 # Local dev (--profile dev) and prod profiles
├── docker-compose.override.yml        # Local host-port remapping
├── docker-compose.coolify-dev.yml     # Coolify dev deployment
├── docker-compose.coolify-staging.yml # Coolify staging deployment
├── AGENTS.md                          # Contributor/agent guide and development workflow
└── README.md
```

## Quick Start

```bash
# Clone and start with Docker
git clone https://github.com/KhourySpecialProjects/ExamEngine.git
cd ExamEngine
cp .env.example .env
cp backend/.env.example backend/.env
docker-compose --profile dev up -d

# Access the application (host port set in docker-compose.override.yml)
open http://localhost:3100
```

See [Development Guide](./docs/DEVELOPMENT.md) for detailed setup instructions and
[AGENTS.md](./AGENTS.md) for the development workflow.

## Support

- API docs available at `/docs` endpoint when running
