"""Optional integration tests; use only a disposable sci_receiver_test database."""
import os
import unittest
from unittest.mock import patch

import psycopg2
from psycopg2.extras import Json

from src.kb_parse_worker import sci_finalizer as receiver
from tests import test_sci_finalizer as fixtures

DOC, JOB = fixtures.DOC, fixtures.JOB


@unittest.skipUnless(os.getenv('SCI_TEST_DATABASE_URL'), 'requires disposable PostgreSQL')
class PostgresReceiptTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ReceiverTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.conn = psycopg2.connect(os.environ['SCI_TEST_DATABASE_URL'])
        self.addCleanup(self.conn.close)
        with self.conn, self.conn.cursor() as cur:
            cur.execute('select current_database()')
            if cur.fetchone()[0] != 'sci_receiver_test':
                raise RuntimeError('Refusing anything except disposable sci_receiver_test database')
            cur.execute("select to_regclass('public.kb_documents')")
            if cur.fetchone()[0]:
                raise RuntimeError('Expected empty disposable database')
            cur.execute('''create table journals(id uuid primary key, upload_time timestamptz,
                embedding_time timestamptz,fulltext_time timestamptz);
                create table kb_documents(id uuid primary key,document_version int,deleted_at timestamptz,
                sha256 text,metadata_json jsonb,status text,parse_time timestamptz,
                processed_manifest_local_uri text,processed_manifest_hash text,processed_artifact_uuid uuid,
                last_error text,last_error_stage text);
                create table kb_jobs(id uuid primary key,document_id uuid,document_version int,stage text,
                status text,locked_by text,locked_until timestamptz,payload_json jsonb,
                finished_at timestamptz,next_retry_at timestamptz,last_error text)''')
            cur.execute('insert into journals values (%s,now(),null,null)',(DOC,))
            f=self.fixture
            cur.execute('''insert into kb_documents(id,document_version,sha256,metadata_json,status)
                values (%s,1,%s,%s,'parsing')''',(DOC,f.snapshot.sha256,Json(f.meta)))
            cur.execute('''insert into kb_jobs(id,document_id,document_version,stage,status,locked_by,
                locked_until,payload_json) values (%s,%s,1,'parse','running',%s,now()+interval '1 hour',%s)''',
                (JOB,DOC,f.config.worker_id,Json(f.payload)))
        self.addCleanup(self.drop_fixture)

    def drop_fixture(self):
        self.conn.rollback()
        with self.conn, self.conn.cursor() as cur:
            cur.execute('drop table kb_jobs,kb_documents,journals')

    def receive(self):
        f=self.fixture
        return receiver.receive(self.conn,f.config,f.claim,f.snapshot,f.staged)

    def state(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute('select status,locked_by from kb_jobs where id=%s',(JOB,))
            job=cur.fetchone()
            cur.execute('select status,processed_manifest_local_uri from kb_documents where id=%s',(DOC,))
            doc=cur.fetchone()
            cur.execute('select row_to_json(j)::text from journals j where id=%s',(DOC,))
            return job,doc,cur.fetchone()[0]

    def test_real_sql_receipt_replay_and_sci_unchanged(self):
        before=self.state()[2]
        self.receive()
        first=self.state()
        self.assertEqual(first[0],('succeeded',None))
        self.assertEqual(first[1][0],'parsed_local')
        self.assertEqual(first[2],before)
        self.receive()
        self.assertEqual(self.state(),first)

    def test_expired_or_replaced_task_does_not_write(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("update kb_jobs set locked_until=now()-interval '1 second'")
        with self.assertRaises(receiver.SCILeaseLost):
            self.receive()
        self.assertFalse(self.fixture.destination.exists())
        with self.conn, self.conn.cursor() as cur:
            cur.execute("update kb_jobs set locked_until=now()+interval '1 hour',payload_json=jsonb_set(payload_json,'{two_stage,task_id}','\"new-task\"')")
        with self.assertRaises(receiver.SCILeaseLost):
            self.receive()
        self.assertFalse(self.fixture.destination.exists())

    def test_receipt_failure_rolls_back_db_and_replay_repairs(self):
        before=self.state()
        original=receiver.promote
        def expire(staged,destination):
            original(staged,destination)
            with self.conn.cursor() as cur:
                cur.execute("update kb_jobs set locked_until=now()-interval '1 second'")
        with patch.object(receiver,'promote',side_effect=expire):
            with self.assertRaises(receiver.SCILeaseLost):
                self.receive()
        self.assertEqual(self.state(),before)
        self.receive()
        self.assertEqual(self.state()[0],('succeeded',None))


if __name__=='__main__':
    unittest.main()
