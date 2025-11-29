import math
import random
import os
os.environ['QISKIT_PARALLEL'] = 'False'

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from sympy import symbols, Not, Or, And, to_cnf
from sympy.parsing.sympy_parser import parse_expr
import re

class SatOracleBuilder:
    def __init__(self):
        self.simulator = AerSimulator()

    def parse_expression(self, expression_string):
        # extract all unique alphabetic sequences as variables
        var_names = sorted(list(set(re.findall(r'[a-zA-Z]+', expression_string))))
        if not var_names:
            raise ValueError("no variables found in expression")
        
        syms = symbols(var_names)
        sym_dict = {name: sym for name, sym in zip(var_names, syms)}
        
        try:
            # sympy parser handles &, |, ~ for and, or, not
            expr = parse_expr(expression_string, local_dict=sym_dict)
        except Exception as e:
            raise ValueError(f"failed to parse expression: {e}")
            
        return expr, var_names

    def solve_classically(self, expression_string):
        expr, var_names = self.parse_expression(expression_string)
        num_vars = len(var_names)
        solutions = []
        
        # brute force check all 2^n assignments
        for i in range(2**num_vars):
            bin_str = format(i, f'0{num_vars}b')
            assignment = {var_names[j]: int(bin_str[j]) for j in range(num_vars)}
            
            if expr.subs(assignment):
                solutions.append(bin_str)
                
        return solutions

    def build_oracle_circuit(self, expression_string):
        expr, var_names = self.parse_expression(expression_string)
        cnf_expr = to_cnf(expr, simplify=True)
        num_vars = len(var_names)
        
        if isinstance(cnf_expr, And):
            clauses = cnf_expr.args
        else:
            clauses = [cnf_expr]

        var_map = {name: i for i, name in enumerate(var_names)}
        
        num_clauses = len(clauses)
        qc = QuantumCircuit(num_vars + num_clauses)
        clause_qubits = list(range(num_vars, num_vars + num_clauses))
        
        def apply_clause(clause, target_qubit):
            if isinstance(clause, Or):
                literals = clause.args
            else:
                literals = [clause]
            
            qubits_to_check = []
            x_gates_to_apply = []
            
            for lit in literals:
                if isinstance(lit, Not):
                    sym = lit.args[0]
                    idx = var_map[str(sym)]
                    qubits_to_check.append(idx)
                else:
                    sym = lit
                    idx = var_map[str(sym)]
                    qubits_to_check.append(idx)
                    x_gates_to_apply.append(idx)
            
            # flip variables so that 1 means "literal is false"
            if x_gates_to_apply:
                qc.x(x_gates_to_apply)
            
            # compute and (all literals false) into target
            qc.mcx(qubits_to_check, target_qubit)
            
            # unflip variables
            if x_gates_to_apply:
                qc.x(x_gates_to_apply)
            
            # flip target (so 1 means clause true)
            qc.x(target_qubit)

        # compute all clauses
        for i, clause in enumerate(clauses):
            apply_clause(clause, clause_qubits[i])
            
        # phase flip if all clauses are true
        if clause_qubits:
            if len(clause_qubits) == 1:
                qc.z(clause_qubits[0])
            else:
                qc.mcp(math.pi, clause_qubits[:-1], clause_qubits[-1])
        
        # uncompute clauses (reverse order)
        for i in range(len(clauses)-1, -1, -1):
            apply_clause(clauses[i], clause_qubits[i])
            
        return qc, list(range(num_vars))

    def solve_quantum(self, expression_string, iterations=None):
        """
        Uses Grover's algorithm to find a solution.
        """
        # 1. Create Oracle
        try:
            oracle_qc, objective_qubits = self.build_oracle_circuit(expression_string)
        except Exception as e:
            raise ValueError(f"Error creating Oracle: {e}")

        # 2. Determine Iterations
        if iterations is None:
            solutions = self.solve_classically(expression_string)
            M = len(solutions)
            N = 2 ** len(objective_qubits)
            if M == 0:
                iterations = 0
            else:
                theta = math.asin(math.sqrt(M / N))
                iterations = max(1, int(round((math.pi / (4 * theta)) - 0.5)))
        
        # 3. Construct Circuit
        qc = self.construct_grover_circuit(oracle_qc, objective_qubits, iterations)
        
        # 4. Run
        qc = transpile(qc, self.simulator)
        job = self.simulator.run(qc, shots=1024)
        result = job.result()
        counts = result.get_counts()
        
        # Find top measurement
        top_measurement = max(counts, key=counts.get)
        # Qiskit counts keys are already the measured bits (reversed? No, measure maps q_i to c_i)
        # But qiskit prints 'c_n...c_0'.
        # My measure: qc.measure(objective_qubits, range(len(objective_qubits)))
        # objective_qubits are [0, 1, ... k].
        # So q0 -> c0, q1 -> c1.
        # Result string '10' means c1=1, c0=0.
        # This matches standard qiskit bitstring order.
        
        return {
            "top_measurement": top_measurement,
            "iterations_used": iterations,
            "oracle_qubits": oracle_qc.num_qubits
        }

    def get_histogram_data(self, expression_string, iterations=None):
        """
        Runs the Grover circuit and returns histogram data for the frontend.
        """
        try:
            oracle_qc, objective_qubits = self.build_oracle_circuit(expression_string)
        except:
             return {}

        if iterations is None:
             solutions = self.solve_classically(expression_string)
             M = len(solutions)
             N = 2 ** len(objective_qubits)
             if M == 0: iterations = 0
             else:
                theta = math.asin(math.sqrt(M / N))
                iterations = max(1, int(round((math.pi / (4 * theta)) - 0.5)))

        qc = self.construct_grover_circuit(oracle_qc, objective_qubits, iterations)
        
        qc = transpile(qc, self.simulator)
        job = self.simulator.run(qc, shots=1024)
        result = job.result()
        counts = result.get_counts()
        
        # Counts are already just the measured bits because we only measured objective_qubits
        return counts

    def debug_circuit(self, expression_string):
        oracle_qc, objective_qubits = self.build_oracle_circuit(expression_string)
        # Calculate iterations
        solutions = self.solve_classically(expression_string)
        M = len(solutions)
        N = 2 ** len(objective_qubits)
        if M == 0: iterations = 0
        else:
            theta = math.asin(math.sqrt(M / N))
            iterations = max(1, int(round((math.pi / (4 * theta)) - 0.5)))
            
        circuit = self.construct_grover_circuit(oracle_qc, objective_qubits, iterations)
        return circuit

    def solve_unknown(self, expression_string):
        """
        Solves the SAT problem without knowing the number of solutions beforehand.
        Uses the exponential search strategy (Boyer et al.) for Grover's algorithm.
        """
        expr, var_names = self.parse_expression(expression_string)
        num_vars = len(var_names)
        N = 2**num_vars
        
        try:
            oracle_qc, objective_qubits = self.build_oracle_circuit(expression_string)
        except Exception as e:
            raise ValueError(f"Error creating Oracle: {e}")

        # Boyer et al. algorithm parameters
        m = 1.0
        lam = 1.2 # Growth factor
        
        # We limit the search to avoid infinite loops. 
        # If we exceed approx sqrt(N) * few attempts, we assume no solution.
        max_m = math.sqrt(N) * 2.0
        
        attempts = 0
        
        while m <= max_m:
            attempts += 1
            # 1. Pick random iterations 1 <= j <= m
            iterations = random.randint(1, max(1, int(m)))
            
            # 2. Run Grover
            qc = self.construct_grover_circuit(oracle_qc, objective_qubits, iterations)
            qc = transpile(qc, self.simulator)
            job = self.simulator.run(qc, shots=1024)
            result = job.result()
            counts = result.get_counts()
            
            top_measurement = max(counts, key=counts.get)
            
            # 3. Verify Solution Classically
            # Qiskit string is q_n ... q_0 (reversed)
            # My vars are mapped q_0 ... q_n
            assignment = {}
            for i, name in enumerate(var_names):
                # q_i is at index -(i+1) in top_measurement
                val = int(top_measurement[-(i+1)])
                assignment[name] = val
            
            if expr.subs(assignment):
                # generate histogram with the successful iteration count
                histogram = self.get_histogram_with_iterations(expression_string, iterations)
                
                return {
                    "solution": top_measurement,
                    "iterations_used": iterations,
                    "found": True,
                    "attempts": attempts,
                    "histogram": histogram,
                    "message": "Solution found using randomized Grover search."
                }
            
            # 4. Increase m
            m = m * lam
            
        return {
            "found": False,
            "attempts": attempts,
            "histogram": None,
            "message": "No solution found within search limits."
        }
    
    def get_histogram_with_iterations(self, expression_string, iterations):
        """
        Runs Grover circuit with specified iterations and returns histogram.
        """
        try:
            oracle_qc, objective_qubits = self.build_oracle_circuit(expression_string)
        except:
            return {}

        qc = self.construct_grover_circuit(oracle_qc, objective_qubits, iterations)
        qc = transpile(qc, self.simulator)
        
        job = self.simulator.run(qc, shots=1024)
        result = job.result()
        counts = result.get_counts()
        
        return counts
    
    def add_diffuser(self, qc, target_qubits):
        """
        Appends the Grover Diffuser operator to the circuit.
        """
        # Apply H to all target qubits
        qc.h(target_qubits)
        
        # Apply X to all target qubits
        qc.x(target_qubits)
        
        # Apply Multi-Controlled Z (MCP with pi)
        # Controls: all except last
        # Target: last
        if len(target_qubits) > 1:
            qc.mcp(math.pi, target_qubits[:-1], target_qubits[-1])
        elif len(target_qubits) == 1:
            qc.z(target_qubits[0])
            
        # Apply X to all target qubits
        qc.x(target_qubits)
        
        # Apply H to all target qubits
        qc.h(target_qubits)

    def construct_grover_circuit(self, oracle_qc, objective_qubits, iterations):
        """
        Constructs the full Grover circuit.
        """
        num_qubits = oracle_qc.num_qubits
        qc = QuantumCircuit(num_qubits, len(objective_qubits))
        
        # 1. Initialize: H on all objective qubits
        qc.h(objective_qubits)
        
        # 2. Grover Iterations
        for _ in range(iterations):
            # Apply Oracle
            qc.compose(oracle_qc, inplace=True)
            
            # Apply Diffuser
            self.add_diffuser(qc, objective_qubits)
            
        # 3. Measure
        qc.measure(objective_qubits, range(len(objective_qubits)))
        
        return qc
