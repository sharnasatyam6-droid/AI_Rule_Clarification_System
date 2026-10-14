from __future__ import annotations
import hashlib, hmac, json, os, re, time
from pathlib import Path
from typing import Any
from uuid import UUID
import psycopg
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
COOKIE = "rulebook_admin"
SESSION_SECONDS = 8 * 60 * 60
app = FastAPI(title="Rulebook Policy Clarity API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("APP_ORIGIN", "http://localhost:8000")], allow_credentials=True, allow_methods=["GET","POST","PATCH","DELETE"], allow_headers=["Content-Type"])
app.mount("/assets", StaticFiles(directory=PUBLIC / "assets"), name="assets")

def connect():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url: raise HTTPException(503, "Database is not configured. Set DATABASE_URL.")
    return psycopg.connect(url, connect_timeout=8)

def sign(payload: str) -> str:
    return hmac.new(os.getenv("ADMIN_SESSION_SECRET","").encode(), payload.encode(), hashlib.sha256).hexdigest()

def is_admin(request: Request) -> bool:
    token = request.cookies.get(COOKIE, "")
    if "." not in token: return False
    payload, supplied = token.rsplit(".", 1)
    secret = os.getenv("ADMIN_SESSION_SECRET", "")
    if len(secret) < 32 or not hmac.compare_digest(supplied, sign(payload)): return False
    try:
        data = json.loads(bytes.fromhex(payload).decode())
        return data.get("u") == os.getenv("ADMIN_USERNAME") and int(data.get("exp",0)) > int(time.time())
    except (ValueError, TypeError, json.JSONDecodeError): return False

def require_admin(request: Request):
    if not is_admin(request): raise HTTPException(401, "Admin sign-in required.")

def rows(cur):
    names = [d.name for d in cur.description]
    result = []
    for row in cur.fetchall():
        item = dict(zip(names,row))
        for key,value in item.items():
            if hasattr(value,"isoformat"): item[key] = value.isoformat()
            elif isinstance(value,UUID): item[key] = str(value)
        result.append(item)
    return result

class Login(BaseModel):
    username: str = Field(min_length=1,max_length=120)
    password: str = Field(min_length=1,max_length=256)
class TeacherInput(BaseModel):
    display_name: str = Field(min_length=2,max_length=120)
    email: str = Field(default="",max_length=254)
    @field_validator("display_name")
    @classmethod
    def clean_name(cls,v): return " ".join(v.split()).strip()
class PolicyInput(BaseModel):
    teacher_id: UUID
    title: str = Field(min_length=4,max_length=120)
    subject: str = Field(min_length=2,max_length=100)
    category: str
    summary: str = Field(min_length=10,max_length=280)
    policy_text: str = Field(min_length=20,max_length=20000)
    conditions: str = Field(default="",max_length=5000)
    status: str = "draft"
    @field_validator("category")
    @classmethod
    def check_category(cls,v):
        if v not in {"allowed_with_conditions","limited_use","not_allowed_for_specified_work"}: raise ValueError("Invalid policy category.")
        return v
    @field_validator("status")
    @classmethod
    def check_status(cls,v):
        if v not in {"draft","published"}: raise ValueError("Status must be draft or published.")
        return v
class CheckInput(BaseModel):
    policy_id: UUID
    scenario_id: str = Field(default="",max_length=80)
    scenario_text: str = Field(default="",max_length=1500)

SCENARIOS = [
 {"id":"brainstorm","title":"Brainstorming ideas","description":"I want to use AI to brainstorm ideas before starting my assignment."},
 {"id":"debug","title":"Debugging my own code","description":"I wrote my own program and want AI to explain a bug."},
 {"id":"generated-work","title":"Submitting AI-generated work","description":"I want to submit AI-generated code or writing as my own work."},
 {"id":"assessment","title":"Using AI during an assessment","description":"I want to use AI while completing a quiz, test, or exam."},
 {"id":"proofreading","title":"Proofreading and grammar","description":"I want AI to check grammar and clarity in my own writing."}
]

@app.get("/")
def home(): return FileResponse(PUBLIC / "index.html")
@app.get("/health")
def health(): return {"status":"ok","service":"rulebook-fastapi"}
@app.get("/api/scenarios")
def scenarios(): return {"scenarios":SCENARIOS}

@app.get("/api/policies")
def policies(q: str="", subject: str="", category: str=""):
    where=["p.status='published'"]; params=[]
    if q.strip():
        where.append("(p.title ILIKE %s OR p.subject ILIKE %s OR p.summary ILIKE %s OR t.display_name ILIKE %s)")
        term="%"+q.strip()[:100]+"%"; params.extend([term,term,term,term])
    if subject.strip(): where.append("p.subject=%s"); params.append(subject.strip()[:100])
    if category.strip(): where.append("p.category=%s"); params.append(category.strip()[:50])
    sql="""SELECT p.id,p.title,p.subject,p.category,p.summary,p.conditions,p.policy_text,p.updated_at,t.display_name AS teacher_name,
    CASE WHEN p.policy_text ILIKE 'DEMONSTRATION ONLY%' THEN true ELSE false END AS is_demo
    FROM policies p JOIN teachers t ON t.id=p.teacher_id WHERE """+" AND ".join(where)+" ORDER BY p.updated_at DESC LIMIT 100"
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute(sql,params); return {"policies":rows(cur)}
    except HTTPException: raise
    except Exception: raise HTTPException(503,"Could not load policies. Check DATABASE_URL and db/schema.sql.")

@app.get("/api/policies/{policy_id}")
def policy_detail(policy_id: UUID):
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT p.id,p.title,p.subject,p.category,p.summary,p.conditions,p.policy_text,p.updated_at,t.display_name AS teacher_name,
            CASE WHEN p.policy_text ILIKE 'DEMONSTRATION ONLY%' THEN true ELSE false END AS is_demo
            FROM policies p JOIN teachers t ON t.id=p.teacher_id WHERE p.id=%s AND p.status='published'""",(str(policy_id),))
            result=rows(cur)
            if not result: raise HTTPException(404,"Published policy not found.")
            return result[0]
    except HTTPException: raise
    except Exception: raise HTTPException(503,"Could not load this policy.")

@app.post("/api/check")
def check(body: CheckInput):
    scenario=next((s for s in SCENARIOS if s["id"]==body.scenario_id),None)
    question=body.scenario_text.strip() or (scenario["description"] if scenario else "")
    if len(question)<8: raise HTTPException(422,"Choose a scenario or describe your situation.")
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT p.id,p.title,p.subject,p.policy_text,p.conditions,t.display_name
            FROM policies p JOIN teachers t ON t.id=p.teacher_id WHERE p.id=%s AND p.status='published'""",(str(body.policy_id),))
            row=cur.fetchone()
            if not row: raise HTTPException(404,"Choose a published policy.")
    except HTTPException: raise
    except Exception: raise HTTPException(503,"Policy analysis is temporarily unavailable. Please retry.")
    pid,title,subject,policy_text,conditions,teacher=row
    full=(policy_text+"\n"+(conditions or "")).strip()
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",full) if len(s.strip())>=12]
    stop={"want","with","from","that","this","have","using","while","into","about","work","would","could","should","will","your","their","before","after","assignment","policy"}
    words=set(re.findall(r"[a-zA-Z]{4,}",question.lower()))-stop
    ranked=[]
    for sentence in sentences:
        tokens=set(re.findall(r"[a-zA-Z]{4,}",sentence.lower()))-stop
        score=len(words & tokens)
        if score: ranked.append((score,sentence))
    ranked.sort(key=lambda x:x[0],reverse=True)
    evidence=ranked[0][1] if ranked else ""
    low=full.lower(); q=question.lower()
    prohibit=bool(re.search(r"\b(not permitted|not allowed|prohibit|prohibited|must not|do not use|cannot use|may not|forbidden|independent work)\b",low))
    permit=bool(re.search(r"\b(may use|can use|permitted|allowed|may be used|can help|may help|may explain)\b",low))
    overlap=bool(evidence and words & set(re.findall(r"[a-zA-Z]{4,}",evidence.lower())))
    outcome="unclear"; reason="The selected policy does not provide sufficiently specific evidence for this situation. Ask the instructor before relying on an interpretation."
    if evidence and overlap and prohibit and re.search(r"\b(submit|assessment|exam|quiz|test|generate|generated|answer|independent|own work)\b",q):
        outcome="not_allowed"; reason="The selected policy contains an explicit restriction relevant to this situation."
    elif evidence and overlap and permit and re.search(r"\b(brainstorm|debug|explain|proofread|grammar|outline|practice|concept|ideas)\b",q):
        outcome="allowed"; reason="The selected policy explicitly describes a permitted use relevant to this situation. Follow any stated conditions."
    return {"outcome":outcome,"outcome_label":{"allowed":"Allowed by the provided policy","not_allowed":"Not allowed by the provided policy","unclear":"Unclear — Ask the Instructor"}[outcome],
    "reason":reason,"policy":{"id":str(pid),"title":title,"subject":subject,"teacher_name":teacher},"evidence_excerpt":evidence or None,
    "conditions":conditions or None,"source_note":"Demonstration policy — not an official college rule." if str(policy_text).startswith("DEMONSTRATION ONLY") else "Source: the selected published policy.",
    "question":question,"disclaimer":"This is a policy-navigation aid, not an official ruling. Missing or ambiguous text is not proof of permission."}

