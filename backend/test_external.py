import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

TEMP = tempfile.TemporaryDirectory()
os.environ.setdefault('DATA_DIR', TEMP.name)
os.environ.setdefault('SEED_DIR', TEMP.name)
os.environ.setdefault('MEDIA_GATEWAY_URL', 'http://invalid')
os.environ.setdefault('MEDIA_GATEWAY_TOKEN', 'test')
os.environ.setdefault('TRAILER_FEED_OWNER_PASSWORD', 'test')
import app


class ExternalVersionTests(unittest.TestCase):
    def setUp(self):
        app.initialize()
        self.key = patch.dict(os.environ, {'TRAILER_FEED_REVIEW_INGEST_KEY': 'test-ingest-only'})
        self.key.start()
        self.addCleanup(self.key.stop)
        self.run_id = 'external-' + os.urandom(8).hex()
        with app.connect() as db:
            db.execute('INSERT INTO documents VALUES (?,?,?)', (self.run_id, 'run', json.dumps({'run_id': self.run_id, 'title': 'External verification'})))
            db.execute('INSERT INTO documents VALUES (?,?,?)', (self.run_id, 'artifacts', '[]'))
        self.payload = {'run_id': self.run_id, 'source_asset_id': 'asset-1', 'source_version_id': 'version-1', 'source_created_at': '2026-10-01T10:00:00+00:00', 'media_url': 'https://review.v1su4.dev/api/destination-media/selected-grant/version-1/original', 'metadata': {'model': 'Sora 2', 'prompt': 'Selected original take'}}

    def ingest(self, payload=None, token='test-ingest-only'):
        return app.register_external_version(Mock(body=json.dumps(payload or self.payload), headers={'authorization': 'Bearer ' + token}, path_params={}))

    def test_exact_source_retry_survives_restart_and_keeps_target_edits(self):
        first = self.ingest()
        self.assertEqual(first.status_code, 201)
        artifact = json.loads(first.description)['artifact']
        self.assertEqual(artifact['version_number'], 1)
        self.assertEqual(artifact['media_url'], self.payload['media_url'])
        self.assertEqual(artifact['ownership'], 'external')
        self.assertEqual(artifact['created_at'], '2026-10-01T10:00:00+00:00')
        self.assertEqual(artifact['run_id'], self.run_id)
        self.assertNotIn('object_key', artifact)
        with app.connect() as db:
            values = app.document(db, self.run_id, 'artifacts')
            values[0]['version_prompt'] = 'Target-only edit'
            db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='artifacts'", (json.dumps(values), self.run_id))
        app.initialize()
        retried = self.ingest()
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(json.loads(retried.description)['artifact']['artifact_id'], artifact['artifact_id'])
        public = app.get_document(Mock(headers={}, path_params={'run_id': self.run_id, 'file': 'artifacts.json'}))
        values = json.loads(public.description)
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]['version_prompt'], 'Target-only edit')
        self.assertNotIn('test-ingest-only', public.description)

    def test_ingestion_rejects_owner_sessions_foreign_origins_and_arbitrary_urls(self):
        login = app.login(Mock(body=json.dumps({'username': 'gordo', 'password': 'test'}), headers={'origin': 'https://trailer-feed.vercel.app'}, ip_addr='127.0.0.1'))
        owner_token = json.loads(login.description)['token']
        self.assertEqual(self.ingest(token=owner_token).status_code, 401)
        for url in ['https://evil.example/video.mp4', 'https://review.v1su4.dev/api/owner-media/private', 'https://review.v1su4.dev/api/destination-media/grant/other-version/original', 'https://review.v1su4.dev/api/destination-media/grant/version-1/original?token=private']:
            self.assertEqual(self.ingest({**self.payload, 'media_url': url}).status_code, 400)
        foreign = Mock(body=json.dumps(self.payload), headers={'authorization': 'Bearer test-ingest-only', 'origin': 'https://evil.example'}, path_params={})
        self.assertEqual(app.register_external_version(foreign).status_code, 401)
        public = app.get_document(Mock(headers={}, path_params={'run_id': self.run_id, 'file': 'artifacts.json'}))
        self.assertEqual(json.loads(public.description), [])


if __name__ == '__main__':
    unittest.main()
