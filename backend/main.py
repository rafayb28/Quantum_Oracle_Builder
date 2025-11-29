from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import traceback

try:
    from .logic import SatOracleBuilder
except ImportError:
    from logic import SatOracleBuilder

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

solver = None

@app.on_event("startup")
def startup_event():
    global solver
    solver = SatOracleBuilder()

class SatRequest(BaseModel):
    expression: str
    unknown_solutions: bool = False

@app.post("/solve")
def solve_sat(request: SatRequest):
    global solver
    try:
        print(f"Received request: {request.expression}")
        
        # classical validation (always run for reference/grading)
        classical_solutions = solver.solve_classically(request.expression)
        print(f"Classical solutions: {classical_solutions}")
        num_solutions = len(classical_solutions)
        num_solutions = len(classical_solutions)
        
        result_data = {
            "classical_solutions": classical_solutions,
            "num_solutions": num_solutions,
            "histogram": None,
            "top_measurement": None,
            "method": "classical_optimized"
        }

        if request.unknown_solutions:
            # Group Requirement: Solve without knowing N
            quantum_result = solver.solve_unknown(request.expression)
            result_data["top_measurement"] = quantum_result["solution"] if quantum_result["found"] else None
            result_data["method"] = "unknown_solutions_randomized"
            result_data["quantum_details"] = quantum_result
            result_data["histogram"] = quantum_result.get("histogram")
        else:
            # Standard "A" Grade Path: Use classical count to optimize
            histogram = solver.get_histogram_data(request.expression)
            if histogram:
                top_measurement = max(histogram, key=histogram.get)
            else:
                top_measurement = None
            
            result_data["histogram"] = histogram
            result_data["top_measurement"] = top_measurement

        return result_data

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "SAT Oracle Builder Backend is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
