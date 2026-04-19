# AgentMind Performance Benchmarks

Comprehensive performance benchmarking suite comparing AgentMind with other popular multi-agent frameworks.

## Overview

This benchmark suite measures and compares:
- **Latency**: Response time for various scenarios
- **Memory Usage**: RAM consumption during operations
- **Token Efficiency**: Number of tokens used
- **Throughput**: Requests handled per second

## Frameworks Compared

- **AgentMind**: Lightweight multi-agent framework
- **CrewAI**: Role-based agent collaboration
- **LangGraph**: Graph-based agent orchestration
- **AutoGen**: Microsoft's multi-agent framework

## Benchmark Scenarios

1. **Simple Task**: Single-agent, single-round interaction
2. **Complex Collaboration**: Multi-agent, multi-round collaboration
3. **Tool Usage**: Agent using external tools/functions
4. **Long Conversation**: Extended conversation with memory management

## Running Benchmarks

### Prerequisites

```bash
pip install matplotlib numpy psutil
```

### Run Full Benchmark Suite

```bash
python performance_benchmark.py
```

This will:
- Run all benchmark scenarios
- Measure performance metrics
- Save results to `benchmark_results.json`
- Print summary to console

### Generate Visualizations

```bash
python visualize_benchmarks.py
```

This will:
- Load benchmark results
- Generate comparison charts
- Create markdown report with embedded charts
- Save to `charts/` directory

## Output Files

- `benchmark_results.json`: Raw benchmark data
- `charts/*.png`: Visualization charts (7 charts)
- `BENCHMARK_REPORT.md`: Comprehensive report with analysis

## Charts Generated

1. **Latency Comparison**: Average latency across frameworks
2. **Memory Comparison**: Average memory usage
3. **Scenario Latency**: Latency breakdown by scenario
4. **Scenario Memory**: Memory breakdown by scenario
5. **Performance Radar**: Multi-dimensional performance view
6. **Token Usage**: Token efficiency comparison
7. **Overall Score**: Composite performance metric

## Interpreting Results

### Latency
- Lower is better
- Measured in milliseconds (ms)
- Includes LLM inference time

### Memory
- Lower is better
- Measured in megabytes (MB)
- Peak memory during execution

### Tokens
- Lower is better (for same task)
- Indicates efficiency of prompting
- Directly impacts API costs

## Customizing Benchmarks

Edit `performance_benchmark.py` to:
- Add new scenarios
- Change test parameters
- Modify measurement methods
- Add new frameworks

## CI/CD Integration

Run benchmarks in CI:

```yaml
- name: Run Benchmarks
  run: |
    python benchmarks/performance_benchmark.py
    python benchmarks/visualize_benchmarks.py
```

## Notes

- Benchmarks use Ollama with llama3.2 by default
- Results may vary based on hardware
- Some framework results are simulated for comparison
- Run multiple times for statistical significance

## Contributing

To add new benchmarks:
1. Add scenario method to `PerformanceBenchmark` class
2. Call from `run_benchmarks()` function
3. Update visualization scripts if needed
4. Document in this README

## License

MIT License - see LICENSE file for details
