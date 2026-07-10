from __future__ import annotations
import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class TaskRequest(BaseModel):
    task: str


def create_app(agent_loop, config) -> FastAPI:
    app = FastAPI(title="CodeReflex")
    _event_queue: asyncio.Queue = asyncio.Queue()

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return _TEMPLATES.TemplateResponse(request, "index.html")

    @app.post("/submit")
    async def submit(req: TaskRequest):
        session = await agent_loop.run(req.task)
        return JSONResponse({"session_id": session.id, "status": session.status.value})

    @app.get("/stream")
    async def stream(request: Request):
        async def event_generator():
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(_event_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        from fastapi.responses import StreamingResponse
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/approve/{rid}")
    async def approve(rid: str):
        agent_loop._hitl.approve(rid)
        return JSONResponse({"approved": rid})

    @app.post("/deny/{rid}")
    async def deny(rid: str):
        agent_loop._hitl.deny(rid)
        return JSONResponse({"denied": rid})

    return app
