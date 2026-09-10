from typing import Annotated

from fastapi import APIRouter, Depends


class CheckHealthController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/analyses/{analysis_id}', status_code=200, response_model=AnalysisDto
        )
        def _(
            analysis_id: str,
            account_id: Annotated[Id, Depends(AuthPipe.get_account_id_from_request)],
            analyses_repository: Annotated[
                AnalysesRepository,
                Depends(DatabasePipe.get_analyses_repository_from_request),
            ],
        ) -> AnalysisDto:
            use_case = GetAnalysisUseCase(
                analyses_repository=analyses_repository,
            )

            return use_case.execute(
                account_id=account_id.value,
                analysis_id=analysis_id,
            )
