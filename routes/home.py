from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from model import User, Friends
from sqlalchemy import or_
from database import get_db
from routes.auth import get_current_user

router = APIRouter(prefix="/home", tags=["home"])
templates = Jinja2Templates(directory="templates")


@router.get("/friends")
def friends(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Build friends list (name_tags) from Friends links for current user
    friend_links = db.query(Friends).filter_by(user_id=current_user.id).all()
    friends_list = []
    for link in friend_links:
        friend_user = db.query(User).filter_by(id=link.friend_id).first()
        if friend_user:
            friends_list.append(friend_user.name_tag)

    return templates.TemplateResponse(
        request=request,
        name="friends.html",
        context={"request": request, "current_user": current_user, "friends": friends_list},
    )


@router.post("/add_friend")
def add_friend(friend_name_tag: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    # normalize: allow users to submit with or without leading '@'
    normalized_tag = friend_name_tag.lstrip('@').strip()
    # match either stored tag with or without leading '@'
    friend_user = db.query(User).filter(
        or_(User.name_tag == normalized_tag, User.name_tag == ('@' + normalized_tag))
    ).first()
    if not friend_user:
            return {"error": "Friend not Found"}

    existing_link = db.query(Friends).filter_by(user_id=current_user.id, friend_id=friend_user.id).first()
    if existing_link:
        return {"error": "Friend already added"}

    new_link = Friends(user_id=current_user.id, friend_id=friend_user.id)
    db.add(new_link)
    db.commit()
    return {"message": "Friend added successfully"}



@router.get('/chat/{friend_tag}')
def chat(request: Request, friend_tag: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    friend_user = db.query(User).filter_by(name_tag=friend_tag).first()
    if not friend_user:
        return RedirectResponse(url="/home/friends", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"request": request, "current_user": current_user, "friend": friend_user},
    )