@app.post("/api/admin/login")
def admin_login(body: Login,response: Response):
    username=os.getenv("ADMIN_USERNAME",""); password=os.getenv("ADMIN_PASSWORD",""); secret=os.getenv("ADMIN_SESSION_SECRET","")
    if not username or not password or len(secret)<32: raise HTTPException(503,"Admin login is not configured in deployment environment.")
    if not hmac.compare_digest(body.username,username) or not hmac.compare_digest(body.password,password): raise HTTPException(401,"Incorrect admin username or password.")
    payload=json.dumps({"u":username,"exp":int(time.time())+SESSION_SECONDS},separators=(",",":")).encode().hex()
    response.set_cookie(COOKIE,payload+"."+sign(payload),httponly=True,secure=os.getenv("VERCEL")=="1" or os.getenv("ENVIRONMENT")=="production",samesite="strict",max_age=SESSION_SECONDS,path="/")
    return {"ok":True}
@app.post("/api/admin/logout")
def admin_logout(response: Response):
    response.delete_cookie(COOKIE,path="/",httponly=True,samesite="strict"); return {"ok":True}
@app.get("/api/admin/session")
def admin_session(request: Request): return {"authenticated":is_admin(request)}

@app.get("/api/admin/teachers")
def admin_teachers(request: Request,q: str=""):
    require_admin(request)
    try:
        with connect() as conn, conn.cursor() as cur:
            term="%"+q.strip()[:100]+"%"
            cur.execute("SELECT id,display_name,email,approved,created_at FROM teachers WHERE display_name ILIKE %s OR email ILIKE %s ORDER BY display_name LIMIT 100",(term,term))
            return {"teachers":rows(cur)}
    except Exception: raise HTTPException(503,"Could not load teacher profiles. Check database schema.")

