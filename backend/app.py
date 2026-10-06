"""Trailer Feed catalog and upload adapter; all media processing stays in RustFS."""
from contextlib import contextmanager
import base64
import binascii
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import unquote, urlsplit
from datetime import datetime, timezone

import httpx
from robyn import Robyn, Request, Response

DATA = Path(os.getenv('DATA_DIR', '/data'))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'trailer-feed.sqlite'
GATEWAY = os.environ['MEDIA_GATEWAY_URL'].rstrip('/')
TOKEN = os.environ['MEDIA_GATEWAY_TOKEN']
PASSWORD = os.environ['TRAILER_FEED_OWNER_PASSWORD']
ORIGINS = set(os.getenv('ALLOWED_ORIGINS', 'https://trailer-feed.vercel.app,http://127.0.0.1:5191').split(','))
BUCKET = 'trailer-feed'
lock = threading.RLock()
app = Robyn(__file__)


@contextmanager
def connect():
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize():
    with connect() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS documents (run_id TEXT, kind TEXT, value TEXT NOT NULL, PRIMARY KEY(run_id,kind));
        CREATE TABLE IF NOT EXISTS uploads (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, sha TEXT NOT NULL, version INTEGER NOT NULL, object_key TEXT NOT NULL, media_url TEXT, job_id TEXT, status TEXT NOT NULL, error TEXT, created TEXT NOT NULL, UNIQUE(run_id,sha), UNIQUE(run_id,version));
        CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS login_attempts (ip TEXT PRIMARY KEY, count INTEGER, until REAL);
        CREATE TABLE IF NOT EXISTS deleted_runs (run_id TEXT PRIMARY KEY, deleted_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS external_versions (source_app TEXT NOT NULL, source_asset_id TEXT NOT NULL, source_version_id TEXT NOT NULL, run_id TEXT NOT NULL, artifact_id TEXT NOT NULL UNIQUE, version INTEGER NOT NULL, PRIMARY KEY(source_app,source_asset_id,source_version_id), UNIQUE(run_id,version));
        CREATE TABLE IF NOT EXISTS external_batches (batch_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, selection TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS external_connections (source_project_id TEXT NOT NULL, source_folder_id TEXT NOT NULL, run_id TEXT NOT NULL, PRIMARY KEY(source_project_id,source_folder_id));
        CREATE TABLE IF NOT EXISTS version_counters (run_id TEXT PRIMARY KEY, last_version INTEGER NOT NULL);
        PRAGMA user_version=3;
        ''')
        if 'state' not in {row['name'] for row in db.execute('PRAGMA table_info(external_versions)')}:
            db.execute("ALTER TABLE external_versions ADD COLUMN state TEXT NOT NULL DEFAULT 'registered'")
        if 'generation' not in {row['name'] for row in db.execute('PRAGMA table_info(external_versions)')}:
            db.execute('ALTER TABLE external_versions ADD COLUMN generation INTEGER NOT NULL DEFAULT 1')
            for batch in db.execute('SELECT batch_id,selection FROM external_batches').fetchall():
                selection = json.loads(batch['selection'])
                for item in selection:
                    item.setdefault('consent_generation', 1)
                db.execute('UPDATE external_batches SET selection=? WHERE batch_id=?', (json.dumps(selection, sort_keys=True), batch['batch_id']))
        seed = Path(os.getenv('SEED_DIR', '/app/seed'))
        for folder in seed.glob('*'):
            if not folder.is_dir():
                continue
            if db.execute('SELECT 1 FROM deleted_runs WHERE run_id=?', (folder.name,)).fetchone():
                continue
            for kind in ('run', 'answers', 'artifacts', 'prompts', 'decisions'):
                path = folder / f'{kind}.json'
                if path.exists():
                    # Seeds never overwrite server-owned project data on deploy.
                    db.execute('INSERT OR IGNORE INTO documents VALUES (?,?,?)', (folder.name, kind, path.read_text()))


def document(db, run_id, kind):
    row = db.execute('SELECT value FROM documents WHERE run_id=? AND kind=?', (run_id, kind)).fetchone()
    return json.loads(row['value']) if row else None


def title_identity(title):
    """Match the short project name shown in the screening room."""
    head = re.sub(r'\s*\([^)]*\)', '', title).strip()
    head = re.split(r'\s+[—–-]\s+', head, maxsplit=1)[0]
    return ' '.join(head.split()).casefold()


def project_with_title(db, title, exclude_run_id=None):
    identity = title_identity(title)
    for row in db.execute("SELECT run_id,value FROM documents WHERE kind='run'"):
        if row['run_id'] != exclude_run_id and title_identity(json.loads(row['value']).get('title', '')) == identity:
            return row['run_id']
    return None


def stored_key_from_url(url):
    if not isinstance(url, str):
        return None
    parsed = urlsplit(url)
    if parsed.scheme == 'https' and parsed.netloc == 's3.v1su4.dev' and parsed.path.startswith('/trailer-feed/'):
        return unquote(parsed.path[len('/trailer-feed/'):])
    return None


def project_storage(db, run_id):
    """Derive only this run's storage prefixes."""
    prefixes = {f'version-assets/{run_id}/'}
    uploads = [dict(row) for row in db.execute('SELECT * FROM uploads WHERE run_id=?', (run_id,))]
    artifacts = document(db, run_id, 'artifacts') or []
    for key in [*(row['object_key'] for row in uploads), *(
        value for artifact in artifacts for value in (
            artifact.get('object_key'), artifact.get('thumbnail_key'), artifact.get('shot_grid_object_key'),
            stored_key_from_url(artifact.get('media_url')), stored_key_from_url(artifact.get('thumbnail_url')),
            stored_key_from_url(artifact.get('shot_grid_url')),
        ) if isinstance(value, str)
    )]:
        match = re.match(r'^media-uploads/(\d{4})/(\d{2}_\d{2})/' + re.escape(run_id) + r'/', key)
        if match:
            prefixes.add(f'media-uploads/{match[1]}/{match[2]}/{run_id}/')
    return sorted(prefixes), uploads


def reply(request, body, status=200):
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-store'}
    origin = request.headers.get('origin')
    if origin in ORIGINS:
        headers.update({'Access-Control-Allow-Origin': origin, 'Vary': 'Origin', 'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-Filename, X-Run-Id', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'})
    return Response(status_code=status, headers=headers, description=json.dumps(body))


def authorized(request):
    origin = request.headers.get('origin')
    if origin and origin not in ORIGINS:
        return False
    token = request.headers.get('authorization') or ''
    if not token.startswith('Bearer '):
        return False
    digest = hashlib.sha256(token[7:].encode()).hexdigest()
    with connect() as db:
        return db.execute('SELECT 1 FROM sessions WHERE digest=? AND expires>?', (digest, time.time())).fetchone() is not None


@app.get('/health')
def health(request: Request):
    with connect() as db:
        count = db.execute("SELECT count(*) FROM documents WHERE kind='run'").fetchone()[0]
    return reply(request, {'ok': True, 'service': 'trailer-feed-api', 'projects': count, 'revision': os.getenv('RELEASE_SHA', 'local')})


@app.options('/*path')
def options(request: Request):
    return reply(request, {})


@app.post('/login')
def login(request: Request):
    # Caddy replaces this header with the direct client IP; never trust a caller's value.
    ip = request.headers.get('x-real-ip') or 'local'
    with lock, connect() as db:
        attempt = db.execute('SELECT * FROM login_attempts WHERE ip=?', (ip,)).fetchone()
        if attempt and attempt['until'] > time.time() and attempt['count'] >= 10:
            return reply(request, {'error': 'Too many attempts. Try again in 15 minutes.'}, 429)
        try:
            payload = json.loads(request.body)
        except (ValueError, TypeError):
            return reply(request, {'error': 'Invalid request'}, 400)
        if request.headers.get('origin') not in ORIGINS or not hmac.compare_digest(str(payload.get('password', '')), PASSWORD) or payload.get('username') != 'gordo':
            count = attempt['count'] + 1 if attempt and attempt['until'] > time.time() else 1
            db.execute('INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)', (ip, count, time.time()+900))
            return reply(request, {'error': 'Incorrect username or password'}, 401)
        token = secrets.token_urlsafe(32)
        db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        db.execute('INSERT INTO sessions VALUES (?,?)', (hashlib.sha256(token.encode()).hexdigest(), time.time()+86400))
        db.execute('DELETE FROM login_attempts WHERE ip=?', (ip,))
    return reply(request, {'token': token})


@app.get('/data/comparisons.index.json')
def index(request: Request):
    with connect() as db:
        runs = []
        for row in db.execute("SELECT run_id,value FROM documents WHERE kind='run'"):
            run = json.loads(row['value'])
            artifacts = document(db, row['run_id'], 'artifacts') or []
            ready = [a for a in artifacts if a.get('media_url')]
            preview = sorted(ready, key=lambda a:a.get('created_at',''))[-1] if ready else None
            runs.append({**run, 'preview': preview, 'artifact_count': len(artifacts), 'answer_count': len(document(db,row['run_id'],'answers') or []), 'model_labels': run.get('models_requested',[])})
    return reply(request, {'runs': runs, 'expected_models': []})


@app.get('/data/comparisons/:run_id/:file')
def get_document(request: Request):
    kind = request.path_params['file'].removesuffix('.json')
    if kind not in ('run','answers','artifacts','prompts','decisions'):
        return reply(request, {'error':'Not found'}, 404)
    with connect() as db:
        value = document(db, request.path_params['run_id'], kind)
    return reply(request, value, 200 if value is not None else 404)


def review_ingest_error(request):
    key = os.getenv('TRAILER_FEED_REVIEW_INGEST_KEY', '')
    authorization = request.headers.get('authorization') or ''
    if not key:
        return reply(request, {'error': 'Review ingestion is not configured'}, 503)
    if request.headers.get('origin') or not hmac.compare_digest(authorization.encode(), ('Bearer ' + key).encode()):
        return reply(request, {'error': 'Review issuer authorization required'}, 401)
    return None


def external_identity(payload):
    asset_id, version_id = (payload[field] for field in ('source_asset_id', 'source_version_id'))
    if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value) for value in (asset_id, version_id)):
        raise ValueError()
    created_at = datetime.fromisoformat(payload['source_created_at'])
    if created_at.tzinfo is None:
        raise ValueError()
    generation = payload.get('consent_generation', 1)
    if isinstance(generation, bool) or not isinstance(generation, int) or not 1 <= generation <= 2147483647:
        raise ValueError()
    return {'source_asset_id': asset_id, 'source_version_id': version_id, 'source_created_at': created_at.astimezone(timezone.utc).isoformat(), 'consent_generation': generation}


@app.post('/external/review/connections')
def connect_review_project(request: Request):
    denied = review_ingest_error(request)
    if denied is not None:
        return denied
    try:
        if len(request.body) > 4096:
            raise ValueError()
        payload = json.loads(request.body)
        project_id, folder_id = payload['source_project_id'], payload.get('source_folder_id')
        if folder_id is None:
            folder_id = '__root__'
        if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value) for value in (project_id, folder_id)):
            raise ValueError()
        mode = payload['mode']
        if mode == 'create':
            title = payload['title']
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
                raise ValueError()
            target_id = 'review-' + hashlib.sha256(json.dumps([project_id, folder_id]).encode()).hexdigest()[:32]
        elif mode == 'connect':
            target_id = payload['run_id']
            if not isinstance(target_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', target_id):
                raise ValueError()
        else:
            raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError):
        return reply(request, {'error': 'Confirm creating or connecting a target project'}, 400)
    with lock, connect() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT * FROM external_connections WHERE source_project_id=? AND source_folder_id=?', (project_id, folder_id)).fetchone()
        if existing:
            if mode == 'connect' and existing['run_id'] != target_id:
                return reply(request, {'error': 'Source folder already has another target connection'}, 409)
            if not document(db, existing['run_id'], 'run'):
                return reply(request, {'error': 'Connected target was removed; explicit reactivation required'}, 409)
            return reply(request, dict(existing))
        if mode == 'create':
            if db.execute('SELECT 1 FROM deleted_runs WHERE run_id=?', (target_id,)).fetchone():
                return reply(request, {'error': 'Removed target cannot be recreated by a connection retry'}, 409)
            duplicate = project_with_title(db, title.strip())
            if duplicate:
                return reply(request, {'error': 'Choose the existing project or a different name', 'existing_run_id': duplicate}, 409)
            now = datetime.now(timezone.utc).isoformat()
            run = {'run_id': target_id, 'title': title.strip(), 'logline': '', 'tags': [], 'format': '', 'status': 'draft', 'created': now, 'created_by': 'review-room', 'question': '', 'models_requested': [], 'target_models': [], 'source_refs': []}
            for kind, value in [('run', run), ('answers', []), ('artifacts', []), ('prompts', []), ('decisions', [])]:
                db.execute('INSERT INTO documents VALUES (?,?,?)', (target_id, kind, json.dumps(value)))
        elif not document(db, target_id, 'run'):
            return reply(request, {'error': 'Selected target project not found'}, 404)
        db.execute('INSERT INTO external_connections VALUES (?,?,?)', (project_id, folder_id, target_id))
    return reply(request, {'source_project_id': project_id, 'source_folder_id': folder_id, 'run_id': target_id}, 201)


def review_resolver_url(value, version_id, variant='original'):
    parsed = urlsplit(value)
    match = re.fullmatch(r'/api/destination-media/([A-Za-z0-9_-]+)/' + re.escape(version_id) + '/' + variant, parsed.path)
    if parsed.scheme != 'https' or parsed.netloc != 'review.v1su4.dev' or parsed.fragment or parsed.query not in ('', 'cors=1') or not match:
        raise ValueError()
    return match[1]


def allocated_version_ceiling(db, run_id):
    videos = [item for item in (document(db, run_id, 'artifacts') or []) if item.get('artifact_type') in ('video_result', 'end_video', 'video')]
    highest = max([int(item.get('version_number', index + 1)) for index, item in enumerate(videos)] + [0])
    uploaded = db.execute('SELECT max(version) FROM uploads WHERE run_id=?', (run_id,)).fetchone()[0] or 0
    external = db.execute('SELECT max(version) FROM external_versions WHERE run_id=?', (run_id,)).fetchone()[0] or 0
    counter = db.execute('SELECT last_version FROM version_counters WHERE run_id=?', (run_id,)).fetchone()
    return max(highest, uploaded, external, counter['last_version'] if counter else 0)


def external_creative_metadata(metadata):
    limits = {'model': 200, 'prompt': 20000, 'sourceLabel': 500, 'notes': 20000, 'releaseDate': 10}
    result = {}
    for name, limit in limits.items():
        value = metadata.get(name, '')
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError()
        result[name] = value
    if result['releaseDate'] and datetime.strptime(result['releaseDate'], '%Y-%m-%d').date().isoformat() != result['releaseDate']:
        raise ValueError()
    platforms = metadata.get('releasePlatforms', [])
    if not isinstance(platforms, list) or len(platforms) > 20 or any(not isinstance(value, str) or len(value) > 100 for value in platforms):
        raise ValueError()
    fields = metadata.get('customFields', [])
    if not isinstance(fields, list) or len(fields) > 30:
        raise ValueError()
    custom = []
    for field in fields:
        field_id, label, kind, value = (field[name] for name in ('id', 'label', 'kind', 'value'))
        if not isinstance(field_id, str) or not 1 <= len(field_id.strip()) <= 100 or not isinstance(label, str) or not 1 <= len(label.strip()) <= 200:
            raise ValueError()
        if kind in ('text', 'date'):
            if not isinstance(value, str) or len(value) > 20000:
                raise ValueError()
            if kind == 'date' and value and datetime.strptime(value, '%Y-%m-%d').date().isoformat() != value:
                raise ValueError()
        elif kind == 'number':
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError()
        elif kind == 'boolean':
            if value is not None and not isinstance(value, bool):
                raise ValueError()
        else:
            raise ValueError()
        custom.append({'id': field_id.strip(), 'label': label, 'kind': kind, 'value': value})
    if len({field['id'] for field in custom}) != len(custom):
        raise ValueError()
    result.update(releasePlatforms=platforms, customFields=custom)
    source_created_at = metadata.get('sourceCreatedAt')
    if source_created_at is not None:
        if isinstance(source_created_at, bool) or not isinstance(source_created_at, int) or not 0 <= source_created_at <= 8640000000000000:
            raise ValueError()
        result['sourceCreatedAt'] = source_created_at
    return result


@app.post('/external/review/batches')
def reserve_external_batch(request: Request):
    denied = review_ingest_error(request)
    if denied is not None:
        return denied
    try:
        if len(request.body) > 150000:
            raise ValueError()
        payload = json.loads(request.body)
        run_id, batch_id = payload['run_id'], payload['batch_id']
        if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value) for value in (run_id, batch_id)) or not isinstance(payload['versions'], list) or not 1 <= len(payload['versions']) <= 100:
            raise ValueError()
        versions = sorted([external_identity(item) for item in payload['versions']], key=lambda item: (item['source_created_at'], item['source_version_id'], item['source_asset_id']))
        if len({(item['source_asset_id'], item['source_version_id']) for item in versions}) != len(versions):
            raise ValueError()
        selection = json.dumps(versions, sort_keys=True)
    except (ValueError, KeyError, TypeError, AttributeError):
        return reply(request, {'error': 'Provide an immutable ordered source batch'}, 400)
    with lock, connect() as db:
        db.execute('BEGIN IMMEDIATE')
        batch = db.execute('SELECT * FROM external_batches WHERE batch_id=?', (batch_id,)).fetchone()
        if batch and (batch['run_id'] != run_id or batch['selection'] != selection):
            return reply(request, {'error': 'Batch identity already has different consent'}, 409)
        if not document(db, run_id, 'run'):
            return reply(request, {'error': 'Connected project not found'}, 404)
        existing = [db.execute("SELECT * FROM external_versions WHERE source_app='review-room' AND source_asset_id=? AND source_version_id=?", (item['source_asset_id'], item['source_version_id'])).fetchone() for item in versions]
        if any(row and row['run_id'] != run_id for row in existing):
            return reply(request, {'error': 'Source version is already connected to another project'}, 409)
        if any(row and row['generation'] != item['consent_generation'] for row, item in zip(existing, versions)):
            return reply(request, {'error': 'Source consent generation changed'}, 409)
        if any(row and row['state'] not in ('reserved', 'registered') for row in existing):
            return reply(request, {'error': 'Source version requires explicit reactivation'}, 409)
        number = allocated_version_ceiling(db, run_id)
        allocated = []
        for item, row in zip(versions, existing):
            if not row:
                number += 1
                artifact_id = 'review-' + hashlib.sha256(json.dumps(['review-room', item['source_asset_id'], item['source_version_id']]).encode()).hexdigest()[:32]
                db.execute('INSERT INTO external_versions (source_app,source_asset_id,source_version_id,run_id,artifact_id,version,state,generation) VALUES (?,?,?,?,?,?,?,?)', ('review-room', item['source_asset_id'], item['source_version_id'], run_id, artifact_id, number, 'reserved', item['consent_generation']))
                row = {'version': number, 'artifact_id': artifact_id, 'state': 'reserved'}
            allocated.append({**item, 'version_number': row['version'], 'artifact_id': row['artifact_id'], 'state': row['state']})
        db.execute('INSERT OR IGNORE INTO external_batches VALUES (?,?,?)', (batch_id, run_id, selection))
        db.execute('INSERT OR REPLACE INTO version_counters VALUES (?,?)', (run_id, number))
    return reply(request, {'batch_id': batch_id, 'versions': allocated}, 200 if batch else 201)


@app.post('/external/review/status')
def external_version_status(request: Request):
    denied = review_ingest_error(request)
    if denied is not None:
        return denied
    try:
        if len(request.body) > 150000:
            raise ValueError()
        versions = json.loads(request.body)['versions']
        if not isinstance(versions, list) or not 1 <= len(versions) <= 100:
            raise ValueError()
        identities = [(item['source_asset_id'], item['source_version_id']) for item in versions]
        if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value) for item in identities for value in item):
            raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError):
        return reply(request, {'error': 'Provide exact source versions'}, 400)
    result = []
    with connect() as db:
        for asset_id, version_id in identities:
            row = db.execute("SELECT * FROM external_versions WHERE source_app='review-room' AND source_asset_id=? AND source_version_id=?", (asset_id, version_id)).fetchone()
            result.append({'source_asset_id': asset_id, 'source_version_id': version_id, 'state': row['state'] if row else 'unregistered', **({'run_id': row['run_id'], 'artifact_id': row['artifact_id'], 'version_number': row['version'], 'consent_generation': row['generation']} if row else {})})
    return reply(request, {'versions': result})


@app.post('/versions/:id/remove')
def remove_external_version(request: Request):
    if not authorized(request):
        return reply(request, {'error': 'Sign in to remove this version'}, 401)
    try:
        payload = json.loads(request.body)
        artifact_id = request.path_params['id']
        run_id = payload['run_id']
        generation = payload.get('expected_generation', 1)
        if not isinstance(run_id, str) or payload['confirm_artifact_id'] != artifact_id or isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        return reply(request, {'error': 'Confirm the exact selected version'}, 400)
    with lock, connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM external_versions WHERE artifact_id=? AND run_id=?', (artifact_id, run_id)).fetchone()
        if not row:
            return reply(request, {'error': 'External version not found'}, 404)
        if row['generation'] != generation:
            return reply(request, {'error': 'Version consent changed; reload before removing it'}, 409)
        # Retain terminal source deletion if this is a repeated target removal.
        if row['state'] != 'source_deleted':
            db.execute("UPDATE external_versions SET state='target_suppressed' WHERE artifact_id=?", (artifact_id,))
        artifacts = document(db, run_id, 'artifacts')
        if artifacts is not None:
            surviving = [item for item in artifacts if item['artifact_id'] != artifact_id and item.get('source_parent_artifact_id') != artifact_id]
            db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='artifacts'", (json.dumps(surviving), run_id))
    return reply(request, {'deleted': True, 'artifact_id': artifact_id, 'state': 'source_deleted' if row['state'] == 'source_deleted' else 'target_suppressed'})


@app.post('/external/review/reactivations')
def reactivate_external_version(request: Request):
    denied = review_ingest_error(request)
    if denied is not None:
        return denied
    try:
        if len(request.body) > 4096:
            raise ValueError()
        payload = json.loads(request.body)
        expected = payload['expected_generation']
        if payload['intent'] != 'sync-again' or isinstance(expected, bool) or not isinstance(expected, int) or not 1 <= expected < 2147483647:
            raise ValueError()
        run_id, batch_id = payload['run_id'], payload['batch_id']
        if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value) for value in (run_id, batch_id)):
            raise ValueError()
        identity = external_identity({**payload, 'consent_generation': expected + 1})
        selection = json.dumps([identity], sort_keys=True)
    except (ValueError, KeyError, TypeError, AttributeError):
        return reply(request, {'error': 'Confirm Sync again for this exact version and current generation'}, 400)
    with lock, connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute("SELECT * FROM external_versions WHERE source_app='review-room' AND source_asset_id=? AND source_version_id=?", (identity['source_asset_id'], identity['source_version_id'])).fetchone()
        if not row:
            return reply(request, {'error': 'Suppressed source version not found'}, 404)
        batch = db.execute('SELECT * FROM external_batches WHERE batch_id=?', (batch_id,)).fetchone()
        if batch:
            if batch['run_id'] == run_id and batch['selection'] == selection and row['run_id'] == run_id and row['generation'] == expected + 1 and row['state'] in ('reserved', 'registered'):
                return reply(request, {'batch_id': batch_id, 'consent_generation': row['generation'], 'version_number': row['version']})
            return reply(request, {'error': 'Reactivation operation has different or superseded consent'}, 409)
        if row['state'] != 'target_suppressed' or row['generation'] != expected:
            return reply(request, {'error': 'Source version is not suppressed at this consent generation'}, 409)
        if not document(db, run_id, 'run'):
            return reply(request, {'error': 'Choose an existing target project before reactivation'}, 404)
        number = row['version']
        old_ceiling = allocated_version_ceiling(db, row['run_id'])
        db.execute('INSERT OR REPLACE INTO version_counters VALUES (?,?)', (row['run_id'], old_ceiling))
        if row['run_id'] != run_id:
            number = allocated_version_ceiling(db, run_id) + 1
        db.execute('INSERT OR REPLACE INTO version_counters VALUES (?,?)', (run_id, max(number, allocated_version_ceiling(db, run_id))))
        db.execute("UPDATE external_versions SET state='reserved',generation=?,run_id=?,version=? WHERE artifact_id=?", (expected + 1, run_id, number, row['artifact_id']))
        db.execute('INSERT INTO external_batches VALUES (?,?,?)', (batch_id, run_id, selection))
    return reply(request, {'batch_id': batch_id, 'consent_generation': expected + 1, 'version_number': number}, 201)


@app.post('/external/review/versions')
def register_external_version(request: Request):
    """Register a selected Review version; the issuer key never enters catalog JSON."""
    denied = review_ingest_error(request)
    if denied is not None:
        return denied
    try:
        if len(request.body) > 2000000:
            raise ValueError()
        payload = json.loads(request.body)
        run_id, batch_id = payload['run_id'], payload['batch_id']
        if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value) for value in (run_id, batch_id)):
            raise ValueError()
        identity = external_identity(payload)
        asset_id, version_id = identity['source_asset_id'], identity['source_version_id']
        media_url = payload['media_url']
        slug = review_resolver_url(media_url, version_id)
        poster_url = payload.get('poster_url')
        if poster_url is not None and review_resolver_url(poster_url, version_id, 'poster') != slug:
            raise ValueError()
        metadata = external_creative_metadata(payload.get('metadata', {}))
        references = payload.get('references', [])
        grid = payload.get('grid')
        if not isinstance(references, list) or len(references) > 20:
            raise ValueError()
        attachments = []
        for image, artifact_type in ([ (grid, 'shot_grid') ] if grid is not None else []) + [(image, 'image_result') for image in references]:
            image_id = image['source_version_id']
            if not isinstance(image_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', image_id) or review_resolver_url(image['media_url'], image_id) != slug:
                raise ValueError()
            attachments.append({'source_version_id': image_id, 'media_url': image['media_url'], 'artifact_type': artifact_type})
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return reply(request, {'error': 'Provide an exact Review source version and controlled resolver URL'}, 400)
    with lock, connect() as db:
        db.execute('BEGIN IMMEDIATE')
        batch = db.execute('SELECT * FROM external_batches WHERE batch_id=?', (batch_id,)).fetchone()
        if not batch or batch['run_id'] != run_id or identity not in json.loads(batch['selection']):
            return reply(request, {'error': 'Version is not in this reserved consent batch'}, 409)
        existing = db.execute("SELECT * FROM external_versions WHERE source_app='review-room' AND source_asset_id=? AND source_version_id=?", (asset_id, version_id)).fetchone()
        if existing:
            if existing['run_id'] != run_id:
                return reply(request, {'error': 'Source version is already connected to another project'}, 409)
            if existing['generation'] != identity['consent_generation']:
                return reply(request, {'error': 'Source consent generation changed'}, 409)
            artifact = next((item for item in (document(db, run_id, 'artifacts') or []) if item['artifact_id'] == existing['artifact_id']), None)
            if existing['state'] not in ('reserved', 'registered') or (existing['state'] == 'registered' and not artifact):
                return reply(request, {'error': 'Source version is disconnected; explicit reactivation required'}, 409)
            if existing['state'] == 'registered':
                return reply(request, {'artifact': artifact, 'existing': True})
        else:
            return reply(request, {'error': 'Version reservation unavailable'}, 409)
        if not document(db, run_id, 'run'):
            return reply(request, {'error': 'Connected project not found'}, 404)
        artifacts = document(db, run_id, 'artifacts') or []
        number, artifact_id = existing['version'], existing['artifact_id']
        artifact = {'artifact_id': artifact_id, 'run_id': run_id, 'title': metadata['sourceLabel'] or f'Review version {number}', 'created_at': identity['source_created_at'], 'provider': 'unknown', 'source': 'manual', 'artifact_type': 'video_result', 'status': 'generated', 'ownership': 'external', 'source_app': 'review-room', 'source_asset_id': asset_id, 'source_version_id': version_id, 'consent_generation': identity['consent_generation'], 'version_number': number, 'media_url': media_url, 'video_model': metadata['model'], 'version_prompt': metadata['prompt'], 'notes': metadata['notes'], 'creative_metadata': metadata, 'reference_image_ids': []}
        if poster_url is not None:
            artifact['thumbnail_url'] = poster_url
        for image in attachments:
            image_artifact_id = 'review-image-' + hashlib.sha256(json.dumps([asset_id, version_id, image['source_version_id'], image['artifact_type']]).encode()).hexdigest()[:32]
            attachment = {**image, 'artifact_id': image_artifact_id, 'run_id': run_id, 'title': 'Review image', 'created_at': identity['source_created_at'], 'provider': 'unknown', 'source': 'manual', 'status': 'generated', 'ownership': 'external', 'source_app': 'review-room', 'source_parent_artifact_id': artifact_id}
            artifacts.append(attachment)
            if image['artifact_type'] == 'shot_grid':
                artifact.update(shot_grid_url=image['media_url'], shot_grid_artifact_id=image_artifact_id)
            else:
                artifact['reference_image_ids'].append(image_artifact_id)
        db.execute("UPDATE external_versions SET state='registered' WHERE source_app='review-room' AND source_asset_id=? AND source_version_id=?", (asset_id, version_id))
        artifacts.append(artifact)
        db.execute('INSERT OR REPLACE INTO documents VALUES (?,?,?)', (run_id, 'artifacts', json.dumps(artifacts)))
        run = document(db, run_id, 'run')
        if run.get('status') == 'draft':
            run['status'] = 'ready_for_review'
            db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='run'", (json.dumps(run), run_id))
    return reply(request, {'artifact': artifact, 'existing': False}, 201)


@app.post('/versions')
def upload(request: Request):
    if not authorized(request):
        return reply(request, {'error': 'Sign in to upload', 'login_required': True}, 401)
    run_id = request.headers.get('x-run-id') or ''
    filename = unquote(request.headers.get('x-filename') or '')
    extension = Path(filename).suffix.lower()
    body = request.body
    if isinstance(body, str):
        return reply(request, {'error':'Upload binary video data'}, 400)
    if extension not in ('.mp4','.mov','.webm') or not body or len(body)>95*1000*1000:
        return reply(request, {'error':'Choose MP4, MOV or WebM, up to 95 MB'}, 400)
    sha = hashlib.sha256(body).hexdigest()
    with lock, connect() as db:
        db.execute('BEGIN IMMEDIATE')
        run = document(db,run_id,'run')
        if not run:
            return reply(request, {'error':'Project not found'},404)
        artifacts = document(db,run_id,'artifacts') or []
        existing = db.execute('SELECT * FROM uploads WHERE run_id=? AND sha=?',(run_id,sha)).fetchone()
        if existing and existing['status']=='failed' and not existing['media_url']:
            db.execute('DELETE FROM uploads WHERE id=?',(existing['id'],))
            existing=None
        if existing:
            return reply(request, {'added':0,'versions':[], 'status':existing['status'], 'upload_id':existing['id'], 'error':existing['error']})
        if any(a.get('media_sha256')==sha or a.get('upload_sha256')==sha for a in artifacts):
            return reply(request, {'added':0,'versions':[],'status':'ready'})
        version = allocated_version_ceiling(db, run_id) + 1
        db.execute('INSERT OR REPLACE INTO version_counters VALUES (?,?)', (run_id, version))
        uid = secrets.token_hex(16)
        now = datetime.now(timezone.utc)
        key = f'media-uploads/{now:%Y/%m_%d}/{run_id}/versions/v{version}/{sha}{extension}'
        db.execute('INSERT INTO uploads (id,run_id,sha,version,object_key,status,created) VALUES (?,?,?,?,?,?,?)',(uid,run_id,sha,version,key,'uploading',now.isoformat()))
    try:
        with httpx.Client(timeout=600) as client:
            response = client.post(GATEWAY+'/upload',headers={'Authorization':f'Bearer {TOKEN}'},data={'bucket':BUCKET,'userId':BUCKET,'folder':key.rsplit('/',1)[0],'preserveFilename':'true'},files={'file':(key.rsplit('/',1)[1],body,'application/octet-stream')})
            response.raise_for_status()
            media = response.json()
            if media.get('bucket') != BUCKET or media.get('objectKey') != key:
                raise ValueError('Unexpected storage destination')
        with connect() as db:
            db.execute("UPDATE uploads SET status='queued',media_url=? WHERE id=?",(media.get('publicUrl') or media['mediaUrl'],uid))
        return reply(request, {'added':1,'versions':[version],'upload_id':uid,'status':'queued'},202)
    except Exception:
        with connect() as db:
            db.execute("UPDATE uploads SET status='failed',error='Storage upload failed' WHERE id=?",(uid,))
        return reply(request, {'error':'Storage upload failed. Retry this upload.','upload_id':uid},502)


@app.post('/versions/:id/details')
def version_details(request: Request):
    if not authorized(request):
        return reply(request, {'error': 'Sign in to edit this version'}, 401)
    try:
        if len(request.body) > 15*1000*1000:
            raise ValueError()
        payload = json.loads(request.body)
        run_id = payload['run_id']
        prompt = payload['prompt']
        model = payload['video_model']
        if not isinstance(prompt, str) or len(prompt)>100000 or not isinstance(model,str) or len(model)>100:
            raise ValueError()
        grid = payload.get('grid')
        image = None
        if isinstance(grid, dict) and 'data' in grid:
            image = base64.b64decode(grid['data'], validate=True)
            if not image or len(image)>10*1000*1000:
                raise ValueError()
            if image.startswith(b'\x89PNG\r\n\x1a\n'):
                extension, mime = 'png', 'image/png'
            elif image.startswith(b'\xff\xd8\xff'):
                extension, mime = 'jpg', 'image/jpeg'
            elif image.startswith(b'RIFF') and image[8:12]==b'WEBP':
                extension, mime = 'webp', 'image/webp'
            else:
                raise ValueError()
        elif grid is not None and (not isinstance(grid,dict) or not isinstance(grid.get('artifact_id'),str)):
            raise ValueError()
    except (ValueError, KeyError, TypeError, binascii.Error):
        return reply(request, {'error':'Provide a prompt, video model and a PNG, JPEG or WebP grid up to 10 MB'},400)
    artifact_id = request.path_params['id']
    with lock, connect() as db:
        artifacts = document(db,run_id,'artifacts') or []
        target = next((a for a in artifacts if a['artifact_id']==artifact_id and a['artifact_type'] in ('video_result','end_video')),None)
        if not target:
            return reply(request, {'error':'Video version not found'},404)
        if payload.get('revision',0) != target.get('context_revision',0):
            return reply(request, {'error':'This version changed. Reload the project before editing.'},409)
        linked = None
        if grid and image is None:
            linked = next((a for a in artifacts if a['artifact_id']==grid['artifact_id'] and a['artifact_type'] in ('shot_grid','image_result') and a.get('media_url')),None)
            if not linked:
                return reply(request, {'error':'Shot grid not found in this project'},400)
    grid_url = linked['media_url'] if linked else None
    grid_key = None
    if image is not None:
        # Content-addressed keys keep replacement grids and other versions intact.
        safe_id = hashlib.sha256(artifact_id.encode()).hexdigest()[:24]
        key = f'version-assets/{run_id}/{safe_id}/shot-grids/{hashlib.sha256(image).hexdigest()}.{extension}'
        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(GATEWAY+'/upload',headers={'Authorization':f'Bearer {TOKEN}'},data={'bucket':BUCKET,'userId':BUCKET,'folder':key.rsplit('/',1)[0],'preserveFilename':'true'},files={'file':(key.rsplit('/',1)[1],image,mime)})
                response.raise_for_status()
                media = response.json()
                if media.get('bucket')!=BUCKET or media.get('objectKey')!=key:
                    raise ValueError()
                grid_url = media.get('publicUrl') or media['mediaUrl']
                grid_key = key
        except (httpx.HTTPError,ValueError,KeyError):
            return reply(request, {'error':'Grid upload failed. Your version was not changed.'},502)
    with lock, connect() as db:
        artifacts = document(db,run_id,'artifacts') or []
        target = next((a for a in artifacts if a['artifact_id']==artifact_id),None)
        if not target or payload.get('revision',0)!=target.get('context_revision',0):
            return reply(request, {'error':'This version changed. Reload the project before editing.'},409)
        target.update(version_prompt=prompt,video_model=model.strip(),context_revision=target.get('context_revision',0)+1)
        # Omitted grid preserves the existing attachment; null explicitly removes it.
        if 'grid' in payload:
            target.update(shot_grid_url=grid_url,shot_grid_object_key=grid_key,shot_grid_artifact_id=linked['artifact_id'] if linked else None)
        db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='artifacts'",(json.dumps(artifacts),run_id))
    return reply(request, {'artifact':target})


@app.post('/runs')
def create_run(request: Request):
    """Create an upload-first project, safely replaying a lost response."""
    if not authorized(request):
        return reply(request, {'error': 'Sign in to create a project'}, 401)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError()
        request_id = payload.get('request_id', '')
        title = payload.get('title', '')
        logline = payload.get('logline', '')
        tags = payload.get('tags', [])
        project_format = payload.get('format', '')
        if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9]{32}', request_id):
            raise ValueError()
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise ValueError()
        if not isinstance(logline, str) or len(logline) > 600:
            raise ValueError()
        if not isinstance(tags, list) or len(tags) > 20 or any(not isinstance(tag, str) or not 1 <= len(tag.strip()) <= 40 for tag in tags):
            raise ValueError()
        if project_format not in ('', 'trailer', 'music video', 'commercial', 'short film scene', 'visual concept', 'other'):
            raise ValueError()
    except (ValueError, TypeError):
        return reply(request, {'error': 'Provide a project name (up to 120 characters), description (up to 600), and up to 20 tags (40 characters each).'}, 400)
    run_id = 'upload-' + request_id
    fields = {'title': title.strip(), 'logline': logline.strip(), 'tags': list(dict.fromkeys(tag.strip() for tag in tags)), 'format': project_format}
    with lock, connect() as db:
        if db.execute('SELECT 1 FROM deleted_runs WHERE run_id=?', (run_id,)).fetchone():
            return reply(request, {'error': 'This project request was already removed. Start a new upload.'}, 409)
        existing = document(db, run_id, 'run')
        if existing:
            if any(existing.get(key) != value for key, value in fields.items()):
                return reply(request, {'error': 'This project was already created with different details. Open it in Projects to edit.'}, 409)
            return reply(request, {'run': existing})
        duplicate = project_with_title(db, fields['title'])
        if duplicate:
            return reply(request, {'error': 'A project with this title already exists. Open it in Projects or choose another title.', 'existing_run_id': duplicate}, 409)
        run = {**fields, 'run_id': run_id, 'question': '', 'created': datetime.now(timezone.utc).isoformat(), 'created_by': 'gordo', 'status': 'draft', 'models_requested': [], 'target_models': [], 'source_refs': []}
        for kind, value in [('run', run), ('answers', []), ('artifacts', []), ('prompts', []), ('decisions', [])]:
            db.execute('INSERT INTO documents VALUES (?,?,?)', (run_id, kind, json.dumps(value)))
    return reply(request, {'run': run}, 201)


@app.post('/runs/:run_id')
def run_details(request: Request):
    """Rename a project or rewrite its logline after the fact."""
    if not authorized(request):
        return reply(request, {'error': 'Sign in to edit this project'}, 401)
    try:
        payload = json.loads(request.body)
        changes = {}
        if 'title' in payload:
            title = payload['title']
            if not isinstance(title, str) or not title.strip() or len(title.strip()) > 120:
                raise ValueError()
            changes['title'] = title.strip()
        if 'logline' in payload:
            logline = payload['logline']
            if not isinstance(logline, str) or len(logline) > 600:
                raise ValueError()
            changes['logline'] = logline.strip()
        if not changes:
            raise ValueError()
    except (ValueError, TypeError):
        return reply(request, {'error': 'Provide a title up to 120 characters or a logline up to 600'}, 400)
    run_id = request.path_params['run_id']
    with lock, connect() as db:
        run = document(db, run_id, 'run')
        if run is None:
            return reply(request, {'error': 'Project not found'}, 404)
        if 'title' in changes:
            duplicate = project_with_title(db, changes['title'], run_id)
            if duplicate:
                return reply(request, {'error': 'A project with this title already exists. Choose another title.', 'existing_run_id': duplicate}, 409)
        run.update(changes)
        db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='run'", (json.dumps(run), run_id))
    return reply(request, {'run': run})


@app.post('/runs/:run_id/delete')
def delete_run(request: Request):
    """Remove an owner-confirmed project and every run-scoped RustFS object."""
    if not authorized(request):
        return reply(request, {'error': 'Sign in to remove this project'}, 401)
    run_id = request.path_params['run_id']
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or payload.get('confirm_run_id') != run_id:
            raise ValueError()
    except (ValueError, TypeError):
        return reply(request, {'error': 'Confirm the selected project before removing it'}, 400)
    with lock, connect() as db:
        run = document(db, run_id, 'run')
        if not run:
            if db.execute('SELECT 1 FROM deleted_runs WHERE run_id=?', (run_id,)).fetchone():
                return reply(request, {'deleted': True, 'run_id': run_id})
            return reply(request, {'error': 'Project not found'}, 404)
        prefixes, uploads = project_storage(db, run_id)
        if any(row['status'] in ('uploading', 'queued', 'processing') for row in uploads):
            return reply(request, {'error': 'Wait for video processing to finish before removing this project'}, 409)
        try:
            with httpx.Client(timeout=300) as client:
                cleanup = client.post(GATEWAY + '/trailer-feed/delete-run-objects',
                    headers={'Authorization': f'Bearer {TOKEN}'},
                    json={'runId': run_id, 'prefixes': prefixes})
                cleanup.raise_for_status()
                if cleanup.json().get('failed'):
                    raise ValueError('Storage cleanup incomplete')
        except (httpx.HTTPError, ValueError):
            return reply(request, {'error': 'Storage cleanup did not finish. The project is still listed; retry removal.'}, 502)
        db.execute('INSERT OR IGNORE INTO deleted_runs VALUES (?,?)',
            (run_id, datetime.now(timezone.utc).isoformat()))
        db.execute('DELETE FROM uploads WHERE run_id=?', (run_id,))
        db.execute("UPDATE external_versions SET state='target_suppressed' WHERE run_id=? AND state!='source_deleted'", (run_id,))
        db.execute('DELETE FROM documents WHERE run_id=?', (run_id,))
    return reply(request, {'deleted': True, 'run_id': run_id})


def delete_project_thumbnail_object(key):
    with httpx.Client(timeout=30) as client:
        response = client.post(GATEWAY + '/delete',
            headers={'Authorization': f'Bearer {TOKEN}'},
            json={'bucket': BUCKET, 'objectKeys': [key]})
        response.raise_for_status()
        if response.json().get('failed') or response.json().get('deleted') != 1:
            raise ValueError('Thumbnail cleanup incomplete')


@app.post('/runs/:run_id/thumbnail')
def upload_project_thumbnail(request: Request):
    """Set a cover for the Projects strip without changing take artifacts."""
    if not authorized(request):
        return reply(request, {'error': 'Sign in to edit this project'}, 401)
    image = request.body
    if not isinstance(image, bytes) or not image or len(image) > 5 * 1000 * 1000:
        return reply(request, {'error': 'Choose a PNG, JPEG or WebP image up to 5 MB'}, 400)
    if image.startswith(b'\x89PNG\r\n\x1a\n'):
        extension, mime = 'png', 'image/png'
    elif image.startswith(b'\xff\xd8\xff'):
        extension, mime = 'jpg', 'image/jpeg'
    elif image.startswith(b'RIFF') and image[8:12] == b'WEBP':
        extension, mime = 'webp', 'image/webp'
    else:
        return reply(request, {'error': 'Choose a PNG, JPEG or WebP image up to 5 MB'}, 400)
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != mime:
        return reply(request, {'error': 'Image type does not match the file'}, 400)
    run_id = request.path_params['run_id']
    key = f'version-assets/{run_id}/project-covers/{hashlib.sha256(image).hexdigest()}.{extension}'
    with lock, connect() as db:
        run = document(db, run_id, 'run')
        if run is None:
            return reply(request, {'error': 'Project not found'}, 404)
        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(GATEWAY + '/upload',
                    headers={'Authorization': f'Bearer {TOKEN}'},
                    data={'bucket': BUCKET, 'userId': BUCKET, 'folder': key.rsplit('/', 1)[0], 'preserveFilename': 'true'},
                    files={'file': (key.rsplit('/', 1)[1], image, mime)})
                response.raise_for_status()
                media = response.json()
                if media.get('bucket') != BUCKET or media.get('objectKey') != key:
                    raise ValueError('Unexpected object key')
                url = media.get('publicUrl') or media['mediaUrl']
                if not isinstance(url, str) or not url.startswith('https://'):
                    raise ValueError('Invalid media URL')
        except (httpx.HTTPError, ValueError, KeyError):
            return reply(request, {'error': 'Thumbnail upload failed. The project was not changed.'}, 502)
        old_key = run.get('project_thumbnail_object_key')
        run.update(project_thumbnail_url=url, project_thumbnail_object_key=key)
        db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='run'", (json.dumps(run), run_id))
    if isinstance(old_key, str) and old_key != key and old_key.startswith(f'version-assets/{run_id}/project-covers/'):
        try:
            delete_project_thumbnail_object(old_key)
        except (httpx.HTTPError, ValueError, KeyError):
            pass  # The run-scoped project deletion still cleans up this old file.
    return reply(request, {'project_thumbnail_url': url})


@app.post('/runs/:run_id/thumbnail/remove')
def remove_project_thumbnail(request: Request):
    if not authorized(request):
        return reply(request, {'error': 'Sign in to edit this project'}, 401)
    run_id = request.path_params['run_id']
    with lock, connect() as db:
        run = document(db, run_id, 'run')
        if run is None:
            return reply(request, {'error': 'Project not found'}, 404)
        key = run.get('project_thumbnail_object_key')
        if key:
            if not isinstance(key, str) or not key.startswith(f'version-assets/{run_id}/project-covers/'):
                return reply(request, {'error': 'Thumbnail storage path is invalid'}, 409)
            try:
                delete_project_thumbnail_object(key)
            except (httpx.HTTPError, ValueError, KeyError):
                return reply(request, {'error': 'Thumbnail cleanup failed. Retry to use the automatic image.'}, 502)
        run.pop('project_thumbnail_url', None)
        run.pop('project_thumbnail_object_key', None)
        db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='run'", (json.dumps(run), run_id))
    return reply(request, {'project_thumbnail_url': None})


@app.get('/uploads/:id')
def upload_status(request: Request):
    if not authorized(request):
        return reply(request, {'error':'Sign in to view upload status'},401)
    with connect() as db:
        row=db.execute('SELECT id,status,error,version FROM uploads WHERE id=?',(request.path_params['id'],)).fetchone()
    return reply(request,dict(row) if row else {'error':'Not found'},200 if row else 404)


def process_once():
    with connect() as db:
        pending=[dict(r) for r in db.execute("SELECT * FROM uploads WHERE status IN ('queued','processing')")]
    with httpx.Client(timeout=30,headers={'Authorization':f'Bearer {TOKEN}'}) as client:
        for item in pending:
            try:
                if not item['job_id']:
                    result=client.post(GATEWAY+'/video/jobs',json={'bucket':BUCKET,'objectKey':item['object_key'],'metadata':{'project':'trailer-feed','upload_id':item['id']}})
                    result.raise_for_status()
                    job=result.json().get('job',result.json())
                    with connect() as db:
                        db.execute("UPDATE uploads SET job_id=?,status='processing' WHERE id=?",(job['job_id'],item['id']))
                    continue
                result=client.get(GATEWAY+'/video/jobs/'+item['job_id'])
                if result.status_code==404:
                    with connect() as db:
                        db.execute("UPDATE uploads SET status='failed',error='Processing job expired. Retry processing.' WHERE id=?",(item['id'],))
                    continue
                result.raise_for_status()
                job=result.json().get('job',result.json())
                if job['status']=='failed':
                    with connect() as db:
                        db.execute("UPDATE uploads SET status='failed',error='Video processing failed. Retry processing.' WHERE id=?",(item['id'],))
                elif job['status']=='completed':
                    result=client.get(GATEWAY+'/video/jobs/'+item['job_id']+'/result')
                    result.raise_for_status()
                    payload=result.json()
                    manifest=payload.get('manifest',payload)
                    segments=manifest.get('segments',[])
                    if not segments or not segments[0].get('thumbnail_url'):
                        raise ValueError('Missing thumbnail')
                    with lock, connect() as db:
                        run=document(db,item['run_id'],'run')
                        artifacts=document(db,item['run_id'],'artifacts') or []
                        answers=document(db,item['run_id'],'answers') or []
                        artifact={'artifact_id':item['id'],'run_id':item['run_id'],'answer_id':next((a.get('answer_id') for a in artifacts if a.get('artifact_type')=='video_result'), answers[0].get('answer_id') if answers else None),'artifact_type':'video_result','provider':'manual_upload','target_model':'manual','title':f"{run['title']} — v{item['version']}",'version_number':item['version'],'source':'uploaded','status':'generated','created_at':item['created'],'media_url':item['media_url'],'thumbnail_url':segments[0]['thumbnail_url'],'storage_bucket':BUCKET,'object_key':item['object_key'],'media_sha256':item['sha'],'duration_seconds':manifest.get('duration_seconds'),'job_id':item['job_id']}
                        if not any(a['artifact_id']==item['id'] for a in artifacts):
                            artifacts.append(artifact)
                            db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='artifacts'",(json.dumps(artifacts),item['run_id']))
                        if item['run_id'].startswith('upload-') and run.get('status') == 'draft':
                            run['status'] = 'ready_for_review'
                            db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='run'", (json.dumps(run), item['run_id']))
                        db.execute("UPDATE uploads SET status='ready',error=NULL WHERE id=?",(item['id'],))
            except (ValueError,KeyError):
                with connect() as db:
                    db.execute("UPDATE uploads SET status='failed',error='Processing result incomplete. Retry processing.' WHERE id=?",(item['id'],))
            except httpx.HTTPError:
                continue


@app.post('/uploads/:id/retry')
def retry(request: Request):
    if not authorized(request):
        return reply(request,{'error':'Sign in to retry'},401)
    with lock,connect() as db:
        row=db.execute('SELECT * FROM uploads WHERE id=?',(request.path_params['id'],)).fetchone()
        if not row or row['status']!='failed' or not row['media_url']:
            return reply(request,{'error':'Choose the file again to retry the upload'},409)
        db.execute("UPDATE uploads SET status='queued',job_id=NULL,error=NULL WHERE id=?",(row['id'],))
    return reply(request,{'ok':True})


def worker():
    while True:
        try:
            process_once()
        except Exception:
            print('Upload reconciliation failed; will retry',flush=True)
        time.sleep(5)


if __name__=='__main__':
    initialize()
    with connect() as db:
        db.execute("UPDATE uploads SET status='failed',error='Upload interrupted. Choose the file again.' WHERE status='uploading'")
    threading.Thread(target=worker,daemon=True).start()
    app.start(host='0.0.0.0',port=int(os.getenv('PORT','18100')))
