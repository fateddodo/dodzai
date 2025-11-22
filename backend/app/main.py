import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import tasks

logger = logging.getLogger(__name__)


@asynccontextmanager
def lifespan(app: FastAPI):
    logger.info("Creating database tables if they do not exist")
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Dodzai Tasks API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "dodzai"}
