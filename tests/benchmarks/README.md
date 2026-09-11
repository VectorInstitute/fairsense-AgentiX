# Performance Benchmarking

**Phase 6.5**: Comprehensive performance benchmarking suite for FairSense-AgentiX graphs.

## Overview

This benchmarking suite provides detailed performance profiling for all graph workflows, including:
- **Latency tracking**: p50, p95, p99 percentiles
- **Memory profiling**: Delta memory usage per operation
- **Throughput measurement**: Operations per second
- **Success rate tracking**: Error rate monitoring
- **Statistical analysis**: Mean, std, min, max for all metrics

The benchmarks leverage the telemetry infrastructure integrated in Phase 6.4 for consistent, production-representative measurements.

## Quick Start

### Run All Benchmarks

```bash
# Run comprehensive benchmarks (all graphs, 20 iterations each)
uv run python tests/benchmarks/benchmark_graphs.py

# Results saved to: benchmark_results.json
```

### Run Specific Graphs

```bash
# Benchmark only BiasTextGraph and RiskGraph
uv run python tests/benchmarks/benchmark_graphs.py --graphs bias_text risk --iterations 50

# Benchmark the orchestrator
uv run python tests/benchmarks/benchmark_graphs.py --graphs orchestrator --iterations 100
```

### Custom Output Location

```bash
# Save results to custom path
uv run python tests/benchmarks/benchmark_graphs.py --output results/benchmarks_$(date +%Y%m%d).json
```

## Input Sizes

Each graph is benchmarked with three input sizes:

### BiasTextGraph
- **small**: 10-word sentence (baseline)
- **medium**: ~100-word job posting with multiple bias types
- **large**: ~500-word executive job posting with complex biases

### BiasImageGraph
- **small / medium / large**: the three JPEG fixtures in `tests/fixtures/bias_images/`, ordered by file size (~45 KB, ~110 KB, ~130 KB). Real images are required so that OCR/caption/VLM tools can decode them; random bytes fail on every iteration.

### RiskGraph
- **small**: ~20-word AI deployment scenario (top_k=3)
- **medium**: ~100-word hiring system scenario (top_k=5)
- **large**: ~500-word healthcare AI scenario (top_k=10, rmf_per_risk=5)

### OrchestratorGraph
- **text**: Text workflow via orchestrator
- **image**: Image workflow via orchestrator
- **risk**: Risk workflow via orchestrator

## Exit Status

The script exits **0** only when every requested graph and input size completed all iterations successfully. It exits **1** if any input size has no successful iterations (a "missing result group") or if any iteration failed, and prints the problems under `BENCHMARK INCOMPLETE`. Pass `--allow-errors` to still exit 0 for exploratory runs (problems are reported either way and stored under `"problems"` in the JSON).

An iteration counts as failed when `graph.invoke` raises **or** when the returned result carries a failure — the orchestrator catches workflow exceptions and reports them via `final_result["status"] != "success"` / `final_result["errors"]` rather than raising, so a returned result is not proof of success.

## Output Format

Results are saved as JSON with the following structure:

```json
{
  "timestamp": "2025-11-14T07:53:24.494Z",
  "configuration": {
    "iterations": 20,
    "llm_provider": "fake",
    "llm_model": "gpt-4",
    "telemetry_enabled": false,
    "cache_enabled": true
  },
  "graphs": {
    "bias_text": {
      "graph_name": "bias_text",
      "iterations": 20,
      "input_sizes": {
        "small": {
          "latency_seconds": {
            "p50": 0.002,
            "p95": 0.003,
            "p99": 0.004,
            "mean": 0.0023,
            "std": 0.0005,
            "min": 0.002,
            "max": 0.004
          },
          "memory_delta_mb": {
            "p50": 0.5,
            "p95": 1.2,
            "p99": 1.5,
            "mean": 0.6,
            "std": 0.3,
            "min": 0.2,
            "max": 1.5
          },
          "throughput_ops_per_sec": 434.78,
          "success_rate": 1.0,
          "total_errors": 0
        }
      },
      "missing_sizes": [],
      "error_samples": {}
    }
  },
  "problems": []
}
```

