"""Feasibility marker only: official ExpertAF is not an arbitrary-video observer."""


class ExpertAFObserver:
    def load(self) -> None:
        raise RuntimeError(
            "ExpertAF requires learner/expert pose and video features plus training artifacts; "
            "it is intentionally skipped in the zero-shot first-round benchmark."
        )
