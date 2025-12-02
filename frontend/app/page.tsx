"use client";

import { useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function Home() {
  const [expression, setExpression] = useState("(A | B) & (~A | C)");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch("https://qsat.pkrm.dev/api/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expression }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "failed to solve");
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const chartData = result?.counts
    ? {
        labels: Object.keys(result.counts),
        datasets: [
          {
            label: "measurement count",
            data: Object.values(result.counts),
            backgroundColor: Object.keys(result.counts).map((key) =>
              key === result.top_measurement
                ? "rgba(79, 70, 229, 0.8)" // indigo-600
                : "rgba(209, 213, 219, 0.5)" // gray-300
            ),
            borderColor: Object.keys(result.counts).map((key) =>
              key === result.top_measurement
                ? "rgba(79, 70, 229, 1)"
                : "rgba(209, 213, 219, 1)"
            ),
            borderWidth: 1,
          },
        ],
      }
    : null;

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <header className="mb-12 text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl mb-4">
            SAT Oracle Builder
          </h1>
          <p className="text-lg text-gray-600 uppercase tracking-wider font-medium">
            Quantum Satisfiability Solver using Grover's Algorithm
          </p>
        </header>

        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8 mb-10 transition-all hover:shadow-xl">
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label htmlFor="expression" className="sr-only">Boolean Expression</label>
              <input
                id="expression"
                type="text"
                value={expression}
                onChange={(e) => setExpression(e.target.value)}
                placeholder="(A | B) & (~A | C)"
                className="w-full px-6 py-4 text-lg border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono bg-gray-50 transition-all"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-8 py-4 bg-indigo-600 text-white text-lg font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg uppercase tracking-wide"
            >
              {loading ? "Solving..." : "Solve"}
            </button>
          </form>
          {error && (
            <div className="mt-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 rounded-r">
              <p className="font-medium">Error</p>
              <p className="text-sm">{error}</p>
            </div>
          )}
        </div>

        {result && (
          <div className="grid gap-8 lg:grid-cols-2">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8 transition-all hover:shadow-xl">
              <h2 className="text-xl font-bold text-gray-900 mb-6 uppercase tracking-wide border-b pb-2">
                Analysis Results
              </h2>
              <div className="space-y-8">
                <div>
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3">
                    Classical Solutions
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {result.classical_solutions.map((sol: string) => (
                      <span
                        key={sol}
                        className="px-3 py-1.5 bg-green-100 text-green-800 rounded-md text-sm font-mono font-medium border border-green-200"
                      >
                        {sol}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                    <div>
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">
                        Solution Count
                    </p>
                    <p className="text-3xl font-mono font-bold text-gray-900">
                        {result.num_solutions}
                    </p>
                    </div>
                    <div>
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">
                        Top Measurement
                    </p>
                    <span className="inline-block px-3 py-1 bg-indigo-100 text-indigo-800 rounded-md text-lg font-mono font-bold border border-indigo-200">
                        {result.top_measurement}
                    </span>
                    </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8 transition-all hover:shadow-xl">
              <h2 className="text-xl font-bold text-gray-900 mb-6 uppercase tracking-wide border-b pb-2">
                Probability Distribution
              </h2>
              <div className="relative h-64 w-full">
                {chartData ? (
                  <Bar
                    data={chartData}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: { display: false },
                        tooltip: {
                          backgroundColor: 'rgba(17, 24, 39, 0.9)',
                          padding: 12,
                          titleFont: { size: 13 },
                          bodyFont: { size: 13 },
                          callbacks: {
                            label: (context) => `Count: ${context.raw}`,
                          },
                        },
                      },
                      scales: {
                        y: { 
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                      },
                    }}
                  />
                ) : (
                    <div className="flex items-center justify-center h-full text-gray-400 italic">
                        No solution found within search limits.
                    </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
