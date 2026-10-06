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
            db.execute('INSERT INTO documents VALUES (?,?,?)', (self.run_id, 'run', json.dumps({'run_id': self.run_id, 'title': 'External verification', 'status': 'draft'})))
            db.execute('INSERT INTO documents VALUES (?,?,?)', (self.run_id, 'artifacts', '[]'))
        self.payload = {'run_id': self.run_id, 'batch_id': 'single-' + self.run_id, 'source_asset_id': 'asset-' + self.run_id, 'source_version_id': 'version-1', 'source_created_at': '2026-10-01T10:00:00+00:00', 'media_url': 'https://review.v1su4.dev/api/destination-media/selected-grant/version-1/original', 'metadata': {'model': 'Sora 2', 'prompt': 'Selected original take'}}

    def ingest(self, payload=None, token='test-ingest-only'):
        return app.register_external_version(Mock(body=json.dumps(payload or self.payload), headers={'authorization': 'Bearer ' + token}, path_params={}))

    def reserve(self, versions, batch_id='batch-1'):
        payload = {'run_id': self.run_id, 'batch_id': batch_id, 'versions': versions}
        return app.reserve_external_batch(Mock(body=json.dumps(payload), headers={'authorization': 'Bearer test-ingest-only'}, path_params={}))

    def connect(self, payload):
        return app.connect_review_project(Mock(body=json.dumps(payload), headers={'authorization': 'Bearer test-ingest-only'}, path_params={}))

    def test_folder_connection_persists_ids_across_renames_and_requires_explicit_name_collision_choice(self):
        identity = {'source_project_id': 'review-project-' + self.run_id, 'source_folder_id': 'folder-1'}
        title = 'Connected project ' + self.run_id
        first = self.connect({**identity, 'mode': 'create', 'title': title})
        self.assertEqual(first.status_code, 201)
        run_id = json.loads(first.description)['run_id']
        with app.connect() as db:
            run = app.document(db, run_id, 'run')
            self.assertIn('created', run)
            self.assertEqual(run['question'], '')
            run['title'] = 'Renamed target ' + self.run_id
            db.execute("UPDATE documents SET value=? WHERE run_id=? AND kind='run'", (json.dumps(run), run_id))
        app.initialize()
        repeated = self.connect({**identity, 'mode': 'create', 'title': 'Renamed source folder'})
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(json.loads(repeated.description)['run_id'], run_id)
        other = {**identity, 'source_folder_id': 'folder-2'}
        collision = self.connect({**other, 'mode': 'create', 'title': 'Renamed target ' + self.run_id})
        self.assertEqual(collision.status_code, 409)
        self.assertEqual(json.loads(collision.description)['existing_run_id'], run_id)
        selected = self.connect({**other, 'mode': 'connect', 'run_id': run_id})
        self.assertEqual(selected.status_code, 201)
        self.assertEqual(json.loads(selected.description)['run_id'], run_id)
        self.assertEqual(self.connect({**identity, 'mode': 'connect', 'run_id': self.run_id}).status_code, 409)

    def test_reservation_keeps_oldest_first_when_later_delivery_succeeds_before_retry(self):
        oldest = {key: self.payload[key] for key in ('source_asset_id', 'source_version_id', 'source_created_at')}
        newer = {**oldest, 'source_version_id': 'version-2', 'source_created_at': '2026-10-02T10:00:00+00:00'}
        newest = {**oldest, 'source_version_id': 'version-3', 'source_created_at': '2026-10-03T10:00:00+00:00'}
        reservation = self.reserve([newest, oldest, newer])
        self.assertEqual(reservation.status_code, 201)
        allocated = json.loads(reservation.description)['versions']
        self.assertEqual([(item['source_version_id'], item['version_number']) for item in allocated], [('version-1', 1), ('version-2', 2), ('version-3', 3)])
        second = {**self.payload, **newer, 'batch_id': 'batch-1', 'media_url': 'https://review.v1su4.dev/api/destination-media/selected-grant/version-2/original'}
        self.assertEqual(json.loads(self.ingest(second).description)['artifact']['version_number'], 2)
        app.initialize()
        self.assertEqual(self.reserve([newer, newest, oldest]).status_code, 200)
        first = self.ingest({**self.payload, 'batch_id': 'batch-1'})
        self.assertEqual(json.loads(first.description)['artifact']['version_number'], 1)
        third = {**self.payload, **newest, 'batch_id': 'batch-1', 'media_url': 'https://review.v1su4.dev/api/destination-media/selected-grant/version-3/original'}
        self.assertEqual(json.loads(self.ingest(third).description)['artifact']['version_number'], 3)

    def test_batch_identity_rejects_changed_selection_without_allocating_any_new_versions(self):
        original = self.payload
        self.assertEqual(self.reserve([original], self.payload['batch_id']).status_code, 201)
        changed = {**original, 'source_version_id': 'version-2'}
        self.assertEqual(self.reserve([original, changed], self.payload['batch_id']).status_code, 409)
        fresh = self.reserve([changed], 'new-' + self.run_id)
        self.assertEqual(json.loads(fresh.description)['versions'][0]['version_number'], 2)
        outside_batch = {**changed, 'batch_id': self.payload['batch_id'], 'media_url': 'https://review.v1su4.dev/api/destination-media/grant/version-2/original'}
        self.assertEqual(self.ingest(outside_batch).status_code, 409)

    def test_local_upload_cannot_take_an_external_batch_reserved_number(self):
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 201)
        login = app.login(Mock(body=json.dumps({'username': 'gordo', 'password': 'test'}), headers={'origin': 'https://trailer-feed.vercel.app'}))
        token = json.loads(login.description)['token']
        # Simulate only the external gateway failing after allocation; the actual upload route owns numbering.
        import httpx
        with patch.object(app.httpx, 'Client', side_effect=httpx.ConnectError('Gateway offline')):
            response = app.upload(Mock(body=b'local-video', headers={'authorization': 'Bearer ' + token, 'x-run-id': self.run_id, 'x-filename': 'local.mp4'}))
        self.assertEqual(response.status_code, 502)
        with app.connect() as db:
            upload = db.execute('SELECT version FROM uploads WHERE run_id=?', (self.run_id,)).fetchone()
        self.assertEqual(upload['version'], 2)

    def test_concurrent_deliveries_of_the_same_reserved_version_create_one_artifact(self):
        from concurrent.futures import ThreadPoolExecutor
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 201)
        with ThreadPoolExecutor(max_workers=4) as executor:
            responses = list(executor.map(lambda _: self.ingest(), range(4)))
        self.assertEqual(sorted(response.status_code for response in responses), [200, 200, 200, 201])
        self.assertEqual(len({json.loads(response.description)['artifact']['artifact_id'] for response in responses}), 1)

    def test_grid_and_references_remain_external_and_retry_does_not_overwrite_them(self):
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 201)
        grid = {'source_version_id': 'grid-1', 'media_url': 'https://review.v1su4.dev/api/destination-media/selected-grant/grid-1/original'}
        image = {'source_version_id': 'image-1', 'media_url': 'https://review.v1su4.dev/api/destination-media/selected-grant/image-1/original'}
        fields = [{'id': 'seed', 'label': 'Seed', 'kind': 'number', 'value': 42}, {'id': 'unused', 'label': 'Unused', 'kind': 'number', 'value': None}, {'id': 'approved', 'label': 'Approved', 'kind': 'boolean', 'value': None}]
        payload = {**self.payload, 'grid': grid, 'references': [image], 'poster_url': 'https://review.v1su4.dev/api/destination-media/selected-grant/version-1/poster', 'metadata': {**self.payload['metadata'], 'sourceLabel': 'Selected V7', 'notes': 'Camera test', 'customFields': fields}}
        first = self.ingest(payload)
        artifact = json.loads(first.description)['artifact']
        self.assertEqual(artifact['shot_grid_url'], grid['media_url'])
        self.assertEqual(artifact['thumbnail_url'], payload['poster_url'])
        self.assertEqual(artifact['title'], 'Selected V7')
        self.assertEqual(artifact['notes'], 'Camera test')
        self.assertEqual(artifact['creative_metadata']['customFields'], fields)
        public = app.get_document(Mock(headers={}, path_params={'run_id': self.run_id, 'file': 'artifacts.json'}))
        values = json.loads(public.description)
        references = [item for item in values if item['artifact_type'] in ('shot_grid', 'image_result')]
        self.assertEqual([item['media_url'] for item in references], [grid['media_url'], image['media_url']])
        self.assertTrue(all(item['ownership'] == 'external' and 'object_key' not in item for item in references))
        self.assertEqual(self.ingest({**payload, 'grid': None, 'references': []}).status_code, 200)
        public = app.get_document(Mock(headers={}, path_params={'run_id': self.run_id, 'file': 'artifacts.json'}))
        self.assertEqual(json.loads(public.description), values)

    def test_invalid_creative_date_does_not_consume_a_reserved_delivery(self):
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 201)
        invalid = {**self.payload, 'metadata': {**self.payload['metadata'], 'releaseDate': '2026-02-30'}}
        self.assertEqual(self.ingest(invalid).status_code, 400)
        self.assertEqual(self.ingest().status_code, 201)

    def test_target_removal_persists_suppression_and_old_retries_cannot_restore_the_version(self):
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 201)
        artifact = json.loads(self.ingest().description)['artifact']
        login = app.login(Mock(body=json.dumps({'username': 'gordo', 'password': 'test'}), headers={'origin': 'https://trailer-feed.vercel.app'}))
        token = json.loads(login.description)['token']
        request = Mock(body=json.dumps({'run_id': self.run_id, 'confirm_artifact_id': artifact['artifact_id']}), headers={'authorization': 'Bearer ' + token}, path_params={'id': artifact['artifact_id']})
        with patch.object(app.httpx, 'Client') as storage:
            self.assertEqual(app.remove_external_version(request).status_code, 200)
            storage.assert_not_called()
        app.initialize()
        status = app.external_version_status(Mock(body=json.dumps({'versions': [self.payload]}), headers={'authorization': 'Bearer test-ingest-only'}))
        self.assertEqual(json.loads(status.description)['versions'][0]['state'], 'target_suppressed')
        self.assertEqual(self.ingest().status_code, 409)
        self.assertEqual(self.reserve([self.payload], 'generic-retry-' + self.run_id).status_code, 409)
        public = app.get_document(Mock(headers={}, path_params={'run_id': self.run_id, 'file': 'artifacts.json'}))
        self.assertEqual(json.loads(public.description), [])
        newer = {**self.payload, 'source_version_id': 'version-2'}
        self.assertEqual(json.loads(self.reserve([newer], 'new-' + self.run_id).description)['versions'][0]['version_number'], 2)

    def test_project_removal_suppresses_registered_and_reserved_source_versions(self):
        pending = {**self.payload, 'source_version_id': 'pending-version'}
        self.assertEqual(self.reserve([self.payload, pending], self.payload['batch_id']).status_code, 201)
        self.assertEqual(self.ingest().status_code, 201)
        login = app.login(Mock(body=json.dumps({'username': 'gordo', 'password': 'test'}), headers={'origin': 'https://trailer-feed.vercel.app'}))
        token = json.loads(login.description)['token']
        response = Mock(status_code=200)
        response.json.return_value = {'failed': 0}
        client = Mock()
        client.post.return_value = response
        with patch.object(app.httpx, 'Client') as gateway:
            gateway.return_value.__enter__.return_value = client
            removed = app.delete_run(Mock(body=json.dumps({'confirm_run_id': self.run_id}), headers={'authorization': 'Bearer ' + token}, path_params={'run_id': self.run_id}))
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(client.post.call_args.args[0], app.GATEWAY + '/trailer-feed/delete-run-objects')
        self.assertEqual(client.post.call_args.kwargs['json']['prefixes'], ['version-assets/' + self.run_id + '/'])
        status = app.external_version_status(Mock(body=json.dumps({'versions': [self.payload, pending]}), headers={'authorization': 'Bearer test-ingest-only'}))
        self.assertEqual([item['state'] for item in json.loads(status.description)['versions']], ['target_suppressed', 'target_suppressed'])
        self.assertEqual(self.ingest().status_code, 409)

    def test_explicit_exact_version_reactivation_advances_consent_and_rejects_old_delivery_or_removal(self):
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 201)
        artifact = json.loads(self.ingest().description)['artifact']
        login = app.login(Mock(body=json.dumps({'username': 'gordo', 'password': 'test'}), headers={'origin': 'https://trailer-feed.vercel.app'}))
        token = json.loads(login.description)['token']
        removal = Mock(body=json.dumps({'run_id': self.run_id, 'confirm_artifact_id': artifact['artifact_id'], 'expected_generation': 1}), headers={'authorization': 'Bearer ' + token}, path_params={'id': artifact['artifact_id']})
        self.assertEqual(app.remove_external_version(removal).status_code, 200)
        consent = {**self.payload, 'batch_id': 'again-' + self.run_id, 'intent': 'sync-again', 'expected_generation': 1}
        request = Mock(body=json.dumps(consent), headers={'authorization': 'Bearer test-ingest-only'})
        reactivated = app.reactivate_external_version(request)
        self.assertEqual(reactivated.status_code, 201)
        self.assertEqual(json.loads(reactivated.description)['consent_generation'], 2)
        self.assertEqual(app.reactivate_external_version(request).status_code, 200)
        self.assertEqual(self.ingest().status_code, 409)
        self.assertEqual(app.remove_external_version(removal).status_code, 409)
        fresh = {**self.payload, 'batch_id': consent['batch_id'], 'consent_generation': 2, 'media_url': 'https://review.v1su4.dev/api/destination-media/fresh-grant/version-1/original'}
        current = self.ingest(fresh)
        self.assertEqual(current.status_code, 201)
        self.assertEqual(json.loads(current.description)['artifact']['version_number'], 1)
        self.assertEqual(json.loads(current.description)['artifact']['consent_generation'], 2)
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 409)
        self.assertEqual(app.remove_external_version(removal).status_code, 409)

    def test_reactivation_in_another_target_never_reuses_the_old_project_version_number(self):
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 201)
        artifact = json.loads(self.ingest().description)['artifact']
        login = app.login(Mock(body=json.dumps({'username': 'gordo', 'password': 'test'}), headers={'origin': 'https://trailer-feed.vercel.app'}))
        token = json.loads(login.description)['token']
        removal = Mock(body=json.dumps({'run_id': self.run_id, 'confirm_artifact_id': artifact['artifact_id']}), headers={'authorization': 'Bearer ' + token}, path_params={'id': artifact['artifact_id']})
        self.assertEqual(app.remove_external_version(removal).status_code, 200)
        target = self.connect({'source_project_id': 'other-' + self.run_id, 'mode': 'create', 'title': 'Other target ' + self.run_id})
        new_run_id = json.loads(target.description)['run_id']
        consent = {**self.payload, 'run_id': new_run_id, 'batch_id': 'moved-' + self.run_id, 'intent': 'sync-again', 'expected_generation': 1}
        self.assertEqual(app.reactivate_external_version(Mock(body=json.dumps(consent), headers={'authorization': 'Bearer test-ingest-only'})).status_code, 201)
        newer = {**self.payload, 'source_version_id': 'version-2'}
        allocated = self.reserve([newer], 'next-' + self.run_id)
        self.assertEqual(json.loads(allocated.description)['versions'][0]['version_number'], 2)

    def test_exact_source_retry_survives_restart_and_keeps_target_edits(self):
        self.assertEqual(self.reserve([self.payload], self.payload['batch_id']).status_code, 201)
        first = self.ingest()
        self.assertEqual(first.status_code, 201)
        artifact = json.loads(first.description)['artifact']
        self.assertEqual(artifact['version_number'], 1)
        self.assertEqual(artifact['media_url'], self.payload['media_url'])
        self.assertEqual(artifact['ownership'], 'external')
        self.assertEqual(artifact['created_at'], '2026-10-01T10:00:00+00:00')
        self.assertEqual(artifact['run_id'], self.run_id)
        self.assertNotIn('object_key', artifact)
        project = app.get_document(Mock(headers={}, path_params={'run_id': self.run_id, 'file': 'run.json'}))
        self.assertEqual(json.loads(project.description)['status'], 'ready_for_review')
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
