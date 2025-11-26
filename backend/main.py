from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .logic import SatOracleBuilder
import uvicorn

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

solver = SatOracleBuilder()

class SatRequest(BaseModel):
    expression: str

@app.post("/solve")
async def solve_sat(request: SatRequest):
    try:
        # classical validation to get optimal iterations
        classical_solutions = solver.solve_classically(request.expression)
        num_solutions = len(classical_solutions)
        
        # quantum solution (grover's)
        histogram = solver.get_histogram_data(request.expression)
        
        if histogram:
            top_measurement = max(histogram, key=histogram.get)
        else:
            top_measurement = None

        return {
            "classical_solutions": classical_solutions,
            "num_solutions": num_solutions,
            "top_measurement": top_measurement,
            "histogram": histogram
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "SAT Oracle Builder Backend is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
