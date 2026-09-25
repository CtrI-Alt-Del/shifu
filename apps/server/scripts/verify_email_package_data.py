from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import cast


HTML_PATH = (
    'shifu/communication/providers/email/template/generated/account-confirmation.html'
)
MANIFEST_PATH = 'shifu/communication/providers/email/template/generated/account-confirmation.manifest.json'
PLACEHOLDER_PATTERN = re.compile(r'\{\{([a-z][a-z0-9_]*)\}\}')
EXPECTED_PLACEHOLDER_NAMES = frozenset({'display_name', 'action_url', 'expires_at'})
EXPECTED_MANIFEST: dict[str, object] = {
    'template': 'account-confirmation',
    'version': 1,
    'subject': 'Confirme seu e-mail no Shifu',
    'placeholders': [
        {'name': 'display_name', 'type': 'text'},
        {'name': 'action_url', 'type': 'url'},
        {'name': 'expires_at', 'type': 'text'},
    ],
}


def _read_json_manifest(archive: zipfile.ZipFile) -> object:
    try:
        manifest_bytes = archive.read(MANIFEST_PATH)
    except KeyError as error:
        raise ValueError(f'Missing generated manifest: {MANIFEST_PATH}') from error

    try:
        return cast('object', json.loads(manifest_bytes.decode('utf-8')))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            f'Generated manifest is not valid UTF-8 JSON: {MANIFEST_PATH}'
        ) from error


def _read_html(archive: zipfile.ZipFile) -> str:
    try:
        html_bytes = archive.read(HTML_PATH)
    except KeyError as error:
        raise ValueError(f'Missing generated HTML: {HTML_PATH}') from error

    try:
        return html_bytes.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError(f'Generated HTML is not valid UTF-8: {HTML_PATH}') from error


def _validate_generated_contract(archive: zipfile.ZipFile) -> None:
    manifest = _read_json_manifest(archive)
    if manifest != EXPECTED_MANIFEST:
        raise ValueError(
            'Generated e-mail manifest does not match the renderer contract.'
        )

    html = _read_html(archive)
    rendered_placeholder_names = {
        match.group(1) for match in PLACEHOLDER_PATTERN.finditer(html)
    }
    if rendered_placeholder_names != EXPECTED_PLACEHOLDER_NAMES:
        raise ValueError(
            'Generated e-mail HTML placeholders do not match the renderer contract.'
        )

    for required_fragment in ('lang="pt-BR"', 'dir="ltr"'):
        if required_fragment not in html:
            raise ValueError(
                f'Generated e-mail HTML is missing the required {required_fragment} attribute.'
            )


def verify_wheel(wheel_path: Path) -> None:
    if not wheel_path.is_file():
        raise FileNotFoundError(f'Wheel does not exist: {wheel_path}')

    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())
        missing_paths = {HTML_PATH, MANIFEST_PATH} - names
        if missing_paths:
            missing = ', '.join(sorted(missing_paths))
            raise ValueError(
                f'Wheel is missing generated e-mail package data: {missing}'
            )
        _validate_generated_contract(archive)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Verify generated e-mail package data in one or more wheels.'
    )
    parser.add_argument('wheels', nargs='+', type=Path)
    arguments = parser.parse_args()

    try:
        for wheel_path in arguments.wheels:
            verify_wheel(wheel_path)
            print(f'Verified generated e-mail package data: {wheel_path}')
    except (FileNotFoundError, ValueError, zipfile.BadZipFile) as error:
        print(f'Email package data verification failed: {error}', file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