@app.post("/api/admin/teachers")
def add_teacher(body: TeacherInput,request: Request):
    require_admin(request); email=body.email.strip().lower()
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email): raise HTTPException(422,"Enter a valid email address or leave it blank.")
    if not email: email="no-email+"+os.urandom(8).hex()+"@rulebook.invalid"
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO teachers(display_name,email,approved) VALUES(%s,%s,true) RETURNING id,display_name,email,approved,created_at",(body.display_name,email))
            return rows(cur)[0]
    except psycopg.errors.UniqueViolation: raise HTTPException(409,"A teacher with this email already exists.")
    except Exception: raise HTTPException(503,"Could not add teacher.")

@app.get("/api/admin/policies")
def admin_policies(request: Request,teacher_id: str=""):
    require_admin(request)
    try:
        with connect() as conn, conn.cursor() as cur:
            if teacher_id:
                cur.execute("""SELECT p.id,p.teacher_id,p.title,p.subject,p.category,p.summary,p.policy_text,p.conditions,p.status,p.updated_at,t.display_name AS teacher_name
                FROM policies p JOIN teachers t ON t.id=p.teacher_id WHERE p.teacher_id=%s ORDER BY p.updated_at DESC""",(teacher_id,))
            else:
                cur.execute("""SELECT p.id,p.teacher_id,p.title,p.subject,p.category,p.summary,p.policy_text,p.conditions,p.status,p.updated_at,t.display_name AS teacher_name
                FROM policies p JOIN teachers t ON t.id=p.teacher_id ORDER BY p.updated_at DESC LIMIT 200""")
            return {"policies":rows(cur)}
    except Exception: raise HTTPException(503,"Could not load policies.")

@app.post("/api/admin/policies")
def create_policy(body: PolicyInput,request: Request):
    require_admin(request)
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM teachers WHERE id=%s",(str(body.teacher_id),))
            if not cur.fetchone(): raise HTTPException(404,"Select an existing teacher.")
            cur.execute("""INSERT INTO policies(teacher_id,title,subject,category,summary,policy_text,conditions,status)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id,teacher_id,title,subject,category,summary,policy_text,conditions,status,updated_at""",
            (str(body.teacher_id),body.title.strip(),body.subject.strip(),body.category,body.summary.strip(),body.policy_text.strip(),body.conditions.strip(),body.status))
            return rows(cur)[0]
    except HTTPException: raise
    except Exception: raise HTTPException(503,"Could not create policy.")

@app.patch("/api/admin/policies/{policy_id}")
def update_policy(policy_id: UUID,body: PolicyInput,request: Request):
    require_admin(request)
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("""UPDATE policies SET teacher_id=%s,title=%s,subject=%s,category=%s,summary=%s,policy_text=%s,conditions=%s,status=%s,updated_at=now()
            WHERE id=%s RETURNING id,teacher_id,title,subject,category,summary,policy_text,conditions,status,updated_at""",
            (str(body.teacher_id),body.title.strip(),body.subject.strip(),body.category,body.summary.strip(),body.policy_text.strip(),body.conditions.strip(),body.status,str(policy_id)))
            result=rows(cur)
            if not result: raise HTTPException(404,"Policy not found.")
            return result[0]
    except HTTPException: raise
    except Exception: raise HTTPException(503,"Could not update policy.")

@app.delete("/api/admin/policies/{policy_id}")
def delete_policy(policy_id: UUID,request: Request):
    require_admin(request)
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM policies WHERE id=%s RETURNING id",(str(policy_id),))
            if not cur.fetchone(): raise HTTPException(404,"Policy not found.")
            return {"ok":True}
    except HTTPException: raise
    except Exception: raise HTTPException(503,"Could not delete policy.")
