# Video Lesson Package Contract

Use a public source video as the lesson container and one mixed-doubles
technique package as the teaching unit. A package may explain a serve/receive
route, front/rear connection, recovery movement, or another controlled action;
it must never turn match context or tactical commentary into a coach-action
reference.

1. Resolve the source video's complete title- and reviewed-ASR-supported semantic inventory before selecting media. Keep each controlled action, family, taxonomy path, semantic interval, and review status.
2. Use the title and reviewed semantic inventory to assign the teaching topic. Use VLM only to reject non-action material and test visual compatibility; it cannot invent the tactical identity of a window.
3. Reject talking, pointing, held poses, isolated racket gestures, grip/racket-face explanation, match replay, tactical review, conditioning, rehabilitation, equipment content, and another player's rally as a correct coach action.
4. Preserve an admitted action as one continuous source-video episode. Do not join different repetitions or borrow frames from a different route.
5. Automatically admit an episode only when one high-confidence, high-purity, semantically compatible repetition visibly covers a meaningful start, active path, finish, and recovery, has the required body/racket visibility, and carries neither `no_full_action` nor `incomplete_sequence`.
6. Keep partial demonstrations only in private review media. Preserve their wider context for a reviewer, label it `review_context_not_confirmed_stage`, and never publish it as stage teaching.
7. For an admitted episode, render 7–9 ordered frames across preparation, start, loading, acceleration, approximate contact window, follow-through, and recovery. Frames are navigation aids inside the already-admitted episode; they cannot manufacture missing stages.
8. Store strict action bounds separately from bounded playback bounds. Playback may retain a short post-roll for landing or shuttle flight, but must end before the next action or unrelated explanation.
9. Attach an original short teaching point and an evidence boundary to every displayed stage. Show the playback clip before its storyboard.
10. Do not quote or reconstruct subtitles, ASR, paid-course content, or private model output. Keep raw media, ASR, frames, prompts, model responses, review ledgers, and absolute paths in ignored private storage.
11. Do not claim precise shuttle contact, racket-face angle, grip pressure, force, true internal rotation, calibrated 3D motion, fixed pair roles, or opponent intent from ordinary monocular video.
12. Publish only `agent_reviewed`, complete, semantically resolved packages. If a supported topic has no such package, return `no_reliable_action_episode`; never substitute a partial candidate, speech frame, match footage, or another technique.

When an approved private staging root is installed through
`BADMINTON_ZHENG_SIWEI_VIDEO_LESSON_ROOT`, it must contain
`video-lessons-index.yaml` and its `video-lessons/` shards. The path belongs to
deployment configuration and must not be committed.

For an explicitly owner-approved public sample, first verify that it is listed
in `references/public-demo-cases.yaml`, then use the repository-wide
`scripts/export_public_lesson.py`. Require a Tier A official source, Zheng
Siwei as the primary demonstrator, correct-example context, at least 20 seconds
of reviewed context on both sides, one uncut action repetition, and exactly
seven ordered JPEGs.
