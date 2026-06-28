from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api.routes import router

app = FastAPI(
    title="SENTINEL API",
    description="Nepal Migrant Worker Intelligence System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"status": "SENTINEL is running"}