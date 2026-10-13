from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db

db.init_db()

app = FastAPI(title="MindIsle 心屿后端", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "心屿后端运行成功"}

@app.get("/health")
def health():
    stats = db.get_stats()
    return {"status": "ok", "stats": stats}