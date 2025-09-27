
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from Controllers.get import get_router
from Controllers.optimizer import optimizer_router


asynccontextmanager
async def lifeSpan(app: FastAPI):
    print(f"Welcome to AWS Cost Optimizer")
    yield


app = FastAPI(title="AWS Cost Optimizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(optimizer_router, prefix="/optimizer", tags=["Optimizer"])
app.include_router(get_router, prefix="", tags=["Get Reports"])