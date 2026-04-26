from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.routes import transfers, players, teams, health


app = FastAPI(
    title="Football Transfer Analysis API",
    description=(
        "API pentru analiza transferurilor de fotbal. "
        "Datele sunt încărcate din S3 (bucket pse-uab) și expuse prin endpoint-uri."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(transfers.router)
app.include_router(players.router)
app.include_router(teams.router)


@app.get("/", tags=["System"], summary="Root")
def root():
    return {
        "message": "Football Transfer Analysis API",
        "docs": "/docs",
        "health": "/health",
    }
