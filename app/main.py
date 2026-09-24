from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import JSONResponse
import json

from app.agent import controller
from app.mcp_tools import MCP_TOOL_DEFINITIONS, STAGE_TOOLS
from app.traces import risk_color
from app.red_team import get_risk_breakdown

app = FastAPI(title="Zero Trust Agents Demo")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                pass


manager = ConnectionManager()


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/state")
async def get_state():
    state = controller.get_state()
    state["risk_color"] = risk_color(state["risk_score"])
    state["risk_breakdown"] = get_risk_breakdown(state["red_team_results"])
    return state


@app.get("/api/tools")
async def get_tools():
    return {
        "definitions": MCP_TOOL_DEFINITIONS,
        "stage_tools": STAGE_TOOLS,
    }


@app.post("/api/advance/{target_stage}")
async def advance_stage(target_stage: int):
    result = await controller.advance_stage(target_stage)
    if "error" in result:
        return JSONResponse(status_code=400, content=result)

    result["risk_color"] = risk_color(result.get("risk_score", 0))
    await manager.broadcast({"type": "stage_advance", "data": result})
    return result


@app.post("/api/red-team")
async def run_red_team():
    result = await controller.run_red_team()
    if "error" in result:
        return JSONResponse(status_code=400, content=result)

    result["risk_color"] = risk_color(result.get("risk_score", 0))
    result["risk_breakdown"] = get_risk_breakdown(controller.all_red_team)
    await manager.broadcast({"type": "red_team", "data": result})
    return result


@app.post("/api/reset")
async def reset():
    controller.reset()
    state = controller.get_state()
    state["risk_color"] = risk_color(0)
    state["risk_breakdown"] = {"file": 0, "web": 0, "code": 0}
    await manager.broadcast({"type": "reset", "data": state})
    return state


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "simulation"}
