"""Explicitly register one existing SCI PDF; no upload or metadata generation."""
from pathlib import Path
from urllib.parse import quote
from uuid import UUID
from psycopg2.extras import Json
from .artifacts import PIPELINE,digest
from .control import QUEUE,transaction


def plan(config,document_id,job_id):
    document_id=str(UUID(document_id));job_id=str(UUID(job_id))
    with transaction(config) as cur:
        cur.execute('select doi from public.journals where id=%s',(document_id,))
        row=cur.fetchone()
        if not row or not row['doi']:
            raise ValueError('SCI UUID/DOI not found')
    root=(config.nas_raw_root/'journals').resolve()
    pdf=(root/(quote(quote(row['doi'],safe='/'),safe='/')+'.pdf')).resolve(strict=True)
    pdf.relative_to(root)
    with pdf.open('rb') as stream:
        if stream.read(5)!=b'%PDF-':
            raise ValueError('SCI source is not a PDF')
    return {'document_id':document_id,'job_id':job_id,'doi':row['doi'],'raw_uri':str(pdf),
            'source_sha256':digest(pdf),'file_size':pdf.stat().st_size,'filename':pdf.name}


def enqueue(config,plan,owner_id,reprocess=False):
    doc=plan['document_id'];job=plan['job_id']
    meta={'pipeline':PIPELINE,'source_table':'journals','journal_id':doc,'doi':plan['doi']}
    payload={'pipeline':PIPELINE,'source_sha256':plan['source_sha256']}
    with transaction(config) as cur:
        # Serialize registration for a UUID even before its document row exists.
        cur.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',('sci:'+doc,))
        cur.execute('select doi from public.journals where id=%s for share',(doc,))
        if (cur.fetchone() or {}).get('doi')!=plan['doi']:
            raise ValueError('SCI DOI changed since plan')
        cur.execute('select * from private.sci_parse_jobs where id=%s',(job,))
        old=cur.fetchone()
        if old:
            if str(old['document_id'])==doc and old['source_sha256']==plan['source_sha256']:
                return {'job_id':job,'status':old['status'],'duplicate':True}
            raise ValueError('request job UUID belongs to different source')
        cur.execute("select id from private.sci_parse_jobs where document_id=%s and status in ('queued','running')",(doc,))
        if cur.fetchone():
            raise ValueError('SCI document already has an active job')
        cur.execute('select * from public.kb_documents where id=%s for update',(doc,))
        existing=cur.fetchone()
        if existing:
            metadata=existing['metadata_json'] or {}
            if (not reprocess or existing['deleted_at'] is not None
                    or existing['sha256']!=plan['source_sha256']
                    or metadata.get('source_table')!='journals'
                    or not (metadata.get('pipeline')==PIPELINE or metadata.get('manual_probe'))):
                raise ValueError('existing document requires explicit compatible SCI reprocess')
            cur.execute("select id from public.kb_jobs where document_id=%s and status in ('queued','running','failed')",(doc,))
            if cur.fetchone():
                raise ValueError('document still has a legacy job; do not cross pipelines')
            version=existing['document_version']
        else:
            if not owner_id:
                raise ValueError('existing operator owner UUID required for first registration')
            cur.execute('select id from auth.users where id=%s',(str(UUID(owner_id)),))
            if not cur.fetchone():
                raise ValueError('owner UUID does not exist')
            cur.execute("insert into public.kb_collections(name,path,content_type,raw_retention_policy,processed_retention_policy) values ('SCI documents','/sci','application/pdf','archive_only','archive_only') on conflict(path) do nothing")
            cur.execute("select id from public.kb_collections where path='/sci'")
            collection=cur.fetchone()['id']
            cur.execute('''insert into public.kb_documents(id,primary_collection_id,dedupe_scope,
              original_filename,file_ext,file_size,sha256,status,created_by,owner_user_id,
              metadata_json,metadata_status) values (%s,%s,'sci-existing-pdf',%s,'.pdf',%s,%s,
              'received',%s,%s,%s,'not_applicable')''',
              (doc,collection,plan['filename'],plan['file_size'],plan['source_sha256'],owner_id,owner_id,Json(meta)))
            version=1
        cur.execute('''update public.kb_documents set status='parse_queued',raw_uri=%s,
          metadata_json=coalesce(metadata_json,'{}'::jsonb)||%s,processed_manifest_local_uri=null,
          processed_manifest_s3_key=null,
          processed_manifest_hash=null,processed_artifact_uuid=null,chunk_count=null,parse_time=null,
          index_time=null,processed_s3_ready_at=null,opensearch_indexed=false,pinecone_indexed=false,
          last_error=null,last_error_stage=null
          where id=%s''',(plan['raw_uri'],Json(meta),doc))
        cur.execute('''insert into private.sci_parse_jobs(id,document_id,document_version,source_sha256,payload_json)
          values (%s,%s,%s,%s,%s)''',(job,doc,version,plan['source_sha256'],Json(payload)))
        cur.execute('select pgmq.send(%s,%s) as msg_id',(QUEUE,Json({'job_id':job,'pipeline':PIPELINE})))
        msg_id=cur.fetchone()['msg_id']
        cur.execute('update private.sci_parse_jobs set pgmq_msg_id=%s where id=%s',(msg_id,job))
        return {'document_id':doc,'job_id':job,'msg_id':msg_id,'queue':QUEUE,'status':'queued'}
