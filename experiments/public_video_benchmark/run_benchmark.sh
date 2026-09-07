#!/usr/bin/env bash
set -euo pipefail

BENCHMARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$BENCHMARK_DIR/../.." && pwd)"
cd "$PROJECT_DIR"
MODEL="all"
SKIP_DOWNLOAD=0
SKIP_MODEL_DOWNLOAD=0
SMOKE_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-download) SKIP_DOWNLOAD=1 ;;
    --skip-model-download) SKIP_MODEL_DOWNLOAD=1 ;;
    --smoke-only) SMOKE_ONLY=1 ;;
    --model) MODEL="$2"; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

PREPARE_ARGS=()
[[ "$SKIP_DOWNLOAD" == 1 ]] && PREPARE_ARGS+=(--skip-download)
python "$BENCHMARK_DIR/scripts/prepare_badminsense.py" "${PREPARE_ARGS[@]}"
python "$BENCHMARK_DIR/scripts/select_benchmark.py" --samples-per-cell 5 --seed 42

MODELS=(qwen3-vl-2b qwen25-vl-3b)
[[ "$MODEL" != all ]] && MODELS=("$MODEL")
for model in "${MODELS[@]}"; do
  if [[ "$SKIP_MODEL_DOWNLOAD" == 0 ]]; then
    case "$model" in
      qwen3-vl-2b) hf download Qwen/Qwen3-VL-2B-Instruct --local-dir models/Qwen3-VL-2B-Instruct ;;
      qwen25-vl-3b) hf download Qwen/Qwen2.5-VL-3B-Instruct --local-dir models/Qwen2.5-VL-3B-Instruct ;;
    esac
  fi
  python "$BENCHMARK_DIR/scripts/run_observer.py" --model "$model" --smoke
done

python "$BENCHMARK_DIR/scripts/run_skill.py" --all
for model in "${MODELS[@]}"; do
  python "$BENCHMARK_DIR/scripts/smoke_gate.py" --model "$model"
done
if [[ "$SMOKE_ONLY" == 0 ]]; then
  for model in "${MODELS[@]}"; do
    python "$BENCHMARK_DIR/scripts/run_observer.py" --model "$model"
  done
  python "$BENCHMARK_DIR/scripts/run_skill.py" --all
fi
python "$BENCHMARK_DIR/scripts/evaluate.py"
python "$BENCHMARK_DIR/scripts/build_site_data.py"
