from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.database import get_db
from src.repo.conflict_analyses import ConflictAnalysesRepo
from src.repo.course import CourseRepo
from src.repo.dataset import DatasetRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.room import RoomRepo
from src.repo.run import RunRepo
from src.repo.schedule import ScheduleRepo
from src.repo.time_slot import TimeSlotRepo
from src.repo.user import UserRepo
from src.schemas.db import Users
from src.services.auth import AuthService
from src.services.dataset import DatasetService
from src.services.schedule import ScheduleService


settings = get_settings()


def get_token_from_cookie(request: Request) -> str:
    """Extract JWT token from HTTP-only cookie."""
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Users:
    """
    Get current authenticated user from JWT cookie.

    This is a FastAPI dependency that validates the JWT token
    and returns the authenticated user object.

    Usage:
        @router.get("/profile")
        def get_profile(user: Users = Depends(get_current_user)):
            return {"email": user.email}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = get_token_from_cookie(request)

        user_repo = UserRepo(db)
        auth_service = AuthService(user_repo)

        user = auth_service.get_user_from_token(token)

        if user is None:
            raise credentials_exception

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise credentials_exception from e


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency injection for AuthService."""
    user_repo = UserRepo(db)
    return AuthService(user_repo)


def get_admin_user(current_user: Users = Depends(get_current_user)) -> Users:
    """
    Dependency to ensure current user is an admin.

    Args:
        current_user: Current authenticated user

    Returns:
        Admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_dataset_service(db: Session = Depends(get_db)) -> DatasetService:
    """Dependency injection for DatasetService."""
    dataset_repo = DatasetRepo(db)
    return DatasetService(dataset_repo)


def get_schedule_service(db: Session = Depends(get_db)) -> ScheduleService:
    """Dependency injection for ScheduleService."""
    schedule_repo = ScheduleRepo(db)
    run_repo = RunRepo(db)
    exam_assignment_repo = ExamAssignmentRepo(db)
    conflict_analyses_repo = ConflictAnalysesRepo(db)
    course_repo = CourseRepo(db)
    time_slot_repo = TimeSlotRepo(db)
    room_repo = RoomRepo(db)

    dataset_repo = DatasetRepo(db)
    dataset_service = DatasetService(dataset_repo)

    return ScheduleService(
        schedule_repo,
        run_repo,
        exam_assignment_repo,
        conflict_analyses_repo,
        course_repo,
        time_slot_repo,
        room_repo,
        dataset_service,
    )


def get_user_repo(db: Session = Depends(get_db)) -> UserRepo:
    """Dependency injection for UserRepo."""
    return UserRepo(db)


def get_dataset_repo(db: Session = Depends(get_db)) -> DatasetRepo:
    """Dependency injection for DatasetRepository."""
    return DatasetRepo(db)


def get_schedule_repo(db: Session = Depends(get_db)):
    """Dependency injection for ScheduleRepository."""
    return ScheduleRepo(db)


def get_conflict_analyses_repo(db: Session = Depends(get_db)) -> ConflictAnalysesRepo:
    """Dependency injection for ConflictAnalysesRepo."""
    return ConflictAnalysesRepo(db)
