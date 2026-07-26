# Video Lesson Package Contract

Use the source video as the lesson container and one Li Yuxuan technique package as the teaching unit. One source video may yield several independently reviewed techniques and several pure-action episodes per technique.

1. Resolve every reviewed-ASR-supported technique in the source before selecting visual material. Record its controlled action, framework-compatible taxonomy path, semantic interval, and review status. Do not reduce a multi-topic video to a single title label.
2. Use the public title and the reviewed private ASR timestamp index only to route the teaching topic. Use VLM frames only to reject non-action material and check visible compatibility; it must never invent a technical identity or replace the reviewed routing.
3. Scan the whole source for candidate actions. Reject speech, pointing, ordinary gestures, shuttle throwing without a racket action, grip adjustment, racket-face placement, isolated wrist or forearm rotation, and held poses.
4. Preserve an admitted action as one continuous source-video episode. Never assemble an action route from different repetitions. Several clean repetitions may remain separate episodes of the same technique.
5. An automatic candidate may enter manual review only when a single repetition has high confidence, high demonstration purity, semantic compatibility, a clear person, required racket visibility, a full action trajectory, and at least four visible stage codes. Partial or uncertain episodes remain private and cannot populate a reliable lesson.
6. Render nine ordered navigation stages within one admitted episode: preparation, start, loading, acceleration, approximate contact neighborhood, release, follow-through, recovery, and ready-again. They show a continuous process; they do not manufacture evidence for an unseen stage.
7. Keep the strict action boundary separate from the playback boundary. A playback clip may retain 1–2 seconds after the action to show shuttle flight, landing, or recovery, but must end before a different action or speech segment.
8. Attach a teaching point and an evidence boundary to every stage. First show the continuous clip, then the ordered stages; never replace the lesson with a three-frame or one-frame gallery.
9. Do not quote or reconstruct private ASR, subtitles, or raw model output. Publish only short original summaries, controlled labels, agent-reviewed lesson metadata, and approved staged media.
10. Do not claim exact shuttle contact, racket-face angle, grip pressure, force, true internal rotation, calibrated 3D motion, or opponent intent from ordinary monocular video. Mark missing evidence as unknown or request a clearer demonstration.
11. If a reviewed topic has no reliable complete episode, retain the semantic gap privately and return `no_reliable_action_episode`; never substitute talking, a partial candidate, or another technique.

Run the staged pipeline as `inventory`, `prepare`, `gate`, `materialize`, `summarize`, and `publish`. The pipeline must directly reuse restored private source videos when present, rather than re-downloading or copying the corpus. Keep sources, candidate frames, clips, ASR, model output, review decisions, databases, and logs in private ignored storage. A deployment may set `BADMINTON_LI_YUXUAN_VIDEO_LESSON_ROOT` to an approved private staging root; do not commit that absolute path.
