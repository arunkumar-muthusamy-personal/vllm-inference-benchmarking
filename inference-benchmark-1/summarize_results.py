import json
import glob

files = sorted(glob.glob("results_*.json"))

if not files:
    print("No result files found. Run some benchmarks first.")
    exit()

header = f"{'Config':<12} {'Conc':>5} {'req/s':>7} {'tok/s':>8} {'p50ms':>7} {'p99ms':>7} {'errors':>7}"
print(header)
print("-" * 60)

for f in files:
    d = json.load(open(f))
    print(
        f"{d['config']:<12} {d['concurrency']:>5} "
        f"{d['throughput_req_s']:>7.2f} {d['throughput_tok_s']:>8.1f} "
        f"{str(d['latency_p50_ms']):>7} {str(d['latency_p99_ms']):>7} "
        f"{d['failed']:>7}"
    )
