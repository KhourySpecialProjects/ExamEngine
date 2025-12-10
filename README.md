<p align="center">
  <img src="frontend/public/github.svg" alt="Exam Engine" width="250"/>
  <p align="center"><em>Schedule Smarter</em></p>
</p>

An intelligent exam scheduling system that uses the DSATUR graph coloring algorithm to automatically generate conflict-free exam schedules. Built for Northeastern University's Office of the Vice Provost to replace manual scheduling processes.

## Quick Links

| Document                                   | Description                                 |
| ------------------------------------------ | ------------------------------------------- |
| [Development Guide](./docs/DEVELOPMENT.md) | Local setup, running the app, code style    |
| [Infrastructure](./docs/INFRASTRUCTURE.md) | AWS deployment, Terraform, production setup |
| [Testing](./docs/TESTING.md)               | Running tests, CI/CD workflows              |
| [Data Guide](./docs/DATA.md)                | CSV formats, validation, database schema    |
| [Algorithm](./docs/ALGORITHM.md)           | DSATUR implementation details               |

## Overview

ExamEngine solves the complex problem of creating conflict-free exam timetables by analyzing student enrollment data, classroom capacities, and scheduling constraints.

**Key Capabilities:**

- Schedules 15,000+ students across 1,500+ course sections
- Uses 270 rooms and 25 time slots
- Generates schedules in minutes (vs. weeks manually)
- Prevents student conflicts and back-to-back exams
- Limits students to max 2 exams per day

## Tech Stack

| Layer          | Technology                                      |
| -------------- | ----------------------------------------------- |
| Frontend       | Next.js 15, TypeScript, Tailwind CSS, Shadcn/ui |
| Backend        | FastAPI, Python 3.12, SQLAlchemy                |
| Database       | PostgreSQL 15                                   |
| Infrastructure | AWS (ECS Fargate, RDS, S3, ALB), Terraform      |
| CI/CD          | GitHub Actions, Docker                          |

## Project Structure

```
ExamEngine/
├── frontend/           # Next.js React application
├── backend/            # FastAPI Python server
├── infrastructure/     # Terraform IaC
├── docs/               # Documentation
│   ├── DEVELOPMENT.md
│   ├── INFRASTRUCTURE.md
│   ├── TESTING.md
│   ├── DATA.md
│   └── ALGORITHM.md
├── docker-compose.yml
└── README.md
```

## Quick Start

```bash
# Clone and start with Docker
git clone https://github.com/example.git
cd ExamEngine
cp .env.example .env
docker-compose --profile dev up -d

# Access the application
open http://localhost:3000
```

See [Development Guide](./docs/DEVELOPMENT.md) for detailed setup instructions.

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Support

- [Open an issue](https://github.com/shuklashreyas/ExamEngine/issues)
- API docs available at `/docs` endpoint when running
