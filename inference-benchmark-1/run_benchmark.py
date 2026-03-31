"""
run_benchmark.py
Sends requests from test_dataset.jsonl to vLLM /v1/completions
and reports throughput and latency metrics.

Usage:
    python run_benchmark.py --host localhost --port 8000 \
        --concurrency 16 --config CONFIG-02
"""

import argparse
import json
import time
import statistics
import asyncio
import aiohttp
from pathlib import Path


async def send_request(session: aiohttp.ClientSession, url: str, payload: dict) -> dict:
    start = time.perf_counter()
    ttft = None
    try:
        async with session.post(url, json={
            "model": "gpt-oss-20b",
            "prompt": payload["prompt"],
            "max_tokens": payload["max_tokens"],
            "temperature": payload["temperature"],
            "top_p": payload["top_p"],
            "stream": False,
        }) as resp:
            data = await resp.json()
            end = time.perf_counter()
            tokens_out = data.get("usage", {}).get("completion_tokens", 0)
            return {
                "success": resp.status == 200,
                "latency_ms": (end - start) * 1000,
                "ttft_ms": ttft,
                "tokens_out": tokens_out,
                "category": payload.get("category", "unknown"),
            }
    except Exception as e:
        end = time.perf_counter()
        return {
            "success": False,
            "latency_ms": (end - start) * 1000,
            "ttft_ms": None,
            "tokens_out": 0,
            "category": payload.get("category", "unknown"),
            "error": str(e),
        }


async def run(host: str, port: int, concurrency: int, dataset: list, config_name: str):
    url = f"http://{host}:{port}/v1/completions"
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def bounded(payload):
        async with semaphore:
            return await send_request(session, url, payload)

    print(f"\n{'='*60}")
    print(f"Config: {config_name} | Concurrency: {concurrency} | Prompts: {len(dataset)}")
    print(f"Target: {url}")
    print(f"{'='*60}")

    # Warmup
    print("Warming up (10 requests)...")
    async with aiohttp.ClientSession() as session:
        warmup = await asyncio.gather(*[bounded(dataset[i % len(dataset)]) for i in range(10)])

    wall_start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[bounded(p) for p in dataset])
    wall_end = time.perf_counter()

    wall_time = wall_end - wall_start
    successes = [r for r in results if r["success"]]
    failures = len(results) - len(successes)
    latencies = [r["latency_ms"] for r in successes]
    total_tokens = sum(r["tokens_out"] for r in successes)

    print(f"\nResults:")
    print(f"  Total requests   : {len(results)}")
    print(f"  Successful       : {len(successes)}")
    print(f"  Failed           : {failures}")
    print(f"  Wall time        : {wall_time:.2f}s")
    print(f"  Throughput       : {len(successes)/wall_time:.2f} req/s")
    print(f"  Token throughput : {total_tokens/wall_time:.1f} tok/s")
    if latencies:
        print(f"  Latency p50      : {statistics.median(latencies):.1f} ms")
        print(f"  Latency p90      : {statistics.quantiles(latencies, n=10)[8]:.1f} ms")
        print(f"  Latency p99      : {statistics.quantiles(latencies, n=100)[98]:.1f} ms")

    # Save results
    out = {
        "config": config_name,
        "concurrency": concurrency,
        "total_requests": len(results),
        "successful": len(successes),
        "failed": failures,
        "wall_time_s": round(wall_time, 3),
        "throughput_req_s": round(len(successes)/wall_time, 3),
        "throughput_tok_s": round(total_tokens/wall_time, 1),
        "latency_p50_ms": round(statistics.median(latencies), 1) if latencies else None,
        "latency_p90_ms": round(statistics.quantiles(latencies, n=10)[8], 1) if len(latencies) >= 10 else None,
        "latency_p99_ms": round(statistics.quantiles(latencies, n=100)[98], 1) if len(latencies) >= 100 else None,
    }

    results_file = Path(f"results_{config_name}_c{concurrency}.json")
    results_file.write_text(json.dumps(out, indent=2))
    print(f"\n  Saved -> {results_file}")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--dataset", default="test_dataset.jsonl")
    parser.add_argument("--config", default="CONFIG-XX", help="Config label for output files")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        print("Run: python generate_dataset.py")
        return

    dataset = [json.loads(line) for line in dataset_path.read_text().splitlines() if line.strip()]
    asyncio.run(run(args.host, args.port, args.concurrency, dataset, args.config))


if __name__ == "__main__":
    main()
