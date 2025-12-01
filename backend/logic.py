import math
import random
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from sympy import symbols, Not, Or, And, to_cnf
from sympy.parsing.sympy_parser import parse_expr
import re


class SatOracleBuilder:
    def __init__(self):
        self.simulator = AerSimulator()

    def parse_expression(self, expression_string) -> tuple:
        """
        Parses a boolean expression string into a sympy expression and extracts variable names
        """
        # extract all a-z, A-Z
        variables = sorted(list(set(re.findall(r"[a-zA-Z]+", expression_string))))
        if not variables:
            raise ValueError("no variables found in expression")

        syms = {name: symbols(name) for name in variables}

        try:
            # sympy handles &, |, ~
            expr = parse_expr(expression_string, local_dict=syms)
        except Exception as e:
            raise ValueError(f"failed to parse expression: {e}")

        return expr, variables

    def solve_classically(self, expression_string) -> list:
        """
        Classically solves the SAT problem by brute force
        """
        expr, variables = self.parse_expression(expression_string)
        num_vars = len(variables)
        solutions = []

        # check all possible assignments
        for i in range(2**num_vars):
            bin_str = format(i, f"0{num_vars}b")
            assignment = {
                variables[j]: int(bin_str[j]) for j in range(num_vars)
            }  # {'x': 0, 'y': 1, ...}

            if expr.subs(assignment):  # evaluate
                solutions.append(bin_str)

        return solutions

    def solve_quantum(self, expression_string):
        """
        Solves the SAT problem using Grover's algorithm without knowing the number of solutions in advance.
        """
        expr, variables = self.parse_expression(expression_string)
        num_vars = len(variables)
        N = 2**num_vars

        try:
            oracle_qc, objective_qubits = self.build_oracle_circuit(expr, variables)
        except Exception as e:
            raise ValueError(f"Error creating Oracle: {e}")

        # Implementing algorithm from "Tight bounds on quantum searching" https://arxiv.org/pdf/quant-ph/9605034
        m = 1.0
        lam = 1.2  # scaling factor
        max_m = math.sqrt(N)  # upper limit

        attempts = 0

        while m <= max_m:
            attempts += 1
            # 1. pick random iterations [0, m-1]
            iterations = random.randint(0, int(m) - 1)

            # 2. run grover
            qc = self.construct_grover_circuit(oracle_qc, objective_qubits, iterations)
            qc = transpile(qc, self.simulator)
            job = self.simulator.run(qc, shots=1024)
            result = job.result()
            counts = result.get_counts()
            top_measurement = max(counts, key=counts.get)

            # 3. classically verify
            assignment = {}
            for i, name in enumerate(variables):
                val = int(top_measurement[-(i + 1)])  # q_i is at -(i+1)
                assignment[name] = val

            if expr.subs(assignment):
                # reverse measurements to match variable order
                reversed_counts = {}
                for meas, count in counts.items():
                    reversed_meas = meas[::-1]
                    reversed_counts[reversed_meas] = count

                return {
                    "solution": top_measurement[::-1],
                    "iterations_used": iterations,
                    "attempts": attempts,
                    "counts": reversed_counts,
                    "message": "Solution found using randomized Grover search.",
                }

            # 4. increase m
            m = lam * m

        return {
            "solution": None,
            "iterations_used": None,
            "attempts": attempts,
            "counts": None,
            "message": "No solution found within search limits.",
        }

    def build_oracle_circuit(self, expr, variables):
        """
        Builds a quantum oracle circuit in CNF form for the given SAT expression.
        """
        cnf_expr = to_cnf(expr, simplify=True)

        if isinstance(cnf_expr, And):  # multiple clauses
            clauses = cnf_expr.args
        else:  # single clause
            clauses = [cnf_expr]

        num_clauses = len(clauses)
        num_vars = len(variables)
        qc = QuantumCircuit(num_vars + num_clauses)
        clause_qubits = list(range(num_vars, num_vars + num_clauses))  # ancilla qubits

        # compute all clauses
        for i, clause in enumerate(clauses):
            self.apply_clause(clause, variables, clause_qubits[i], qc)

        # phase flip if all clauses are true - grover oracle
        if clause_qubits:
            if len(clause_qubits) == 1:
                qc.z(clause_qubits[0])
            else:
                qc.mcp(math.pi, clause_qubits[:-1], clause_qubits[-1])

        # uncompute clauses (reverse order) for later amplitude amplification
        for i in range(len(clauses) - 1, -1, -1):
            self.apply_clause(clauses[i], variables, clause_qubits[i], qc)

        return qc, list(range(num_vars))

    def apply_clause(self, clause, variables, target_qubit, qc):
        """
        Applies the clause logic to the target qubit
        """
        if isinstance(clause, Or):  # multiple literals
            literals = clause.args
        else:  # single literal
            literals = [clause]

        qubits_to_check = []
        x_gates_to_apply = []

        var_map = {name: i for i, name in enumerate(variables)}

        for lit in literals:
            sym = lit if not isinstance(lit, Not) else lit.args[0]
            idx = var_map[str(sym)]
            qubits_to_check.append(idx)

            if not isinstance(lit, Not):
                x_gates_to_apply.append(idx)

        # flip variables whre literal is positive
        if x_gates_to_apply:
            qc.x(x_gates_to_apply)

        # at this point, all controls are 1 when every literal is false

        # flip target if all literals are false
        qc.mcx(qubits_to_check, target_qubit)

        # unflip variables
        if x_gates_to_apply:
            qc.x(x_gates_to_apply)

        # flip target (so 1 means clause true)
        qc.x(target_qubit)

    def construct_grover_circuit(self, oracle_qc, objective_qubits, iterations):
        """
        Constructs the full Grover circuit.
        """
        num_qubits = oracle_qc.num_qubits
        qc = QuantumCircuit(num_qubits, len(objective_qubits))

        qc.h(objective_qubits)

        for _ in range(iterations):
            qc.compose(oracle_qc, inplace=True)  # apply oracle
            self.add_diffuser(qc, objective_qubits)

        qc.measure(objective_qubits, range(len(objective_qubits)))

        return qc

    def add_diffuser(self, qc, target_qubits):
        """
        Appends the Grover Diffuser operator to the circuit.
        """
        qc.h(target_qubits)
        qc.x(target_qubits)

        # phase flip
        if len(target_qubits) == 1:
            qc.z(target_qubits[0])
        else:
            qc.mcp(math.pi, target_qubits[:-1], target_qubits[-1])

        qc.x(target_qubits)
        qc.h(target_qubits)
