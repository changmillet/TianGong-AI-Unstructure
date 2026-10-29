"""Test fixture registration and local-stage receipt; no production RPC changes."""
from psycopg2.extras import Json, RealDictCursor
from src.kb_parse_worker.queue import QueueMessage

COLLECTION_PATH = '/sci_parse_probe'


def journal(conn, document_id):
    with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('select * from public.journals where id=%s', (document_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError('SCI UUID does not exist')
        return dict(row)


def register_and_reserve(conn, plan, owner_id, vt_seconds):
    """Insert + existing enqueue RPC + actual PGMQ read in one transaction.

    Reserving before commit prevents an older consumer taking the new test
    message between enqueue and this bounded one-document worker invocation.
    No other queued message is read or archived.
    """
    with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('select id from auth.users where id=%s', (owner_id,))
        if not cur.fetchone():
            raise ValueError('owner must be an existing operator account')
        cur.execute('select id from public.kb_documents where id=%s', (plan['document_id'],))
        if cur.fetchone():
            raise ValueError('document is already registered; inspect the existing run')
        cur.execute('''insert into public.kb_collections
            (name,path,content_type,raw_retention_policy,processed_retention_policy)
            values ('SCI single-document test',%s,'application/pdf','archive_only','archive_only')
            on conflict (path) do nothing''', (COLLECTION_PATH,))
        cur.execute('select * from public.kb_collections where path=%s for share', (COLLECTION_PATH,))
        collection = cur.fetchone()
        if (collection['raw_retention_policy'] != 'archive_only'
                or collection['processed_retention_policy'] != 'archive_only'):
            raise ValueError('test collection must retain files')
        cur.execute('''insert into public.kb_documents
            (id,primary_collection_id,dedupe_scope,original_filename,file_ext,file_size,
             sha256,status,created_by,owner_user_id,metadata_json,metadata_status)
            values (%s,%s,'sci-single-document-test',%s,'.pdf',%s,%s,'received',%s,%s,%s,'not_applicable')''',
            (plan['document_id'],collection['id'],plan['filename'],plan['source_bytes'],
             plan['source_sha256'],owner_id,owner_id,
             Json({'source_table':'journals','doi':plan['doi'],'manual_probe':plan})))
        cur.execute('''select * from public.mark_raw_ready_and_enqueue_parse(
            %s,%s,%s,%s,%s,%s,%s)''',
            (plan['document_id'],plan['raw_uri'],plan['source_bytes'],plan['source_sha256'],
             owner_id,plan['run_id'],Json({'manual_probe':True,'run_id':plan['run_id']})))
        result=cur.fetchone()
        job_id=str(result['job_id'])
        # One trial only: parser errors must not trigger background retries.
        cur.execute('update public.kb_jobs set max_attempts=1 where id=%s',(job_id,))
        cur.execute('select msg_id,message from pgmq.read(%s,%s,1,%s)',
                    ('kb_parse_queue',vt_seconds,Json({'job_id':job_id})))
        message=cur.fetchone()
        if not message or message['msg_id'] != result['msg_id']:
            raise ValueError('could not reserve the exact test queue message')
        return QueueMessage(int(message['msg_id']),job_id,dict(message['message']))


def complete(conn, plan, message, worker_id, manifest, manifest_hash, expected_journal):
    """Record only local parsing after the probe stops at the parser boundary."""
    with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('select * from public.journals where id=%s for share',(plan['document_id'],))
        if dict(cur.fetchone() or {}) != expected_journal:
            raise ValueError('SCI row changed before receipt')
        cur.execute('''select d.deleted_at,d.document_version,j.status,j.locked_by,
            j.locked_until>now() as lease_valid from public.kb_documents d
            join public.kb_jobs j on j.document_id=d.id where d.id=%s and j.id=%s
            for update of d,j''',(plan['document_id'],message.job_id))
        row=cur.fetchone()
        if (not row or row['deleted_at'] or row['document_version']!=1
                or row['status']!='running' or row['locked_by']!=worker_id or not row['lease_valid']):
            raise ValueError('test job lost ownership before local-stage receipt')
        cur.execute('''update public.kb_jobs set status='succeeded',finished_at=now(),
            locked_by=null,locked_until=null,payload_json=payload_json || %s where id=%s''',
            (Json({'manual_probe':True,'stopped_after':'parser','manifest_sha256':manifest_hash}),message.job_id))
        cur.execute('''update public.kb_documents set status='parsed',parse_time=%s,
            processed_manifest_local_uri=%s,processed_manifest_hash=%s,
            processed_artifact_uuid=%s where id=%s''',
            (manifest['created_at'],plan['output_path']+'/manifest.json',manifest_hash,
             plan['run_id'],plan['document_id']))
        cur.execute('select pgmq.archive(%s,%s) as archived',('kb_parse_queue',message.msg_id))
        if not cur.fetchone()['archived']:
            raise ValueError('test message was not archived')


def cancel_probe(conn, message, worker_id):
    """Contain an unsuccessful test without scheduling a background retry."""
    conn.rollback()
    with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''select * from public.kb_jobs where id=%s for update''',(message.job_id,))
        job=cur.fetchone()
        if not job or job['payload_json'].get('manual_probe') is not True:
            raise ValueError('not this manual test job')
        if job['status']=='succeeded':
            return
        if job['locked_by'] not in (None,worker_id):
            raise ValueError('another worker owns the test; do not modify it')
        cur.execute('''update public.kb_jobs set status='cancelled',finished_at=now(),
            locked_by=null,locked_until=null,next_retry_at=null,last_error='manual probe stopped; inspect evidence'
            where id=%s''',(message.job_id,))
        cur.execute("update public.kb_documents set status='failed' where id=%s and deleted_at is null",
                    (job['document_id'],))
        cur.execute('select pgmq.archive(%s,%s)',('kb_parse_queue',message.msg_id))
