import csv
import codecs
import io
import json
import math
import multiprocessing
import warnings
from collections.abc import Buffer, Callable
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from threading import Event, Thread
from typing import NoReturn, Protocol, cast

import pypdfium2
from PIL import Image, UnidentifiedImageError
from pypdf import PageObject, PdfReader
from pypdf._configuration import CURRENT_CONFIGURATION
from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentChunk,
    MentorAttachmentExtraction,
)
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class MentorAttachmentExtractionSettings(Protocol):
    mentor_attachment_max_image_pixels: int
    mentor_attachment_max_pdf_pages: int
    mentor_attachment_max_extracted_chars: int
    mentor_attachment_pdf_processing_timeout_seconds: int
    mentor_attachment_max_pdf_rendered_bytes: int


class _RenderedPdfBitmap(Protocol):
    def to_pil(self) -> Image.Image: ...

    def close(self) -> None: ...


class _RenderablePdfPage(Protocol):
    def get_size(self) -> tuple[float, float]: ...

    def render(self, *, scale: float) -> _RenderedPdfBitmap: ...

    def close(self) -> None: ...


class _RenderablePdfDocument(Protocol):
    def __len__(self) -> int: ...

    def __getitem__(self, page_index: int) -> object: ...

    def close(self) -> None: ...


_TEXT_TYPES = frozenset({'text/plain', 'text/csv', 'application/json'})
_CHUNK_SIZE = 3000
_MAX_ATTACHMENT_BYTES = 10_000_000
_MAX_JSON_VALIDATION_BYTES = 1_000_000


@dataclass(frozen=True)
class _PdfParseResult:
    page_count: int
    page_texts: tuple[str | None, ...]
    truncated: bool


class _PdfRenderOutputLimitError(Exception):
    pass


class _LimitedPdfRenderBuffer(io.BytesIO):
    def __init__(self, max_bytes: int) -> None:
        super().__init__()
        self._max_bytes: int = max_bytes

    def write(self, buffer: Buffer) -> int:
        if self.tell() + len(memoryview(buffer)) > self._max_bytes:
            raise _PdfRenderOutputLimitError
        return super().write(buffer)


def _parse_pdf_in_worker(
    result_pipe: Connection,
    content: bytes,
    max_pdf_pages: int,
    max_extracted_chars: int,
) -> None:
    try:
        configuration = CURRENT_CONFIGURATION.get().with_overwrites(
            maximum_declared_stream_length=8_000_000,
            array_based_stream_maximum_output_length=4_000_000,
            jbig2_maximum_output_length=4_000_000,
            lzw_maximum_output_length=4_000_000,
            run_length_maximum_output_length=4_000_000,
            zlib_maximum_output_length=4_000_000,
            brotli_maximum_output_length=4_000_000,
            flate_maximum_columns=100_000,
            flate_maximum_row_length=1_000_000,
            image_maximum_buffer_size=4_000_000,
            stream_filters_maximum_length=8,
            stream_decoding_work_maximum_length=50_000_000,
            page_tree_maximum_entries=1000,
            page_tree_maximum_depth=64,
            xform_maximum_invocations_per_extraction=1000,
        )
        configuration_token = CURRENT_CONFIGURATION.set(configuration)
        try:
            result_pipe.send(
                _parse_pdf_content(content, max_pdf_pages, max_extracted_chars)
            )
        finally:
            CURRENT_CONFIGURATION.reset(configuration_token)
    except Exception:  # noqa: BLE001 - parser failures are a safe attachment failure.
        with suppress(OSError, RuntimeError):
            result_pipe.send(None)
    finally:
        result_pipe.close()


