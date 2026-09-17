from fastapi import Depends, WebSocket, WebSocketDisconnect, APIRouter
from database import get_db
from model import User, Message, Friends
from dotenv import load_dotenv
import jwt
import os

load_dotenv()
SECRET_KEY = str(os.getenv("SECRET_KEY"))
router = APIRouter(tags=["websocket"])
online_users = {}  # name_tag -> WebSocket
socket_to_user = {}  # websocket id -> name_tag


async def notify_friends_user_offline(db, disconnected_name_tag: str):
    user = db.query(User).filter(User.name_tag == disconnected_name_tag).first()
    if not user:
        return

    friend_links = db.query(Friends).filter(Friends.user_id == user.id).all()
    for link in friend_links:
        friend = db.query(User).filter(User.id == link.friend_id).first()
        if not friend:
            continue

        peer_ws = online_users.get(friend.name_tag)
        if peer_ws:
            try:
                await peer_ws.send_json({"type": "status", "status": "offline", "friend_name": disconnected_name_tag})
            except Exception:
                pass


@router.websocket("/wss")
async def websocket_endpoint(websocket: WebSocket, db=Depends(get_db)):
    # Read access token from cookies (browser will send cookies on same-origin ws/wss)
    access_token = None
    try:
        access_token = websocket.cookies.get("access_token")
    except Exception:
        access_token = None

    if not access_token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is None:
            await websocket.close(code=1008)
            return

        current_user = db.query(User).filter(User.id == user_id).first()
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008)
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    name_tag = current_user.name_tag if current_user else None
    if name_tag:
        online_users[name_tag] = websocket
        socket_to_user[id(websocket)] = name_tag
        friends_list = db.query(Friends).filter(Friends.user_id == current_user.id).all()
        for friend in friends_list:
            friend_obj = db.query(User).filter(User.id == friend.friend_id).first()
            if friend_obj:
                friend_socket = online_users.get(friend_obj.name_tag)
                if friend_socket:
                    await friend_socket.send_json({"type": "status", "status": "online", "friend_name": current_user.name_tag})

            
        


    try:
        while True:
            data = await websocket.receive_json()
            typ = data.get("type")

            # MESSAGE: send to recipient (by name_tag) and persist
            if typ == "message":
                receiver_tag = data.get("receiver")
                content = data.get("content")
                if receiver_tag and content:
                    recv_ws = online_users.get(receiver_tag)
                    if recv_ws:
                        await recv_ws.send_json({"type": "message", "sender": name_tag, "content": content})

                    receiver_user = db.query(User).filter_by(name_tag=receiver_tag).first()
                    if receiver_user:
                        message = Message(sender_id=current_user.id, receiver_id=receiver_user.id, content=content)
                        db.add(message)
                        db.commit()

                    await websocket.send_json({"type": "message_status", "status": "sent"})

            # FRIEND LIST: return friend name_tags
            elif typ == "friend_list":
                friend_links = db.query(Friends).filter_by(user_id=current_user.id).all()
                friends_list = []
                for link in friend_links:
                    friend_user = db.query(User).filter_by(id=link.friend_id).first()
                    if friend_user:
                        friends_list.append(friend_user.name_tag)
                await websocket.send_json({"type": "friend_list", "friends": friends_list})

            # CHAT HISTORY: provide messages between current_user and the given friend
            elif typ == "chat_history":
                other_tag = data.get("with")
                chat_history = []
                if other_tag:
                    other_user = db.query(User).filter_by(name_tag=other_tag).first()
                    if other_user:
                        messages = db.query(Message).filter(
                            ((Message.sender_id == current_user.id) & (Message.receiver_id == other_user.id)) |
                            ((Message.sender_id == other_user.id) & (Message.receiver_id == current_user.id))
                        ).order_by(Message.created_at.desc()).all()

                        # return in chronological order
                        for m in reversed(messages):
                            sender = db.query(User).filter_by(id=m.sender_id).first()
                            receiver = db.query(User).filter_by(id=m.receiver_id).first()
                            chat_history.append({
                                "sender": sender.name_tag if sender else str(m.sender_id),
                                "receiver": receiver.name_tag if receiver else str(m.receiver_id),
                                "content": m.content,
                                "created_at": m.created_at.isoformat() if m.created_at else None,
                            })

                await websocket.send_json({"type": "chat_history", "messages": chat_history})

            elif typ == "user_status":
                friend_user = db.query(User).filter(User.name_tag == data.get("username")).first()
                if friend_user:
                    is_friend = db.query(Friends).filter(
                        Friends.user_id == current_user.id,
                        Friends.friend_id == friend_user.id
                    ).first()
                    if is_friend and friend_user.name_tag in online_users:
                        await websocket.send_json({"type": "status", "status": "online", "friend_name": friend_user.name_tag})

    except WebSocketDisconnect:
        pass
    finally:
        
        tag = socket_to_user.pop(id(websocket), None)
        if tag:
            if online_users.get(tag) is websocket:
                online_users.pop(tag, None)
            await notify_friends_user_offline(db, tag)
        
