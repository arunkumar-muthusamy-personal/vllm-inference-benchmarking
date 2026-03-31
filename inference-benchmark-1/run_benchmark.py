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


async def post_grafana_annotation(
    grafana_url: str, api_key: str, text: str, tags: list, time_ms: int, end_ms: int = None
) -> None:
    """Post a region or point annotation to Grafana. Silently skips if Grafana unreachable."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        # fall back to basic auth admin:admin
        import base64
        headers["Authorization"] = "Basic " + base64.b64encode(b"admin:admin").decode()

    body = {"text": text, "tags": tags, "time": time_ms}
    if end_ms:
        body["timeEnd"] = end_ms

    try:
        async with aiohttp.ClientSession() as s:
            await s.post(f"{grafana_url}/api/annotations", headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=3))
    except Exception:
        pass  # Grafana unavailable — don't block the benchmark


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


def print_progress(done: int, total: int, start: float, errors: int) -> None:
    elapsed = time.perf_counter() - start
    rps = done / elapsed if elapsed > 0 else 0
    pct = done / total * 100
    bar = ("█" * int(pct / 5)).ljust(20)
    print(f"\r  [{bar}] {done}/{total} ({pct:.0f}%)  {rps:.1f} req/s  errors: {errors}  elapsed: {elapsed:.1f}s",
          end="", flush=True)


async def run(host: str, port: int, concurrency: int, dataset: list, config_name: str,
              grafana_url: str = "http://localhost:3000", grafana_key: str = "",
              num_prompts: int = 0):
    url = f"http://{host}:{port}/v1/completions"
    semaphore = asyncio.Semaphore(concurrency)
    done_count = 0
    error_count = 0

    async def bounded(payload, start_time, total):
        nonlocal done_count, error_count
        async with semaphore:
            result = await send_request(session, url, payload)
            done_count += 1
            if not result["success"]:
                error_count += 1
            print_progress(done_count, total, start_time, error_count)
            return result

    print(f"\n{'='*60}")
    print(f"Config: {config_name} | Concurrency: {concurrency} | Prompts: {num_prompts or len(dataset)}")
    print(f"Target: {url}")
    print(f"{'='*60}")

    # Warmup — no progress tracking
    print("Warming up (10 requests)...", end="", flush=True)
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[send_request(session, url, dataset[i % len(dataset)]) for i in range(10)])
    print(" done.")

    print(f"\nRunning benchmark...")
    wall_start = time.perf_counter()
    wall_start_ms = int(time.time() * 1000)

    # Annotate run start in Grafana
    await post_grafana_annotation(
        grafana_url, grafana_key,
        text=f"▶ {config_name} | concurrency={concurrency}",
        tags=["benchmark", config_name, f"c{concurrency}"],
        time_ms=wall_start_ms,
    )

    async with aiohttp.ClientSession() as session:
        # Build the exact prompt list to send
        if num_prompts and num_prompts != len(dataset):
            work = [dataset[i % len(dataset)] for i in range(num_prompts)]
        else:
            work = dataset
        results = await asyncio.gather(*[bounded(p, wall_start, len(work)) for p in work])
    print()  # newline after progress bar
    wall_end = time.perf_counter()
    wall_end_ms = int(time.time() * 1000)

    wall_time = wall_end - wall_start
    successes = [r for r in results if r["success"]]
    failures = len(results) - len(successes)
    latencies = [r["latency_ms"] for r in successes]
    total_tokens = sum(r["tokens_out"] for r in successes)

    # Annotate run end as a region spanning the full run window
    await post_grafana_annotation(
        grafana_url, grafana_key,
        text=f"■ {config_name} | c={concurrency} | {len(successes)}/{len(results)} ok",
        tags=["benchmark", config_name, f"c{concurrency}"],
        time_ms=wall_start_ms,
        end_ms=wall_end_ms,
    )

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
    parser.add_argument("--grafana-url", default="http://localhost:3000", help="Grafana base URL for annotations")
    parser.add_argument("--grafana-key", default="", help="Grafana API key (leave blank to use admin:admin)")
    parser.add_argument("--num-prompts", type=int, default=200,
                        help="Number of prompts to send. Cycles dataset if larger than dataset size. Defaults to full dataset.")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        print("Run: python generate_dataset.py")
        return

    dataset = [json.loads(line) for line in dataset_path.read_text().splitlines() if line.strip()]
    asyncio.run(run(args.host, args.port, args.concurrency, dataset, args.config,
                    args.grafana_url, args.grafana_key, args.num_prompts))


if __name__ == "__main__":
    main()
