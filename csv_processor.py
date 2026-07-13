"""CSV reading/validation helpers."""

import io
import pandas as pd


class CSVValidationError(Exception):
    pass


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    if not content:
        raise CSVValidationError("Uploaded file is empty.")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise CSVValidationError(f"Could not parse CSV file: {e}")

    if df.empty:
        raise CSVValidationError("CSV file contains no data rows.")

    # normalize column names: lowercase, strip whitespace
    df.columns = [str(c).strip().lower() for c in df.columns]

    return df


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
