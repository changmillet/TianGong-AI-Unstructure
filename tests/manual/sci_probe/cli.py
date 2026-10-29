"""Test the existing Worker/PGMQ/parser up to the parsing boundary only."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import UUID

import psycopg2
from dotenv import load_dotenv

from src.kb_parse_worker.config import database_url_from_env
from src.kb_parse_worker.parser_adapter import parse_with_unstructure_serve
from .artifacts import PIPELINE, digest, publish, document_path, verify_run
from .registry import complete, journal, cancel_probe


def source_path(root: Path, doi: str) -> Path:
    # Match the current SCI layout: slash remains the publisher directory.
    path = root / (quote(quote(doi, safe="/"), safe="/") + ".pdf")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("PDF must be a regular file inside the SCI source root")
    with resolved.open("rb") as stream:
        if b"%PDF-" not in stream.read(1024):
            raise ValueError("source does not have a PDF header")
    return resolved


def prior_artifacts(root: Path, document_id: str, doi: str) -> list[str]:
    if not root.is_dir():
        raise ValueError("legacy artifact root must exist for the unparsed check")
    names = {document_id, doi.rsplit("/", 1)[-1], quote(doi, safe=""),
             quote(quote(doi, safe=""), safe="")}
    found = []
    for path in root.rglob("*.pkl"):
        if any(name in path.stem for name in names):
            found.append(str(path))
    return found


class ParseBoundaryReached(BaseException):
    """Test-only stop before the existing worker's embedding writer."""


def main(argv=None):
    from dataclasses import replace
    from unittest.mock import patch
    from src.kb_parse_worker.config import WorkerConfig
    from src.kb_parse_worker.worker import ParseWorker
    from .registry import COLLECTION_PATH, register_and_reserve

    parser = argparse.ArgumentParser(description="Manual single-PDF integration probe; not a production mode")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--document-id", type=lambda s: str(UUID(s)), required=True)
    parser.add_argument("--run-id", type=lambda s: str(UUID(s)), required=True)
    parser.add_argument("--owner-id", type=lambda s: str(UUID(s)), required=True)
    parser.add_argument("--pdf-root", type=Path, required=True)
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--parser-version", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.env_file.is_file():
        raise ValueError("explicit runtime env file does not exist")
    load_dotenv(args.env_file, override=False)
    config=WorkerConfig.from_env()
    # Only this process gets the test worker identity and one-message timeout.
    config=replace(config,worker_id="sci-probe-"+args.run_id,queue_name="kb_parse_queue",
                   parse_job_timeout_seconds=900,lock_seconds=1800,queue_vt_seconds=1800)
    conn=psycopg2.connect(config.database_url,connect_timeout=15)
    message=None
    try:
        before=journal(conn,args.document_id)
        raw=source_path(args.pdf_root,before["doi"])
        output=document_path(args.output_root.resolve(),args.document_id)
        alias=config.nas_raw_root / COLLECTION_PATH.strip("/") / (args.document_id+".pdf")
        plan={"pipeline":PIPELINE,"document_id":args.document_id,"run_id":args.run_id,
              "doi":before["doi"],"source_path":str(raw),"filename":raw.name,
              "source_bytes":raw.stat().st_size,"source_sha256":digest(raw),
              "output_path":str(output),"raw_uri":str(alias.absolute()),
              "registered_at":datetime.now(timezone.utc).isoformat()}
        existing=prior_artifacts(args.legacy_root,args.document_id,before["doi"])
        if existing:
            raise ValueError(f"historical parsing artifacts exist: {existing[:5]}")
        if output.exists() or alias.exists() or alias.is_symlink():
            raise ValueError("test output/input alias already exists; inspect before rerunning")
        print(json.dumps({"mode":"execute" if args.execute else "plan",**plan,
                          "queue":"kb_parse_queue","worker":"ParseWorker",
                          "parser_endpoint":config.unstructure_serve_two_stage_base_url
                          if config.use_two_stage_parser else config.unstructure_serve_url},ensure_ascii=False),flush=True)
        if not args.execute:
            return 0
        alias.parent.mkdir(parents=True,exist_ok=True)
        alias.symlink_to(raw)
        message=register_and_reserve(conn,plan,args.owner_id,config.queue_vt_seconds)
        print(json.dumps({"job_id":message.job_id,"pgmq_msg_id":message.msg_id}),flush=True)
        captured={}
        def capture(config,job_id,snapshot,parsed,deadline,lease=None):
            if lease: lease.check()
            deadline.check()
            if digest(raw)!=plan["source_sha256"]:
                raise ValueError("source changed during parsing")
            publish(args.output_root.resolve(),args.document_id,args.run_id,plan["source_sha256"],
                    parsed,{"endpoint":config.unstructure_serve_two_stage_base_url
                            if config.use_two_stage_parser else config.unstructure_serve_url,
                            "profile":config.parser_profile,"version":args.parser_version,
                            "worker":"ParseWorker","job_id":job_id,"return_txt":True})
            captured["manifest"]=verify_run(output,args.document_id,args.run_id,plan["source_sha256"])
            raise ParseBoundaryReached()
        # Only the post-parser boundary is substituted. Real PGMQ, claim RPC,
        # lease heartbeat, file validation and parser calls execute unchanged.
        with patch("src.kb_parse_worker.worker.write_processed_artifacts_from_parsed",capture), \
             patch("src.kb_parse_worker.worker.add_chunk_embeddings",side_effect=AssertionError("embedding forbidden in probe")), \
             patch("src.kb_parse_worker.worker.complete_parse_local_ready_and_archive_with_retry",
                   side_effect=AssertionError("cloud handoff forbidden in probe")):
            try:
                ParseWorker(config).process_message(message)
            except ParseBoundaryReached:
                pass
        if "manifest" not in captured:
            raise RuntimeError("worker did not reach parser boundary; inspect the registered job")
        complete(conn,plan,message,config.worker_id,captured["manifest"],digest(output/"manifest.json"),before)
        if journal(conn,args.document_id)!=before:
            raise ValueError("SCI row changed concurrently; inspect before accepting")
        print(json.dumps({"status":"parsed","document_id":args.document_id,"run_id":args.run_id,
                          "job_id":message.job_id,"pgmq_msg_id":message.msg_id,
                          "parsed_item_count":captured["manifest"]["parsed_item_count"],
                          "output_path":str(output),"sci_row_unchanged":True,"cloud_handoff":False}),flush=True)
        return 0
    except BaseException:
        if message is not None:
            cancel_probe(conn,message,config.worker_id)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
