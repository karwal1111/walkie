import asyncio, json, re
from collections import defaultdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
groups = defaultdict(set)   # group code -> set of websockets
member = {}                 # websocket -> set of group codes
MAX_CLIP = 400_000          # max base64 chars per clip (~300 KB)
MAX_GROUPS = 20
MIMES = {"audio/webm;codecs=opus", "audio/webm", "audio/mp4"}

def clean(g):
    g = re.sub(r"[^a-z0-9-]", "", str(g or "").lower())[:24]
    return g or None

async def safe_send(ws, obj):
    try:
        await ws.send_text(json.dumps(obj))
    except Exception:
        pass

async def peers(g):
    n = len(groups[g])
    await asyncio.gather(*(safe_send(w, {"t": "peers", "g": g, "n": n}) for w in list(groups[g])))

async def leave(ws, g):
    groups[g].discard(ws)
    member[ws].discard(g)
    if groups[g]:
        await peers(g)
    else:
        groups.pop(g, None)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    member[ws] = set()
    try:
        while True:
            m = json.loads(await ws.receive_text())
            t = m.get("t")
            if t == "join":
                g = clean(m.get("g"))
                if g and g not in member[ws] and len(member[ws]) < MAX_GROUPS:
                    groups[g].add(ws); member[ws].add(g)
                    await peers(g)
            elif t == "leave":
                g = clean(m.get("g"))
                if g in member[ws]:
                    await leave(ws, g)
            elif t == "v":  # voice clip; also used for broadcast (several groups)
                d, mt = m.get("d"), m.get("m")
                if not isinstance(d, str) or len(d) > MAX_CLIP or mt not in MIMES:
                    continue
                targets = [g for g in (clean(x) for x in m.get("gs", [])) if g in member[ws]]
                per = defaultdict(list)  # recipient -> groups shared with sender
                for g in targets:
                    for w in groups[g]:
                        if w is not ws:
                            per[w].append(g)
                f = str(m.get("f") or "Anon")[:20]
                await asyncio.gather(*(safe_send(w, {"t": "v", "gs": gs, "f": f, "m": mt, "d": d})
                                       for w, gs in per.items()))
                await safe_send(ws, {"t": "ack", "n": len(per)})
    except (WebSocketDisconnect, ValueError, RuntimeError):
        pass
    finally:
        for g in list(member.get(ws, ())):
            await leave(ws, g)
        member.pop(ws, None)

@app.get("/")
async def index():
    return FileResponse("static/index.html")

app.mount("/", StaticFiles(directory="static"), name="static")
