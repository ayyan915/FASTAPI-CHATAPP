# SecureChat

A real-time 1:1 chat app built with **FastAPI**, **SQLAlchemy**, and **WebSockets**. Users register with a unique `@name_tag`, add friends by tag, and exchange messages live over a WebSocket connection, with full chat history stored in the database.

## Features

- Email/username registration and login with hashed passwords (`pwdlib`, Argon2)
- JWT stored in an HTTP-only cookie for session auth
- Add friends by `@name_tag`
- Real-time messaging over a single shared WebSocket (`/wss`)
- Persisted chat history per friend pair
- Server-rendered UI with Jinja2 templates (login, register, friends list, chat)

## Tech stack

| Layer      | Tool                          |
|------------|-------------------------------|
| Framework  | FastAPI                       |
| Server     | Uvicorn                       |
| Database   | SQLAlchemy ORM + SQLite       |
| Auth       | PyJWT + pwdlib (Argon2 hash)  |
| Realtime   | FastAPI WebSockets            |
| Templates  | Jinja2                        |

## Project structure

```
.
├── app.py                # FastAPI app entrypoint, wires up routers + DB
├── sockets.py             # WebSocket endpoint (/wss) — messaging, friend list, chat history
├── model.py               # SQLAlchemy models: User, Message, Friends
├── database.py            # Engine, session, Base
├── routes/
│   ├── __init__.py
│   ├── auth.py            # /auth/register, /auth/login, /auth/logout
│   └── home.py             # /home/friends, /home/add_friend, /home/chat/{friend_tag}
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── friends.html
│   └── chat.html
├── requirements.txt
├── .gitignore
└── .env                    # not committed — holds SECRET_KEY
```

## Setup (local)

1. **Clone and enter the project**
   ```bash
   git clone <your-repo-url>
   cd <your-repo>
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**

   Create a `.env` file in the project root:
   ```
   SECRET_KEY=your-long-random-secret
   ```
   Generate one with:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

5. **Run the app**
   ```bash
   uvicorn app:app --reload
   ```
   The app will be available at `http://127.0.0.1:8000`. Tables are created automatically on startup (`Base.metadata.create_all`).

6. **Use it**
   - Go to `/auth/register` to create an account (display name must start with `@`).
   - Log in at `/auth/login` — you'll land on `/home/friends`.
   - Add a friend by their `@name_tag`, then open a chat to start messaging in real time.

## Environment variables

| Variable      | Description                                  |
|---------------|-----------------------------------------------|
| `SECRET_KEY`  | Secret used to sign JWT access tokens. Keep this private and never commit it. |

## Notes on the database

This project uses SQLite (`test.db`) by default, which is convenient for local development but **not safe for most hosting platforms with an ephemeral filesystem** (e.g. Render's free tier) — the file is wiped on every redeploy or restart. For production, point `SQLALCHEMY_DATABASE_URL` in `database.py` at a managed Postgres/MySQL instance, or attach a persistent disk.

## Deployment

Any ASGI-compatible host works (Render, Railway, Fly.io, etc.). Typical start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Make sure to:
- Set `SECRET_KEY` as an environment variable on the host (not in a committed `.env`).
- Use a persistent database (see above).
- Serve over HTTPS so cookies can be marked `secure`.

## License

Add a license of your choice here.
