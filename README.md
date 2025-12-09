<p align="center">
  <img src="frontend/public/github.svg" alt="Exam Engine" width="250"/>
  <p align="center" class="logo-subtitle"><em>Schedule Smarter</em></p>
</p>

An intelligent exam scheduling system that uses the DSATUR graph coloring algorithm to automatically generate conflict-free exam schedules. The system optimizes scheduling by analyzing student enrollment data, classroom capacities, and scheduling constraints to produce efficient exam timetables.

---

## Table of Contents

- [System Overview](#system-overview)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [CI/CD Workflows](#cicd-workflows)
- [Docker Compose](#docker-compose)
- [API Documentation](#api-documentation)
- [Algorithm Details](#algorithm-details)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## System Overview

**ExamEngine** is a sophisticated exam scheduling application that solves the complex problem of creating conflict-free exam timetables for educational institutions.

### Project Structure

```
ExamEngine/
├── frontend/                # Next.js React application
│   ├── src/
│   │   ├── app/            # Next.js 15 app router pages
│   │   │   ├── dashboard/  # Main upload interface
│   │   │   ├── login/      # Authentication pages
│   │   │   └── profile/    # User profile pages
│   │   ├── components/     # React components
│   │   │   ├── ui/         # Shadcn/ui components
│   │   │   ├── upload/     # CSV upload interface
│   │   │   ├── schedule/   # Schedule generation UI
│   │   │   ├── statistics/ # Statistics dashboard
│   │   │   └── visualization/ # Schedule visualization components
│   │   ├── lib/            # Utilities and stores
│   │   │   ├── api/        # API client
│   │   │   ├── store/      # Zustand state management
│   │   │   └── hooks/      # Custom React hooks
│   │   └── middleware.ts   # Next.js middleware
│   ├── e2e/                # End-to-end tests
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example        # Frontend environment template
├── backend/                # FastAPI Python server
│   ├── src/
│   │   ├── algorithms/     # DSATUR scheduling algorithms
│   │   │   ├── enhanced_dsatur_scheduler.py  # Main DSATUR implementation
│   │   │   └── original_dsatur_scheduler.py  # Legacy implementation
│   │   ├── api/           # FastAPI routes and middleware
│   │   │   ├── routes/
│   │   │   │   ├── auth.py        # Authentication endpoints
│   │   │   │   ├── datasets.py    # Dataset management
│   │   │   │   └── schedule.py    # Scheduling API endpoints
│   │   │   └── deps.py     # API dependencies
│   │   ├── core/          # Core application logic
│   │   │   ├── config.py  # Configuration management
│   │   │   ├── database.py # Database connection
│   │   │   └── exceptions.py # Custom exceptions
│   │   ├── services/      # Business logic services
│   │   │   ├── auth.py    # Authentication service
│   │   │   ├── dataset.py # Dataset service
│   │   │   └── schedule.py # Schedule service
│   │   ├── repo/          # Database repositories
│   │   └── schemas/       # Pydantic schemas
│   ├── tests/             # Unit tests
│   ├── requirements.txt   # Python dependencies
│   ├── Dockerfile
│   └── .env.example       # Backend environment template
├── .github/
│   └── workflows/         # CI/CD workflows
│       ├── unit-test.yml  # Unit test workflow
│       └── e2e.yml        # E2E test workflow
├── docker-compose.yml     # Docker Compose configuration
├── nginx.conf             # Nginx reverse proxy configuration
└── README.md              # This file
```

### Key Features
- **DSATUR Algorithm**: Implements the degree of saturation graph coloring algorithm for optimal exam scheduling
- **Conflict Detection**: Automatically identifies and resolves student enrollment conflicts
- **Room Assignment**: Intelligently assigns exams to appropriate classrooms based on capacity
- **Multiple Constraints**: Handles scheduling constraints like:
  - Maximum exams per student per day
  - Avoiding back-to-back exams for students
  - Room capacity limitations
  - Time slot availability
- **Multiple View Formats**: Generates schedules in various formats (compact, density, list views)
- **CSV Import/Export**: Easy data import and schedule export functionality

## Technology Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, Zustand, Shadcn/ui
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy, PostgreSQL
- **Database**: PostgreSQL 15
- **Algorithms**: DSATUR graph coloring, constraint satisfaction
- **Data Processing**: Pandas, NetworkX
- **Storage**: AWS S3 (for dataset files)
- **Authentication**: JWT tokens
- **Containerization**: Docker, Docker Compose
- **Reverse Proxy**: Nginx
- **Testing**: Pytest (backend), Playwright (E2E), Vitest (frontend unit)

---

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software
- **Docker** (version 20.10+) and **Docker Compose** (version 2.0+)
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Node.js** (version 18+) and **npm** (version 9+)
  - [Install Node.js](https://nodejs.org/)
- **Python** (version 3.12+) - Optional (only if running without Docker)
  - [Install Python](https://www.python.org/downloads/)
- **PostgreSQL** (version 15+) - Optional (included in Docker Compose)
  - [Install PostgreSQL](https://www.postgresql.org/download/)

### Required Accounts
- **AWS Account** with S3 bucket access (for dataset storage)
  - Access Key ID and Secret Access Key
  - S3 bucket for storing uploaded datasets

---

## Installation & Setup

### Option 1: Docker Compose (Recommended)

This is the easiest way to run the entire application stack.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shuklashreyas/ExamEngine.git
   cd ExamEngine
   ```

2. **Set up environment variables:**
   
   **Important:** Docker Compose reads environment variables from a `.env` file in the **root directory** (same location as `docker-compose.yml`), not from `backend/.env`.
   
   **Create root `.env` file:**
   ```bash
   # Create .env in the root directory (ExamEngine-5/.env)
   # Copy from backend/.env.example or create manually with:
   ```
   
   **Required variables for root `.env`:**
   ```env
   # AWS Configuration (Required for S3 file storage)
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   AWS_REGION=us-east-1
   AWS_S3_BUCKET=your-s3-bucket-name
   
   # Database Configuration
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=exam_engine_db
   
   # Backend Configuration
   SECRET_KEY=your_secret_key_here_change_in_production
   FRONTEND_URL=http://localhost:3000
   
   # Frontend Configuration
   NEXT_PUBLIC_API_URL=http://localhost:8000
   
   # Admin Configuration (Optional - for add_admin.py script)
   ADMIN_EMAIL=theadmin@northeastern.edu
   ADMIN_PASSWORD=admin
   ```
   
   **Note:** The backend application also reads from `backend/.env` for local development (without Docker), but Docker Compose uses the root `.env` file.
   
   **Frontend (optional):**
   ```bash
   cd frontend
   cp .env.example .env.local
   # Edit .env.local if you need custom API URLs
   ```

3. **Start all services:**
   
   **For Development:**
   ```bash
   docker-compose --profile dev up -d
   ```
   
   **For Production:**
   ```bash
   docker-compose --profile prod up -d
   ```
   
   This will start:
   - PostgreSQL database (port 5432) - dev only
   - Backend API (port 8000)
   - Frontend application (port 3000)
   - Nginx reverse proxy (port 80) - dev only

4. **Verify services are running:**
   ```bash
   docker-compose ps
   ```
   
   All services should show as "healthy" or "running".

5. **Create the first admin user:**
   
   After the services are running, create the initial admin account:
   ```bash
   # For development
   docker-compose exec backend-dev python script/add_admin.py
   
   # For production
   docker-compose exec backend python script/add_admin.py
   ```
   
   **Admin credentials:**
   The script reads admin credentials from environment variables. You can set them in:
   - **Root `.env` file** (recommended for Docker): `ADMIN_EMAIL` and `ADMIN_PASSWORD`
   - **`backend/.env` file** (for local development)
   - **Command line** (temporary): Use `-e` flags as shown below
   
   **Default values** (if not set in .env):
   - Email: `theadmin@northeastern.edu`
   - Password: `admin`
   
   **Custom admin credentials:**
   Option 1: Set in root `.env` file:
   ```env
   ADMIN_EMAIL=your-email@northeastern.edu
   ADMIN_PASSWORD=your-secure-password
   ```
   
   Option 2: Set via command line (temporary):
   ```bash
   docker-compose exec -e ADMIN_EMAIL=your-email@northeastern.edu -e ADMIN_PASSWORD=your-password backend-dev python script/add_admin.py
   ```

6. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Nginx (if configured): http://localhost

### Option 2: Local Development (Without Docker)

For development without Docker, you'll need to set up services manually.

**Backend Setup:**
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

**Frontend Setup:**
```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local if needed
```

**Database Setup:**
- Install and start PostgreSQL
- Create a database: `createdb exam_engine_db`
- Update `DATABASE_URL` in `backend/.env`

---

## Environment Variables

### Backend Environment Variables

**For Docker Compose:** Create a `.env` file in the **root directory** (same location as `docker-compose.yml`).

**For Local Development:** Create `backend/.env` from `backend/.env.example`.

**Required variables:**

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/exam_engine_db
# Note: For Docker, DATABASE_URL is auto-generated from POSTGRES_* variables

# AWS Configuration (Required for S3 file storage)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket-name

# Security Settings
SECRET_KEY=your_secret_key_here_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS Settings
FRONTEND_URL=http://localhost:3000

# Application Settings
DEBUG=True
ENVIRONMENT=development

# Admin Configuration (Optional - for add_admin.py script)
ADMIN_EMAIL=theadmin@northeastern.edu
ADMIN_PASSWORD=admin

# Database Connection Pool Settings (Optional)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

**Important Notes:**
- **Docker Compose** reads from the **root `.env`** file
- **Local development** (without Docker) reads from `backend/.env`
- Make sure your AWS credentials are valid and have access to the S3 bucket
- The `ADMIN_EMAIL` and `ADMIN_PASSWORD` variables are used by the `add_admin.py` script

### Frontend Environment Variables (`frontend/.env.local`)

Create `frontend/.env.local` from `frontend/.env.example`:

```bash
# API Configuration
# For client-side requests (browser)
NEXT_PUBLIC_API_URL=http://localhost:8000

# For server-side requests (Node.js)
# Only needed if running in Docker or server-side rendering
API_URL=http://backend:8000

# Environment
NODE_ENV=development
```

**Note:** Never commit `.env` or `.env.local` files to version control. They are already in `.gitignore`.

---

## Running the Application

### Development Mode

#### Using Docker Compose (Recommended)

```bash
# Start all services in development mode
docker-compose --profile dev up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

#### Without Docker

**Start PostgreSQL:**
```bash
# On macOS/Linux
sudo service postgresql start
# Or use your system's service manager
```

**Start Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Start Frontend:**
```bash
cd frontend
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Production Mode

#### Using Docker Compose

1. **Update environment variables:**
   - Set `ENVIRONMENT=production` in `backend/.env`
   - Set `DEBUG=False` in `backend/.env`
   - Update `SECRET_KEY` with a strong random key
   - Set `NODE_ENV=production` in `frontend/.env.local`

2. **Build and start:**
   ```bash
   docker-compose -f docker-compose.yml up -d --build
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

#### Without Docker

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Frontend:**
```bash
cd frontend
npm run build
npm start
```

---

## Docker Compose

The project includes a `docker-compose.yml` file that orchestrates all services:

### Services

1. **db** - PostgreSQL 15 database
   - Port: 5432
   - Healthcheck: Enabled
   - Persistent volume: `postgres_data`

2. **backend** - FastAPI application
   - Port: 8000
   - Healthcheck: Enabled
   - Environment: Loads from `backend/.env`
   - Hot reload: Enabled in development

3. **frontend** - Next.js application
   - Port: 3000
   - Healthcheck: Enabled
   - Environment: Loads from `frontend/.env.local`
   - Hot reload: Enabled in development

4. **webserver** - Nginx reverse proxy
   - Port: 80
   - Routes traffic between frontend and backend
   - Only starts when frontend and backend are healthy

### Useful Docker Commands

```bash
# Start all services (development)
docker-compose --profile dev up -d

# Start all services (production)
docker-compose --profile prod up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Restart a specific service
docker-compose restart [service_name]

# Rebuild and start
docker-compose up -d --build

# Remove all containers and volumes
docker-compose down -v

# Check service status
docker-compose ps

# Execute command in a container
docker-compose exec backend python -c "print('Hello')"
```

---

## Testing

### Backend Tests

```bash
# Run all backend tests
cd backend
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_enhanced_dsatur_algorithm.py
```

### Frontend Tests

```bash
# Run unit tests
cd frontend
npm test

# Run E2E tests with Playwright
npm run test:e2e

# Run E2E tests in UI mode
npm run test:e2e -- --ui
```

### Running Tests in Docker

```bash
# Backend tests
docker-compose exec backend pytest tests/

# Frontend tests
docker-compose exec frontend npm test
```

---

## CI/CD Workflows

The project uses GitHub Actions for continuous integration and deployment.

### Workflow Files

1. **`.github/workflows/unit-test.yml`**
   - Runs on: Push and PR to `main`/`master`
   - Tests: Backend and frontend unit tests
   - Environment: Ubuntu Latest, Node.js 20, Python 3.12
   - Steps:
     - Checkout code
     - Setup Node.js and Python
     - Install dependencies
     - Run all tests

2. **`.github/workflows/e2e.yml`**
   - Runs on: Push and PR to `main`/`master` (frontend changes only)
   - Tests: Playwright E2E tests
   - Environment: Ubuntu Latest, Node.js LTS
   - Steps:
     - Checkout code
     - Setup Node.js
     - Install dependencies
     - Install Playwright browsers
     - Run E2E tests
     - Upload test reports as artifacts

### Viewing Workflow Runs

- Navigate to the "Actions" tab in your GitHub repository
- Click on a workflow run to see detailed logs
- Download artifacts (like Playwright reports) from completed runs

### Local CI/CD Testing

You can test CI/CD workflows locally using [act](https://github.com/nektos/act):

```bash
# Install act
# On macOS: brew install act
# On Linux: See act documentation

# Run unit test workflow
act -j tests

# Run E2E test workflow
act -j e2e
```

### Using the Application

1. **Access the Dashboard**: Navigate to `http://localhost:3000/dashboard`
2. **Login/Signup**: Create an account or login with existing credentials
3. **Upload Dataset**: Upload three CSV files:
   - **Courses Data**: CRN, CourseID, num_students
   - **Enrollment Data**: Student_PIDM, CRN, Instructor Name
   - **Room Availability**: room_name, capacity
4. **Select Dataset**: Choose your uploaded dataset from the dropdown
5. **Generate Schedule**: 
   - Click "Optimize" button
   - Enter schedule name
   - Configure parameters (max exams per day, avoid back-to-back, etc.)
   - Optionally enable "Prioritize Large Classes" for size-first scheduling
   - Click "Generate Schedule"
6. **View Results**: 
   - View schedules in multiple formats (Density, Compact, List, Statistics)
   - Export schedule as CSV
   - Review conflicts and statistics

### Required Data Format

The system expects three CSV files with specific formats:

1. **Courses Data**:
   - Required columns: `CRN`, `CourseID` (or `course_ref`), `num_students`
   - Example:
     ```csv
     CRN,CourseID,num_students
     12345,CS3000,150
     12346,MATH2000,200
     ```

2. **Enrollment Data**:
   - Required columns: `Student_PIDM` (or `student_id`), `CRN`, `Instructor Name` (or `instructor_name`)
   - Example:
     ```csv
     Student_PIDM,CRN,Instructor Name
     1001,12345,Dr. Smith
     1002,12345,Dr. Smith
     ```

3. **Room Availability**:
   - Required columns: `room_name`, `capacity`
   - Example:
     ```csv
     room_name,capacity
     WVH 101,100
     WVH 102,150
     ```

---

## API Documentation

### Authentication Endpoints

- `POST /auth/signup` - Register a new user
- `POST /auth/login` - Login and get JWT token
- `POST /auth/logout` - Logout
- `GET /auth/me` - Get current user info

### Dataset Endpoints

- `POST /datasets/upload` - Upload dataset files (courses, enrollments, rooms)
- `GET /datasets` - List all datasets for current user
- `DELETE /datasets/{dataset_id}` - Delete a dataset

### Schedule Endpoints

- `POST /schedule/generate/{dataset_id}` - Generate schedule
  - Query parameters:
    - `schedule_name` (required): Name for the schedule
    - `max_per_day` (default: 3): Max exams per student per day
    - `instructor_per_day` (default: 2): Max exams per instructor per day
    - `avoid_back_to_back` (default: true): Avoid consecutive exam blocks
    - `max_days` (default: 7): Days to spread exams across
    - `prioritize_large_courses` (default: false): Schedule larger classes first

### Interactive API Documentation

When the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Algorithm Details

### DSATUR Algorithm

The system uses the **DSATUR (Degree of Saturation)** algorithm, which:

1. **Builds a conflict graph** where courses are nodes and edges represent student/instructor conflicts
2. **Colors the graph** using DSATUR strategy to assign time slots
3. **Maps colors to time slots** (days and time blocks)
4. **Assigns classrooms** based on enrollment and capacity
5. **Tracks conflicts** and reports violations

### Algorithm Variants

#### Standard DSATUR
- Default scheduling mode
- Colors courses by saturation degree
- Places courses within color groups by size (largest first)

#### Large Class Priority Mode
- Enabled via "Prioritize Large Classes" option
- Schedules larger courses (more enrolled students) first
- Helps ensure large classes get preferred time slots
- Useful for minimizing conflicts in high-enrollment courses

### Scheduling Constraints

The algorithm respects the following constraints:

- **Hard Constraints** (cannot be violated):
  - Student double-booking: Students cannot have two exams at the same time
  - Instructor double-booking: Instructors cannot teach two exams at the same time
  - Room capacity: Exam size must not exceed room capacity

- **Soft Constraints** (minimized, but may occur):
  - Student per-day limit: Maximum exams per student per day (default: 3)
  - Instructor per-day limit: Maximum exams per instructor per day (default: 2)
  - Back-to-back exams: Avoids consecutive exam blocks for students/instructors
  - Large course placement: Prefers earlier days for large courses (≥100 students)

### Time Slots

The system uses 5 time blocks per day:
- Block 0: 9:00 AM - 11:00 AM
- Block 1: 11:30 AM - 1:30 PM
- Block 2: 2:00 PM - 4:00 PM
- Block 3: 4:30 PM - 6:30 PM
- Block 4: 7:00 PM - 9:00 PM

Days are configurable (default: Monday through Sunday, 7 days total).

---

## Troubleshooting

### Common Issues

#### Port Conflicts

**Problem:** Services fail to start due to port conflicts

**Solution:**

```bash
# Check what's using the ports
# On macOS/Linux:
lsof -i :3000
lsof -i :8000
lsof -i :5432

# On Windows:
netstat -ano | findstr :3000
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# Stop conflicting services or change ports in docker-compose.yml
```

#### Database Connection Errors

**Problem:** Backend cannot connect to database

**Solution:**

```bash
# Verify PostgreSQL is running
docker-compose ps db

# Check DATABASE_URL in backend/.env
# Ensure database exists
docker-compose exec db psql -U postgres -c "\l"

# Reset database
docker-compose down -v && docker-compose up -d db
```

#### AWS S3 Access Denied

**Problem:** Dataset upload fails with AWS errors

**Solution:**

- Verify AWS credentials in root `.env` file (for Docker) or `backend/.env` (for local)
- Check S3 bucket name and region
- Ensure IAM user has S3 read/write permissions
- Verify bucket exists: `aws s3 ls s3://your-bucket-name`

#### Environment Variables Not Loading

**Problem:** Application uses wrong configuration

**Solution:**

- Verify `.env` files exist (not just `.env.example`)
- Check file names: root `.env` (for Docker), `backend/.env` (for local backend), `frontend/.env.local` (for frontend)
- Restart services: `docker-compose restart`
- Check logs: `docker-compose logs backend`

#### Frontend Cannot Connect to Backend

**Problem:** API calls fail with connection errors

**Solution:**

- Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Check backend is running: `docker-compose ps backend`
- Verify CORS settings in root `.env`: `FRONTEND_URL`
- Check browser console for CORS errors

#### Docker Build Failures

**Problem:** `docker-compose up` fails during build

**Solution:**

```bash
# Clear Docker cache
docker-compose build --no-cache

# Check Docker has enough resources (memory, disk)
# Verify Dockerfile syntax
# Check logs
docker-compose logs [service_name]
```

### Performance Tips

- Use smaller test datasets for initial testing
- Monitor memory usage with large enrollment files
- Increase Docker resources if processing large datasets
- Use database indexes for faster queries (automatically created)
- Enable connection pooling (configured in `backend/.env`)

### Debugging

#### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# Last 100 lines
docker-compose logs --tail=100 backend
```

#### Access Container Shell

```bash
# Backend
docker-compose exec backend-dev bash

# Frontend
docker-compose exec frontend-dev sh

# Database
docker-compose exec db psql -U postgres -d exam_engine_db
```

#### Check Service Health

```bash
# Service status
docker-compose ps

# Health checks
docker-compose exec backend-dev python -c "import requests; print(requests.get('http://localhost:8000/').status_code)"
docker-compose exec frontend-dev curl http://localhost:3000
```

---

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**:
   - Follow existing code style
   - Add tests for new features
   - Update documentation as needed
4. **Run tests**:
   ```bash
   # Backend tests
   cd backend && pytest tests/
   
   # Frontend tests
   cd frontend && npm test
   ```
5. **Commit your changes**:
   ```bash
   git commit -m 'feat: Add amazing feature'
   ```
6. **Push to the branch**:
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request** on GitHub

### Code Style

- **Backend**: Follow PEP 8, use type hints, run `ruff` linter
- **Frontend**: Follow ESLint rules, use TypeScript, format with Prettier
- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)

### Testing Requirements

- All new features must include tests
- Maintain or improve test coverage
- E2E tests for user-facing features

---

## Additional Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)

### Algorithm References
- [DSATUR Algorithm](https://en.wikipedia.org/wiki/DSatur)
- [Graph Coloring](https://en.wikipedia.org/wiki/Graph_coloring)
- [Constraint Satisfaction](https://en.wikipedia.org/wiki/Constraint_satisfaction_problem)

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Support

For issues, questions, or contributions:
- Open an issue on [GitHub](https://github.com/shuklashreyas/ExamEngine/issues)
- Check existing documentation and troubleshooting guide
- Review API documentation at `/docs` endpoint
