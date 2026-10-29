"""Publish the current parsing output directly under the SCI document UUID."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from src.kb_parse_worker.parser_adapter import ParsedDocument

PIPELINE = "sci-ingestion-contract-v1"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def document_path(root: Path, document_id: str) -> Path:
    return root / str(UUID(document_id))


def reject_vectors(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in {"embedding", "embeddings", "vector", "vectors"}:
                raise ValueError("parse-only result contains vector fields")
            reject_vectors(item)
    elif isinstance(value, list):
        for item in value:
            reject_vectors(item)


def verify_run(directory: Path, document_id: str, run_id: str, source_hash: str) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text())
    expected = {"pipeline": PIPELINE, "schema_version": 1, "stage": "parsed",
                "document_id": document_id, "run_id": run_id, "source_sha256": source_hash}
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError("manifest identity mismatch")
    files = manifest.get("files", {})
    if set(files) != {"parsed.pkl", "fulltext.txt"}:
        raise ValueError("manifest must describe exactly parsed.pkl and fulltext.txt")
    for name, info in files.items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("artifact missing or symlinked")
        if path.stat().st_size != info["size_bytes"] or digest(path) != info["sha256"]:
            raise ValueError("artifact checksum mismatch")
    if not isinstance(manifest.get("parsed_item_count"), int) or manifest["parsed_item_count"] < 1:
        raise ValueError("empty manifest item count")
    return manifest


def publish(root: Path, document_id: str, run_id: str, source_hash: str,
            parsed: ParsedDocument, parser: dict) -> Path:
    destination = document_path(root, document_id)
    if destination.exists():
        raise FileExistsError("run already exists; verify and finalize instead of overwriting")
    if not parsed.result or not parsed.txt or not parsed.txt.strip():
        raise ValueError("parser must return nonempty chunks and full text")
    if any(not isinstance(x, dict) or not isinstance(x.get("text"), str)
           or not x["text"].strip() for x in parsed.result):
        raise ValueError("every parsed item must contain nonempty text")
    reject_vectors(parsed.result)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=destination.parent))
    try:
        with (staging / "parsed.pkl").open("wb") as stream:
            pickle.dump(parsed.result, stream, protocol=4)
            stream.flush()
            os.fsync(stream.fileno())
        with (staging / "fulltext.txt").open("w", encoding="utf-8") as stream:
            stream.write(parsed.txt)
            stream.flush()
            os.fsync(stream.fileno())
        manifest = {
            "schema_version": 1, "pipeline": PIPELINE, "stage": "parsed",
            "document_id": document_id, "run_id": run_id, "source_sha256": source_hash,
            "created_at": datetime.now(timezone.utc).isoformat(), "parser": parser,
            "parsed_item_count": len(parsed.result),
            "dropped_empty_text_count": parsed.dropped_empty_text_count,
            "files": {name: {"size_bytes": (staging / name).stat().st_size,
                              "sha256": digest(staging / name)}
                      for name in ("parsed.pkl", "fulltext.txt")},
        }
        with (staging / "manifest.json").open("w", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        verify_run(staging, document_id, run_id, source_hash)
        staging.rename(destination)
        return destination
    finally:
        if staging.exists():
            shutil.rmtree(staging)