def _render_pdf_pages_in_worker(
    result_pipe: Connection,
    content: bytes,
    page_numbers: tuple[int, ...],
    max_image_pixels: int,
    max_rendered_bytes: int,
) -> None:
    document: _RenderablePdfDocument | None = None
    output: list[tuple[int, bytes]] = []
    output_bytes = 0
    try:
        document = cast('_RenderablePdfDocument', pypdfium2.PdfDocument(content))
        page_count = len(document)
        for page_number in page_numbers:
            if not 1 <= page_number <= page_count:
                continue
            remaining_bytes = max_rendered_bytes - output_bytes
            if remaining_bytes <= 0:
                break
            try:
                page = cast('_RenderablePdfPage', document[page_number - 1])
                rendered = _render_pdf_page(page, max_image_pixels, remaining_bytes)
            except Exception:  # noqa: BLE001, S112 - omit one bad page without logging.
                continue
            if rendered is None:
                continue
            output.append((page_number, rendered))
            output_bytes += len(rendered)
    except Exception:  # noqa: BLE001, S110 - failures leave pages uninterpreted.
        pass
    finally:
        if document is not None:
            with suppress(Exception):
                document.close()
        with suppress(OSError, RuntimeError):
            result_pipe.send(tuple(output))
        result_pipe.close()


def _parse_pdf_content(
    content: bytes, max_pdf_pages: int, max_extracted_chars: int
) -> _PdfParseResult | None:
    reader = PdfReader(io.BytesIO(content), strict=True)
    if reader.is_encrypted:
        return None
    page_count = len(reader.pages)
    if page_count < 1:
        return None

    page_texts: list[str | None] = []
    characters_collected = 0
    truncated = False
    for page_number in range(1, min(page_count, max_pdf_pages) + 1):
        try:
            page_text, page_truncated = _extract_pdf_page_text(
                reader.pages[page_number - 1],
                max_extracted_chars + 1 - characters_collected,
            )
        except Exception:  # noqa: BLE001 - malformed pages fail independently.
            page_texts.append(None)
            continue

        page_texts.append(page_text)
        characters_collected += len(page_text)
        truncated = truncated or page_truncated
        if characters_collected >= max_extracted_chars:
            if page_number < page_count:
                truncated = True
            break

    return _PdfParseResult(
        page_count=page_count,
        page_texts=tuple(page_texts),
        truncated=truncated,
    )


def _extract_pdf_page_text(page: PageObject, max_output_chars: int) -> tuple[str, bool]:
    parts: list[str] = []
    characters_collected = 0
    truncated = False

    def collect_text(
        text: str, *_context: object, page_parts: list[str] = parts
    ) -> None:
        nonlocal characters_collected, truncated
        remaining = max_output_chars - characters_collected
        if remaining <= 0:
            truncated = True
            return
        accepted = text[:remaining]
        page_parts.append(accepted)
        characters_collected += len(accepted)
        if len(accepted) < len(text):
            truncated = True

    page.extract_text(visitor_text=collect_text)
    return ''.join(parts), truncated


def _stop_pdf_process(process: BaseProcess) -> None:
    if process.is_alive():
        process.terminate()
        process.join(timeout=0.2)
    if process.is_alive():
        process.kill()
        process.join(timeout=0.2)


def _run_pdf_worker(
    target: Callable[[Connection], None], timeout_seconds: float
) -> object | None:
    context = multiprocessing.get_context('spawn')
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=target, args=(sender,), daemon=True)
    result_received = Event()
    results: list[object] = []
    receiver_thread: Thread | None = None

    def receive_result() -> None:
        try:
            results.append(receiver.recv())
        except (EOFError, OSError):
            results.append(None)
        finally:
            result_received.set()

    try:
        process.start()
        sender.close()
        receiver_thread = Thread(target=receive_result, daemon=True)
        receiver_thread.start()
        if not result_received.wait(timeout_seconds):
            _stop_pdf_process(process)
            return None

        process.join(timeout=0.2)
        _stop_pdf_process(process)
        return results[0] if results else None
    except Exception:  # noqa: BLE001 - child failures are safe empty results.
        _stop_pdf_process(process)
        return None
    finally:
        _stop_pdf_process(process)
        if receiver_thread is not None:
            receiver_thread.join(timeout=0.2)
        receiver.close()
        sender.close()


