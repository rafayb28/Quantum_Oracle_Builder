from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import traceback

from .logic import SatOracleBuilder


app = FastAPI(root_path="/api")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

solver = SatOracleBuilder()


class SatRequest(BaseModel):
    expression: str


@app.post("/solve")
def solve_sat(request: SatRequest):
    try:
        print(f"Received request: {request.expression}")

        # classical validation
        classical_solutions = solver.solve_classically(request.expression)
        num_solutions = len(classical_solutions)

        # quantum solving - we are not guaranteed to find a solution on
        # first try, so run up to 3 times if needed
        max_attempts = 3
        for _ in range(max_attempts):
            result = solver.solve_quantum(request.expression)
            if result["solution"]:
                break

        result_data = {
            "classical_solutions": classical_solutions,
            "num_solutions": num_solutions,
            "counts": result.get("counts"),
            "top_measurement": result["solution"],
        }

        return result_data

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
