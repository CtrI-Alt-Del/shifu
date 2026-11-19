from __future__ import annotations

from io import BytesIO
from typing import Any, ClassVar

from PIL import Image, ImageDraw, ImageFont

from shifu.intelligence.ai.agno.agents import MentorAttachmentVisionAgent
from shifu.intelligence.ai.data.mentor_inference_usage import inference_guard_scope

from evals.eval import Eval


class PrepareMentorAttachmentEval(Eval):
    selector = 'prepare-mentor-attachment'
    workflow_id = 'intelligence-prepare-mentor-attachment'
    prompt_revision = 'mentor-attachment-vision-eval-v1'
    unavailable_failure_code = 'vision_unavailable'

    CASES: ClassVar[tuple[Eval.LocalCase, ...]] = (
        Eval.LocalCase(
            name='vision_reads_synthetic_fraction_page',
            tags=('smoke', 'vision', 'coverage'),
            input='synthetic-legible-page',
            expected={'legible': True, 'required_terms': ('1/2', '2/4')},
        ),
    )

    def __init__(self, *, mode: str) -> None:
        super().__init__(mode=mode)
        self.agent = MentorAttachmentVisionAgent()
        if self.double:
            self.agent.model = self.SyntheticModel(
                self.synthetic_response, profile='mentor-attachment-vision'
            )
            self.model_profile = 'synthetic-vision-model'
        else:
            self.require_model(self.agent)
            self.model_profile = 'configured-vision-profile'
        self.agents = (self.agent,)
        self.pages = {'synthetic-legible-page': self.synthetic_page()}

    def cases(self) -> tuple[Eval.LocalCase, ...]:
        return self.CASES

    def run_case(self, case: Eval.LocalCase) -> Eval.CaseOutcome:
        # Eval pages are fixed synthetic inputs with no learner context.
        with inference_guard_scope(lambda: None):
            output = self.agent.analyze(
                self.pages[case.input],
                media_type='image/png',
                attachment_id=case.input,
                page_number=1,
            )
        legible = getattr(output, 'legible', None)
        description = getattr(output, 'description', None)
        if isinstance(output, dict):
            legible = output.get('legible')
            description = output.get('description')
        normalized = description.casefold() if isinstance(description, str) else ''
        passed = bool(legible) and all(
            term in normalized for term in case.expected['required_terms']
        )
        return self.CaseOutcome(passed, None if passed else 'vision_coverage_rejected')

    @staticmethod
    def synthetic_response(_user_text: str, _schema: Any) -> dict[str, Any]:
        return {
            'legible': True,
            'description': 'A página mostra que 1/2 é equivalente a 2/4.',
        }

    @staticmethod
    def synthetic_page() -> bytes:
        image = Image.new('RGB', (960, 320), color='white')
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=42)
        draw.text((52, 70), 'FRACOES EQUIVALENTES', fill='black', font=font)
        draw.text((52, 160), '1/2 = 2/4', fill='black', font=font)
        buffer = BytesIO()
        image.save(buffer, format='PNG', optimize=False)
        return buffer.getvalue()
