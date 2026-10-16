import pytest

from videofacturacion.storage.files import LocalFileStore


def test_deletion_can_be_rolled_back_or_recovered(tmp_path):
    store = LocalFileStore(tmp_path)
    target = store.save("synthetic", ".csv", b"synthetic")
    staged = store.stage_delete("synthetic", ".csv")
    assert not target.exists() and staged[1].exists()
    store.rollback_delete(*staged)
    assert target.read_bytes() == b"synthetic"
    store.stage_delete("synthetic", ".csv")
    store.recover_deletions(lambda identifier: True)
    assert target.read_bytes() == b"synthetic"
    store.stage_delete("synthetic", ".csv")
    store.recover_deletions(lambda identifier: False)
    assert list(tmp_path.iterdir()) == []


def test_failed_write_removes_partial_file(tmp_path, monkeypatch):
    store = LocalFileStore(tmp_path)
    original = type(tmp_path).replace

    def fail_replace(path, target):
        if path.suffix == ".partial":
            raise OSError("simulated disk error")
        return original(path, target)

    monkeypatch.setattr(type(tmp_path), "replace", fail_replace)
    with pytest.raises(OSError):
        store.save("synthetic", ".csv", b"synthetic")
    assert list(tmp_path.iterdir()) == []