`missing_sizes` lists input sizes with no successful iteration; `error_samples` holds the first error message per input size; `problems` is the flattened list printed at the end of the run.

## Metrics Explained

### Latency Percentiles
- **p50 (median)**: 50% of requests complete faster than this
- **p95**: 95% of requests complete faster than this (good for SLA targets)
- **p99**: 99% of requests complete faster than this (captures tail latency)

### Memory Delta
- Tracks memory increase during graph execution
- Helps identify memory leaks or high-memory operations
- Measured in MB (megabytes)

### Throughput
- Operations per second based on mean latency
- Inverse of mean latency: `throughput = 1 / mean_latency`
- Higher is better

### Success Rate
- Percentage of iterations that completed without errors (raised exceptions **and** results reporting a failure status both count as errors)
- Should be 1.0 (100%) for production readiness
- Values < 1.0 indicate stability issues and make the script exit non-zero

## Interpretation Guide

### Good Performance Indicators
- p99 latency < 2x p50 latency (consistent performance)
- Memory delta < 100MB for typical operations
- Success rate = 1.0 (no errors)
- Low std (standard deviation) indicates consistent performance

### Performance Issues
- p99 >> p50 suggests high tail latency (investigate outliers)
- Memory delta > 500MB may indicate memory leaks
- Success rate < 1.0 indicates errors (check logs)
- High std suggests inconsistent performance

## Integration with CI/CD

### Baseline Tracking

```bash
# Create baseline
uv run python tests/benchmarks/benchmark_graphs.py --output baselines/v1.0.0.json

# Compare against baseline (manual review)
diff baselines/v1.0.0.json benchmark_results.json
```

### Performance Regression Detection

Add this to your CI pipeline:

```bash
# Run benchmarks
uv run python tests/benchmarks/benchmark_graphs.py --iterations 30

# Compare p95 latencies against baseline
python scripts/compare_benchmarks.py baselines/main.json benchmark_results.json --threshold 1.2
```

## Tips for Accurate Benchmarking

1. **Warm-up runs**: First iteration may be slower due to model loading
2. **Sufficient iterations**: Use ≥20 iterations for statistical significance
3. **Stable environment**: Run on dedicated hardware without background tasks
4. **Real LLM testing**: For production estimates, use `llm_provider=openai` or `anthropic`
5. **Cache effects**: Set `cache_enabled=false` to measure uncached performance

## Advanced Usage

### With Real LLMs

```bash
# Set environment variables
export FAIRSENSE_LLM_PROVIDER=openai
export FAIRSENSE_LLM_MODEL_NAME=gpt-4
export FAIRSENSE_LLM_API_KEY=your_key_here

# Run benchmarks
uv run python tests/benchmarks/benchmark_graphs.py --iterations 10
```

### With Telemetry Enabled

```bash
# Enable detailed logging
export FAIRSENSE_TELEMETRY_ENABLED=true
export FAIRSENSE_LOG_LEVEL=INFO

# Run benchmarks (logs will show detailed timing)
uv run python tests/benchmarks/benchmark_graphs.py
```

### Custom Input Fixtures

Edit `benchmark_graphs.py` to add custom inputs:

```python
def get_bias_text_inputs() -> dict[str, dict[str, Any]]:
    return {
        "custom_scenario": {
            "text": "Your custom text here...",
            "options": {"temperature": 0.5},
        },
    }
```

## Troubleshooting

### "ModuleNotFoundError: psutil"

```bash
uv pip install psutil
```

### High Memory Usage

- Large models (BLIP-2, LLMs) consume significant memory
- Use `caption_model=fake` and `llm_provider=fake` for lightweight benchmarks
- Run with `--graphs bias_text` to avoid image model loading

### Inconsistent Results

- Ensure no background processes are running
- Use more iterations (`--iterations 100`)
- Check for thermal throttling on laptops
- Disable cache (`FAIRSENSE_CACHE_ENABLED=false`)

## Future Enhancements

- [ ] Automated regression detection
- [ ] Comparison visualization (graphs/charts)
- [ ] Multi-threaded load testing
- [ ] GPU profiling metrics
- [ ] Cost tracking for LLM API calls
