"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

logger = logging.getLogger(__name__)
teachers_file = Path(os.environ.get("TEACHERS_FILE", current_dir / "teachers.json"))
session_cookie_name = "teacher_session"
session_lifetime_seconds = 8 * 60 * 60
pbkdf2_iterations = 600_000
cookie_secure = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
active_sessions: dict[str, tuple[str, float]] = {}


class TeacherLogin(BaseModel):
    username: str
    password: str


def read_teacher_credentials() -> dict[str, dict[str, str]]:
    try:
        credential_data = json.loads(teachers_file.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher credentials are not configured. See src/README.md.",
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        logger.exception("Could not read teacher credentials from %s", teachers_file)
        raise HTTPException(
            status_code=503,
            detail="Teacher credentials could not be loaded.",
        ) from error

    if not isinstance(credential_data, dict) or not isinstance(
        credential_data.get("teachers"), list
    ):
        raise HTTPException(
            status_code=503,
            detail="Teacher credentials file must contain a teachers list.",
        )

    teachers: dict[str, dict[str, str]] = {}
    for teacher in credential_data["teachers"]:
        if (
            not isinstance(teacher, dict)
            or not isinstance(teacher.get("username"), str)
            or not teacher["username"].strip()
            or not isinstance(teacher.get("salt"), str)
            or not isinstance(teacher.get("password_hash"), str)
        ):
            raise HTTPException(
                status_code=503,
                detail="Teacher credentials file contains an invalid entry.",
            )

        username = teacher["username"].strip()
        try:
            salt = bytes.fromhex(teacher["salt"])
            password_hash = bytes.fromhex(teacher["password_hash"])
        except ValueError as error:
            raise HTTPException(
                status_code=503,
                detail="Teacher credentials file contains an invalid entry.",
            ) from error

        if len(salt) < 16 or len(password_hash) != hashlib.sha256().digest_size:
            raise HTTPException(
                status_code=503,
                detail="Teacher credentials file contains an invalid entry.",
            )
        if username in teachers:
            raise HTTPException(
                status_code=503,
                detail="Teacher credentials file contains duplicate usernames.",
            )

        teachers[username] = {
            "salt": teacher["salt"],
            "password_hash": teacher["password_hash"],
        }

    return teachers


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, pbkdf2_iterations
    )


def get_authenticated_teacher(request: Request) -> str | None:
    session_id = request.cookies.get(session_cookie_name)
    if not session_id:
        return None

    session = active_sessions.get(session_id)
    if session is None:
        return None

    username, expires_at = session
    if expires_at <= time.time():
        active_sessions.pop(session_id, None)
        return None

    return username


def require_teacher(request: Request) -> str:
    username = get_authenticated_teacher(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required.")
    return username


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "schedule_sort_order": 4 * 24 * 60 + 15 * 60 + 30,
        "category": "Academic",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "schedule_sort_order": 24 * 60 + 15 * 60 + 30,
        "category": "Academic",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "schedule_sort_order": 14 * 60,
        "category": "Sports",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "schedule_sort_order": 24 * 60 + 16 * 60,
        "category": "Sports",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "schedule_sort_order": 2 * 24 * 60 + 15 * 60 + 30,
        "category": "Sports",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "schedule_sort_order": 3 * 24 * 60 + 15 * 60 + 30,
        "category": "Arts",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "schedule_sort_order": 16 * 60,
        "category": "Arts",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "schedule_sort_order": 24 * 60 + 15 * 60 + 30,
        "category": "Academic",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "schedule_sort_order": 4 * 24 * 60 + 16 * 60,
        "category": "Academic",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/me")
def get_current_teacher(request: Request):
    username = get_authenticated_teacher(request)
    if username is None:
        return {"authenticated": False}
    return {"authenticated": True, "username": username}


@app.post("/auth/login")
def login_teacher(credentials: TeacherLogin, response: Response):
    teachers = read_teacher_credentials()
    teacher = teachers.get(credentials.username.strip())

    if teacher is None:
        salt = b"mergington-invalid-user-salt"
        expected_hash = bytes(hashlib.sha256().digest_size)
    else:
        salt = bytes.fromhex(teacher["salt"])
        expected_hash = bytes.fromhex(teacher["password_hash"])

    password_hash = hash_password(credentials.password, salt)
    if teacher is None or not hmac.compare_digest(password_hash, expected_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    session_id = secrets.token_urlsafe(32)
    active_sessions[session_id] = (
        credentials.username.strip(),
        time.time() + session_lifetime_seconds,
    )
    response.set_cookie(
        key=session_cookie_name,
        value=session_id,
        max_age=session_lifetime_seconds,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"authenticated": True, "username": credentials.username.strip()}


@app.post("/auth/logout")
def logout_teacher(request: Request, response: Response):
    session_id = request.cookies.get(session_cookie_name)
    if session_id:
        active_sessions.pop(session_id, None)
    response.delete_cookie(
        key=session_cookie_name,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"authenticated": False}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, request: Request):
    """Sign up a student for an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, request: Request):
    """Unregister a student from an activity"""
    require_teacher(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
