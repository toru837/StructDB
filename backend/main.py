
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
import re
import os 
from io import BytesIO 
from sqlalchemy import create_engine  # for integrating database 

app = FastAPI()
# creates data.db if not exist
engine = create_engine("sqlite:///data01.db")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# COLUMN_MAP = {
#     "associate": "name", "staff member": "name", "employee full name": "name", "full name": "name",
#     "employee code": "employee_id", "employee id": "employee_id", "emp id": "employee_id",
#     "mobile": "phone", "contact number": "phone", "phone number": "phone",
#     "corporate email": "email", "work email": "email", "email id": "email",
#     "role": "designation",
#     "city": "office location",
#     "department": "department name",
# }

# Dictionary to standardize different column name variants into one name
COLUMN_MAP = {
    "full name": "name",
    "student name": "name",

    "contact": "phone",
    "mobile": "phone",
    "phone number": "phone",

    "admission id": "admission_id", 

    "parent name": "parent_name",
}

# Priority order used to pick the primary key for each table
KEY_PRIORITY = ["admission_id", "phone", "name"]

#Rename messy column to our standard names using COLUMN_MAP
def standardize_columns(df):
    new_cols = {}
    for col in df.columns:
        key = col.strip().lower()
        new_cols[col] = COLUMN_MAP.get(key, key)
    return df.rename(columns=new_cols)

#trimming spaces, lowercase text fields, validate phone numbers.
def clean_data(df):
    
    if "name" in df.columns:
        df["name"] = df["name"].str.strip().str.lower()
        df["name"] = df["name"].apply(lambda x: re.sub(r"\s+", " ", x) if pd.notna(x) else x)
    if "email" in df.columns:
        df["email"] = df["email"].str.strip().str.lower()
    if "phone" in df.columns:
        df["phone"] = df["phone"].str.strip()
        df.loc[df["phone"].str.len() != 10, "phone"] = None
    return df


def detect_primary_key(df):
    """Pick the first column (in priority order) that is fully unique and non-null.""" #docstring
    for col in KEY_PRIORITY:
        if col in df.columns and df[col].notna().all() and df[col].nunique() == len(df):
            return col
    return None  # no clean unique key found


def find_best_common_key(df1, df2):
    """
    Find the strongest shared column between two tables.
    take column with less missing values, in order of KEY_PRIORITY.
    """
    candidates = [col for col in KEY_PRIORITY if col in df1.columns and col in df2.columns]

    if not candidates:
        return None

    best_col = None
    best_missing = float("inf")

    for col in candidates:
        missing = df1[col].isna().sum() + df2[col].isna().sum()
        if missing < best_missing:
            best_missing = missing
            best_col = col

    return best_col


def merge_fill_missing(left, right, key):
    """
    Outer join 
    Merge two tables on `key`, but only FILL missing values.
    Existing valid values in `left` are never overwritten.

    """
    merged = pd.merge(left, right, on=key, how="outer", suffixes=("", "_new"))

    for col in list(merged.columns):
        if col.endswith("_new"):
            original = col.replace("_new", "")
            merged[original] = merged[original].combine_first(merged[col])
            merged.drop(columns=[col], inplace=True)

    return merged


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    tables = []          # list of {"filename": ..., "df": ...}
    primary_keys = {}    # filename -> detected key (or None)  

# Step 1 + 2 + 3: read, standardize, clean each file
    for file in files:
        content = await file.read()
#read the uploaded file and check if its empty, wrong formated or blank then do not accept it..
# ---- CHECK 1: empty file ----   not needed 
        if len(content) == 0:
            return JSONResponse(
                status_code=400,
                content={"error": f"'{file.filename}' is empty. Please upload a valid file."}
            )

# save a copy to backend/uploads/
        with open(os.path.join(UPLOAD_DIR, file.filename), "wb") as f:
            f.write(content)

# ---- CHECK 2: wrong file type ----
        if file.filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(content), dtype=str)
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(BytesIO(content), dtype=str)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"'{file.filename}' is not a supported file type. Use .csv or .xlsx."}
            )

# ---- CHECK 3: blank spreadsheet (no rows/columns) ----
        if df.empty or len(df.columns) == 0:
            return JSONResponse(
                status_code=400,
                content={"error": f"'{file.filename}' has no readable data or columns."}
            )

        df = standardize_columns(df)
        df = clean_data(df)

        tables.append({"filename": file.filename, "df": df})

    # Step 4: detect primary key for EACH table individually
    for t in tables:
        key = detect_primary_key(t["df"]) 
        primary_keys[t["filename"]] = key if key else "none detected"

    # Step 5: merge tables one by one, logging how each merge happened
    merge_log = []
    merged = tables[0]["df"].copy()
    merged_label = tables[0]["filename"]

    for t in tables[1:]:
        next_df = t["df"]
        next_key = detect_primary_key(next_df)
        prev_key = primary_keys.get(merged_label)

        # Rule: if both tables share the same detected primary key, use it
        if prev_key and prev_key == next_key and prev_key in merged.columns and prev_key in next_df.columns:
            merge_key = prev_key
        else:
            # Otherwise fall back to the strongest common column
            merge_key = find_best_common_key(merged, next_df)

        if merge_key is None:
            merge_log.append(f"{merged_label} + {t['filename']}: SKIPPED (no common column found)")
            continue

        merged = merge_fill_missing(merged, next_df, merge_key)
        merge_log.append(f"{merged_label} + {t['filename']} merged using '{merge_key}'")
        merged_label = f"({merged_label} + {t['filename']})"

    # Step 6: save final result
    merged = merged.astype(object).where(pd.notnull(merged), None)  # replace NaN with None for valid JSON
    merged.to_csv("merged.csv", index=False)

    return {
        "uploaded_files": [t["filename"] for t in tables],
        "primary_keys": primary_keys,
        "merge_log": merge_log,
        "rows": len(merged),
        "data": merged.to_dict(orient="records"),
    }


# ---- Save merged data to database ----
class SaveRequest(BaseModel):
    data: List[Dict[str, Any]]   


@app.post("/save-to-db")
def save_to_db(request: SaveRequest):
    try:
        df = pd.DataFrame(request.data)

        if df.empty:
            return JSONResponse(status_code=400, content={"error": "No data to save."})
#overwrite
        df.to_sql("records", con=engine, if_exists="replace", index=False)

        return {"status": "saved", "rows": len(df)}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to save: {str(e)}"})


@app.get("/download")
def download_file():
    if not os.path.exists("merged.csv"):
        return JSONResponse(status_code=404, content={"error": "No merged file available yet."})
    return FileResponse("merged.csv", media_type="text/csv", filename="merged.csv")
