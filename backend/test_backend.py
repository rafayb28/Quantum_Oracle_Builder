from logic import SatOracleBuilder

def test():
    solver = SatOracleBuilder()
    # expression = "(A | B) & (~A | C) & (~B | D)"
    expression = "A & B"
    
    print(f"Testing expression: {expression}")
    
    try:
        print("Running classical solver...")
        solutions = solver.solve_classically(expression)
        print(f"Classical solutions: {solutions}")
    except Exception as e:
        print(f"Classical solver failed: {e}")

    try:
        print("Running quantum solver (histogram)...")
        hist = solver.get_histogram_data(expression)
        print(f"Histogram: {hist}")
        if hist:
            top = max(hist, key=hist.get)
            print(f"Top measurement: {top}")
            
        # print("Debugging with Statevector...")
        # qc = solver.debug_circuit(expression)
        # from qiskit.quantum_info import Statevector
        # # Remove measurements if any (construct_circuit usually doesn't add measurements unless specified)
        # # But we need to be careful about ancillas.
        # sv = Statevector.from_instruction(qc)
        # probs = sv.probabilities_dict()
        # # Filter for objective qubits
        # # Statevector dict keys are full bitstrings.
        # # We want to see if '11' (for A&B) has high prob.
        # # My vars are q0, q1.
        # # q0=A, q1=B.
        # # '11' means q1=1, q0=1.
        # # Bitstring '...11'.
        # print("Statevector probabilities (top 10):")
        # sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:10]
        # for state, prob in sorted_probs:
        #     print(f"{state}: {prob:.4f}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Quantum solver failed: {e}")

if __name__ == "__main__":
    test()
