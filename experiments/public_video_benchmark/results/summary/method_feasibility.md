# Method feasibility review

## ExpertAF

- Code available: yes
- Direct arbitrary-video inference: no
- Training required: yes
- Blocking inputs: learner and expert video/pose features, private-path pose checkpoints and extracted InternVideo/PCT features, plus the LLaVA-style training stage
- Decision: skip in the first-round zero-shot benchmark

The published repository is a research training pipeline rather than a released arbitrary-video observer checkpoint. Reconstructing its inputs or training it would violate this round's no-training stop condition.

## FineDiving

- Code available: yes
- Direct arbitrary badminton inference: no
- Generic zero-shot AQA checkpoint: not provided
- Domain: procedure-aware diving action-quality assessment using query/exemplar pairs and FineDiving annotations
- Decision: method feasibility only; retain as a candidate if Video VLM observation fails

The public backbone is not a complete generic quality assessor. Applying the method to badminton would require phase definitions, exemplars, annotations, and training, all outside this round.
