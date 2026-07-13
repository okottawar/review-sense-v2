import base64
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.analyzer import analyze_dataframe, REQUIRED_COLUMNS

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_DIR = "/tmp/fuzzy_sessions"
os.makedirs(SESSION_DIR, exist_ok=True)


def session_path(session_id: str) -> str:
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return os.path.join(SESSION_DIR, f"{safe_id}.jsonl")


@app.post("/api/analyze")
async def analyze(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    session_id = payload.get("session_id") or str(uuid.uuid4())
    chunk_index = payload.get("chunk_index", 0)
    chunk_count = payload.get("chunk_count", 1)
    header = payload.get("header") or []
    rows = payload.get("rows") or []

    if not rows:
        raise HTTPException(status_code=400, detail="No rows received in chunk.")

    missing = [c for c in REQUIRED_COLUMNS if c not in [h.strip().lower() for h in header]]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required column(s): {', '.join(missing)}. "
                    f"Expected at least: {', '.join(REQUIRED_COLUMNS)}",
        )

    path = session_path(session_id)

    try:
        # Append this chunk's rows to the session file on disk.
        with open(path, "a", encoding="utf-8") as f:
            for row in rows:
                normalized = {str(k).strip().lower(): v for k, v in row.items()}
                f.write(json.dumps(normalized) + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to buffer chunk: {e}")

    is_final = (chunk_index == chunk_count - 1)

    if not is_final:
        return JSONResponse({"session_id": session_id, "final": False})

    # Final chunk: read back all buffered rows, run the fuzzy analysis, clean up.
    try:
        all_rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_rows.append(json.loads(line))

        df = pd.DataFrame(all_rows)
        df_out, summary = analyze_dataframe(df)

        csv_bytes = df_out.to_csv(index=False).encode("utf-8")
        csv_b64 = base64.b64encode(csv_bytes).decode("utf-8")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    return JSONResponse({
        "session_id": session_id,
        "final": True,
        "summary": summary,
        "processed_csv_base64": csv_b64,
        "processed_filename": "analyzed_dataset.csv",
    })


@app.get("/api/health")
async def health():
    return {"status": "ok"}
