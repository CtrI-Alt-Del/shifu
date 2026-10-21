from __future__ import annotations

from io import BytesIO
from time import monotonic
from typing import Any, Protocol

from PIL import Image, ImageDraw, ImageFont
from shifu.intelligence.ai.data.mentor_inference_usage import inference_guard_scope

from evals.common import (
    DATASET_REVISION,
    CaseDefinition,
    close_agent,
    select_definitions,
)


class _VisionAgent(Protocol):
    def analyze(
        self,
        image_content: bytes,
        *,
        media_type: str,
        attachment_id: str,
        page_number: int,
    ) -> Any: ...


_DEFINITIONS = (
    CaseDefinition(
        name='vision_reads_synthetic_fraction_page',
        tags=('smoke', 'vision', 'coverage'),
        input='synthetic-legible-page',
        expected={'legible': True, 'required_terms': ('1/2', '2/4')},
    ),
    CaseDefinition(
        name='vision_marks_noise_page_illegible',
        tags=('vision', 'coverage', 'safety'),
        input='synthetic-illegible-page',
        expected={'legible': False, 'description': ''},
    ),
)


def _synthetic_page(*, legible: bool) -> bytes:
    image = Image.new('RGB', (960, 320), color='white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=42)
    if legible:
        draw.text((52, 70), 'FRACOES EQUIVALENTES', fill='black', font=font)
        draw.text((52, 160), '1/2 = 2/4', fill='black', font=font)
    else:
        for y in range(20, 300, 18):
            for x in range(20, 940, 18):
                color = ((x * 7 + y * 3) % 256, (x * 11 + y) % 256, (y * 13) % 256)
                draw.rectangle((x, y, x + 8, y + 8), fill=color)
    buffer = BytesIO()
    image.save(buffer, format='PNG', optimize=False)
    return buffer.getvalue()


PAGES = {
    'synthetic-legible-page': _synthetic_page(legible=True),
    'synthetic-illegible-page': _synthetic_page(legible=False),
}


class PrepareMentorAttachmentEval:
    selector = 'prepare-mentor-attachment'
    workflow_id = 'intelligence-prepare-mentor-attachment'
    dataset_revision = DATASET_REVISION
    prompt_revision = 'mentor-attachment-vision-eval-v1'

    def __init__(
        self, vision_agent: _VisionAgent, *, mode: str, model_profile: str
    ) -> None:
        self._vision_agent = vision_agent
        self._mode = mode
        self._model_profile = model_profile

    @classmethod
    def definitions(cls) -> tuple[CaseDefinition, ...]:
        return _DEFINITIONS

    def run(self, name: str | None = None, tag: str | None = None) -> dict[str, Any]:
        definitions = self.definitions()
        selected = select_definitions(definitions, name=name, tag=tag)
        case_reports: list[dict[str, Any]] = []
        for definition in selected:
            started = monotonic()
            try:
                # Eval pages are fixed synthetic inputs with no learner context.
                with inference_guard_scope(lambda: None):
                    output = self._vision_agent.analyze(
                        PAGES[definition.input],
                        media_type='image/png',
                        attachment_id=definition.input,
                        page_number=1,
                    )
                legible = getattr(output, 'legible', None)
                description = getattr(output, 'description', None)
                if isinstance(output, dict):
                    legible = output.get('legible')
                    description = output.get('description')
                expected = definition.expected
                if expected['legible']:
                    normalized = (
                        description.casefold() if isinstance(description, str) else ''
                    )
                    passed = bool(legible) and all(
                        term in normalized for term in expected['required_terms']
                    )
                else:
                    passed = legible is False and description == expected['description']
                outcome = 'passed' if passed else 'failed'
                failure_code = None if passed else 'vision_coverage_rejected'
            except Exception:  # noqa: BLE001 - provider errors can contain image/request data.
                passed = False
                outcome = 'failed'
                failure_code = 'vision_unavailable'
            case_reports.append(
                {
                    'case_id': definition.name,
                    'outcome': outcome,
                    'duration_seconds': round(max(monotonic() - started, 0.0), 3),
                    'skipped': False,
                    'scorer_passed': passed,
                    'failure_code': failure_code,
                }
            )

        successful = bool(case_reports) and all(
            case['outcome'] == 'passed' for case in case_reports
        )
        return {
            'workflow': self.selector,
            'status': 'passed' if successful else 'failed',
            'partial': len(selected) < len(definitions),
            'mode': self._mode,
            'model_profile': self._model_profile,
            'dataset_revision': DATASET_REVISION,
            'prompt_revision': self.prompt_revision,
            'selected_case_ids': [definition.name for definition in selected],
            'counts': {
                'selected': len(case_reports),
                'passed': sum(case['outcome'] == 'passed' for case in case_reports),
                'failed': sum(case['outcome'] == 'failed' for case in case_reports),
                'skipped': 0,
            },
            'cases': case_reports,
        }

    def close(self) -> None:
        close_agent(self._vision_agent)
