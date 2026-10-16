from pathlib import Path


class LocalFileStore:
    """Borrado recuperable: el renombrado precede a la transacción de base de datos."""

    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def path(self, identifier: str, suffix: str) -> Path:
        return self.root / (identifier + suffix)

    def save(self, identifier: str, suffix: str, data: bytes) -> Path:
        target = self.path(identifier, suffix)
        staged = target.with_suffix(suffix + ".partial")
        try:
            staged.write_bytes(data)
            staged.replace(target)
        except Exception:
            staged.unlink(missing_ok=True)
            raise
        return target

    def stage_delete(self, identifier: str, suffix: str) -> tuple[Path, Path]:
        original = self.path(identifier, suffix)
        tombstone = original.with_suffix(suffix + ".deleted")
        if original.exists():
            original.replace(tombstone)
        return original, tombstone

    def rollback_delete(self, original: Path, tombstone: Path) -> None:
        if tombstone.exists():
            tombstone.replace(original)

    def finish_delete(self, tombstone: Path) -> None:
        tombstone.unlink(missing_ok=True)

    def recover_deletions(self, record_exists) -> None:
        for tombstone in self.root.glob("*.deleted"):
            original = tombstone.with_suffix("")
            if record_exists(original.stem):
                if original.exists():
                    tombstone.unlink()
                else:
                    tombstone.replace(original)
            else:
                tombstone.unlink()
