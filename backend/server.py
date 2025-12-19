"""Minimal FastAPI wrapper for DocuMancer conversions."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
  host: str = Field("127.0.0.1", description="Bind host", validation_alias="DOCUMANCER_HOST")
  port: int = Field(8000, description="Bind port", validation_alias="DOCUMANCER_PORT")
  log_level: str = Field("INFO", description="Log level", validation_alias="DOCUMANCER_LOG_LEVEL")
  log_dir: Path = Field(default_factory=lambda: Path(os.environ.get("DOCUMANCER_LOG_DIR", "./logs")))

  @field_validator("log_dir")
  @classmethod
  def ensure_log_dir(cls, value: Path) -> Path:
    value.mkdir(parents=True, exist_ok=True)
    return value.resolve()


settings = Settings()


class JsonFormatter(logging.Formatter):
  def format(self, record: logging.LogRecord) -> str:  # noqa: D401
    base = {
      "level": record.levelname,
      "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
      "message": record.getMessage(),
      "logger": record.name,
    }
    if record.exc_info:
      base["exception"] = self.formatException(record.exc_info)
    if request_id := getattr(record, "request_id", None):
      base["request_id"] = request_id
    return json.dumps(base, ensure_ascii=False)


def configure_logging() -> logging.Logger:
  logger = logging.getLogger("documancer.server")
  logger.setLevel(settings.log_level.upper())

  stream_handler = logging.StreamHandler()
  stream_handler.setFormatter(JsonFormatter())

  file_handler = RotatingFileHandler(settings.log_dir / "server.log", maxBytes=2_000_000, backupCount=5)
  file_handler.setFormatter(JsonFormatter())

  logger.handlers.clear()
  logger.addHandler(stream_handler)
  logger.addHandler(file_handler)

  return logger


logger = configure_logging()
app = FastAPI(title="DocuMancer Backend", version="0.2.0")

SUPPORTED_SUFFIXES = {".txt", ".md", ".json"}


class ConvertRequest(BaseModel):
  files: List[Path] = Field(..., description="Absolute paths to files to convert")

  @field_validator("files", mode="before")
  @classmethod
  def ensure_list(cls, value: List[str] | str):
    if isinstance(value, str):
      return [value]
    return value

  @field_validator("files", mode="after")
  @classmethod
  def ensure_absolute(cls, value: List[Path]):
    normalized = []
    for item in value:
      path = Path(item).expanduser()
      if not path.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")
      normalized.append(path)
    return normalized


class ConversionResult(BaseModel):
  file: Path
  status: str
  message: str | None = None
  content: dict | None = None


@app.middleware("http")
async def request_context(request: Request, call_next):  # noqa: D401
  request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
  request.state.request_id = request_id
  start = time.perf_counter()
  try:
    response = await call_next(request)
  finally:
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
      json.dumps(
        {
          "path": request.url.path,
          "method": request.method,
          "duration_ms": duration_ms,
        }
      ),
      extra={"request_id": request_id},
    )
  response.headers["x-request-id"] = request_id
  return response


@app.get("/health")
async def health(request: Request):
  return {"status": "ok", "request_id": request.state.request_id}


def _extract_plain_text(path: Path) -> str:
  if not path.exists():
    raise FileNotFoundError(f"Missing file: {path}")

  if path.suffix.lower() in SUPPORTED_SUFFIXES:
    return path.read_text(encoding="utf-8", errors="ignore")

  raise ValueError(f"Unsupported format for lightweight converter: {path.suffix}")


@app.post("/convert")
async def convert(request: ConvertRequest, http_request: Request):
  if not request.files:
    raise HTTPException(status_code=400, detail="No files supplied for conversion")

  results: List[ConversionResult] = []

  for file_path in request.files:
    try:
      content = await asyncio.to_thread(_extract_plain_text, file_path)
      results.append(
        ConversionResult(
          file=file_path,
          status="ok",
          content={
            "path": str(file_path),
            "length": len(content),
            "preview": content[:400],
          },
        )
      )
    except FileNotFoundError as missing:
      logger.warning("File not found", extra={"request_id": http_request.state.request_id, "file": str(file_path)})
      results.append(ConversionResult(file=file_path, status="error", message=str(missing)))
    except ValueError as exc:
      logger.warning("Unsupported format", extra={"request_id": http_request.state.request_id, "file": str(file_path)})
      results.append(ConversionResult(file=file_path, status="error", message=str(exc)))
    except Exception as exc:  # noqa: BLE001
      logger.exception("Failed to convert file", extra={"request_id": http_request.state.request_id, "file": str(file_path)})
      results.append(ConversionResult(file=file_path, status="error", message="Unexpected conversion failure"))

  return {"request_id": http_request.state.request_id, "results": [json.loads(item.json()) for item in results]}


def main():
  import uvicorn

  uvicorn.run(app, host=settings.host, port=int(settings.port), log_level=settings.log_level.lower())


if __name__ == "__main__":
  main()
