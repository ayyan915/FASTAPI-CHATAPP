from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from model import User
from database import get_db
from pydantic import BaseModel
from pwdlib import PasswordHash
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY = str(os.getenv("SECRET_KEY"))

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")
pwd_hash = PasswordHash.recommended()



class RegisterRequest(BaseModel):
    username: str = Form(..., min_length=3, max_length=50)
    password: str = Form(..., min_length=6)
    name_tag: str = Form(...)
    email: str = Form(...)


def create_access_token(user_id: int):
    payload = {
        "user_id": user_id,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Reads the access_token cookie set at login and returns the matching
    User, or None if there's no valid session. This is the piece that was
    missing before -- routes need a real way to know who's logged in."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()




@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"request": request})



@router.post("/register")
def register(
    username: str = Form(..., min_length=3, max_length=50),
    password: str = Form(..., min_length=6),
    name_tag: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    # Implementation for user registration
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    # Create new user
    new_user = User(
        username=username,
        password=pwd_hash.hash(password),
        email=email,
        name_tag=name_tag,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RedirectResponse(url="/", status_code=303)

@router.get("/")
def login_form(request: Request, current_user: User = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/home/friends", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})


@router.post("/")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_hash.verify(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(user.id)
    response = RedirectResponse(url="/home/friends", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax", secure=True)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response