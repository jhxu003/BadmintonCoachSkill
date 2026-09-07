# Comparison with the supplied Rally Lab archive

Archive reviewed: `/public/home/jhxu/badminton/badminton-coach-main.zip` (Rally Lab).

## What Rally Lab implements

Rally Lab is a product-oriented full-stack MVP: React, Express, SQLite, account sessions, private uploads, asynchronous jobs, reports, trends, usage accounting, sharing, and community/admin foundations. Its real analysis provider samples 6/12/18 JPEG frames with FFmpeg and sends them to the hosted OpenAI Responses API. The same model response generates observations, phase scores, weaknesses, and training recommendations.

It is strongest as a usable application shell: authentication, user isolation, task lifecycle, persistence, upload validation, and product screens are already present.

## How this repository differs

| Dimension | Rally Lab archive | BadmintonCoachSkill + public benchmark |
|---|---|---|
| Primary goal | Full-stack coaching product MVP | Evidence-bounded coaching knowledge and reproducible model viability study |
| Visual model | Hosted OpenAI API | Local open-source Qwen 2B/3B baselines |
| Model role | Observation, scores, weaknesses, and recommendations in one response | Observation only; coaching stays in the existing Skill |
| Diagnosis | Free model output under a product JSON schema | Existing rule matcher and coach-specific knowledge |
| Evaluation data | User uploads / deterministic demo fallback | Fixed 60-clip public BADS_CLL benchmark |
| Ground truth discipline | Phase/overall scores are model-generated | Dataset rating is kept separate from model-generated issues |
| Reproducibility | Product task metadata and usage | Manifest seed, model/prompt/schema/media hashes, environment, cached per-sample outputs |
| Deployment | Requires Node server for full functionality | Static public benchmark on GitHub Pages; inference remains offline |
| Privacy | Strong user-level private media isolation | Public-license sample evaluation, with raw dataset excluded from Git |

## Reusable ideas

Rally Lab's upload validation, job state model, user isolation, provider interface, and report history are useful if BadmintonCoachSkill later becomes a private-video product. Its frontend also demonstrates a broader dashboard workflow than the current public lesson site.

The analysis logic should not be copied into this first-round benchmark: it lets the VLM prescribe coaching, invents 0–100 action/phase scores without benchmark ground truth, relies on a hosted closed API, and uses sparse JPEG frames. Those choices answer a different product question from the current zero-shot open-model viability study.
