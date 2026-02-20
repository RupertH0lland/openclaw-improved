"""FastAPI dashboard - login, chat, message log."""
import asyncio
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from starlette.middleware.sessions import SessionMiddleware

from src.config import load_config
from src.integrations.dashboard_api import get_orchestrator, get_message_bus

ROOT = Path(__file__).parent.parent.parent
config_dir = ROOT / "config"
static_dir = ROOT / "src" / "dashboard" / "static"
templates_dir = ROOT / "src" / "dashboard" / "templates"

static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="AI Orchestrator Dashboard")
app.add_middleware(SessionMiddleware, secret_key="ai-orchestrator-secret-change-in-production")
templates = Jinja2Templates(directory=str(templates_dir))


def _get_password_hash() -> str | None:
    """Read password hash from settings."""
    settings_path = config_dir / "settings.yaml"
    if not settings_path.exists():
        return None
    import yaml
    with open(settings_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    dash = data.get("dashboard", {})
    return dash.get("password_hash") or None


def _verify_password(plain: str) -> bool:
    h = _get_password_hash()
    if not h:
        return True
    return pwd_ctx.verify(plain, h)


async def require_auth(request: Request) -> bool:
    """Check session for auth."""
    if not _get_password_hash():
        return True
    return request.session.get("authenticated", False)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _get_password_hash() is None:
        return HTMLResponse(
            "<script>window.location.href='/';</script><p>No password set. Redirecting...</p>"
        )
    if request.session.get("authenticated"):
        return HTMLResponse("<script>window.location.href='/';</script>")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if _verify_password(password):
        request.session["authenticated"] = True
        return HTMLResponse(
            "<script>window.location.href='/';</script><p>Logged in. Redirecting...</p>"
        )
    raise HTTPException(status_code=401, detail="Invalid password")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return HTMLResponse("<script>window.location.href='/login';</script>")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if _get_password_hash() and not request.session.get("authenticated"):
        return HTMLResponse("<script>window.location.href='/login';</script>")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/memory")
async def api_memory(request: Request, q: str = "", n: int = 5):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    orch = get_orchestrator(ROOT)
    if not q:
        return {"results": []}
    results = orch._memory.search(q, n_results=n)
    return {"results": [{"content": r["content"]} for r in results]}


@app.post("/api/memory")
async def api_memory_add(request: Request, text: str = Form(default="")):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text")
    orch = get_orchestrator(ROOT)
    orch._memory.add_fact(text)
    return {"ok": True}


@app.get("/api/cost")
async def api_cost(request: Request):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    orch = get_orchestrator(ROOT)
    ct = orch._cost_tracker
    return {"daily_usd": ct.get_daily_total(), "monthly_usd": ct.get_monthly_total()}


@app.get("/api/files")
async def api_files_list(request: Request, path: str = ""):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    orch = get_orchestrator(ROOT)
    out_dir = orch.output_dir
    if not out_dir.exists():
        return {"files": []}
    items = []
    target = out_dir / path if path else out_dir
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")
    for child in sorted(target.iterdir()):
        items.append({
            "name": child.name,
            "is_dir": child.is_dir(),
            "size": child.stat().st_size if child.is_file() else 0,
            "path": str(child.relative_to(out_dir)) if path else child.name,
        })
    return {"files": items, "base_path": str(out_dir)}


@app.get("/api/files/download/{filepath:path}")
async def api_files_download(request: Request, filepath: str):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from fastapi.responses import FileResponse
    orch = get_orchestrator(ROOT)
    full_path = (orch.output_dir / filepath).resolve()
    try:
        full_path.relative_to(orch.output_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full_path, filename=full_path.name)


@app.post("/api/screenshot")
async def api_screenshot(request: Request, url: str = Form(default="")):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    from src.tools.browser import take_screenshot
    orch = get_orchestrator(ROOT)
    out_path = orch.output_dir / "screenshots"
    import uuid
    fname = f"shot_{uuid.uuid4().hex[:8]}.png"
    path = out_path / fname
    await take_screenshot(url, path)
    from fastapi.responses import FileResponse
    return FileResponse(path, filename=fname)


@app.post("/api/config/apply")
async def api_config_apply(request: Request, config_file: str = Form(default="settings.yaml")):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    orch = get_orchestrator(ROOT)
    ok = orch._config_engine.apply_pending(config_file)
    return {"applied": ok}


@app.get("/api/skills")
async def api_skills(request: Request):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from src.orchestrator.config_engine import load_skills
    skills = load_skills(ROOT)
    return {"skills": [{"name": s.get("name"), "enabled": s.get("enabled", False)} for s in skills]}


@app.get("/api/health")
async def api_health(request: Request):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    import shutil
    import httpx
    orch = get_orchestrator(ROOT)
    health = {"orchestrator": "ok", "ollama": "disabled", "disk_free_gb": 0}
    from src.models.ollama_client import OllamaClient
    ollama = OllamaClient(ROOT)
    if ollama.enabled:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{ollama.base_url}/api/tags")
                health["ollama"] = "ok" if r.status_code == 200 else "error"
        except Exception:
            health["ollama"] = "unreachable"
    try:
        health["disk_free_gb"] = round(shutil.disk_usage(ROOT).free / (1024**3), 2)
    except Exception:
        pass
    return health


@app.get("/api/cron")
async def api_cron_list(request: Request):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    import sys
    if sys.platform == "win32":
        return {"jobs": [], "note": "crontab not available on Windows"}
    try:
        import subprocess
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        jobs = r.stdout.strip().splitlines() if r.returncode == 0 else []
    except Exception:
        jobs = []
    return {"jobs": jobs}


@app.post("/api/cron")
async def api_cron_add(request: Request, expr: str = Form(...), cmd: str = Form(...)):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    import sys
    if sys.platform == "win32":
        raise HTTPException(status_code=501, detail="crontab not available on Windows")
    try:
        import subprocess
        current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        lines = current.stdout.splitlines() if current.returncode == 0 else []
        lines.append(f"{expr} {cmd}")
        subprocess.run(["crontab", "-"], input="\n".join(lines), text=True, check=True)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/webhook")
async def api_webhook(request: Request):
    """External trigger endpoint. Opt-in. Send JSON body."""
    from src.integrations.webhooks import dispatch
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    await dispatch(payload)
    return {"ok": True}


@app.get("/api/audit/export")
async def api_audit_export(request: Request):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    import io
    orch = get_orchestrator(ROOT)
    bus = get_message_bus(ROOT)
    msgs = bus.get_recent(limit=10000)
    lines = ["timestamp,source,target,role,content\n"]
    for m in reversed(msgs):
        content = (m.get("content") or "").replace('"', '""')
        lines.append(f'"{m["timestamp"]}","{m["source"]}","{m["target"]}","{m["role"]}","{content}"\n')
    from fastapi.responses import Response
    return Response(
        content="".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
    )


@app.get("/api/digest")
async def api_digest(request: Request):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from src.scheduler.digest import generate_digest
    digest = await generate_digest(ROOT)
    return {"digest": digest}


@app.get("/api/agents")
async def api_agents(request: Request):
    """Agent registry: active, status."""
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    orch = get_orchestrator(ROOT)
    agents = []
    if orch.settings.use_subagents:
        r = orch.router
        for aid, agent in r._agents.items():
            agents.append({"id": aid, "status": agent.status})
    return {"agents": agents}


@app.get("/api/messages")
async def api_messages(request: Request, limit: int = 100, source: str | None = None):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    bus = get_message_bus(ROOT)
    msgs = bus.get_recent(limit=limit, source=source)
    return {"messages": msgs}


@app.post("/api/chat")
async def api_chat(request: Request, message: str = Form(...)):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    orch = get_orchestrator(ROOT)
    full = ""
    async for tok in orch.process(message, source="dashboard", stream=True):
        full += tok
    return {"response": full or "(No response)"}


@app.get("/api/chat/stream")
async def api_chat_stream(request: Request, message: str = ""):
    if _get_password_hash() and not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not message:
        raise HTTPException(status_code=400, detail="Missing message")

    orch = get_orchestrator(ROOT)

    async def stream():
        async for token in orch.process(message, source="dashboard", stream=True):
            yield f"data: {repr(token)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
    )
