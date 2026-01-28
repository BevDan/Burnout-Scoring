from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from passlib.hash import bcrypt
import jwt
import csv
import io
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import email.charset
from fastapi.responses import StreamingResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

JWT_SECRET = os.environ.get('JWT_SECRET', 'burnout-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    name: str
    role: str  # admin or judge
    is_active: bool = True  # For judges - whether they're active for current event
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    role: str = "judge"

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: User

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None

class CompetitionClass(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CompetitionClassCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class Competitor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    car_number: str
    vehicle_info: str
    plate: str
    class_id: str
    email: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CompetitorCreate(BaseModel):
    name: str
    car_number: str
    vehicle_info: str
    plate: str
    class_id: str
    email: Optional[str] = ""

class CompetitorWithClass(BaseModel):
    id: str
    name: str
    car_number: str
    vehicle_info: Optional[str] = ""
    plate: Optional[str] = ""
    class_id: str
    class_name: str
    email: Optional[str] = ""  # Competitor's email for score reports
    created_at: datetime

class Event(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    date: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EventCreate(BaseModel):
    name: str
    date: str
    is_active: bool = True

class Round(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    is_minor: bool = False  # Minor rounds are used for cumulative scoring before finals
    round_status: str = "active"  # active or completed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RoundCreate(BaseModel):
    name: str
    is_minor: bool = False
    round_status: str = "active"

class Score(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    judge_id: str
    judge_name: str
    competitor_id: str
    round_id: str
    tip_in: float = 0  # 0-10 (0.5 increments) - NEW
    instant_smoke: float = 0  # 0-10 (0.5 increments)
    constant_smoke: float = 0  # 0-20 (0.5 increments)
    volume_of_smoke: float = 0  # 0-20 (0.5 increments)
    driving_skill: float = 0  # 0-40 (0.5 increments)
    tyres_popped: int = 0  # count (max 2)
    penalty_reversing: int = 0  # count
    penalty_stopping: int = 0  # count
    penalty_contact_barrier: int = 0  # count
    penalty_small_fire: int = 0  # count
    penalty_failed_drive_off: int = 0  # count
    penalty_large_fire: int = 0  # count
    penalty_disqualified: bool = False  # If true, final score is 0
    score_subtotal: float = 0
    penalty_total: int = 0
    final_score: float = 0
    email_sent: bool = False  # Track if score report was emailed
    deviation_acknowledged: bool = False  # Mark as reviewed if score deviates from average
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    edited_at: Optional[datetime] = None

class ScoreCreate(BaseModel):
    competitor_id: str
    round_id: str
    tip_in: float = 0
    instant_smoke: float = 0
    constant_smoke: float = 0
    volume_of_smoke: float = 0
    driving_skill: float = 0
    tyres_popped: int = 0
    penalty_reversing: int = 0
    penalty_stopping: int = 0
    penalty_contact_barrier: int = 0
    penalty_small_fire: int = 0
    penalty_failed_drive_off: int = 0
    penalty_large_fire: int = 0
    penalty_disqualified: bool = False

class ScoreUpdate(BaseModel):
    tip_in: Optional[float] = None
    instant_smoke: Optional[float] = None
    constant_smoke: Optional[float] = None
    volume_of_smoke: Optional[float] = None
    driving_skill: Optional[float] = None
    tyres_popped: Optional[int] = None
    penalty_reversing: Optional[int] = None
    penalty_stopping: Optional[int] = None
    penalty_contact_barrier: Optional[int] = None
    penalty_small_fire: Optional[int] = None
    penalty_failed_drive_off: Optional[int] = None
    penalty_large_fire: Optional[int] = None
    penalty_disqualified: Optional[bool] = None

class ScoreWithDetails(BaseModel):
    id: str
    judge_id: str
    judge_name: str
    competitor_id: str
    competitor_name: str
    car_number: str
    round_id: str
    round_name: str
    tip_in: float = 0
    instant_smoke: float = 0
    constant_smoke: float = 0
    volume_of_smoke: float = 0
    driving_skill: float = 0
    tyres_popped: int = 0
    penalty_reversing: int = 0
    penalty_stopping: int = 0
    penalty_contact_barrier: int = 0
    penalty_small_fire: int = 0
    penalty_failed_drive_off: int = 0
    penalty_large_fire: int = 0
    penalty_disqualified: bool = False
    score_subtotal: float = 0
    penalty_total: int = 0
    final_score: float = 0
    email_sent: bool = False
    deviation_acknowledged: bool = False
    submitted_at: datetime
    edited_at: Optional[datetime] = None

class LeaderboardEntry(BaseModel):
    competitor_id: str
    competitor_name: str
    car_number: str
    vehicle_info: str
    class_name: str
    total_score: float
    average_score: float
    score_count: int

class MinorRoundsLeaderboardEntry(BaseModel):
    competitor_id: str
    competitor_name: str
    car_number: str
    vehicle_info: str
    class_name: str
    total_score: float
    average_score: float
    rounds_competed: int
    score_count: int

# Helper functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_data = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user_data:
            raise HTTPException(status_code=401, detail="User not found")
        if isinstance(user_data.get('created_at'), str):
            user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
        return User(**user_data)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Auth routes
@api_router.post("/auth/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_request: LoginRequest):
    user_data = await db.users.find_one({"username": login_request.username}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not bcrypt.verify(login_request.password, user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token_payload = {
        "user_id": user_data["id"],
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
    
    user_data.pop("password_hash", None)
    return LoginResponse(token=token, user=User(**user_data))

@api_router.post("/auth/register", response_model=User)
async def register(user_create: UserCreate, admin: User = Depends(require_admin)):
    existing = await db.users.find_one({"username": user_create.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user = User(
        username=user_create.username,
        name=user_create.name,
        role=user_create.role
    )
    
    doc = user.model_dump()
    doc["password_hash"] = bcrypt.hash(user_create.password)
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    return user

@api_router.put("/auth/profile", response_model=User)
async def update_profile(profile_update: ProfileUpdate, current_user: User = Depends(get_current_user)):
    update_data = {}
    
    if profile_update.name:
        update_data["name"] = profile_update.name
    
    if profile_update.password:
        update_data["password_hash"] = bcrypt.hash(profile_update.password)
    
    if update_data:
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": update_data}
        )
    
    # Return updated user
    updated_user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "password_hash": 0})
    if isinstance(updated_user.get('created_at'), str):
        updated_user['created_at'] = datetime.fromisoformat(updated_user['created_at'])
    
    return User(**updated_user)

# Admin - Judge management
@api_router.get("/admin/judges", response_model=List[User])
async def get_judges(admin: User = Depends(require_admin)):
    judges = await db.users.find({"role": "judge"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    for judge in judges:
        if isinstance(judge.get('created_at'), str):
            judge['created_at'] = datetime.fromisoformat(judge['created_at'])
    return judges

@api_router.delete("/admin/judges/{judge_id}")
async def delete_judge(judge_id: str, admin: User = Depends(require_admin)):
    result = await db.users.delete_one({"id": judge_id, "role": "judge"})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Judge not found")
    return {"message": "Judge deleted"}

@api_router.put("/admin/judges/{judge_id}/toggle-active")
async def toggle_judge_active(judge_id: str, admin: User = Depends(require_admin)):
    """Toggle a judge's active status"""
    judge = await db.users.find_one({"id": judge_id, "role": "judge"})
    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")
    
    new_status = not judge.get("is_active", True)
    await db.users.update_one(
        {"id": judge_id},
        {"$set": {"is_active": new_status}}
    )
    return {"message": f"Judge {'activated' if new_status else 'deactivated'}", "is_active": new_status}

class ScoringError(BaseModel):
    round_id: str
    round_name: str
    competitor_id: str
    competitor_name: str
    car_number: str
    error_type: str  # "missing_scores", "duplicate_scores", or "score_deviation"
    details: str
    judge_count: int
    expected_count: int
    score_id: Optional[str] = None  # For deviation errors, allows acknowledgment
    judge_name: Optional[str] = None  # For deviation errors, which judge
    deviation_amount: Optional[float] = None  # How much the score deviates

@api_router.get("/admin/scoring-errors", response_model=List[ScoringError])
async def get_scoring_errors(admin: User = Depends(require_admin)):
    """Check for scoring errors: missing scores, duplicate scores, or score deviations"""
    errors = []
    
    # Get score deviation threshold from settings (default 5)
    deviation_settings = await db.settings.find_one({"key": "score_deviation"}, {"_id": 0})
    deviation_threshold = deviation_settings.get("threshold", 5) if deviation_settings else 5
    
    # Get active judges
    active_judges = await db.users.find(
        {"role": "judge", "is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(100)
    active_judge_ids = [j["id"] for j in active_judges]
    active_judge_map = {j["id"]: j["name"] for j in active_judges}
    active_judge_count = len(active_judge_ids)
    
    if active_judge_count == 0:
        return errors
    
    # Get all active rounds
    rounds = await db.rounds.find({"round_status": "active"}, {"_id": 0}).to_list(100)
    
    # Get all competitors
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(10000)
    competitor_map = {c["id"]: c for c in competitors}
    
    # Get all scores
    all_scores = await db.scores.find({}, {"_id": 0}).to_list(100000)
    
    for round_data in rounds:
        round_id = round_data["id"]
        round_name = round_data.get("name", "Unknown Round")
        
        # Group scores by competitor for this round
        round_scores = [s for s in all_scores if s["round_id"] == round_id]
        
        # Build a map: competitor_id -> list of scores
        competitor_scores_map = {}
        for score in round_scores:
            comp_id = score["competitor_id"]
            if comp_id not in competitor_scores_map:
                competitor_scores_map[comp_id] = []
            competitor_scores_map[comp_id].append(score)
        
        # Check each competitor that has at least one score in this round
        for comp_id, scores in competitor_scores_map.items():
            competitor = competitor_map.get(comp_id)
            if not competitor:
                continue
            
            # Only consider scores from active judges
            active_scores = [s for s in scores if s["judge_id"] in active_judge_ids]
            judge_ids = [s["judge_id"] for s in active_scores]
            unique_active_judges = set(judge_ids)
            
            # Check for missing scores (not all active judges have scored)
            if len(unique_active_judges) < active_judge_count:
                missing_count = active_judge_count - len(unique_active_judges)
                errors.append(ScoringError(
                    round_id=round_id,
                    round_name=round_name,
                    competitor_id=comp_id,
                    competitor_name=competitor.get("name", "Unknown"),
                    car_number=competitor.get("car_number", "?"),
                    error_type="missing_scores",
                    details=f"Missing {missing_count} score(s) from active judges",
                    judge_count=len(unique_active_judges),
                    expected_count=active_judge_count
                ))
            
            # Check for duplicate scores (same judge scored same competitor twice in round)
            if len(judge_ids) != len(unique_active_judges):
                from collections import Counter
                judge_counts = Counter(judge_ids)
                duplicates = [jid for jid, count in judge_counts.items() if count > 1]
                duplicate_names = [active_judge_map.get(jid, "Unknown") for jid in duplicates]
                
                errors.append(ScoringError(
                    round_id=round_id,
                    round_name=round_name,
                    competitor_id=comp_id,
                    competitor_name=competitor.get("name", "Unknown"),
                    car_number=competitor.get("car_number", "?"),
                    error_type="duplicate_scores",
                    details=f"Duplicate scores from: {', '.join(duplicate_names)}",
                    judge_count=len(judge_ids),
                    expected_count=active_judge_count
                ))
            
            # Check for score deviations (only if we have multiple scores to compare)
            if len(active_scores) >= 2:
                # Calculate average final score
                final_scores = [s.get("final_score", 0) for s in active_scores]
                avg_score = sum(final_scores) / len(final_scores)
                
                # Check each score against the average
                for score in active_scores:
                    # Skip if already acknowledged
                    if score.get("deviation_acknowledged", False):
                        continue
                    
                    score_value = score.get("final_score", 0)
                    deviation = abs(score_value - avg_score)
                    
                    if deviation > deviation_threshold:
                        judge_name = active_judge_map.get(score["judge_id"], "Unknown")
                        errors.append(ScoringError(
                            round_id=round_id,
                            round_name=round_name,
                            competitor_id=comp_id,
                            competitor_name=competitor.get("name", "Unknown"),
                            car_number=competitor.get("car_number", "?"),
                            error_type="score_deviation",
                            details=f"{judge_name}'s score ({score_value}) deviates {deviation:.1f} pts from average ({avg_score:.1f})",
                            judge_count=len(active_scores),
                            expected_count=active_judge_count,
                            score_id=score.get("id"),
                            judge_name=judge_name,
                            deviation_amount=deviation
                        ))
    
    return errors

# Score deviation settings
@api_router.get("/admin/settings/score-deviation")
async def get_score_deviation_settings(admin: User = Depends(require_admin)):
    """Get score deviation threshold setting"""
    settings = await db.settings.find_one({"key": "score_deviation"}, {"_id": 0})
    return {"threshold": settings.get("threshold", 5) if settings else 5}

@api_router.put("/admin/settings/score-deviation")
async def update_score_deviation_settings(threshold: float, admin: User = Depends(require_admin)):
    """Update score deviation threshold setting"""
    if threshold < 0:
        raise HTTPException(status_code=400, detail="Threshold must be positive")
    
    await db.settings.update_one(
        {"key": "score_deviation"},
        {"$set": {"key": "score_deviation", "threshold": threshold}},
        upsert=True
    )
    return {"threshold": threshold, "message": "Threshold updated"}

@api_router.post("/admin/scores/{score_id}/acknowledge-deviation")
async def acknowledge_score_deviation(score_id: str, admin: User = Depends(require_admin)):
    """Mark a score's deviation as acknowledged/reviewed"""
    result = await db.scores.update_one(
        {"id": score_id},
        {"$set": {"deviation_acknowledged": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Score not found")
    return {"message": "Score deviation acknowledged"}

@api_router.post("/admin/scores/{score_id}/unacknowledge-deviation")
async def unacknowledge_score_deviation(score_id: str, admin: User = Depends(require_admin)):
    """Remove acknowledgment from a score's deviation"""
    result = await db.scores.update_one(
        {"id": score_id},
        {"$set": {"deviation_acknowledged": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Score not found")
    return {"message": "Score deviation acknowledgment removed"}

# Admin - Class management
@api_router.get("/admin/classes", response_model=List[CompetitionClass])
async def get_classes(current_user: User = Depends(get_current_user)):
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    for cls in classes:
        if isinstance(cls.get('created_at'), str):
            cls['created_at'] = datetime.fromisoformat(cls['created_at'])
    return classes

@api_router.post("/admin/classes", response_model=CompetitionClass)
async def create_class(class_create: CompetitionClassCreate, admin: User = Depends(require_admin)):
    comp_class = CompetitionClass(**class_create.model_dump())
    doc = comp_class.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.classes.insert_one(doc)
    return comp_class

@api_router.put("/admin/classes/{class_id}", response_model=CompetitionClass)
async def update_class(class_id: str, class_update: CompetitionClassCreate, admin: User = Depends(require_admin)):
    result = await db.classes.update_one(
        {"id": class_id},
        {"$set": class_update.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Class not found")
    
    updated = await db.classes.find_one({"id": class_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    return CompetitionClass(**updated)

@api_router.delete("/admin/classes/{class_id}")
async def delete_class(class_id: str, admin: User = Depends(require_admin)):
    result = await db.classes.delete_one({"id": class_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Class not found")
    return {"message": "Class deleted"}

# Admin - Competitor management
@api_router.get("/admin/competitors", response_model=List[CompetitorWithClass])
async def get_competitors(current_user: User = Depends(get_current_user)):
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(1000)
    classes_dict = {}
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    for cls in classes:
        classes_dict[cls["id"]] = cls["name"]
    
    result = []
    for comp in competitors:
        if isinstance(comp.get('created_at'), str):
            comp['created_at'] = datetime.fromisoformat(comp['created_at'])
        result.append(CompetitorWithClass(
            **comp,
            class_name=classes_dict.get(comp["class_id"], "Unknown")
        ))
    return result

@api_router.post("/admin/competitors", response_model=Competitor)
async def create_competitor(competitor_create: CompetitorCreate, admin: User = Depends(require_admin)):
    competitor = Competitor(**competitor_create.model_dump())
    doc = competitor.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.competitors.insert_one(doc)
    return competitor

@api_router.post("/admin/competitors/bulk")
@limiter.limit("2/minute")
async def bulk_import_competitors(request: Request, admin: User = Depends(require_admin)):
    try:
        csv_data = await request.body()
        csv_data = csv_data.decode('utf-8')
        csv_file = io.StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        imported = 0
        errors = []
        
        # Get all classes for name-to-id lookup
        classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
        class_name_to_id = {c["name"].lower(): c["id"] for c in classes}
        class_id_set = {c["id"] for c in classes}
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            class_value = row.get('class_id', '').strip() or row.get('class', '').strip() or row.get('class_name', '').strip()
            
            # Try to resolve class - accept either ID or name
            resolved_class_id = None
            if class_value:
                if class_value in class_id_set:
                    # It's already a valid class ID
                    resolved_class_id = class_value
                elif class_value.lower() in class_name_to_id:
                    # It's a class name - look up the ID
                    resolved_class_id = class_name_to_id[class_value.lower()]
                else:
                    errors.append(f"Row {row_num}: Unknown class '{class_value}'")
                    continue
            
            competitor = Competitor(
                name=row.get('name', ''),
                car_number=row.get('car_number', ''),
                vehicle_info=row.get('vehicle_info', ''),
                plate=row.get('plate', ''),
                class_id=resolved_class_id or '',
                email=row.get('email', '').strip()
            )
            doc = competitor.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.competitors.insert_one(doc)
            imported += 1
        
        message = f"Imported {imported} competitors"
        if errors:
            message += f". Errors: {'; '.join(errors[:5])}"
            if len(errors) > 5:
                message += f" (+{len(errors) - 5} more)"
        
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

@api_router.put("/admin/competitors/{competitor_id}", response_model=Competitor)
async def update_competitor(competitor_id: str, competitor_update: CompetitorCreate, admin: User = Depends(require_admin)):
    result = await db.competitors.update_one(
        {"id": competitor_id},
        {"$set": competitor_update.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    updated = await db.competitors.find_one({"id": competitor_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    return Competitor(**updated)

@api_router.put("/admin/competitors/{competitor_id}", response_model=Competitor)
async def update_competitor(competitor_id: str, competitor_update: CompetitorCreate, admin: User = Depends(require_admin)):
    result = await db.competitors.update_one(
        {"id": competitor_id},
        {"$set": competitor_update.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    updated = await db.competitors.find_one({"id": competitor_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    return Competitor(**updated)

@api_router.delete("/admin/competitors/{competitor_id}")
async def delete_competitor(competitor_id: str, admin: User = Depends(require_admin)):
    result = await db.competitors.delete_one({"id": competitor_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return {"message": "Competitor deleted"}

# Admin - Event management
@api_router.get("/admin/events", response_model=List[Event])
async def get_events(current_user: User = Depends(get_current_user)):
    events = await db.events.find({}, {"_id": 0}).to_list(1000)
    for evt in events:
        if isinstance(evt.get('created_at'), str):
            evt['created_at'] = datetime.fromisoformat(evt['created_at'])
    return events

@api_router.post("/admin/events", response_model=Event)
async def create_event(event_create: EventCreate, admin: User = Depends(require_admin)):
    event_obj = Event(**event_create.model_dump())
    doc = event_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.events.insert_one(doc)
    return event_obj

@api_router.put("/admin/events/{event_id}", response_model=Event)
async def update_event(event_id: str, event_update: EventCreate, admin: User = Depends(require_admin)):
    result = await db.events.update_one(
        {"id": event_id},
        {"$set": event_update.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    updated = await db.events.find_one({"id": event_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    return Event(**updated)

@api_router.delete("/admin/events/{event_id}")
async def delete_event(event_id: str, admin: User = Depends(require_admin)):
    result = await db.events.delete_one({"id": event_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}

# Admin - Round management
@api_router.get("/admin/rounds", response_model=List[Round])
async def get_rounds(current_user: User = Depends(get_current_user)):
    rounds = await db.rounds.find({}, {"_id": 0}).to_list(1000)
    for rnd in rounds:
        if isinstance(rnd.get('created_at'), str):
            rnd['created_at'] = datetime.fromisoformat(rnd['created_at'])
    return rounds

@api_router.post("/admin/rounds", response_model=Round)
async def create_round(round_create: RoundCreate, admin: User = Depends(require_admin)):
    round_obj = Round(**round_create.model_dump())
    doc = round_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.rounds.insert_one(doc)
    return round_obj

@api_router.put("/admin/rounds/{round_id}", response_model=Round)
async def update_round(round_id: str, round_update: RoundCreate, admin: User = Depends(require_admin)):
    result = await db.rounds.update_one(
        {"id": round_id},
        {"$set": round_update.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Round not found")
    
    updated = await db.rounds.find_one({"id": round_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    return Round(**updated)

@api_router.delete("/admin/rounds/{round_id}")
async def delete_round(round_id: str, admin: User = Depends(require_admin)):
    result = await db.rounds.delete_one({"id": round_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Round not found")
    return {"message": "Round deleted"}

# Judge - Scoring
@api_router.get("/judge/competitors/{round_id}", response_model=List[CompetitorWithClass])
async def get_competitors_for_round(round_id: str, current_user: User = Depends(get_current_user)):
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(1000)
    classes_dict = {}
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    for cls in classes:
        classes_dict[cls["id"]] = cls["name"]
    
    result = []
    for comp in competitors:
        if isinstance(comp.get('created_at'), str):
            comp['created_at'] = datetime.fromisoformat(comp['created_at'])
        result.append(CompetitorWithClass(
            **comp,
            class_name=classes_dict.get(comp["class_id"], "Unknown")
        ))
    return result

@api_router.post("/judge/scores", response_model=Score)
@limiter.limit("10/minute")
async def submit_score(request: Request, score_create: ScoreCreate, current_user: User = Depends(get_current_user)):
    # Calculate scores
    score_subtotal = (
        score_create.tip_in +
        score_create.instant_smoke +
        score_create.constant_smoke +
        score_create.volume_of_smoke +
        score_create.driving_skill +
        (score_create.tyres_popped * 5)
    )
    
    # Calculate penalties (cumulative)
    penalty_total = (
        (score_create.penalty_reversing * 5) +
        (score_create.penalty_stopping * 5) +
        (score_create.penalty_contact_barrier * 5) +
        (score_create.penalty_small_fire * 5) +
        (score_create.penalty_failed_drive_off * 10) +
        (score_create.penalty_large_fire * 10)
    )
    
    # If disqualified, final score is 0
    if score_create.penalty_disqualified:
        final_score = 0
    else:
        final_score = max(0, score_subtotal - penalty_total)
    
    score = Score(
        judge_id=current_user.id,
        judge_name=current_user.name,
        **score_create.model_dump(),
        score_subtotal=score_subtotal,
        penalty_total=penalty_total,
        final_score=final_score
    )
    
    doc = score.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    await db.scores.insert_one(doc)
    return score

@api_router.get("/judge/scores", response_model=List[ScoreWithDetails])
async def get_judge_scores(current_user: User = Depends(get_current_user)):
    scores = await db.scores.find({"judge_id": current_user.id}, {"_id": 0}).to_list(1000)
    
    # Get competitors and rounds for enrichment
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(1000)
    rounds = await db.rounds.find({}, {"_id": 0}).to_list(1000)
    
    competitors_dict = {c["id"]: c for c in competitors}
    rounds_dict = {r["id"]: r for r in rounds}
    
    enriched_scores = []
    for score in scores:
        if isinstance(score.get('submitted_at'), str):
            score['submitted_at'] = datetime.fromisoformat(score['submitted_at'])
        if score.get('edited_at') and isinstance(score['edited_at'], str):
            score['edited_at'] = datetime.fromisoformat(score['edited_at'])
        
        competitor = competitors_dict.get(score["competitor_id"], {})
        round_data = rounds_dict.get(score["round_id"], {})
        
        enriched_scores.append(ScoreWithDetails(
            **score,
            competitor_name=competitor.get("name", "Unknown"),
            car_number=competitor.get("car_number", "?"),
            round_name=round_data.get("name", "Unknown Round")
        ))
    
    return enriched_scores

@api_router.put("/judge/scores/{score_id}", response_model=Score)
async def update_score(score_id: str, score_update: ScoreUpdate, current_user: User = Depends(get_current_user)):
    # Get existing score
    existing_score = await db.scores.find_one({"id": score_id}, {"_id": 0})
    if not existing_score:
        raise HTTPException(status_code=404, detail="Score not found")
    
    # Verify judge owns this score
    if existing_score["judge_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own scores")
    
    # Update only provided fields
    update_data = {k: v for k, v in score_update.model_dump().items() if v is not None}
    
    if update_data:
        # Recalculate scores with updated values
        updated_score = {**existing_score, **update_data}
        
        score_subtotal = (
            updated_score.get("tip_in", 0) +
            updated_score["instant_smoke"] +
            updated_score["constant_smoke"] +
            updated_score["volume_of_smoke"] +
            updated_score["driving_skill"] +
            (updated_score["tyres_popped"] * 5)
        )
        
        penalty_total = (
            (updated_score["penalty_reversing"] * 5) +
            (updated_score["penalty_stopping"] * 5) +
            (updated_score["penalty_contact_barrier"] * 5) +
            (updated_score["penalty_small_fire"] * 5) +
            (updated_score["penalty_failed_drive_off"] * 10) +
            (updated_score["penalty_large_fire"] * 10)
        )
        
        # If disqualified, final score is 0
        if updated_score.get("penalty_disqualified", False):
            final_score = 0
        else:
            final_score = max(0, score_subtotal - penalty_total)
        
        update_data["score_subtotal"] = score_subtotal
        update_data["penalty_total"] = penalty_total
        update_data["final_score"] = final_score
        update_data["edited_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.scores.update_one(
            {"id": score_id},
            {"$set": update_data}
        )
    
    # Return updated score
    updated = await db.scores.find_one({"id": score_id}, {"_id": 0})
    if isinstance(updated.get('submitted_at'), str):
        updated['submitted_at'] = datetime.fromisoformat(updated['submitted_at'])
    if updated.get('edited_at') and isinstance(updated['edited_at'], str):
        updated['edited_at'] = datetime.fromisoformat(updated['edited_at'])
    
    return Score(**updated)

# Admin Score Management
@api_router.get("/admin/scores")
async def get_all_scores(
    round_id: Optional[str] = None,
    judge_id: Optional[str] = None,
    admin: User = Depends(require_admin)
):
    """Get all scores with optional filters"""
    query = {}
    if round_id:
        query["round_id"] = round_id
    if judge_id:
        query["judge_id"] = judge_id
    
    scores = await db.scores.find(query, {"_id": 0}).to_list(10000)
    
    # Get related data
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(1000)
    rounds = await db.rounds.find({}, {"_id": 0}).to_list(1000)
    
    competitors_dict = {c["id"]: c for c in competitors}
    rounds_dict = {r["id"]: r for r in rounds}
    
    result = []
    for score in scores:
        comp = competitors_dict.get(score.get("competitor_id"), {})
        round_data = rounds_dict.get(score.get("round_id"), {})
        
        result.append({
            **score,
            "competitor_name": comp.get("name", "Unknown"),
            "car_number": comp.get("car_number", ""),
            "round_name": round_data.get("name", "Unknown")
        })
    
    return result

@api_router.delete("/admin/scores/{score_id}")
async def delete_score(score_id: str, admin: User = Depends(require_admin)):
    """Delete a specific score"""
    result = await db.scores.delete_one({"id": score_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Score not found")
    return {"message": "Score deleted successfully"}

@api_router.put("/admin/scores/{score_id}")
async def admin_edit_score(score_id: str, score_update: ScoreUpdate, admin: User = Depends(require_admin)):
    """Admin endpoint to edit any score"""
    existing_score = await db.scores.find_one({"id": score_id}, {"_id": 0})
    if not existing_score:
        raise HTTPException(status_code=404, detail="Score not found")
    
    # Update only provided fields
    update_data = {k: v for k, v in score_update.model_dump().items() if v is not None}
    
    if update_data:
        # Recalculate scores with updated values
        updated_score = {**existing_score, **update_data}
        
        score_subtotal = (
            updated_score.get("tip_in", 0) +
            updated_score.get("instant_smoke", 0) +
            updated_score.get("constant_smoke", 0) +
            updated_score.get("volume_of_smoke", 0) +
            updated_score.get("driving_skill", 0) +
            (updated_score.get("tyres_popped", 0) * 5)
        )
        
        penalty_total = (
            (updated_score.get("penalty_reversing", 0) * 5) +
            (updated_score.get("penalty_stopping", 0) * 5) +
            (updated_score.get("penalty_contact_barrier", 0) * 5) +
            (updated_score.get("penalty_small_fire", 0) * 5) +
            (updated_score.get("penalty_failed_drive_off", 0) * 10) +
            (updated_score.get("penalty_large_fire", 0) * 10)
        )
        
        # If disqualified, final score is 0
        if updated_score.get("penalty_disqualified", False):
            final_score = 0
        else:
            final_score = max(0, score_subtotal - penalty_total)
        
        update_data["score_subtotal"] = score_subtotal
        update_data["penalty_total"] = penalty_total
        update_data["final_score"] = final_score
        update_data["edited_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.scores.update_one(
            {"id": score_id},
            {"$set": update_data}
        )
    
    # Return updated score
    updated = await db.scores.find_one({"id": score_id}, {"_id": 0})
    return updated

class PendingEmailStats(BaseModel):
    total_competitors_scored: int
    competitors_pending_email: int
    competitors_list: List[dict]

@api_router.get("/admin/pending-emails", response_model=PendingEmailStats)
async def get_pending_emails(admin: User = Depends(require_admin)):
    """Get count of competitors who have been scored but not emailed"""
    # Get active judges count
    active_judges = await db.users.find(
        {"role": "judge", "is_active": {"$ne": False}},
        {"_id": 0, "id": 1}
    ).to_list(100)
    active_judge_count = len(active_judges)
    
    if active_judge_count == 0:
        return PendingEmailStats(
            total_competitors_scored=0,
            competitors_pending_email=0,
            competitors_list=[]
        )
    
    # Get all scores
    scores = await db.scores.find({}, {"_id": 0}).to_list(100000)
    
    # Get competitors and rounds
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(10000)
    rounds = await db.rounds.find({}, {"_id": 0}).to_list(100)
    
    competitors_dict = {c["id"]: c for c in competitors}
    rounds_dict = {r["id"]: r for r in rounds}
    
    # Group scores by competitor and round
    competitor_round_scores = {}
    for score in scores:
        comp_id = score["competitor_id"]
        round_id = score["round_id"]
        key = (comp_id, round_id)
        if key not in competitor_round_scores:
            competitor_round_scores[key] = {
                "scores": [],
                "email_sent": False
            }
        competitor_round_scores[key]["scores"].append(score)
        # If any score in this round has been emailed, mark as sent
        if score.get("email_sent", False):
            competitor_round_scores[key]["email_sent"] = True
    
    # Find competitors with complete scoring (all active judges) but not emailed
    pending_list = []
    total_scored = 0
    
    for (comp_id, round_id), data in competitor_round_scores.items():
        active_judge_ids = [j["id"] for j in active_judges]
        scores_from_active = [s for s in data["scores"] if s["judge_id"] in active_judge_ids]
        unique_judges = set(s["judge_id"] for s in scores_from_active)
        
        # Check if all active judges have scored
        if len(unique_judges) >= active_judge_count:
            total_scored += 1
            if not data["email_sent"]:
                competitor = competitors_dict.get(comp_id, {})
                round_info = rounds_dict.get(round_id, {})
                pending_list.append({
                    "competitor_id": comp_id,
                    "competitor_name": competitor.get("name", "Unknown"),
                    "car_number": competitor.get("car_number", "?"),
                    "round_id": round_id,
                    "round_name": round_info.get("name", "Unknown Round"),
                    "score_count": len(scores_from_active)
                })
    
    return PendingEmailStats(
        total_competitors_scored=total_scored,
        competitors_pending_email=len(pending_list),
        competitors_list=pending_list
    )

@api_router.post("/admin/mark-emailed/{competitor_id}/{round_id}")
async def mark_scores_emailed(competitor_id: str, round_id: str, admin: User = Depends(require_admin)):
    """Mark all scores for a competitor in a round as emailed"""
    result = await db.scores.update_many(
        {"competitor_id": competitor_id, "round_id": round_id},
        {"$set": {"email_sent": True}}
    )
    return {"message": f"Marked {result.modified_count} scores as emailed"}

# Leaderboard
@api_router.get("/leaderboard/{round_id}", response_model=List[LeaderboardEntry])
async def get_leaderboard(round_id: str, class_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    # Get all scores for the round
    scores = await db.scores.find({"round_id": round_id}, {"_id": 0}).to_list(10000)
    
    # Get competitors and classes
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(1000)
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    
    competitors_dict = {c["id"]: c for c in competitors}
    classes_dict = {c["id"]: c["name"] for c in classes}
    
    # Calculate totals and averages
    competitor_scores = {}
    for score in scores:
        comp_id = score["competitor_id"]
        if comp_id not in competitor_scores:
            competitor_scores[comp_id] = []
        competitor_scores[comp_id].append(score.get("final_score", 0))
    
    leaderboard = []
    for comp_id, score_list in competitor_scores.items():
        if comp_id not in competitors_dict:
            continue
        
        competitor = competitors_dict[comp_id]
        
        # Filter by class if specified
        if class_id and competitor.get("class_id") != class_id:
            continue
        
        total_score = sum(score_list)
        avg_score = total_score / len(score_list) if score_list else 0
        leaderboard.append(LeaderboardEntry(
            competitor_id=comp_id,
            competitor_name=competitor.get("name", "Unknown"),
            car_number=competitor.get("car_number", ""),
            vehicle_info=competitor.get("vehicle_info", ""),
            class_name=classes_dict.get(competitor.get("class_id"), "Unknown"),
            total_score=round(total_score, 2),
            average_score=round(avg_score, 2),
            score_count=len(score_list)
        ))
    
    # Sort by average score descending (default)
    leaderboard.sort(key=lambda x: x.average_score, reverse=True)
    return leaderboard

@api_router.get("/leaderboard/minor-rounds/cumulative", response_model=List[MinorRoundsLeaderboardEntry])
async def get_minor_rounds_leaderboard(class_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get cumulative leaderboard for all minor rounds"""
    # Get all minor rounds
    minor_rounds = await db.rounds.find({"is_minor": True}, {"_id": 0}).to_list(100)
    minor_round_ids = [r["id"] for r in minor_rounds]
    
    if not minor_round_ids:
        return []
    
    # Get all scores for minor rounds
    scores = await db.scores.find({"round_id": {"$in": minor_round_ids}}, {"_id": 0}).to_list(10000)
    
    # Get competitors and classes
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(1000)
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    
    competitors_dict = {c["id"]: c for c in competitors}
    classes_dict = {c["id"]: c["name"] for c in classes}
    
    # Calculate cumulative scores
    competitor_data = {}
    for score in scores:
        comp_id = score["competitor_id"]
        round_id = score["round_id"]
        if comp_id not in competitor_data:
            competitor_data[comp_id] = {"scores": [], "rounds": set()}
        competitor_data[comp_id]["scores"].append(score.get("final_score", 0))
        competitor_data[comp_id]["rounds"].add(round_id)
    
    leaderboard = []
    for comp_id, data in competitor_data.items():
        if comp_id not in competitors_dict:
            continue
        
        competitor = competitors_dict[comp_id]
        
        # Filter by class if specified
        if class_id and competitor.get("class_id") != class_id:
            continue
        
        total_score = sum(data["scores"])
        avg_score = total_score / len(data["scores"]) if data["scores"] else 0
        leaderboard.append(MinorRoundsLeaderboardEntry(
            competitor_id=comp_id,
            competitor_name=competitor.get("name", "Unknown"),
            car_number=competitor.get("car_number", ""),
            vehicle_info=competitor.get("vehicle_info", ""),
            class_name=classes_dict.get(competitor.get("class_id"), "Unknown"),
            total_score=round(total_score, 2),
            average_score=round(avg_score, 2),
            rounds_competed=len(data["rounds"]),
            score_count=len(data["scores"])
        ))
    
    # Sort by total score descending
    leaderboard.sort(key=lambda x: x.total_score, reverse=True)
    return leaderboard

# Export
@api_router.get("/export/all-data")
async def export_all_data(admin: User = Depends(require_admin)):
    # Export all data including competitors, rounds, classes, and all scores
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(10000)
    rounds = await db.rounds.find({}, {"_id": 0}).to_list(10000)
    classes = await db.classes.find({}, {"_id": 0}).to_list(10000)
    scores = await db.scores.find({}, {"_id": 0}).to_list(10000)
    
    # Create dictionaries for lookups
    competitors_dict = {c["id"]: c for c in competitors}
    rounds_dict = {r["id"]: r for r in rounds}
    classes_dict = {c["id"]: c for c in classes}
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write comprehensive header (includes Tip In)
    writer.writerow([
        "Score ID", "Judge Name", "Round Name", "Round Date", "Competitor Name", 
        "Car Number", "Plate", "Vehicle", "Class", "Tip In", "Instant Smoke", "Constant Smoke", 
        "Volume Smoke", "Driving Skill", "Tyres Popped", "Tyres Points",
        "Reversing Count", "Stopping Count", "Barrier Contact Count", "Small Fire Count",
        "Failed Drive Off Count", "Large Fire Count",
        "Score Subtotal", "Penalty Total", "Final Score", 
        "Submitted At", "Edited At", "Was Edited"
    ])
    
    for score in scores:
        comp = competitors_dict.get(score["competitor_id"], {})
        round_data = rounds_dict.get(score["round_id"], {})
        class_name = classes_dict.get(comp.get("class_id", ""), {}).get("name", "Unknown")
        
        was_edited = "Yes" if score.get("edited_at") else "No"
        
        writer.writerow([
            score["id"],
            score["judge_name"],
            round_data.get("name", "Unknown"),
            round_data.get("date", ""),
            comp.get("name", "Unknown"),
            comp.get("car_number", ""),
            comp.get("plate", ""),
            comp.get("vehicle_info", ""),
            class_name,
            score.get("tip_in", 0),  # Handle old scores without tip_in
            score.get("instant_smoke", 0),
            score.get("constant_smoke", 0),
            score.get("volume_of_smoke", 0),
            score.get("driving_skill", 0),
            score.get("tyres_popped", 0),
            score.get("tyres_popped", 0) * 5,
            score.get("penalty_reversing", 0),
            score.get("penalty_stopping", 0),
            score.get("penalty_contact_barrier", 0),
            score.get("penalty_small_fire", 0),
            score.get("penalty_failed_drive_off", 0),
            score.get("penalty_large_fire", 0),
            score.get("score_subtotal", 0),
            score.get("penalty_total", 0),
            score.get("final_score", 0),
            score.get("submitted_at", ""),
            score.get("edited_at", ""),
            was_edited
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=burnout_scoring_all_data.csv"}
    )

@api_router.get("/export/scores/{round_id}")
async def export_scores(round_id: str, admin: User = Depends(require_admin)):
    scores = await db.scores.find({"round_id": round_id}, {"_id": 0}).to_list(10000)
    competitors = await db.competitors.find({}, {"_id": 0}).to_list(1000)
    classes = await db.classes.find({}, {"_id": 0}).to_list(1000)
    
    competitors_dict = {c["id"]: c for c in competitors}
    classes_dict = {c["id"]: c["name"] for c in classes}
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Competitor Name", "Car Number", "Vehicle", "Class", "Judge",
        "Tip In", "Instant Smoke", "Constant Smoke", "Volume Smoke", "Driving Skill",
        "Tyres Popped", "Score Subtotal", "Penalty Total", "Final Score", "Submitted At"
    ])
    
    for score in scores:
        comp = competitors_dict.get(score["competitor_id"], {})
        class_name = classes_dict.get(comp.get("class_id", ""), "Unknown")
        writer.writerow([
            comp.get("name", ""),
            comp.get("car_number", ""),
            comp.get("vehicle_info", ""),
            class_name,
            score.get("judge_name", ""),
            score.get("tip_in", 0),  # Handle old scores without tip_in
            score.get("instant_smoke", 0),
            score.get("constant_smoke", 0),
            score.get("volume_of_smoke", 0),
            score.get("driving_skill", 0),
            score.get("tyres_popped", 0),
            score.get("score_subtotal", 0),
            score.get("penalty_total", 0),
            score.get("final_score", 0),
            score.get("submitted_at", "")
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=scores_round_{round_id}.csv"}
    )

# Admin Data Reset Endpoints
class ResetResponse(BaseModel):
    message: str
    deleted_counts: dict

@api_router.delete("/admin/reset/scores", response_model=ResetResponse)
async def reset_scores(admin: User = Depends(require_admin)):
    """Reset all scores only"""
    result = await db.scores.delete_many({})
    return ResetResponse(
        message="All scores have been deleted",
        deleted_counts={"scores": result.deleted_count}
    )

@api_router.delete("/admin/reset/competition", response_model=ResetResponse)
async def reset_competition_data(admin: User = Depends(require_admin)):
    """Reset all competition data (scores, competitors, rounds, classes)"""
    scores_result = await db.scores.delete_many({})
    competitors_result = await db.competitors.delete_many({})
    rounds_result = await db.rounds.delete_many({})
    classes_result = await db.classes.delete_many({})
    
    return ResetResponse(
        message="All competition data has been deleted",
        deleted_counts={
            "scores": scores_result.deleted_count,
            "competitors": competitors_result.deleted_count,
            "rounds": rounds_result.deleted_count,
            "classes": classes_result.deleted_count
        }
    )

@api_router.delete("/admin/reset/full", response_model=ResetResponse)
async def reset_full(admin: User = Depends(require_admin)):
    """Full reset - delete everything except the current admin user"""
    # Get current admin's ID to preserve
    current_admin = await db.users.find_one({"role": "admin"}, {"_id": 0, "id": 1})
    admin_id = current_admin["id"] if current_admin else None
    
    scores_result = await db.scores.delete_many({})
    competitors_result = await db.competitors.delete_many({})
    rounds_result = await db.rounds.delete_many({})
    classes_result = await db.classes.delete_many({})
    # Delete all judges but keep admin
    judges_result = await db.users.delete_many({"role": "judge"})
    
    return ResetResponse(
        message="Full reset completed (admin account preserved)",
        deleted_counts={
            "scores": scores_result.deleted_count,
            "competitors": competitors_result.deleted_count,
            "rounds": rounds_result.deleted_count,
            "classes": classes_result.deleted_count,
            "judges": judges_result.deleted_count
        }
    )

# Settings/Logo endpoints
@api_router.post("/admin/settings/logo")
async def upload_logo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload organization logo for reports"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, and WebP images are allowed")
    
    # Read file and convert to base64
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:  # 2MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 2MB")
    
    base64_data = base64.b64encode(content).decode('utf-8')
    
    # Store in settings collection
    await db.settings.update_one(
        {"key": "logo"},
        {"$set": {
            "key": "logo",
            "data": base64_data,
            "content_type": file.content_type,
            "filename": file.filename,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": "Logo uploaded successfully", "filename": file.filename}

@api_router.get("/admin/settings/logo")
async def get_logo():
    """Get organization logo"""
    logo = await db.settings.find_one({"key": "logo"}, {"_id": 0})
    if not logo:
        return {"logo": None}
    return {
        "logo": f"data:{logo['content_type']};base64,{logo['data']}",
        "filename": logo.get("filename")
    }

@api_router.delete("/admin/settings/logo")
async def delete_logo(current_user: User = Depends(get_current_user)):
    """Delete organization logo"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    await db.settings.delete_one({"key": "logo"})
    return {"message": "Logo deleted successfully"}

@api_router.get("/admin/settings/website")
async def get_website_settings():
    """Get website/organization name for reports"""
    settings = await db.settings.find_one({"key": "website"}, {"_id": 0})
    if not settings:
        return {"website_url": "", "organization_name": ""}
    return {
        "website_url": settings.get("website_url", ""),
        "organization_name": settings.get("organization_name", "")
    }

@api_router.put("/admin/settings/website")
async def update_website_settings(
    website_url: str = "",
    organization_name: str = "",
    current_user: User = Depends(get_current_user)
):
    """Update website/organization settings"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    await db.settings.update_one(
        {"key": "website"},
        {"$set": {
            "key": "website",
            "website_url": website_url,
            "organization_name": organization_name,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"message": "Settings updated successfully"}

# SMTP Settings
class SMTPSettings(BaseModel):
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_email: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

@api_router.get("/admin/settings/smtp")
async def get_smtp_settings(admin: User = Depends(require_admin)):
    """Get SMTP settings (password masked)"""
    settings = await db.settings.find_one({"key": "smtp"}, {"_id": 0})
    if not settings:
        return {"smtp_server": "", "smtp_port": 587, "smtp_email": "", "smtp_password": "", "smtp_use_tls": True}
    # Mask password for security
    return {
        "smtp_server": settings.get("smtp_server", ""),
        "smtp_port": settings.get("smtp_port", 587),
        "smtp_email": settings.get("smtp_email", ""),
        "smtp_password": "********" if settings.get("smtp_password") else "",
        "smtp_use_tls": settings.get("smtp_use_tls", True)
    }

@api_router.put("/admin/settings/smtp")
async def update_smtp_settings(settings: SMTPSettings, admin: User = Depends(require_admin)):
    """Update SMTP settings"""
    update_data = {
        "key": "smtp",
        "smtp_server": settings.smtp_server,
        "smtp_port": settings.smtp_port,
        "smtp_email": settings.smtp_email,
        "smtp_use_tls": settings.smtp_use_tls,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    # Only update password if it's not masked
    if settings.smtp_password and settings.smtp_password != "********":
        update_data["smtp_password"] = settings.smtp_password
    else:
        # Keep existing password
        existing = await db.settings.find_one({"key": "smtp"})
        if existing and existing.get("smtp_password"):
            update_data["smtp_password"] = existing["smtp_password"]
    
    await db.settings.update_one(
        {"key": "smtp"},
        {"$set": update_data},
        upsert=True
    )
    return {"message": "SMTP settings updated successfully"}

@api_router.post("/admin/settings/smtp/test")
async def test_smtp_connection(admin: User = Depends(require_admin)):
    """Test SMTP connection"""
    settings = await db.settings.find_one({"key": "smtp"}, {"_id": 0})
    if not settings or not settings.get("smtp_server"):
        raise HTTPException(status_code=400, detail="SMTP not configured")
    
    try:
        port = settings.get("smtp_port", 587)
        use_tls = settings.get("smtp_use_tls", True)
        
        # For port 465, use SSL directly; for 587, use STARTTLS
        if port == 465 or not use_tls:
            server = smtplib.SMTP_SSL(settings["smtp_server"], port, timeout=30)
        else:
            server = smtplib.SMTP(settings["smtp_server"], port, timeout=30)
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
        
        server.login(settings["smtp_email"], settings["smtp_password"])
        server.quit()
        return {"message": "SMTP connection successful"}
    except smtplib.SMTPAuthenticationError as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: Check email/password. {str(e)}")
    except smtplib.SMTPConnectError as e:
        raise HTTPException(status_code=400, detail=f"Could not connect to server: {str(e)}")
    except smtplib.SMTPServerDisconnected as e:
        raise HTTPException(status_code=400, detail=f"Server disconnected: {str(e)}")
    except TimeoutError:
        raise HTTPException(status_code=400, detail="Connection timed out. Check server address and port.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SMTP connection failed: {str(e)}")

class EmailRequest(BaseModel):
    competitor_id: str
    round_id: Optional[str] = None  # If None, send all rounds
    recipient_email: str

class BulkEmailRequest(BaseModel):
    competitor_emails: List[dict]  # List of {competitor_id, recipient_email, round_id}

@api_router.post("/admin/send-competitor-report")
async def send_competitor_report(request: EmailRequest, admin: User = Depends(require_admin)):
    """Send score report email to a competitor"""
    # Get SMTP settings
    smtp_settings = await db.settings.find_one({"key": "smtp"}, {"_id": 0})
    if not smtp_settings or not smtp_settings.get("smtp_server"):
        raise HTTPException(status_code=400, detail="SMTP not configured")
    
    # Get competitor info
    competitor = await db.competitors.find_one({"id": request.competitor_id}, {"_id": 0})
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    # Get class info
    comp_class = await db.classes.find_one({"id": competitor.get("class_id")}, {"_id": 0})
    class_name = comp_class.get("name", "Unknown") if comp_class else "Unknown"
    
    # Get event info
    event = await db.events.find_one({"is_active": {"$ne": False}}, {"_id": 0})
    event_name = event.get("name", "Burnout Competition") if event else "Burnout Competition"
    event_date = event.get("date", "") if event else ""
    
    # Format date as DD/MM/YYYY
    if event_date:
        try:
            date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00')) if 'T' in event_date else datetime.strptime(event_date, '%Y-%m-%d')
            event_date = date_obj.strftime('%d/%m/%Y')
        except:
            pass
    
    # Get website settings
    website_settings = await db.settings.find_one({"key": "website"}, {"_id": 0})
    website_url = website_settings.get("website_url", "") if website_settings else ""
    org_name = website_settings.get("organization_name", "") if website_settings else ""
    
    # Get logo
    logo_settings = await db.settings.find_one({"key": "logo"}, {"_id": 0})
    logo_data = None
    if logo_settings and logo_settings.get("data"):
        logo_data = f"data:{logo_settings['content_type']};base64,{logo_settings['data']}"
    
    # Get scores for this competitor
    score_filter = {"competitor_id": request.competitor_id}
    if request.round_id:
        score_filter["round_id"] = request.round_id
    
    scores = await db.scores.find(score_filter, {"_id": 0}).to_list(1000)
    if not scores:
        raise HTTPException(status_code=404, detail="No scores found for this competitor")
    
    # Get rounds info
    rounds = await db.rounds.find({}, {"_id": 0}).to_list(100)
    rounds_dict = {r["id"]: r for r in rounds}
    
    # Get judges info
    judges = await db.users.find({"role": "judge"}, {"_id": 0}).to_list(100)
    judges_dict = {j["id"]: j for j in judges}
    
    # Group scores by round
    scores_by_round = {}
    for score in scores:
        round_id = score["round_id"]
        if round_id not in scores_by_round:
            scores_by_round[round_id] = []
        scores_by_round[round_id].append(score)
    
    # Build HTML email
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; border-bottom: 2px solid #f97316; padding-bottom: 15px; margin-bottom: 20px; }}
            .header img {{ max-height: 60px; margin-bottom: 10px; }}
            .event-name {{ font-size: 20px; font-weight: bold; margin-bottom: 5px; }}
            .event-date {{ font-size: 14px; color: #666; }}
            .competitor-info {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .competitor-number {{ font-size: 24px; font-weight: bold; color: #f97316; }}
            .round-section {{ margin-bottom: 25px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }}
            .round-header {{ background: #f97316; color: white; padding: 10px 15px; font-weight: bold; }}
            .score-table {{ width: 100%; border-collapse: collapse; }}
            .score-table th, .score-table td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
            .score-table th {{ background: #f9f9f9; font-size: 12px; color: #666; }}
            .category-row td {{ font-weight: 500; }}
            .penalty-row td {{ color: #dc2626; }}
            .total-row {{ background: #f0fdf4; }}
            .total-row td {{ font-weight: bold; font-size: 16px; }}
            .dq-row {{ background: #fef2f2; }}
            .dq-row td {{ color: #dc2626; font-weight: bold; }}
            .judge-name {{ font-size: 12px; color: #666; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }}
            .summary-box {{ background: #fff7ed; border: 2px solid #f97316; border-radius: 8px; padding: 15px; margin-top: 20px; text-align: center; }}
            .summary-score {{ font-size: 32px; font-weight: bold; color: #f97316; }}
        </style>
    </head>
    <body>
        <div class="header">
            {f'<img src="{logo_data}" alt="Logo" /><br/>' if logo_data else ''}
            <div class="event-name">{event_name}</div>
            {f'<div class="event-date">{event_date}</div>' if event_date else ''}
        </div>
        
        <div class="competitor-info">
            <span class="competitor-number">#{competitor.get('car_number', '?')}</span>
            <strong>{competitor.get('name', 'Unknown')}</strong><br/>
            <span style="color: #666;">Vehicle: {competitor.get('vehicle_info', 'N/A')} | Class: {class_name}</span>
        </div>
    """
    
    total_scores = []
    for round_id, round_scores in scores_by_round.items():
        round_info = rounds_dict.get(round_id, {})
        round_name = round_info.get("name", "Unknown Round")
        
        html_content += f"""
        <div class="round-section">
            <div class="round-header">{round_name}</div>
            <table class="score-table">
                <thead>
                    <tr>
                        <th>Category</th>
        """
        
        # Add judge columns - number them as Judge 1, Judge 2, etc.
        for idx, score in enumerate(round_scores, start=1):
            html_content += f'<th class="judge-name">Judge {idx}</th>'
        
        html_content += """
                    </tr>
                </thead>
                <tbody>
        """
        
        # Score categories
        categories = [
            ("Tip In", "tip_in", "0-10"),
            ("Instant Smoke", "instant_smoke", "0-10"),
            ("Constant Smoke", "constant_smoke", "0-20"),
            ("Volume of Smoke", "volume_of_smoke", "0-20"),
            ("Driving Skill", "driving_skill", "0-40"),
            ("Tyres Popped", "tyres_popped", "×5 pts")
        ]
        
        for cat_name, cat_key, cat_range in categories:
            html_content += f'<tr class="category-row"><td>{cat_name} <span style="color:#999;font-size:11px;">({cat_range})</span></td>'
            for score in round_scores:
                val = score.get(cat_key, 0)
                if cat_key == "tyres_popped":
                    html_content += f'<td>{val} ({val * 5} pts)</td>'
                else:
                    html_content += f'<td>{val}</td>'
            html_content += '</tr>'
        
        # Subtotal row
        html_content += '<tr style="background:#f9f9f9;"><td><strong>Score Subtotal</strong></td>'
        for score in round_scores:
            html_content += f'<td><strong>{score.get("score_subtotal", 0)}</strong></td>'
        html_content += '</tr>'
        
        # Penalties
        penalties = [
            ("Reversing", "penalty_reversing", -5),
            ("Stopping", "penalty_stopping", -5),
            ("Contact with Barrier", "penalty_contact_barrier", -5),
            ("Small Fire", "penalty_small_fire", -5),
            ("Failed to Drive Off", "penalty_failed_drive_off", -10),
            ("Large Fire", "penalty_large_fire", -10)
        ]
        
        html_content += '<tr><td colspan="100%" style="background:#fef2f2;padding:5px 12px;font-weight:bold;color:#dc2626;">Penalties</td></tr>'
        
        for pen_name, pen_key, pen_pts in penalties:
            has_penalty = any(score.get(pen_key, 0) > 0 for score in round_scores)
            if has_penalty:
                html_content += f'<tr class="penalty-row"><td>{pen_name} ({pen_pts} pts)</td>'
                for score in round_scores:
                    val = score.get(pen_key, 0)
                    if val > 0:
                        html_content += f'<td>-{val * abs(pen_pts)}</td>'
                    else:
                        html_content += '<td>-</td>'
                html_content += '</tr>'
        
        # Penalty total
        html_content += '<tr style="background:#fef2f2;"><td><strong>Penalty Total</strong></td>'
        for score in round_scores:
            penalty_total = score.get("penalty_total", 0)
            html_content += f'<td><strong>-{penalty_total}</strong></td>'
        html_content += '</tr>'
        
        # Final score row
        for score in round_scores:
            is_dq = score.get("penalty_disqualified", False)
            if is_dq:
                html_content += '<tr class="dq-row"><td><strong>DISQUALIFIED</strong></td>'
                for s in round_scores:
                    if s.get("penalty_disqualified", False):
                        html_content += '<td>0 (DQ)</td>'
                    else:
                        html_content += f'<td>{s.get("final_score", 0)}</td>'
                html_content += '</tr>'
                break
        
        html_content += '<tr class="total-row"><td>Final Score</td>'
        for score in round_scores:
            final = score.get("final_score", 0)
            total_scores.append(final)
            if score.get("penalty_disqualified", False):
                html_content += '<td style="color:#dc2626;">0 (DQ)</td>'
            else:
                html_content += f'<td>{final}</td>'
        html_content += '</tr>'
        
        html_content += """
                </tbody>
            </table>
        </div>
        """
    
    # Summary
    if total_scores:
        avg_score = sum(total_scores) / len(total_scores)
        total_score = sum(total_scores)
        html_content += f"""
        <div class="summary-box">
            <div>Total Score: <span class="summary-score">{total_score}</span></div>
            <div style="color:#666;margin-top:5px;">Average Score: {avg_score:.2f} (from {len(scores_by_round)} round(s))</div>
        </div>
        """
    
    html_content += f"""
        <div class="footer">
            Generated on {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br/>
            {website_url}
        </div>
    </body>
    </html>
    """
    
    # Send email
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Burnout Scores - #{competitor.get('car_number', '?')} {competitor.get('name', '')} - {event_name}"
        msg['From'] = smtp_settings["smtp_email"]
        msg['To'] = request.recipient_email
        
        # Use base64 encoding to avoid line length issues
        html_part = MIMEText(html_content, 'html', 'utf-8')
        html_part.replace_header('Content-Transfer-Encoding', 'base64')
        msg.attach(html_part)
        
        port = smtp_settings.get("smtp_port", 587)
        use_tls = smtp_settings.get("smtp_use_tls", True)
        
        # For port 465, use SSL directly; for 587, use STARTTLS
        if port == 465 or not use_tls:
            server = smtplib.SMTP_SSL(smtp_settings["smtp_server"], port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_settings["smtp_server"], port, timeout=30)
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
        
        server.login(smtp_settings["smtp_email"], smtp_settings["smtp_password"])
        server.sendmail(smtp_settings["smtp_email"], request.recipient_email, msg.as_string())
        server.quit()
        
        # Mark scores as emailed
        await db.scores.update_many(
            {"competitor_id": request.competitor_id} if not request.round_id else {"competitor_id": request.competitor_id, "round_id": request.round_id},
            {"$set": {"email_sent": True}}
        )
        
        return {"message": f"Email sent successfully to {request.recipient_email}"}
    except smtplib.SMTPAuthenticationError as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

# Helper function to create email HTML content
async def get_completed_rounds_for_competitor(competitor_id: str):
    """Get all round IDs where this competitor has complete scoring from all active judges"""
    # Get active judges
    active_judges = await db.users.find(
        {"role": "judge", "is_active": {"$ne": False}},
        {"_id": 0, "id": 1}
    ).to_list(100)
    active_judge_ids = [j["id"] for j in active_judges]
    active_judge_count = len(active_judge_ids)
    
    if active_judge_count == 0:
        return []
    
    # Get all scores for this competitor
    scores = await db.scores.find({"competitor_id": competitor_id}, {"_id": 0}).to_list(1000)
    
    # Group by round and check if all active judges have scored
    scores_by_round = {}
    for score in scores:
        rid = score["round_id"]
        if rid not in scores_by_round:
            scores_by_round[rid] = set()
        if score["judge_id"] in active_judge_ids:
            scores_by_round[rid].add(score["judge_id"])
    
    # Return round IDs where all active judges have scored
    completed_rounds = [rid for rid, judges in scores_by_round.items() 
                        if len(judges) >= active_judge_count]
    return completed_rounds


async def generate_competitor_email_html(competitor_id: str, round_id: Optional[str] = None, include_all_completed: bool = False):
    """Generate HTML email content for a competitor's scores
    
    Args:
        competitor_id: The competitor's ID
        round_id: Specific round to include (if None and include_all_completed=False, includes all)
        include_all_completed: If True, include all rounds where all active judges have scored
    """
    # Get competitor info
    competitor = await db.competitors.find_one({"id": competitor_id}, {"_id": 0})
    if not competitor:
        return None, "Competitor not found"
    
    # Get class info
    comp_class = await db.classes.find_one({"id": competitor.get("class_id")}, {"_id": 0})
    class_name = comp_class.get("name", "Unknown") if comp_class else "Unknown"
    
    # Get event info
    event = await db.events.find_one({"is_active": {"$ne": False}}, {"_id": 0})
    event_name = event.get("name", "Burnout Competition") if event else "Burnout Competition"
    event_date = event.get("date", "") if event else ""
    
    # Format date as DD/MM/YYYY
    if event_date:
        try:
            date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00')) if 'T' in event_date else datetime.strptime(event_date, '%Y-%m-%d')
            event_date = date_obj.strftime('%d/%m/%Y')
        except:
            pass
    
    # Get website settings
    website_settings = await db.settings.find_one({"key": "website"}, {"_id": 0})
    website_url = website_settings.get("website_url", "") if website_settings else ""
    
    # Get logo
    logo_settings = await db.settings.find_one({"key": "logo"}, {"_id": 0})
    logo_data = None
    if logo_settings and logo_settings.get("data"):
        logo_data = f"data:{logo_settings['content_type']};base64,{logo_settings['data']}"
    
    # Determine which rounds to include
    if include_all_completed:
        # Get all completed rounds for this competitor
        completed_round_ids = await get_completed_rounds_for_competitor(competitor_id)
        if not completed_round_ids:
            return None, "No completed rounds found"
        # Get scores for all completed rounds
        scores = await db.scores.find(
            {"competitor_id": competitor_id, "round_id": {"$in": completed_round_ids}}, 
            {"_id": 0}
        ).to_list(1000)
    else:
        # Original behavior - specific round or all
        score_filter = {"competitor_id": competitor_id}
        if round_id:
            score_filter["round_id"] = round_id
        scores = await db.scores.find(score_filter, {"_id": 0}).to_list(1000)
    
    if not scores:
        return None, "No scores found"
    
    # Get rounds and judges info
    rounds = await db.rounds.find({}, {"_id": 0}).to_list(100)
    rounds_dict = {r["id"]: r for r in rounds}
    judges = await db.users.find({"role": "judge"}, {"_id": 0}).to_list(100)
    judges_dict = {j["id"]: j for j in judges}
    
    # Group scores by round
    scores_by_round = {}
    for score in scores:
        rid = score["round_id"]
        if rid not in scores_by_round:
            scores_by_round[rid] = []
        scores_by_round[rid].append(score)
    
    # Build HTML (simplified version for bulk)
    html = f"""<html><head><style>
        body {{ font-family: Arial, sans-serif; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; border-bottom: 2px solid #f97316; padding-bottom: 15px; margin-bottom: 20px; }}
        .event-name {{ font-size: 20px; font-weight: bold; }}
        .event-date {{ font-size: 14px; color: #666; }}
        .competitor-info {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .competitor-number {{ font-size: 24px; font-weight: bold; color: #f97316; }}
        .round-section {{ margin-bottom: 20px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }}
        .round-header {{ background: #f97316; color: white; padding: 10px 15px; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f9f9f9; font-size: 12px; }}
        .total-row {{ background: #f0fdf4; font-weight: bold; }}
        .summary-box {{ background: #fff7ed; border: 2px solid #f97316; border-radius: 8px; padding: 15px; margin-top: 20px; text-align: center; }}
        .summary-score {{ font-size: 32px; font-weight: bold; color: #f97316; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #999; }}
    </style></head><body>
    <div class="header">
        {f'<img src="{logo_data}" style="max-height:60px;margin-bottom:10px;" /><br/>' if logo_data else ''}
        <div class="event-name">{event_name}</div>
        {f'<div class="event-date">{event_date}</div>' if event_date else ''}
    </div>
    <div class="competitor-info">
        <span class="competitor-number">#{competitor.get('car_number', '?')}</span>
        <strong>{competitor.get('name', 'Unknown')}</strong><br/>
        <span style="color:#666;">Vehicle: {competitor.get('vehicle_info', 'N/A')} | Class: {class_name}</span>
    </div>"""
    
    total_scores = []
    minor_round_scores = []  # Only scores from minor rounds for grand total
    
    for rid, round_scores in scores_by_round.items():
        round_info = rounds_dict.get(rid, {})
        round_name = round_info.get("name", "Unknown Round")
        is_minor = round_info.get("is_minor", False)
        
        html += f'<div class="round-section"><div class="round-header">{round_name}{" (Minor Round)" if is_minor else ""}</div><table><tr><th>Category</th>'
        # Number judges as Judge 1, Judge 2, etc.
        for idx, score in enumerate(round_scores, start=1):
            html += f'<th style="font-size:11px;">Judge {idx}</th>'
        html += '</tr>'
        
        categories = [("Tip In", "tip_in"), ("Instant Smoke", "instant_smoke"), ("Constant Smoke", "constant_smoke"),
                      ("Volume of Smoke", "volume_of_smoke"), ("Driving Skill", "driving_skill"), ("Tyres Popped", "tyres_popped")]
        for cat_name, cat_key in categories:
            html += f'<tr><td>{cat_name}</td>'
            for score in round_scores:
                html += f'<td>{score.get(cat_key, 0)}</td>'
            html += '</tr>'
        
        # Penalty breakdown - show individual penalties
        penalty_types = [
            ("Reversing (-5)", "penalty_reversing"),
            ("Stopping (-5)", "penalty_stopping"),
            ("Contact Barrier (-5)", "penalty_contact_barrier"),
            ("Small Fire (-5)", "penalty_small_fire"),
            ("Failed Drive Off (-10)", "penalty_failed_drive_off"),
            ("Large Fire (-10)", "penalty_large_fire")
        ]
        
        html += '<tr style="background:#fef2f2;"><td colspan="100%" style="font-weight:bold;color:#dc2626;padding-top:10px;">Penalties</td></tr>'
        
        for penalty_name, penalty_key in penalty_types:
            # Check if any judge applied this penalty
            has_penalty = any(score.get(penalty_key, 0) > 0 for score in round_scores)
            if has_penalty:
                html += f'<tr style="background:#fef2f2;"><td style="padding-left:20px;color:#991b1b;">{penalty_name}</td>'
                for score in round_scores:
                    penalty_val = score.get(penalty_key, 0)
                    if penalty_val > 0:
                        html += f'<td style="color:#dc2626;">-{penalty_val}</td>'
                    else:
                        html += '<td style="color:#999;">-</td>'
                html += '</tr>'
        
        # Show disqualified status if any
        has_dq = any(score.get("penalty_disqualified", False) for score in round_scores)
        if has_dq:
            html += '<tr style="background:#fef2f2;"><td style="padding-left:20px;color:#991b1b;font-weight:bold;">DISQUALIFIED</td>'
            for score in round_scores:
                if score.get("penalty_disqualified", False):
                    html += '<td style="color:#dc2626;font-weight:bold;">YES</td>'
                else:
                    html += '<td style="color:#999;">-</td>'
            html += '</tr>'
        
        # Penalty total row
        html += '<tr style="background:#fef2f2;border-top:1px solid #fca5a5;"><td style="font-weight:bold;">Total Penalties</td>'
        for score in round_scores:
            html += f'<td style="color:#dc2626;font-weight:bold;">-{score.get("penalty_total", 0)}</td>'
        html += '</tr>'
        
        html += '<tr class="total-row"><td>Final Score</td>'
        for score in round_scores:
            final = score.get("final_score", 0)
            total_scores.append(final)
            if score.get("penalty_disqualified"):
                html += '<td style="color:#dc2626;">0 (DQ)</td>'
            else:
                html += f'<td>{final}</td>'
        html += '</tr></table>'
        
        # Add round summary (total and average for this round)
        round_total = sum(total_scores[-len(round_scores):])  # Only scores from this round
        round_avg = round_total / len(round_scores) if round_scores else 0
        html += f'''<div style="background:#f0fdf4;padding:10px;text-align:right;border-top:2px solid #22c55e;">
            <strong>Round Total: {round_total:.1f}</strong> &nbsp;|&nbsp; Average: {round_avg:.2f}
        </div></div>'''
    
    # Only show overall summary if multiple rounds
    if len(scores_by_round) > 1 and total_scores:
        html += f'''<div class="summary-box">
            <div>Overall Total: <span class="summary-score">{sum(total_scores)}</span></div>
            <div style="color:#666;margin-top:5px;">Overall Average: {sum(total_scores)/len(total_scores):.2f} (from {len(scores_by_round)} round(s))</div>
        </div>'''
    
    html += f'<div class="footer">Generated on {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}<br/>{website_url}</div></body></html>'
    
    return {"html": html, "competitor": competitor, "event_name": event_name}, None

@api_router.post("/admin/send-bulk-emails")
async def send_bulk_emails(request: BulkEmailRequest, admin: User = Depends(require_admin)):
    """Send score report emails to multiple competitors"""
    # Get SMTP settings
    smtp_settings = await db.settings.find_one({"key": "smtp"}, {"_id": 0})
    if not smtp_settings or not smtp_settings.get("smtp_server"):
        raise HTTPException(status_code=400, detail="SMTP not configured")
    
    results = {"sent": [], "failed": []}
    
    # Connect to SMTP server once for all emails
    try:
        port = smtp_settings.get("smtp_port", 587)
        use_tls = smtp_settings.get("smtp_use_tls", True)
        
        if port == 465 or not use_tls:
            server = smtplib.SMTP_SSL(smtp_settings["smtp_server"], port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_settings["smtp_server"], port, timeout=30)
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
        
        server.login(smtp_settings["smtp_email"], smtp_settings["smtp_password"])
        
        for item in request.competitor_emails:
            competitor_id = item.get("competitor_id")
            recipient_email = item.get("recipient_email")
            round_id = item.get("round_id")  # The newly completed round that triggered this email
            
            if not competitor_id or not recipient_email:
                results["failed"].append({"competitor_id": competitor_id, "error": "Missing data"})
                continue
            
            try:
                # Generate email content including ALL completed rounds for this competitor
                email_data, error = await generate_competitor_email_html(
                    competitor_id, 
                    round_id=None,  # Don't filter by specific round
                    include_all_completed=True  # Include all rounds where all judges have scored
                )
                if error:
                    results["failed"].append({"competitor_id": competitor_id, "error": error})
                    continue
                
                competitor = email_data["competitor"]
                event_name = email_data["event_name"]
                
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"Burnout Scores - #{competitor.get('car_number', '?')} {competitor.get('name', '')} - {event_name}"
                msg['From'] = smtp_settings["smtp_email"]
                msg['To'] = recipient_email
                
                # Use base64 encoding to avoid line length issues
                html_part = MIMEText(email_data["html"], 'html', 'utf-8')
                html_part.replace_header('Content-Transfer-Encoding', 'base64')
                msg.attach(html_part)
                
                server.sendmail(smtp_settings["smtp_email"], recipient_email, msg.as_string())
                
                # Mark only the newly completed round as emailed (not all rounds)
                # This allows future completed rounds to trigger new emails
                if round_id:
                    await db.scores.update_many(
                        {"competitor_id": competitor_id, "round_id": round_id},
                        {"$set": {"email_sent": True}}
                    )
                
                results["sent"].append({"competitor_id": competitor_id, "email": recipient_email, "name": competitor.get("name")})
            except Exception as e:
                results["failed"].append({"competitor_id": competitor_id, "error": str(e)})
        
        server.quit()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP connection failed: {str(e)}")
    
    return {
        "message": f"Sent {len(results['sent'])} emails, {len(results['failed'])} failed",
        "sent": results["sent"],
        "failed": results["failed"]
    }

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_db():
    # Create default admin if not exists
    admin = await db.users.find_one({"username": "admin"})
    if not admin:
        default_admin = User(
            username="admin",
            name="Administrator",
            role="admin"
        )
        doc = default_admin.model_dump()
        doc["password_hash"] = bcrypt.hash("admin123")
        doc['created_at'] = doc['created_at'].isoformat()
        await db.users.insert_one(doc)
        logger.info("Default admin created: username=admin, password=admin123")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()