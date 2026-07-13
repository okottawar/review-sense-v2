import base64
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.analyzer import analyze_dataframe
from utils.csv_processor import read_csv_bytes, dataframe_to_csv_bytes, CSVValidationError

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    content = await file.read()

    try:
        df = read_csv_bytes(content)
        df_out, summary = analyze_dataframe(df)
    except CSVValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    csv_bytes = dataframe_to_csv_bytes(df_out)
    csv_b64 = base64.b64encode(csv_bytes).decode("utf-8")

    return JSONResponse({
        "summary": summary,
        "processed_csv_base64": csv_b64,
        "processed_filename": f"analyzed_{file.filename}",
    })


@app.get("/api/health")
async def health():
    return {"status": "ok"}
