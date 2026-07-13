import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.analyzer import REQUIRED_COLUMNS
from core.engine import analyze_batch

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analyze")
async def analyze(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    header = payload.get("header") or []
    rows = payload.get("rows") or []

    if not rows:
        raise HTTPException(status_code=400, detail="No rows received in chunk.")

    normalized_header = [str(h).strip().lower() for h in header]
    missing = [c for c in REQUIRED_COLUMNS if c not in normalized_header]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required column(s): {', '.join(missing)}. "
                    f"Expected at least: {', '.join(REQUIRED_COLUMNS)}",
        )

    try:
        df = pd.DataFrame(rows)
        df.columns = [str(c).strip().lower() for c in df.columns]

        ratings = df["rating"].fillna(3.0).values
        sentiments = df["sentiment"].fillna("Neutral").values

        scores, categories, rule_hits = analyze_batch(ratings, sentiments)

        df_out = df.copy()
        df_out["satisfaction_score"] = scores
        df_out["satisfaction_category"] = categories

        missing_values = int(df.isna().sum().sum())

        result_rows = df_out.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return JSONResponse({
        "rows": result_rows,
        "missing_values": missing_values,
        "column_count": len(df.columns),
        "rule_hits": rule_hits,
    })


@app.get("/api/health")
async def health():
    return {"status": "ok"}
