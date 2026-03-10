from pathlib import Path


class SnapshotStore:
    """Milestone 0 JSONL store placeholder."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.touch(exist_ok=True)

    def append(self, snapshot: dict) -> None:
        _ = snapshot
        # Full JSONL append is deferred to later milestones.
        return
