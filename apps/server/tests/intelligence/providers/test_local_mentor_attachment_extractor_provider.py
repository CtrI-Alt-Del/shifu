from __future__ import annotations

# ruff: noqa: FBT003, SLF001

from types import SimpleNamespace
from typing import TYPE_CHECKING, ClassVar, cast

import pytest
from PIL import Image

import shifu.intelligence.providers.mentor_attachment.local_mentor_attachment_extractor_provider as extractor
from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.providers.mentor_attachment.local_mentor_attachment_extractor_provider import (
    LocalMentorAttachmentExtractorProvider,
)
from shifu.shared.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Callable


class _TextPage:
    def __init__(self, parts: tuple[str, ...], *, fail: bool = False) -> None:
        self.parts = parts
        self.fail = fail

    def extract_text(self, *, visitor_text: object) -> None:
        if self.fail:
            raise RuntimeError('bad page')
        for part in self.parts:
            cast('Callable[[str], None]', visitor_text)(part)


def _provider() -> LocalMentorAttachmentExtractorProvider:
    return LocalMentorAttachmentExtractorProvider(get_settings())


def test_pdf_page_text_caps_output_and_keeps_bad_pages_independent() -> None:
    text, truncated = extractor._extract_pdf_page_text(
        _TextPage(('abcdef', 'later')),
        3,  # type: ignore[arg-type]
    )
    assert (text, truncated) == ('abc', True)


def test_pdf_parser_rejects_encrypted_and_empty_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Reader:
        is_encrypted: ClassVar[bool] = True
        pages: ClassVar[list[object]] = []

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

    monkeypatch.setattr(extractor, 'PdfReader', Reader)
    assert extractor._parse_pdf_content(b'pdf', 2, 100) is None

    Reader.is_encrypted = False
    assert extractor._parse_pdf_content(b'pdf', 2, 100) is None


def test_require_pdf_render_result_rejects_malformed_and_oversized_results() -> None:
    assert extractor._require_pdf_render_result(None, 10) == ()
    assert extractor._require_pdf_render_result(((),), 10) == ()
    assert extractor._require_pdf_render_result(((1,),), 10) == ()
    assert extractor._require_pdf_render_result(((True, b'x'),), 10) == ()
    assert extractor._require_pdf_render_result(((1, 'image'),), 10) == ()
    assert extractor._require_pdf_render_result(((1, b'123'), (2, b'456')), 5) == ()
    assert extractor._require_pdf_render_result(((1, b'png'),), 3) == ((1, b'png'),)


def test_registered_pdf_worker_returns_none_when_process_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Endpoint:
        def close(self) -> None:
            pass

    class ProcessImpl:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError('spawn failed')

        def is_alive(self) -> bool:
            return False

        def join(self, timeout: float | None = None) -> None:
            pass

        def terminate(self) -> None:
            pass

        def kill(self) -> None:
            pass

    context = SimpleNamespace(
        Pipe=lambda **_kwargs: (Endpoint(), Endpoint()),
        Process=lambda **kwargs: ProcessImpl(**kwargs),
    )
    monkeypatch.setattr(extractor.multiprocessing, 'get_context', lambda _name: context)
    assert extractor._run_pdf_worker(lambda _pipe: None, 0.01) is None


def test_provider_extraction_rejects_invalid_inputs_and_handles_image_preview() -> None:
    provider = _provider()
    with pytest.raises(MentorAttachmentInvalidError):
        provider.validate(b'', 'text/plain')
    with pytest.raises(MentorAttachmentInvalidError):
        provider.extract(b'valid', 'application/octet-stream', 'attachment', 1)
    with pytest.raises(MentorAttachmentInvalidError):
        provider.render_visual_pages(b'not-image', 'image/png', (2,))

    image = Image.new('RGB', (2, 2), color='white')
    from io import BytesIO

    output = BytesIO()
    image.save(output, format='PNG')
    image.close()
    content = output.getvalue()
    extracted = provider.extract(content, 'image/png', 'attachment', 1)
    assert extracted.uninterpreted_pages == (1,)
    assert provider.render_visual_pages(content, 'image/png', (1,)) == ((1, content),)
    assert provider.render_visual_pages(content, 'text/plain', (1,)) == ()


def test_provider_pdf_extraction_records_illegible_empty_and_page_limited_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider()
    provider._max_pdf_pages = 1
    provider._max_extracted_chars = 3
    monkeypatch.setattr(
        extractor,
        '_run_pdf_parser',
        lambda *_args: extractor._PdfParseResult(3, (None, 'later'), False),
    )
    result = provider._extract_pdf(b'pdf', 'attachment', 1)
    assert result.illegible_pages == (1,)
    assert result.uninterpreted_pages == (2, 3)
    assert 'pdf_page_limit_reached' in result.limitations

    provider._max_pdf_pages = 3
    provider._max_extracted_chars = 0
    monkeypatch.setattr(
        extractor,
        '_run_pdf_parser',
        lambda *_args: extractor._PdfParseResult(2, ('text', ''), False),
    )
    result = provider._extract_pdf(b'pdf', 'attachment', 1)
    assert result.uninterpreted_pages == (1, 2)


def test_provider_rejects_zero_page_pdf_and_invalid_images(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider()
    monkeypatch.setattr(
        extractor,
        '_run_pdf_parser',
        lambda *_args: extractor._PdfParseResult(0, (), False),
    )
    with pytest.raises(MentorAttachmentInvalidError):
        provider.extract(b'%PDF', 'application/pdf', 'attachment', 1)
    with pytest.raises(MentorAttachmentInvalidError):
        provider._image(b'bad', 'image/png')


def test_provider_rejects_empty_page_generation_and_json_size_limit() -> None:
    provider = _provider()
    assert provider._text_chunks('  ', 'attachment', 1, None) == ()
    with pytest.raises(MentorAttachmentInvalidError):
        provider._text(b'{"text":"' + b'x' * 1_000_001 + b'"}', 'application/json')
