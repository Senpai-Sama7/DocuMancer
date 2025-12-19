"""DocuMancer backend service"""
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

APP_NAME = "DocuMancer"
PORT = int(os.environ.get("DOCUMANCER_PORT", "4949"))
LOG_PATH = Path(os.environ.get("DOCUMANCER_LOG", "backend.log"))

logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.INFO)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
if not logger.handlers:
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())

app = FastAPI(title=APP_NAME, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConvertRequest(BaseModel):
    files: List[str] = Field(default_factory=list, description="Filesystem paths to convert")


class ConvertedFile(BaseModel):
    path: str
    name: str
    content: str
    encoding: str
    size_bytes: int


class ConvertResponse(BaseModel):
    results: List[ConvertedFile]


def _read_text(path: Path) -> ConvertedFile:
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read {path}: {exc}") from exc

    try:
        content = raw.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        content = raw.hex()
        encoding = "hex"

    return ConvertedFile(
        path=str(path.resolve()),
        name=path.name,
        content=content,
        encoding=encoding,
        size_bytes=len(raw),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/convert", response_model=ConvertResponse)
def convert(req: ConvertRequest) -> ConvertResponse:
    if not req.files:
        raise HTTPException(status_code=400, detail="No files provided")

    logger.info("Received conversion request for %d files", len(req.files))
    converted = [_read_text(Path(file_path)) for file_path in req.files]
    return ConvertResponse(results=converted)


def run():
    uvicorn.run(
        "backend.server:app",
        host="127.0.0.1",
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run()
