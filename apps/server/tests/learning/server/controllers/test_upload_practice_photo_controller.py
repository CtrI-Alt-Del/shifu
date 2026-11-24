from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PIL import Image
import io
from concurrent.futures import ThreadPoolExecutor

from tests.fixtures.practice_draft_fixture import (
    AUTH_HEADERS,
    OTHER_HEADERS,
    PracticeDraftClient,
    PracticeDraftFixture,
)
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoImages

if TYPE_CHECKING:
    from httpx import Response

UPLOAD_KEY = '8b3a3f4e-2f1c-4c52-9d0b-1c2d3e4f5a6b'
OTHER_UPLOAD_KEY = '0f4d6f6e-6a2b-4a8e-8d1e-5a9c1b2d3e4f'


def _photo_path(record_key: str = 'cuts') -> str:
    return f'{PracticeDraftFixture.draft_path()}/photos/{record_key}'


def _put(
    practice: PracticeDraftClient,
    *,
    record_key: str = 'cuts',
    media_type: str = 'image/jpeg',
    upload_key: str = UPLOAD_KEY,
    file: tuple[str, bytes, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    return practice.client.put(  # pyright: ignore[reportReturnType] - TestClient returns its own httpx Response alias.
        _photo_path(record_key),
        files={'file': file or PracticePhotoImages.file(media_type)},
        data={'upload_key': upload_key},
        headers=headers or AUTH_HEADERS,
    )


class TestUploadPracticePhotoController:
    @pytest.mark.parametrize('media_type', ['image/jpeg', 'image/png', 'image/webp'])
    def test_should_store_the_photo_privately_and_return_the_ready_draft(
        self, practice_client: PracticeDraftClient, media_type: str
    ) -> None:
        response = _put(practice_client, media_type=media_type)

        body = response.json()
        assert response.status_code == 200, response.text
        assert response.headers['cache-control'] == 'private, no-store'
        assert body['revision'] == 1
        assert [
            (item['record_key'], item['state'], item['media_type'])
            for item in body['photos']
        ] == [('cuts', 'ready', media_type)]
        object_key = f'practice-photos/{body["photos"][0]["photo_id"]}/original'
        assert list(practice_client.storage.objects) == [object_key]
        assert PracticeDraftFixture.counts(practice_client.database) == (1, 1)

    def test_should_not_duplicate_the_photo_when_the_upload_key_repeats(
        self, practice_client: PracticeDraftClient
    ) -> None:
        file = PracticePhotoImages.file()
        first = _put(practice_client, file=file)
        second = _put(practice_client, file=file)

        assert second.status_code == 200, second.text
        assert second.json() == first.json()
        assert len(practice_client.storage.objects) == 1
        assert PracticeDraftFixture.counts(practice_client.database) == (1, 1)

    def test_should_replace_the_photo_and_queue_the_old_object_for_cleanup(
        self, practice_client: PracticeDraftClient
    ) -> None:
        first = _put(practice_client)
        replaced = _put(
            practice_client,
            upload_key=OTHER_UPLOAD_KEY,
            file=PracticePhotoImages.file('image/png'),
        )

        old_id = first.json()['photos'][0]['photo_id']
        body = replaced.json()
        assert replaced.status_code == 200, replaced.text
        assert [item['photo_id'] for item in body['photos']] != [old_id]
        assert len(body['photos']) == 1
        assert PracticeDraftFixture.counts(practice_client.database) == (1, 2)

    def test_should_mark_the_photo_failed_when_storage_is_unavailable(
        self, practice_client: PracticeDraftClient
    ) -> None:
        practice_client.storage.fail_put = True

        response = _put(practice_client)

        assert response.status_code == 200, response.text
        assert [item['state'] for item in response.json()['photos']] == ['failed']
        assert practice_client.storage.objects == {}

    @pytest.mark.parametrize(
        ('file', 'media_type'),
        [
            (
                ('prato.png', PracticePhotoImages.build('image/jpeg'), 'image/png'),
                'image/jpeg',
            ),
            (
                ('prato.jpg', PracticePhotoImages.build('image/png'), 'image/jpeg'),
                'image/png',
            ),
        ],
        ids=['jpeg-named-png', 'png-named-jpg'],
    )
    def test_should_store_the_real_format_when_the_name_disagrees(
        self,
        practice_client: PracticeDraftClient,
        file: tuple[str, bytes, str],
        media_type: str,
    ) -> None:
        response = _put(practice_client, file=file)

        assert response.status_code == 200, response.text
        assert [item['media_type'] for item in response.json()['photos']] == [
            media_type
        ]

    @pytest.mark.parametrize(
        ('file', 'expected_code'),
        [
            (('prato.jpg', b'', 'image/jpeg'), 'malformed_photo'),
            (('prato.jpg', b'texto simples', 'image/jpeg'), 'malformed_photo'),
            (('prato.gif', b'GIF89a', 'image/gif'), 'malformed_photo'),
            (
                ('prato.jpg', b'\xff\xd8\xff\xe0truncated', 'image/jpeg'),
                'malformed_photo',
            ),
        ],
        ids=[
            'empty',
            'not-an-image',
            'unsupported',
            'undecodable',
        ],
    )
    def test_should_reject_invalid_files_without_writing_anything(
        self,
        practice_client: PracticeDraftClient,
        file: tuple[str, bytes, str],
        expected_code: str,
    ) -> None:
        response = _put(practice_client, file=file)

        assert response.status_code == 422, response.text
        assert response.json()['code'] == expected_code
        assert PracticeDraftFixture.counts(practice_client.database) == (0, 0)
        assert practice_client.storage.objects == {}

    def test_should_accept_exactly_ten_megabytes_and_refuse_one_byte_more(
        self, practice_client: PracticeDraftClient
    ) -> None:
        # A JPEG stays decodable when trailing bytes follow its end marker.
        base = PracticePhotoImages.build('image/jpeg')
        limit = 10 * 1024 * 1024
        accepted = _put(
            practice_client,
            file=('prato.jpg', base + b'\0' * (limit - len(base)), 'image/jpeg'),
        )
        refused = _put(
            practice_client,
            upload_key=OTHER_UPLOAD_KEY,
            file=('prato.jpg', base + b'\0' * (limit + 1 - len(base)), 'image/jpeg'),
        )

        assert accepted.status_code == 200, accepted.text
        assert refused.status_code == 413, refused.text
        assert refused.json()['code'] == 'photo_too_large'
        assert len(practice_client.storage.objects) == 1

    def test_should_refuse_a_pixel_bomb(
        self, practice_client: PracticeDraftClient
    ) -> None:
        buffer = io.BytesIO()
        Image.new('1', (6000, 6000)).save(buffer, format='PNG')

        response = _put(
            practice_client, file=('prato.png', buffer.getvalue(), 'image/png')
        )

        assert response.status_code == 422, response.text
        assert practice_client.storage.objects == {}

    def test_should_reject_a_record_the_activity_does_not_request(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = _put(practice_client, record_key='unknown')

        assert response.status_code == 400, response.text
        assert PracticeDraftFixture.counts(practice_client.database) == (0, 0)

    def test_should_reject_a_missing_file_or_a_non_uuid_upload_key(
        self, practice_client: PracticeDraftClient
    ) -> None:
        missing_file = practice_client.client.put(
            _photo_path(), data={'upload_key': UPLOAD_KEY}, headers=AUTH_HEADERS
        )
        bad_key = _put(practice_client, upload_key='not-a-uuid')

        assert missing_file.status_code == 422, missing_file.text
        assert bad_key.status_code == 422, bad_key.text

    def test_should_answer_413_before_parsing_an_oversized_multipart_body(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = practice_client.client.put(
            _photo_path(),
            content=b'x' * (10 * 1024 * 1024 + 65_000),
            headers={**AUTH_HEADERS, 'Content-Type': 'multipart/form-data; boundary=x'},
        )

        assert response.status_code == 413, response.text
        assert response.json()['code'] == 'photo_too_large'

    def test_should_deny_another_account_without_writing(
        self, practice_client: PracticeDraftClient
    ) -> None:
        response = _put(practice_client, headers=OTHER_HEADERS)

        assert response.status_code == 404, response.text
        assert PracticeDraftFixture.counts(practice_client.database) == (0, 0)
        assert practice_client.storage.objects == {}

    def test_should_keep_the_ready_object_when_two_requests_share_an_upload_key(
        self, practice_client: PracticeDraftClient
    ) -> None:
        file = PracticePhotoImages.file()

        def upload(_index: int) -> Response:
            return _put(practice_client, file=file)

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(upload, range(2)))

        assert [item.status_code for item in responses] == [200, 200]
        read = practice_client.client.get(
            PracticeDraftFixture.draft_path(), headers=AUTH_HEADERS
        ).json()
        assert [item['state'] for item in read['photos']] == ['ready']
        object_key = f'practice-photos/{read["photos"][0]["photo_id"]}/original'
        assert object_key in practice_client.storage.objects
        assert PracticeDraftFixture.counts(practice_client.database) == (1, 1)

    def test_should_store_the_photo_without_exif_or_gps_metadata(
        self, practice_client: PracticeDraftClient
    ) -> None:
        exif = Image.Exif()
        exif[0x010F] = 'CameraMaker'
        exif[0x8825] = {1: 'N', 2: (23.0, 33.0, 1.0), 3: 'W', 4: (46.0, 38.0, 1.0)}
        buffer = io.BytesIO()
        Image.new('RGB', (12, 8), (10, 200, 30)).save(buffer, format='JPEG', exif=exif)
        original = buffer.getvalue()
        assert Image.open(io.BytesIO(original)).getexif().get_ifd(0x8825)

        response = _put(practice_client, file=('prato.jpg', original, 'image/jpeg'))

        assert response.status_code == 200, response.text
        stored = next(iter(practice_client.storage.objects.values()))
        assert b'CameraMaker' not in stored
        with Image.open(io.BytesIO(stored)) as image:
            assert image.format == 'JPEG'
            assert len(image.getexif()) == 0
            assert image.size == (12, 8)
        assert response.json()['photos'][0]['size_bytes'] == len(stored)
