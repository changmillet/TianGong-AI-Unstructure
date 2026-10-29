"""SCI operational CLI; old KB CLI and workers are unchanged."""
import argparse
import json
import logging
import os
import socket
from dataclasses import replace
from dotenv import load_dotenv
from src.kb_parse_worker.config import WorkerConfig
from . import registry
from .worker import Finalizer,Submitter


def main(argv=None):
    parser=argparse.ArgumentParser(description='SCI local parsing workers')
    parser.add_argument('--env-file')
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('run','once'):
        sub=commands.add_parser(name)
        sub.add_argument('--worker',choices=['submitter','finalizer'],required=True)
    sub=commands.add_parser('enqueue')
    sub.add_argument('--document-id',required=True)
    sub.add_argument('--job-id',required=True,help='Stable request UUID; reuse it when retrying registration')
    sub.add_argument('--owner-id')
    sub.add_argument('--reprocess',action='store_true')
    sub.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    if args.env_file:
        load_dotenv(args.env_file,override=True)
    config=WorkerConfig.from_env()
    if args.command=='enqueue':
        plan=registry.plan(config,args.document_id,args.job_id)
        print(json.dumps(registry.enqueue(config,plan,args.owner_id,args.reprocess) if args.execute else plan))
        return 0
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s')
    config=replace(config,worker_id=f'sci-{args.worker}-{socket.gethostname()}-{os.getpid()}')
    worker=(Submitter if args.worker=='submitter' else Finalizer)(config)
    if args.command=='run':
        worker.run_forever()
    else:
        worker.run_once()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
