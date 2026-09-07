# Public Video Benchmark

This experiment asks one deliberately narrow question:

> Are existing low-cost, open-source Video VLMs already good enough to act as the visual observer for BadmintonCoachSkill?

It is a zero-shot pipeline. It does not train, fine-tune, or adapt a model.

```text
Original BADS_CLL GIF
        ↓
Qwen video observation
        ↓
repository VideoObservation schema
        ↓
existing match_diagnosis()
        ↓
issue → correction → drill → retest
```

## Data

The first round uses [BadminSense / BADS_CLL](https://github.com/taizhouchen/BadminSense_Dataset): 848 public stroke samples covering `BackhandTransition`, `ForehandHigh`, `ForehandLob`, and `ForehandKill`.

The benchmark selects 60 samples with seed 42:

- four stroke types;
- low, median-nearest, and high quality tiers computed separately per stroke;
- five clips per stroke-tier cell;
- player diversity preferred within each cell.

The original `actionEval` value is retained. Normalized ratings are stored separately. Raw data and the 14 GB archive are ignored by Git.

> BADS_CLL is CC BY-NC-ND 4.0. This benchmark is non-commercial research. Public selected GIFs must remain unmodified and carry attribution; decoded frames are temporary inference inputs and are not published.

## Models

- `Qwen/Qwen3-VL-2B-Instruct`
- `Qwen/Qwen2.5-VL-3B-Instruct`

Each model first runs one sample from every stroke-tier cell (12 clips). It proceeds to all 60 clips only when at least 10 of 12 runs decode, return schema-valid JSON, and pass through the existing Skill without crashing.

ExpertAF and FineDiving are method-feasibility reviews only in this round. See [method_feasibility.md](results/summary/method_feasibility.md).

## Install

```bash
python -m pip install -e ".[benchmark,test]"
```

GPU inference is expected. A management/login node without CUDA can prepare data, select the manifest, evaluate existing outputs, and build the site, but should not run the VLMs.

## Run

Use an existing official archive when Google Drive is unavailable:

```bash
python experiments/public_video_benchmark/scripts/prepare_badminsense.py \
  --archive /path/to/BADS_CLL_OPENACCESS_V1.zip
```

Or allow the script to download the official Drive file:

```bash
python experiments/public_video_benchmark/scripts/prepare_badminsense.py
```

Select the benchmark:

```bash
python experiments/public_video_benchmark/scripts/select_benchmark.py \
  --samples-per-cell 5 --seed 42
```

Run smoke tests:

```bash
python experiments/public_video_benchmark/scripts/run_observer.py --model qwen3-vl-2b --smoke
python experiments/public_video_benchmark/scripts/run_observer.py --model qwen25-vl-3b --smoke
python experiments/public_video_benchmark/scripts/run_skill.py --all
python experiments/public_video_benchmark/scripts/smoke_gate.py --model qwen3-vl-2b
python experiments/public_video_benchmark/scripts/smoke_gate.py --model qwen25-vl-3b
```

After both gates pass, omit `--smoke`, then run:

```bash
python experiments/public_video_benchmark/scripts/run_skill.py --all
python experiments/public_video_benchmark/scripts/evaluate.py
python experiments/public_video_benchmark/scripts/build_site_data.py
```

The orchestrator supports `--skip-download`, `--skip-model-download`, `--smoke-only`, and `--model`:

```bash
bash experiments/public_video_benchmark/run_benchmark.sh --smoke-only --skip-download
```

## Outputs and cache

Every model/sample directory contains:

- `raw_output.txt`
- `observation.json`
- `run_meta.json`
- `coach_result.json`

Inference is reused only when the media hash, prompt hash, schema hash, model identity, and inference configuration still match. Reproducibility metadata includes the Git commit, model ID, Python, Transformers, Torch, CUDA, sampling rate, frame count, hashes, and random seed/config.

## Evaluation

The generated summary reports:

- schema success rate;
- end-to-end pipeline success rate;
- mapped stroke recognition accuracy and confusion matrix;
- average issue count and confidence-weighted burden by quality tier;
- high-quality multi-issue false-alarm proxy;
- low-versus-high separation;
- runtime.

It must not report “technical error accuracy.” BADS_CLL has no fine-grained error labels. Case review should classify failures as action recognition, temporal understanding, fine-grained observation, hallucination, schema, or Skill coverage failures.

## Static site

`build_site_data.py` publishes the benchmark to `web/public/benchmark/`, which the existing Vite Pages workflow deploys as:

<https://jhxu003.github.io/BadmintonCoachSkill/benchmark/>

Dataset labels and model-generated issues are deliberately rendered as separate evidence layers.
