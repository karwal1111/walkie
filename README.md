# Walkie – push-to-talk (FastAPI + WebSocket)

## Run locally
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8000
Open http://localhost:8000 on two devices/tabs, enter the same group code, hold the button.

## Deploy
Microphone access needs HTTPS (localhost is exempt). Put it behind HTTPS (Caddy, nginx, Render, Fly.io, Railway).
Docker: `docker build -t walkie . && docker run -p 8000:8000 walkie`
Reverse proxy must allow WebSocket upgrade on /ws.

## Protocol (JSON over /ws)
Client -> server: {t:"join",g} | {t:"leave",g} | {t:"v",gs:[groups],f:name,m:mime,d:base64}
Server -> client: {t:"peers",g,n} | {t:"v",gs,f,m,d} | {t:"ack",n}
Sending to several groups in "gs" is the broadcast feature.

## Limits / next steps
In-memory state = single process only (use Redis pub/sub to scale). No auth, history or push notifications yet.
