from fastapi import FastAPI
from fastapi.responses import FileResponse
from backend.routers import leaseholders, charges
import os

app = FastAPI(title="Block Management API")

app.include_router(leaseholders.router)
app.include_router(charges.router)

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def serve_frontend():
    return FileResponse(frontend_path)