def _raise_invalid_pdf() -> NoReturn:
    raise MentorAttachmentInvalidError


def _require_pdf_result(result: object) -> _PdfParseResult:
    if not isinstance(result, _PdfParseResult):
        _raise_invalid_pdf()
    return result


def _run_pdf_parser(
    content: bytes,
    max_pdf_pages: int,
    max_extracted_chars: int,
    timeout_seconds: float,
) -> _PdfParseResult:
    result = _run_pdf_worker(
        partial(
            _parse_pdf_in_worker,
            content=content,
            max_pdf_pages=max_pdf_pages,
            max_extracted_chars=max_extracted_chars,
        ),
        timeout_seconds,
    )
    return _require_pdf_result(result)


def _require_pdf_render_result(
    result: object, max_rendered_bytes: int
) -> tuple[tuple[int, bytes], ...]:
    if not isinstance(result, tuple):
        return ()
    output: list[tuple[int, bytes]] = []
    output_bytes = 0
    for entry in cast('tuple[object, ...]', result):
        if not isinstance(entry, tuple):
            return ()
        typed_entry = cast('tuple[object, ...]', entry)
        if len(typed_entry) != 2:
            return ()
        page_number, image = typed_entry
        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or not isinstance(image, bytes)
        ):
            return ()
        output_bytes += len(image)
        if output_bytes > max_rendered_bytes:
            return ()
        output.append((page_number, image))
    return tuple(output)


def _render_pdf_page(
    page: _RenderablePdfPage,
    max_image_pixels: int,
    max_output_bytes: int,
) -> bytes | None:
    bitmap: _RenderedPdfBitmap | None = None
    image: Image.Image | None = None
    try:
        width, height = page.get_size()
        scale = min(1.5, math.sqrt(max_image_pixels / (width * height)))
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        target = _LimitedPdfRenderBuffer(max_output_bytes)
        image.save(target, format='PNG', optimize=True)
        return target.getvalue()
    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        ZeroDivisionError,
        _PdfRenderOutputLimitError,
    ):
        return None
    finally:
        if image is not None:
            image.close()
        if bitmap is not None:
            bitmap.close()
        page.close()


