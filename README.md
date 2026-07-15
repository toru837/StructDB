# From File Chaos to Database Power

This project is a tiny rebellion against the old-school file-system mindset.

In DBMS, we learn this big idea:

- File system = raw, scattered, hard to query
- Database = structured, searchable, powerful

So what if your messy Excel/CSV files could be transformed into something that behaves a little like a database?

That is the whole vibe of this project.

---

## The Big Idea

Instead of treating uploaded files like just "bags of rows," this app:

1. reads them,
2. cleans them,
3. standardizes their columns,
4. detects useful keys,
5. merges them intelligently,
6. and finally stores the result in a SQLite database.

So your unstructured files become something queryable, storable, and much more powerful.

---

## Architecture in One Glance

```text
[User uploads CSV / Excel files]
                |
                v
      [Frontend Interface]
                |
                v
   [FastAPI Backend Processor]
                |
      +---------+-----------+
      |                     |
      v                     v
[Clean + Normalize]   [Detect Keys + Merge]
      |                     |
      +----------+----------+
                 |
                 v
     [Merged Table + CSV Output]
                 |
                 v
      [SQLite Database Storage]
```

---

## How the Flow Works

```text
Input Files
   -> Read file contents
   -> Validate format
   -> Standardize column names
   -> Clean messy values
   -> Detect primary-like keys
   -> Merge rows intelligently
   -> Save as CSV and SQLite
```

---

## Step-by-Step Journey

### 1. Upload
The frontend lets you upload one or more CSV/Excel files.

### 2. Parse
The backend reads the files and checks whether they are valid.

### 3. Clean
Messy headers and values are normalized so the data becomes easier to work with.

### 4. Detect Keys
The system tries to find strong identifiers like admission IDs, phone numbers, or names.

### 5. Merge
Matching rows are combined while filling missing values from other files.

### 6. Save
The merged data is:

- exported as merged.csv
- stored into a SQLite database table named records

---

## What This Project Does Well

- accepts multiple file uploads
- supports CSV and Excel files
- standardizes column names
- detects possible merge keys
- merges data without blindly overwriting values
- saves the final result into a database

---

## Tech Stack

- Frontend: plain HTML + JavaScript
- Backend: FastAPI
- Data handling: pandas
- Database: SQLite via SQLAlchemy

---

## Project Structure

```text
smart-table-generator/
│
├── backend/
│   ├── main.py              # FastAPI server
│   ├── uploads/             # Uploaded files
│   ├── merged.csv           # Generated output
│   └── data12.db            # SQLite database
│
├── frontend/
│   └── index.html
│
└── README.md
```

## Start It

### 1. Open the backend folder

```bash
cd backend
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn pandas openpyxl sqlalchemy
```

### 3. Start the backend

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Open the frontend
You can open the HTML file directly in a browser, or serve the frontend folder with:

```bash
cd frontend
python -m http.server 5500 --bind 127.0.0.1
```

Then visit:

```text
http://127.0.0.1:5500
```

---

## The Core Idea in One Line

This project takes file-based data and gives it database-like power.

It is not just "upload and merge".
It is more like:

```text
file system chaos  ->  database-like structure
```

---

## Quick Mental Model

```text
Before: scattered files, messy columns, weak relationships
After:  merged records, cleaner structure, database storage
```
