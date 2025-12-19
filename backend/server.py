"""Minimal FastAPI wrapper for DocuMancer conversions."""

import asyncio
import json
import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field

logger = logging.getLogger("documancer.server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="DocuMancer Backend", version="0.1.0")


class ConvertRequest(BaseModel):
  files: List[Path] = Field(..., description="Absolute paths to files to convert")


class ConversionResult(BaseModel):
  file: Path
  status: str
  message: str | None = None
  content: dict | None = None


@app.get("/health")
async def health():
  return {"status": "ok"}


def _extract_plain_text(path: Path) -> str:
  if not path.exists():
    raise FileNotFoundError(f"Missing file: {path}")

  if path.suffix.lower() in {".txt", ".md", ".json"}:
    return path.read_text(encoding="utf-8", errors="ignore")

  raise ValueError("Unsupported format for lightweight converter")


@app.post("/convert")
async def convert(request: ConvertRequest):
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
      logger.warning("File not found: %s", file_path)
      results.append(ConversionResult(file=file_path, status="error", message=str(missing)))
    except ValueError as exc:
      logger.warning("Unsupported format for %s: %s", file_path, exc)
      results.append(ConversionResult(file=file_path, status="error", message=str(exc)))
    except Exception as exc:  # noqa: BLE001
      logger.exception("Failed to convert %s", file_path)
      results.append(ConversionResult(file=file_path, status="error", message=str(exc)))

  return {"results": [json.loads(item.json()) for item in results]}


def main():
  import uvicorn

  uvicorn.run(app, host="127.0.0.1", port=int("8000"))


if __name__ == "__main__":
  main()