class LocalMentorAttachmentExtractorProvider:
    def __init__(
        self,
        settings: MentorAttachmentExtractionSettings,
        identifier_provider: IdentifierProvider | None = None,
    ) -> None:
        self._max_image_pixels = settings.mentor_attachment_max_image_pixels
        self._max_pdf_pages = settings.mentor_attachment_max_pdf_pages
        self._max_extracted_chars = settings.mentor_attachment_max_extracted_chars
        self._pdf_processing_timeout_seconds = (
            settings.mentor_attachment_pdf_processing_timeout_seconds
        )
        self._max_pdf_rendered_bytes = settings.mentor_attachment_max_pdf_rendered_bytes
        self._identifier_provider = identifier_provider or SystemIdentifierProvider()

    def validate(self, content: bytes, media_type: str) -> None:
        if not content or len(content) > _MAX_ATTACHMENT_BYTES:
            raise MentorAttachmentInvalidError
        if media_type in _TEXT_TYPES:
            self._text(content, media_type)
            return
        if media_type == 'application/pdf':
            _run_pdf_parser(
                content,
                0,
                0,
                self._pdf_processing_timeout_seconds,
            )
            return
        if media_type.startswith('image/'):
            self._image(content, media_type)
            return
        raise MentorAttachmentInvalidError

    def extract(
        self, content: bytes, media_type: str, attachment_id: str, generation: int
    ) -> MentorAttachmentExtraction:
        if not content or len(content) > _MAX_ATTACHMENT_BYTES:
            raise MentorAttachmentInvalidError
        if media_type in _TEXT_TYPES:
            return self._extract_text(content, media_type, attachment_id, generation)
        if media_type.startswith('image/'):
            self._image(content, media_type)
            return MentorAttachmentExtraction(
                chunks=(),
                analyzed_pages=(),
                illegible_pages=(),
                uninterpreted_pages=(1,),
            )
        if media_type != 'application/pdf':
            raise MentorAttachmentInvalidError
        return self._extract_pdf(content, attachment_id, generation)

    def _extract_text(
        self, content: bytes, media_type: str, attachment_id: str, generation: int
    ) -> MentorAttachmentExtraction:
        text, truncated = self._text(content, media_type)
        chunks = self._text_chunks(text, attachment_id, generation, None)
        return MentorAttachmentExtraction(
            chunks=chunks,
            analyzed_pages=(),
            illegible_pages=(),
            uninterpreted_pages=(),
            limitations=('extracted_text_truncated',) if truncated else (),
        )

    def _extract_pdf(
        self, content: bytes, attachment_id: str, generation: int
    ) -> MentorAttachmentExtraction:
        parsed = _run_pdf_parser(
            content,
            self._max_pdf_pages,
            self._max_extracted_chars,
            self._pdf_processing_timeout_seconds,
        )
        page_count = parsed.page_count
        if page_count < 1:
            raise MentorAttachmentInvalidError
        page_limit = min(page_count, self._max_pdf_pages)
        analyzed_pages: list[int] = []
        illegible_pages: list[int] = []
        uninterpreted_pages: list[int] = list(range(page_limit + 1, page_count + 1))
        chunks: list[MentorAttachmentChunk] = []
        chars_left = self._max_extracted_chars
        truncated = parsed.truncated
        for page_number, page_text in enumerate(parsed.page_texts, start=1):
            if page_number > page_limit:
                break
            if page_text is None:
                illegible_pages.append(page_number)
                continue
            clean_text = page_text.strip()
            if not clean_text:
                uninterpreted_pages.append(page_number)
                continue
            text_for_page = clean_text[:chars_left]
            if not text_for_page:
                uninterpreted_pages.append(page_number)
                truncated = True
                uninterpreted_pages.extend(
                    current
                    for current in range(page_number + 1, page_count + 1)
                    if current not in uninterpreted_pages
                )
                break
            if len(text_for_page) < len(clean_text):
                truncated = True
            chars_left = max(0, chars_left - len(text_for_page))
            chunks.extend(
                self._text_chunks(text_for_page, attachment_id, generation, page_number)
            )
            analyzed_pages.append(page_number)
            if chars_left == 0 and page_number < page_count:
                truncated = True
                uninterpreted_pages.extend(
                    current
                    for current in range(page_number + 1, page_count + 1)
                    if current not in uninterpreted_pages
                )
                break
        return MentorAttachmentExtraction(
            chunks=tuple(chunks),
            analyzed_pages=tuple(analyzed_pages),
            illegible_pages=tuple(illegible_pages),
            uninterpreted_pages=tuple(sorted(set(uninterpreted_pages))),
            limitations=(
                ('pdf_page_limit_reached',) if page_count > self._max_pdf_pages else ()
            )
            + (('extracted_text_truncated',) if truncated else ()),
        )

    def render_visual_pages(
        self,
        content: bytes,
        media_type: str,
        page_numbers: tuple[int, ...],
    ) -> tuple[tuple[int, bytes], ...]:
        if media_type.startswith('image/'):
            if page_numbers not in {(1,), ()}:
                raise MentorAttachmentInvalidError
            self._image(content, media_type)
            return ((1, content),)
        if media_type != 'application/pdf':
            return ()
        if len(page_numbers) > self._max_pdf_pages:
            return ()
        result = _run_pdf_worker(
            partial(
                _render_pdf_pages_in_worker,
                content=content,
                page_numbers=page_numbers,
                max_image_pixels=self._max_image_pixels,
                max_rendered_bytes=self._max_pdf_rendered_bytes,
            ),
            self._pdf_processing_timeout_seconds,
        )
        return _require_pdf_render_result(result, self._max_pdf_rendered_bytes)

    def _image(self, content: bytes, media_type: str) -> tuple[int, int]:
        formats = {
            'image/jpeg': 'JPEG',
            'image/png': 'PNG',
            'image/webp': 'WEBP',
        }
        expected_format = formats.get(media_type)
        if expected_format is None:
            raise MentorAttachmentInvalidError
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    if image.format != expected_format:
                        raise MentorAttachmentInvalidError
                    width, height = image.size
                    if width * height > self._max_image_pixels:
                        raise MentorAttachmentInvalidError
                    image.verify()
                with Image.open(io.BytesIO(content)) as image:
                    if image.format != expected_format:
                        raise MentorAttachmentInvalidError
                    if image.width * image.height > self._max_image_pixels:
                        raise MentorAttachmentInvalidError
                    image.load()
                    return image.size
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as error:
            raise MentorAttachmentInvalidError from error

    def _text(self, content: bytes, media_type: str) -> tuple[str, bool]:
        if not content or len(content) > _MAX_ATTACHMENT_BYTES:
            raise MentorAttachmentInvalidError
        if (
            media_type == 'application/json'
            and len(content) > _MAX_JSON_VALIDATION_BYTES
        ):
            raise MentorAttachmentInvalidError

        try:
            if not self._has_non_whitespace_text(content):
                raise MentorAttachmentInvalidError
            if media_type == 'application/json':
                decoded = content.decode('utf-8-sig', errors='strict')
                json.loads(decoded)
                return decoded[: self._max_extracted_chars], len(
                    decoded
                ) > self._max_extracted_chars
            if media_type == 'text/csv':
                with io.TextIOWrapper(
                    io.BytesIO(content),
                    encoding='utf-8-sig',
                    errors='strict',
                    newline='',
                ) as source:
                    for _row in csv.reader(source, strict=True):
                        pass
        except (UnicodeDecodeError, json.JSONDecodeError, csv.Error) as error:
            raise MentorAttachmentInvalidError from error

        return self._decode_text_prefix(content)

    @staticmethod
    def _has_non_whitespace_text(content: bytes) -> bool:
        decoder = codecs.getincrementaldecoder('utf-8-sig')('strict')
        has_non_whitespace = False
        chunk_size = 64 * 1024
        for start in range(0, len(content), chunk_size):
            end = min(len(content), start + chunk_size)
            decoded = decoder.decode(content[start:end], final=end == len(content))
            if decoded.strip():
                has_non_whitespace = True
        return has_non_whitespace

    def _decode_text_prefix(self, content: bytes) -> tuple[str, bool]:
        byte_limit = 4 * (self._max_extracted_chars + 1) + 3
        prefix = content[:byte_limit]
        decoder = codecs.getincrementaldecoder('utf-8-sig')('strict')
        decoded = decoder.decode(prefix, final=len(prefix) == len(content))
        truncated = (
            len(content) > len(prefix) or len(decoded) > self._max_extracted_chars
        )
        return decoded[: self._max_extracted_chars], truncated

    def _text_chunks(
        self,
        text: str,
        attachment_id: str,
        generation: int,
        page_number: int | None,
    ) -> tuple[MentorAttachmentChunk, ...]:
        output: list[MentorAttachmentChunk] = []
        for start in range(0, len(text), _CHUNK_SIZE):
            raw_content = text[start : start + _CHUNK_SIZE]
            content = raw_content.strip()
            if not content:
                continue
            chunk_number = len(output) + 1
            page_prefix = f'page:{page_number}/' if page_number is not None else ''
            output.append(
                MentorAttachmentChunk(
                    chunk_id=self._identifier_provider.generate(),
                    attachment_id=attachment_id,
                    generation=generation,
                    page_number=page_number,
                    locator=f'{page_prefix}chars:{start + 1}-{start + len(raw_content)}#{chunk_number}',
                    content=content,
                )
            )
        return tuple(output)
