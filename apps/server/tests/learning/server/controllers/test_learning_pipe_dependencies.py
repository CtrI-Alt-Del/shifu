from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import create_autospec

from shifu.learning.pipes import LearningPipe
from shifu.shared.core.interfaces import (
    CodeRubricAssessorProvider,
    CurriculumCatalogProvider,
)


class TestLearningPipeDependencies:
    def test_should_resolve_learning_state_through_fastapi_dependencies(self) -> None:
        assessor = create_autospec(CodeRubricAssessorProvider, instance=True)
        catalog = create_autospec(CurriculumCatalogProvider, instance=True)
        app = FastAPI()
        app.state.code_rubric_assessor_provider = assessor
        app.state.curriculum_catalog_provider = catalog
        app.state.max_activity_payload_bytes = 1024
        app.state.max_code_assessment_input_bytes = 2048

        @app.get('/learning/dependency-state')
        def read_dependency_state(
            request: Request,
            resolved_assessor: Annotated[
                CodeRubricAssessorProvider,
                Depends(LearningPipe.get_code_rubric_assessor_provider),
            ],
            activity_limit: Annotated[
                int,
                Depends(LearningPipe.get_max_activity_payload_bytes),
            ],
            assessment_limit: Annotated[
                int,
                Depends(LearningPipe.get_max_code_assessment_input_bytes),
            ],
            resolved_catalog: Annotated[
                CurriculumCatalogProvider,
                Depends(LearningPipe.get_curriculum_catalog_provider),
            ],
        ) -> dict[str, bool]:
            return {
                'assessor': resolved_assessor
                is request.app.state.code_rubric_assessor_provider,
                'activity_limit': activity_limit == 1024,
                'assessment_limit': assessment_limit == 2048,
                'catalog': resolved_catalog
                is request.app.state.curriculum_catalog_provider,
            }

        with TestClient(app) as client:
            response = client.get('/learning/dependency-state')

        assert response.status_code == 200
        assert response.json() == {
            'assessor': True,
            'activity_limit': True,
            'assessment_limit': True,
            'catalog': True,
        }
