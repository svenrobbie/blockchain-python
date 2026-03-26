# coding:utf-8
import sys
import os

web_dir = os.path.dirname(os.path.abspath(__file__))
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from api import wallet, chain, node, auth

app = FastAPI(
    title="Blockchain Python Web UI",
    description="Web interface for Blockchain Python",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(web_dir, "static")), name="static")

app.include_router(wallet.router)
app.include_router(chain.router)
app.include_router(node.router)
app.include_router(auth.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    with open(os.path.join(web_dir, "templates", "index.html"), "r") as f:
        return f.read()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    with open(os.path.join(web_dir, "templates", "index.html"), "r") as f:
        return f.read()


@app.get("/send", response_class=HTMLResponse)
async def send_page():
    with open(os.path.join(web_dir, "templates", "index.html"), "r") as f:
        return f.read()


@app.get("/history", response_class=HTMLResponse)
async def history_page():
    with open(os.path.join(web_dir, "templates", "index.html"), "r") as f:
        return f.read()


@app.get("/explorer", response_class=HTMLResponse)
async def explorer_page():
    with open(os.path.join(web_dir, "templates", "index.html"), "r") as f:
        return f.read()


@app.get("/wallet", response_class=HTMLResponse)
async def wallet_page():
    with open(os.path.join(web_dir, "templates", "index.html"), "r") as f:
        return f.read()


@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    with open(os.path.join(web_dir, "templates", "index.html"), "r") as f:
        return f.read()


@app.get("/api")
async def api_info():
    return {
        "name": "Blockchain Python API",
        "version": "1.0.0",
        "endpoints": {
            "wallet": "/api/wallet",
            "chain": "/api/chain",
            "node": "/api/node",
            "auth": "/api/auth"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
