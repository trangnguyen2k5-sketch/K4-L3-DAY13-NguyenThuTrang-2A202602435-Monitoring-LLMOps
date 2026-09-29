from __future__ import annotations

import json
import http.server
import socketserver
import webbrowser
from pathlib import Path

LOG_PATH = Path("data/logs.jsonl")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K4-L3A Day 13 Monitoring & LLMOps Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        h1 { text-align: center; color: #38bdf8; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #94a3b8; margin-bottom: 25px; font-size: 14px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; max-width: 1400px; margin: 0 auto; }
        .card { background-color: #1e293b; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); border: 1px solid #334155; }
        .card-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 15px; }
        .card-title { font-size: 16px; font-weight: bold; color: #e2e8f0; }
        .badge { font-size: 12px; padding: 4px 8px; border-radius: 6px; background-color: #3b82f6; color: white; }
        .badge-success { background-color: #10b981; }
        .badge-warning { background-color: #f59e0b; }
        .badge-danger { background-color: #ef4444; }
        .metric-val { font-size: 28px; font-weight: bold; margin: 10px 0; color: #38bdf8; }
        .threshold-info { font-size: 12px; color: #64748b; margin-top: 8px; }
        canvas { max-height: 250px; }
    </style>
</head>
<body>
    <h1>📊 K4-L3A Day 13 Monitoring & LLMOps Dashboard</h1>
    <div class="subtitle">Time Range: 60 phút | Auto Refresh: 30s | Data Source: data/logs.jsonl</div>

    <div class="grid">
        <!-- Panel 1: Latency -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">1. Latency Percentiles & TTFT</span>
                <span class="badge">Unit: ms</span>
            </div>
            <div class="metric-val" id="p95-val">-- ms</div>
            <canvas id="latencyChart"></canvas>
            <div class="threshold-info">SLO Threshold: P95 ≤ 3000 ms</div>
        </div>

        <!-- Panel 2: Traffic -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">2. Request Traffic</span>
                <span class="badge">Unit: req/min</span>
            </div>
            <div class="metric-val" id="traffic-val">-- req/min</div>
            <canvas id="trafficChart"></canvas>
            <div class="threshold-info">Threshold: Rate ≥ 1 req/min</div>
        </div>

        <!-- Panel 3: Errors -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">3. Error Rate & Retrieval Success</span>
                <span class="badge">Unit: %</span>
            </div>
            <div class="metric-val" id="error-val">-- %</div>
            <canvas id="errorChart"></canvas>
            <div class="threshold-info">Guardrail Threshold: Error Rate ≤ 2% | RAG Success ≥ 90%</div>
        </div>

        <!-- Panel 4: Cost -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">4. Cost Over Time</span>
                <span class="badge">Unit: USD ($)</span>
            </div>
            <div class="metric-val" id="cost-val">$--</div>
            <canvas id="costChart"></canvas>
            <div class="threshold-info">Threshold: Total Cost ≤ $2.50</div>
        </div>

        <!-- Panel 5: Tokens -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">5. Input & Output Tokens</span>
                <span class="badge">Unit: tokens</span>
            </div>
            <div class="metric-val" id="tokens-val">-- tokens</div>
            <canvas id="tokensChart"></canvas>
            <div class="threshold-info">Threshold: Total Tokens ≤ 50,000</div>
        </div>

        <!-- Panel 6: Quality -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">6. Quality Proxy Score</span>
                <span class="badge">Unit: score (0 - 1)</span>
            </div>
            <div class="metric-val" id="quality-val">-- / 1.0</div>
            <canvas id="qualityChart"></canvas>
            <div class="threshold-info">Threshold: Mean Quality ≥ 0.75</div>
        </div>
    </div>

    <script>
        async function loadMetrics() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                renderDashboard(data);
            } catch (e) {
                console.error("Lỗi đọc dữ liệu logs:", e);
            }
        }

        function renderDashboard(data) {
            document.getElementById('p95-val').innerText = `${data.latency.p95} ms (P95)`;
            document.getElementById('traffic-val').innerText = `${data.traffic.total_req} requests`;
            document.getElementById('error-val').innerText = `${data.errors.error_rate_pct.toFixed(1)}% (Err) | ${data.errors.retrieval_success_pct.toFixed(1)}% (RAG)`;
            document.getElementById('cost-val').innerText = `$${data.cost.total_usd.toFixed(4)}`;
            document.getElementById('tokens-val').innerText = `${data.tokens.total_tokens.toLocaleString()} tokens`;
            document.getElementById('quality-val').innerText = `${data.quality.mean_score.toFixed(2)} / 1.0`;

            createBarChart('latencyChart', ['P50', 'P95', 'P99', 'TTFT P95'], [data.latency.p50, data.latency.p95, data.latency.p99, data.latency.ttft_p95], '#38bdf8', 3000);
            createLineChart('trafficChart', data.time_labels, data.traffic.by_minute, '#10b981');
            createBarChart('errorChart', ['Error Rate %', 'RAG Success %'], [data.errors.error_rate_pct, data.errors.retrieval_success_pct], '#ef4444');
            createLineChart('costChart', data.time_labels, data.cost.by_minute, '#f59e0b');
            createBarChart('tokensChart', ['Input Tokens', 'Output Tokens'], [data.tokens.input, data.tokens.output], '#a855f7');
            createLineChart('qualityChart', data.time_labels, data.quality.by_minute, '#ec4899');
        }

        function createBarChart(id, labels, values, color, thresholdVal) {
            new Chart(document.getElementById(id), {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{ data: values, backgroundColor: color, borderRadius: 6 }]
                },
                options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#334155' } } } }
            });
        }

        function createLineChart(id, labels, values, color) {
            new Chart(document.getElementById(id), {
                type: 'line',
                data: {
                    labels: labels.length ? labels : ['0m'],
                    datasets: [{ data: values.length ? values : [0], borderColor: color, backgroundColor: color + '33', fill: true, tension: 0.3 }]
                },
                options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#334155' } } } }
            });
        }

        loadMetrics();
        setInterval(loadMetrics, 30000);
    </script>
</body>
</html>
"""

def parse_logs():
    records = []
    if LOG_PATH.exists():
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    latencies = [r["latency_ms"] for r in records if r.get("event") == "response_sent" and "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in records if r.get("event") == "response_sent" and "ttft_ms" in r]
    
    latencies.sort()
    ttfts.sort()

    def percentile(arr, p):
        if not arr:
            return 0
        idx = int(len(arr) * (p / 100.0))
        return arr[min(idx, len(arr) - 1)]

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    ttft_p95 = percentile(ttfts, 95)

    req_received = len([r for r in records if r.get("event") == "request_received"])
    req_failed = len([r for r in records if r.get("event") == "request_failed"])
    total_req = req_received or len(records)
    error_rate_pct = (req_failed / total_req * 100) if total_req else 0.0

    retrieval_logs = [r for r in records if r.get("tool_name") == "retrieval"]
    successful_retriev = len([r for r in retrieval_logs if r.get("tool_success") is True])
    retrieval_success_pct = (successful_retriev / len(retrieval_logs) * 100) if retrieval_logs else 100.0

    total_cost = sum(r.get("cost_usd", 0) for r in records if r.get("event") == "response_sent")
    tokens_in = sum(r.get("tokens_in", 0) for r in records if r.get("event") == "response_sent")
    tokens_out = sum(r.get("tokens_out", 0) for r in records if r.get("event") == "response_sent")
    
    scores = [r.get("quality_score") for r in records if r.get("event") == "response_sent" and "quality_score" in r]
    mean_score = (sum(scores) / len(scores)) if scores else 0.0

    return {
        "latency": {"p50": p50, "p95": p95, "p99": p99, "ttft_p95": ttft_p95},
        "traffic": {"total_req": total_req, "by_minute": [total_req]},
        "errors": {"error_rate_pct": error_rate_pct, "retrieval_success_pct": retrieval_success_pct},
        "cost": {"total_usd": total_cost, "by_minute": [total_cost]},
        "tokens": {"input": tokens_in, "output": tokens_out, "total_tokens": tokens_in + tokens_out},
        "quality": {"mean_score": mean_score, "by_minute": [mean_score]},
        "time_labels": ["Now"]
    }

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = parse_logs()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

def main():
    PORT = 8501
    print(f"🚀 Starting Dashboard Server at http://127.0.0.1:{PORT}")
    with socketserver.TCPServer(("127.0.0.1", PORT), DashboardHandler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    main()
