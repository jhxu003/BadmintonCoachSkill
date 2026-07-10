# Report Contract

This project is non-official and non-authorized. 这是非官方研究项目。The report must not state or imply that Liu Hui personally judged the player, certified the diagnosis, or officially authorized this skill.

## Required Sections

Each issue must include:

1. Problem: one concise diagnosis.
2. Evidence: observable facts from the input with keyframe labels or timestamps and the matching `visual-evidence-contract.yaml` diagnosis id.
3. Evidence boundary: what is missing, what remains a 2D proxy, and which stronger claim is blocked.
4. Cause: why the issue affects power, consistency, injury risk, or recovery.
5. Correction principle: the Liu Hui-inspired coaching idea as an original summary.
6. Drill: one concrete practice from `drills.yaml`.
7. Retest metric: what to check in the next upload.

## Safety Boundaries

- Say `证据不足` when the input lacks required observations.
- Do not use an ASR timestamp, VLM visibility count, or pose detection count as standalone proof of a biomechanical diagnosis.
- Label internal rotation and other invisible 3D mechanics as proxy judgments unless calibrated multi-view evidence exists.
- 不模仿 Liu Hui's personal voice, catchphrases, or course wording.
- 不声称 "刘辉亲自判断", "刘辉认证", or "官方授权".
- Do not create high-confidence diagnosis from third-party discussion alone.
- Do not give medical advice; if pain is present, suggest reducing intensity and consulting a qualified professional.

## Recommended Tone

Use direct coaching language:

- "当前最优先改的是..."
- "证据是..."
- "先不要急着追求..."
- "下次复测看..."

Avoid vague comments:

- "注意发力"
- "多练习"
- "动作不够标准"
