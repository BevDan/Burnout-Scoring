from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request
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
from fastapi.responses import StreamingResponse

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

# Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    name: str
    role: str  # admin or judge
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CompetitorCreate(BaseModel):
    name: str
    car_number: str
    vehicle_info: str
    plate: str
    class_id: str

class CompetitorWithClass(BaseModel):
    id: str
    name: str
    car_number: str
    vehicle_info: str
    plate: str
    class_id: str
    class_name: str
    created_at: datetime

class Round(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    date: str
    status: str = "active"  # active or completed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RoundCreate(BaseModel):
    name: str
    date: str
    status: str = "active"

class Score(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    judge_id: str
    judge_name: str
    competitor_id: str
    round_id: str
    instant_smoke: int = 0  # 0-10
    constant_smoke: int = 0  # 0-20
    volume_of_smoke: int = 0  # 0-20
    driving_skill: int = 0  # 0-40
    tyres_popped: int = 0  # count (max 2)
    penalty_reversing: int = 0  # count
    penalty_stopping: int = 0  # count
    penalty_contact_barrier: int = 0  # count
    penalty_small_fire: int = 0  # count
    penalty_failed_drive_off: int = 0  # count
    penalty_large_fire: int = 0  # count
    score_subtotal: int = 0
    penalty_total: int = 0
    final_score: int = 0
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    edited_at: Optional[datetime] = None

class ScoreCreate(BaseModel):
    competitor_id: str
    round_id: str
    instant_smoke: int = 0
    constant_smoke: int = 0
    volume_of_smoke: int = 0
    driving_skill: int = 0
    tyres_popped: int = 0
    penalty_reversing: int = 0
    penalty_stopping: int = 0
    penalty_contact_barrier: int = 0
    penalty_small_fire: int = 0
    penalty_failed_drive_off: int = 0
    penalty_large_fire: int = 0

class ScoreUpdate(BaseModel):
    instant_smoke: Optional[int] = None
    constant_smoke: Optional[int] = None
    volume_of_smoke: Optional[int] = None
    driving_skill: Optional[int] = None
    tyres_popped: Optional[int] = None
    penalty_reversing: Optional[int] = None
    penalty_stopping: Optional[int] = None
    penalty_contact_barrier: Optional[int] = None
    penalty_small_fire: Optional[int] = None
    penalty_failed_drive_off: Optional[int] = None
    penalty_large_fire: Optional[int] = None

class ScoreWithDetails(BaseModel):
    id: str
    judge_id: str
    judge_name: str
    competitor_id: str
    competitor_name: str
    car_number: str
    round_id: str
    round_name: str
    instant_smoke: int
    constant_smoke: int
    volume_of_smoke: int
    driving_skill: int
    tyres_popped: int
    penalty_reversing: int
    penalty_stopping: int
    penalty_contact_barrier: int
    penalty_small_fire: int
    penalty_failed_drive_off: int
    penalty_large_fire: int
    score_subtotal: int
    penalty_total: int
    final_score: int
    submitted_at: datetime
    edited_at: Optional[datetime] = None

class LeaderboardEntry(BaseModel):
    competitor_id: str
    competitor_name: str
    car_number: str
    vehicle_info: str
    class_name: str
    average_score: float
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
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Auth routes
@api_router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user_data = await db.users.find_one({"username": request.username}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not bcrypt.verify(request.password, user_data["password_hash"]):
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
async def bulk_import_competitors(request: Request, admin: User = Depends(require_admin)):
    try:
        csv_data = await request.body()
        csv_data = csv_data.decode('utf-8')
        csv_file = io.StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        imported = 0
        
        for row in reader:
            competitor = Competitor(
                name=row.get('name', ''),
                car_number=row.get('car_number', ''),
                vehicle_info=row.get('vehicle_info', ''),
                plate=row.get('plate', ''),
                class_id=row.get('class_id', '')
            )
            doc = competitor.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.competitors.insert_one(doc)
            imported += 1
        
        return {"message": f"Imported {imported} competitors"}
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

@api_router.delete("/admin/competitors/{competitor_id}")
async def delete_competitor(competitor_id: str, admin: User = Depends(require_admin)):
    result = await db.competitors.delete_one({"id": competitor_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return {"message": "Competitor deleted"}

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
async def submit_score(score_create: ScoreCreate, current_user: User = Depends(get_current_user)):
    # Calculate scores
    score_subtotal = (
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
    
    final_score = score_subtotal - penalty_total
    
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

@api_router.get("/judge/scores", response_model=List[Score])
async def get_judge_scores(current_user: User = Depends(get_current_user)):
    scores = await db.scores.find({"judge_id": current_user.id}, {"_id": 0}).to_list(1000)
    for score in scores:
        if isinstance(score.get('submitted_at'), str):
            score['submitted_at'] = datetime.fromisoformat(score['submitted_at'])
    return scores

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
    
    # Calculate averages
    competitor_scores = {}
    for score in scores:
        comp_id = score["competitor_id"]
        if comp_id not in competitor_scores:
            competitor_scores[comp_id] = []
        competitor_scores[comp_id].append(score["final_score"])
    
    leaderboard = []
    for comp_id, score_list in competitor_scores.items():
        if comp_id not in competitors_dict:
            continue
        
        competitor = competitors_dict[comp_id]
        
        # Filter by class if specified
        if class_id and competitor["class_id"] != class_id:
            continue
        
        avg_score = sum(score_list) / len(score_list)
        leaderboard.append(LeaderboardEntry(
            competitor_id=comp_id,
            competitor_name=competitor["name"],
            car_number=competitor["car_number"],
            vehicle_info=competitor["vehicle_info"],
            class_name=classes_dict.get(competitor["class_id"], "Unknown"),
            average_score=round(avg_score, 2),
            score_count=len(score_list)
        ))
    
    # Sort by average score descending
    leaderboard.sort(key=lambda x: x.average_score, reverse=True)
    return leaderboard

# Export
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
        "Instant Smoke", "Constant Smoke", "Volume Smoke", "Driving Skill",
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
            score["judge_name"],
            score["instant_smoke"],
            score["constant_smoke"],
            score["volume_of_smoke"],
            score["driving_skill"],
            score["tyres_popped"],
            score["score_subtotal"],
            score["penalty_total"],
            score["final_score"],
            score["submitted_at"]
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=scores_round_{round_id}.csv"}
    )

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