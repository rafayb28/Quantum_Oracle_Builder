# Quantum Oracle Builder

## Backend (Python + FastAPI)

1.  Setup:
    ```bash
    python -m venv venv
    .\venv\Scripts\Activate
    pip install -r backend/requirements.txt
    ```
2.  Run:
    ```bash
    uvicorn backend.main:app --reload
    ```

## Frontend (Next.js)

1.  Setup:
    ```bash
    cd frontend
    npm install
    ```
2.  Run:
    ```bash
    npm run dev
    ```

Open [http://localhost:3000](http://localhost:3000) to view the app.
