verify_analysis
===============

verify_analysis is a lightweight log-analysis tool for benchmark verification runs. It parses raw verifier output, extracts per-instance metadata and verdicts, and writes a compact tab-separated summary that is easy to inspect, filter, or plot later.

It is designed around logs that contain repeated test blocks delimited by `idx:` at the start of each instance and `Result:` at the end.

Supported Features
------------------

The parser extracts the following information when it is present in the log:

* benchmark and instance identifiers
* ONNX model and VNNLIB specification paths
* verified status and success flags
* total violation count
* attack time and total runtime
* test type classification: `CE`, `BaB`, or `AC`
* extra metrics such as initial CROWN bounds, alpha/beta optimization time, unstable neuron counts, BaB rounds, and visited domains

The repository currently includes:

* `parser.py`: parses a log file into structured `TestResult` objects
* `results.py`: converts parsed logs into a TSV-style summary file
* `logs/`: example verifier outputs
* `sums/`: example summary files generated from the logs

Installation and Setup
----------------------

The tool only depends on the Python standard library.

If you want to keep the environment isolated, create and activate a virtual environment first:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instructions
------------

To summarize a verifier log into a tab-separated output file, run:

```bash
python results.py logs/full_benchmark_output output.csv
```

If you omit the second argument, the script writes to `output.csv` by default.

You can also use the parser directly from Python:

```python
from parser import parser

tests = parser("logs/full_benchmark_output")
```

Output Format
-------------

Each output row contains:

* benchmark name
* ONNX model path
* VNNLIB specification path
* attack time
* mapped status (`SAT`, `UNSAT`, or `timeout` when applicable)
* total time

A typical row looks like this:

```text
cifar2020	./benchmarks/cifar2020/nets/cifar10_2_255_simplified.onnx	./benchmarks/cifar2020/specs/cifar10/cifar10_spec_idx_0_eps_0.00784_n1.vnnlib	0.298300000	SAT	0.000000000
```

Notes
-----

* Relative paths are normalized when a `root_path:` entry is present near the top of the log.
* The parser treats `unsafe` as `SAT` and `safe` as `UNSAT` in the summary output.
* `plots.py` is currently reserved for future visualization helpers.
