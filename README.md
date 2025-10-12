# ExamEngine

A lightweight exam creation and delivery application. This README covers project structure, a brief overview, installation steps, and how to run the project locally.

---

## Project structure
Example top-level layout (adjust if your repository differs):

```
ExamEngine/
├── frontend/                # UI app (npm-based)
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── ...
├── backend/                 # API server (optional)
│   ├── src/
│   ├── package.json|requirements.txt
│   └── ...
├── docs/                    # design docs, API specification
├── scripts/                 # utility scripts (migrations, seeders)
├── .env.example             # example environment variables
├── docker-compose.yml       # optional local orchestration
└── README.md
```

---

## Brief overview
- Frontend: single-page application delivering the exam UI and administrative interfaces (authoring, scheduling, reports).
- Backend: REST (or GraphQL) API that manages exams, questions, user sessions, grading, and persistence.
- Data store: relational or document DB depending on implementation.
- Typical flows:
    - Author creates exams and questions.
    - Students take exams through the UI.
    - Backend records answers, scores, and provides analytics.

---

## Installation (prerequisites + setup)
Prerequisites
- Node.js (recommended LTS, e.g., >= 16)
- npm or yarn
- If a backend exists: the runtime for that service (Node/Python/Go), and a database (Postgres, MySQL, MongoDB, etc.)
- Docker & docker-compose (optional, recommended for easy local dev)

Clone repository
```bash
git clone <repo-url> ExamEngine
cd ExamEngine
```

Frontend install
```bash
cd frontend
# using npm
npm install
# or using yarn
# yarn install
```

Backend install (if present)
```bash
cd ../backend
# Node backend
npm install

# OR Python backend
# python -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt
```

Environment
- Copy example env and edit:
```bash
cp .env.example .env
# then open .env and set keys (PORT, DATABASE_URL, JWT_SECRET, etc.)
```
- If using a database, create the DB and run migrations (see scripts or backend README).

Optional Docker
```bash
# run services with docker-compose (if provided)
docker-compose up --build
```

---

## How to run

Frontend (development)
```bash
cd frontend
npm run dev
# or
npm start
```
- Default dev server typically serves at http://localhost:3000 or http://localhost:5173. Check console output.

Frontend (production build)
```bash
cd frontend
npm run build
# serve the build folder with a static server, or let backend serve it
npm install -g serve
serve -s dist -l 3000
```

Backend (development)
```bash
cd backend
# Node
npm run dev         # e.g., nodemon

# Python
# export FLASK_ENV=development
# flask run
```

Run full stack locally
- Option A: start backend and frontend separately in two terminals.
- Option B: use docker-compose (if configured):
```bash
docker-compose up --build
```

Testing
```bash
# frontend tests
cd frontend
npm test

# backend tests
cd backend
npm test
```

Common troubleshooting
- Ensure correct Node version (use nvm to switch versions).
- Verify .env values (API base URL, DB credentials).
- If ports clash, update PORT environment variables.

---

If you want, I can:
- generate a more detailed example .env.example,
- expand the backend section to a specific stack (Express, Django, etc.),
- or produce a startup script (docker-compose) for local development.
