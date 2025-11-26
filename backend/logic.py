import math
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import Sampler
from qiskit.circuit.library import PhaseOracle
from qiskit_algorithms import Grover, AmplificationProblem
from sympy import symbols, Not, Or, And, to_cnf
from sympy.parsing.sympy_parser import parse_expr
import re

class SatOracleBuilder:
    def __init__(self):
        self.simulator = AerSimulator()
        self.sampler = Sampler()

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
        try:
            oracle_qc, objective_qubits = self.build_oracle_circuit(expression_string)
        except Exception as e:
            raise ValueError(f"Error creating Oracle: {e}")

        problem = AmplificationProblem(oracle=oracle_qc, objective_qubits=objective_qubits)
        
        if iterations is None:
            solutions = self.solve_classically(expression_string)
            M = len(solutions)
            N = 2 ** len(objective_qubits)
            if M == 0:
                iterations = 0
            else:
                theta = math.asin(math.sqrt(M / N))
                iterations = max(1, int(round((math.pi / (4 * theta)) - 0.5)))
        
        grover = Grover(sampler=self.sampler, iterations=iterations)
        result = grover.amplify(problem)
        
        return {
            "top_measurement": result.top_measurement,
            "iterations_used": iterations,
            "oracle_qubits": oracle_qc.num_qubits
        }

    def get_histogram_data(self, expression_string, iterations=None):
        try:
            oracle_qc, objective_qubits = self.build_oracle_circuit(expression_string)
        except:
             return {}

        problem = AmplificationProblem(oracle=oracle_qc, objective_qubits=objective_qubits)
        
        if iterations is None:
             solutions = self.solve_classically(expression_string)
             M = len(solutions)
             N = 2 ** len(objective_qubits)
             if M == 0: iterations = 0
             else:
                theta = math.asin(math.sqrt(M / N))
                iterations = max(1, int(round((math.pi / (4 * theta)) - 0.5)))

        grover = Grover(sampler=self.sampler, iterations=iterations)
        circuit = grover.construct_circuit(problem, power=iterations)
        circuit.measure_all()
        
        circuit = transpile(circuit, self.simulator)
        
        job = self.simulator.run(circuit, shots=1024)
        result = job.result()
        counts = result.get_counts()
        
        processed_counts = {}
        num_vars = len(objective_qubits)
        
        for bitstring, count in counts.items():
            # qiskit bitstring order is reversed (q_n ... q_0)
            # objective qubits are 0..num_vars-1 (the lower indices)
            var_part = bitstring[-num_vars:]
            processed_counts[var_part] = processed_counts.get(var_part, 0) + count
            
        return processed_counts

    def debug_circuit(self, expression_string):
        oracle_qc, objective_qubits = self.build_oracle_circuit(expression_string)
        problem = AmplificationProblem(oracle=oracle_qc, objective_qubits=objective_qubits)
        # Calculate iterations
        solutions = self.solve_classically(expression_string)
        M = len(solutions)
        N = 2 ** len(objective_qubits)
        if M == 0: iterations = 0
        else:
            theta = math.asin(math.sqrt(M / N))
            iterations = max(1, int(round((math.pi / (4 * theta)) - 0.5)))
            
        grover = Grover(iterations=iterations)
        circuit = grover.construct_circuit(problem, power=iterations)
        return circuit
