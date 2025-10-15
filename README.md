# ExamEngine

docker-compose up -d db


An intelligent exam scheduling system that uses the DSATUR graph coloring algorithm to automatically generate conflict-free exam schedules. The system optimizes scheduling by analyzing student enrollment data, classroom capacities, and scheduling constraints to produce efficient exam timetables.

---

## Project Structure

```
ExamEngine/
├── frontend/                # Next.js React application
│   ├── src/
│   │   ├── app/            # Next.js 15 app router pages
│   │   │   ├── dashboard/  # Main upload interface
│   │   │   ├── compact/    # Compact schedule view
│   │   │   ├── density/    # Schedule density visualization
│   │   │   └── list/       # List view of schedules
│   │   ├── components/     # React components
│   │   │   ├── ui/         # Shadcn/ui components
│   │   │   ├── upload/     # CSV upload interface
│   │   │   └── visualization/ # Schedule visualization components
│   │   ├── store/          # Zustand state management
│   │   └── types/          # TypeScript type definitions
│   ├── package.json
│   └── Dockerfile
├── backend/                # FastAPI Python server
│   ├── src/
│   │   ├── algorithms/     # DSATUR scheduling algorithms
│   │   │   ├── dsatur_scheduler.py    # Core DSATUR implementation
│   │   │   └── create_schedule.py     # Schedule export utilities
│   │   ├── api/           # FastAPI routes and middleware
│   │   │   └── routes/
│   │   │       └── schedule.py       # Scheduling API endpoints
│   │   ├── config.py      # Application configuration
│   │   └── main.py        # FastAPI application entry point
│   ├── tests/             # Unit tests
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile
├── Data/                  # Sample CSV datasets
│   ├── DB_ClassCensus.csv     # Course information and enrollment counts
│   ├── DB_Enrollment.csv      # Student enrollment data
│   └── DB_Classrooms.csv      # Available classrooms and capacities
├── student_schedule_*.csv # Generated schedule outputs
└── docker-compose.yml    # Container orchestration
```

---

## System Overview

**ExamEngine** is a sophisticated exam scheduling application that solves the complex problem of creating conflict-free exam timetables for educational institutions.

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

### Technology Stack
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, Zustand
- **Backend**: FastAPI (Python), Pandas, NetworkX
- **Algorithms**: DSATUR graph coloring, constraint satisfaction
- **Data Processing**: CSV parsing and export, pandas DataFrames

### Core Algorithm
The system uses the **DSATUR (Degree of Saturation)** algorithm, which:
1. Builds a conflict graph where courses are nodes and edges represent student conflicts
2. Colors the graph to assign time slots, prioritizing highly constrained courses
3. Maps colors to actual time slots (days and time blocks)
4. Assigns appropriate classrooms based on enrollment and capacity

---

## Installation & Setup

### Prerequisites
- **Python 3.8+** (for backend)
- **Node.js 18+** (for frontend)
- **npm or yarn** (package manager)

### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install
# or
yarn install
```

### Required Data Format
The system expects three CSV files with specific formats:

1. **Class Census** (`DB_ClassCensus.csv`):
   - Required columns: `Course_Reference_Number` (CRN), `course_ref`, `Total_Enrollment`

2. **Enrollment Data** (`DB_Enrollment.csv`):
   - Required columns: `Student_PIDM` (student_id), `Course_Reference_Number` (CRN)

3. **Classrooms** (`DB_Classrooms.csv`):
   - Required columns: `Location Name` (room_name), `Capacity`

Sample datasets are provided in the `Data/` directory.

---

## How to Run

### Development Mode

**Start Backend Server:**
```bash
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at: `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

**Start Frontend Development Server:**
```bash
cd frontend
npm run dev
```
The web application will be available at: `http://localhost:3000`

### Production Build

**Frontend:**
```bash
cd frontend
npm run build
npm start
```

**Backend:**
```bash
cd backend
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Using the Application

1. **Access the Dashboard**: Navigate to `http://localhost:3000/dashboard`
2. **Upload Data**: Upload the three required CSV files:
   - Class Census (course and enrollment information)
   - Enrollment Data (student-course relationships)
   - Classrooms (available rooms and capacities)
3. **Generate Schedule**: The system will process the data and generate an optimized exam schedule
4. **Download Results**: Export the generated schedules in various formats

### API Endpoints

- `POST /schedule/generate` - Generate schedule with preview
- `POST /schedule/output` - Generate and download complete schedule files
- `GET /` - API health check

---

## Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

---

## Algorithm Details

The DSATUR algorithm implementation includes:
- **Graph Construction**: Builds conflict graphs from enrollment data
- **Constraint Handling**: Manages multiple scheduling constraints
- **Room Assignment**: Optimizes classroom utilization
- **Schedule Export**: Generates multiple output formats

### Scheduling Constraints
- Maximum 3 exams per student per day
- Avoids back-to-back exam scheduling
- Respects classroom capacity limits
- Distributes exams across available time slots

---

## Troubleshooting

### Common Issues
- **Port conflicts**: Ensure ports 3000 (frontend) and 8000 (backend) are available
- **Python environment**: Verify correct Python version and virtual environment activation
- **CSV format**: Ensure uploaded CSV files match required column names and formats
- **Memory usage**: Large datasets may require increased system memory

### Performance Tips
- Use smaller test datasets for initial testing
- Monitor memory usage with large enrollment files
- Consider chunking very large CSV files

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
