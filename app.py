from fastapi import FastAPI
from routes.auth import router as auth_router
from routes.home import router as home_router
from sockets import router as socket_router
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
import model  # zaroori hai taake User model register ho jaye
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

Base.metadata.create_all(bind=engine)
app = FastAPI()
app.include_router(auth_router)
app.include_router(home_router)
app.include_router(socket_router)
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


@app.get("/sw.js")
async def service_worker():
    # Served at the root ("/sw.js"), not under /static/, so the browser
    # gives it scope "/" and it can control every page -- a service worker
    # served from /static/sw.js would only ever be allowed to control
    # /static/, not /home/friends, /home/chat/..., etc.
    return FileResponse("static/sw.js", media_type="text/javascript")