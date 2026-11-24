from shifu.learning.core.use_cases.mixed_question_snapshots import (
    MixedQuestionSnapshots,
)
from shifu.learning.core.domain.enums import ActivityDifficulty, SkillExperienceStatus
from shifu.learning.core.domain.structures import (
    ChoiceActivityDetail,
    ChoiceOptionDetail,
    ChoiceQuestionDetail,
    CodeQuestionDetail,
    FillBlanksQuestionDetail,
    FillBlanksSegmentDetail,
    FillBlanksWordDetail,
    CodeQuestionCriterionDetail,
    ImageChoiceOptionDetail,
    ImageChoiceQuestionDetail,
    OrderingQuestionDetail,
    OrderingStepDetail,
    VerifiedOrderingDetail,
    VerifiedOrdering,
    PairMatchingItemDetail,
    PairMatchingQuestionDetail,
    PracticalPreparationCriterionDetail,
    PracticalPreparationQuestionDetail,
    PracticalPreparationRecordDetail,
    PracticalPreparationReferenceDetail,
    TranslationQuestionCriterionDetail,
    TranslationQuestionDetail,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.diagnostic_sequence import DiagnosticSequence
from shifu.learning.core.use_cases.choice_evidence_eligibility import (
    ChoiceEvidenceEligibility,
)
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumOrderingQuestionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumImageChoiceQuestionSnapshot,
    CurriculumPairMatchingQuestionSnapshot,
    CurriculumPracticalPreparationQuestionSnapshot,
    CurriculumTranslationQuestionSnapshot,
    CurriculumTranslationRubricPartSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider
from shifu.learning.core.use_cases.ordering_answer_validation import (
    OrderingAnswerValidation,
)


class GetChoiceActivityUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
    ) -> None:
        self._learning_database = learning_database
        self._curriculum_content_provider = curriculum_content_provider

    def execute(  # noqa: C901
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        diagnostic_run_id: str | None = None,
    ) -> ChoiceActivityDetail:
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.id != goal_id or goal.account_id != account_id:
                raise NotFoundError

            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            if (
                experience is None
                or experience.goal_id != goal_id
                or experience.skill_id != skill_id
            ):
                raise NotFoundError

            diagnostic = experience.status is SkillExperienceStatus.DIAGNOSING
            if diagnostic and (
                diagnostic_run_id is None
                or diagnostic_run_id != experience.diagnostic_run_id
            ):
                raise ConflictError

            if not diagnostic:
                progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
                    experience.id, competency_id
                )
                if (
                    progress is None
                    or progress.skill_experience_id != experience.id
                    or progress.competency_id != competency_id
                    or not progress.content_released
                ):
                    raise NotFoundError

            active_passage = (
                repositories.ordering_passages.find_active(experience.id, activity_id)
                if not diagnostic
                else None
            )

        if diagnostic:
            snapshot = self._curriculum_content_provider.get_diagnostic_activity(
                activity_id
            )
        else:
            if active_passage is not None:
                snapshot = active_passage.grading_snapshot
            else:
                mixed_getter = getattr(
                    self._curriculum_content_provider, 'get_learning_activity', None
                )
                snapshot = (
                    mixed_getter(activity_id) if mixed_getter is not None else None
                )
                if not isinstance(
                    snapshot, CurriculumLearningActivitySnapshot
                ) or not MixedQuestionSnapshots.has_non_choice(snapshot.questions):
                    snapshot = self._curriculum_content_provider.get_choice_activity(
                        activity_id
                    )

        if (
            snapshot is None
            or snapshot.id != activity_id
            or snapshot.competency_id != competency_id
            or snapshot.activity_type != ('diagnostic' if diagnostic else 'learning')
            or not self.is_eligible(snapshot, diagnostic=diagnostic)
        ):
            raise NotFoundError

        if isinstance(snapshot, CurriculumChoiceActivitySnapshot):
            live_catalog = self._curriculum_content_provider.get_skill_content(skill_id)
            if not ChoiceEvidenceEligibility.is_valid(snapshot, live_catalog):
                raise NotFoundError

        with self._learning_database.transaction() as repositories:
            if diagnostic:
                locked_experience = (
                    repositories.skill_experiences.find_by_id_for_update(experience.id)
                )
                if (
                    locked_experience is None
                    or locked_experience.status is not SkillExperienceStatus.DIAGNOSING
                    or locked_experience.diagnostic_run_id != diagnostic_run_id
                ):
                    raise ConflictError

                experience = locked_experience
                catalog = self._curriculum_content_provider.get_skill_content(skill_id)
                if catalog is None or not catalog.v2_eligible:
                    raise NotFoundError

                diagnostic_attempts = tuple(
                    repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                        experience.id, diagnostic_run_id or ''
                    )
                )
                if diagnostic_attempts or not any(
                    item_competency_id == competency_id and item.id == activity_id
                    for item_competency_id, item in DiagnosticSequence.ordered(catalog)
                ):
                    raise NotFoundError
            unresolved = repositories.activity_evaluations.find_unresolved_by_skill_experience_id(
                experience.id
            )
            if unresolved is not None:
                unresolved_attempt = repositories.activity_attempts.find_by_id(
                    unresolved.attempt_id
                )
                if (
                    unresolved_attempt is not None
                    and unresolved_attempt.grading_snapshot is not None
                    and unresolved_attempt.grading_snapshot.id
                ):
                    unresolved_attempt_id = unresolved_attempt.id
                else:
                    unresolved_attempt_id = None
            else:
                unresolved_attempt_id = None
            active_passage = (
                repositories.ordering_passages.find_active(experience.id, activity_id)
                if not diagnostic
                else None
            )
            verified_by_question = (
                {item.question_key: item for item in active_passage.verified_orderings}
                if active_passage is not None
                else {}
            )
            if active_passage is not None:
                snapshot = active_passage.grading_snapshot
            attempts = (
                [
                    item
                    for item in repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                        experience.id, diagnostic_run_id or ''
                    )
                    if item.activity_id == activity_id
                ]
                if diagnostic
                else repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id(
                    experience.id, activity_id
                )
            )
            latest_attempt = attempts[-1] if attempts else None
            return ChoiceActivityDetail(
                activity_id=activity_id,
                title=snapshot.title,
                difficulty=ActivityDifficulty(snapshot.difficulty),
                questions=tuple(
                    self._ordering_question_detail(
                        question,
                        active_passage.activity_revision
                        if active_passage is not None
                        else snapshot.revision or snapshot.id,
                        verified_by_question.get(question.key),
                    )
                    if isinstance(question, CurriculumOrderingQuestionSnapshot)
                    else self.fill_blanks_question_detail(question)
                    if isinstance(question, CurriculumFillBlanksQuestionSnapshot)
                    else CodeQuestionDetail(
                        key=question.key,
                        kind=question.kind,
                        prompt=question.prompt,
                        initial_files=question.initial_files,
                        entrypoint=(
                            question.frontend_entrypoint
                            if isinstance(
                                question, CurriculumReactFastifyQuestionSnapshot
                            )
                            else question.entrypoint
                        ),
                        editable_paths=tuple(
                            item.path
                            for item in question.initial_files
                            if item.editable
                        ),
                        fixed_dependencies=question.fixed_dependencies,
                        permitted_commands=question.permitted_commands,
                        criteria=tuple(
                            CodeQuestionCriterionDetail(
                                key=item.key,
                                name=item.name,
                                weight_percentage=item.weight_percentage,
                            )
                            for part in (() if diagnostic else snapshot.parts)
                            if isinstance(part, CurriculumCodeRubricPartSnapshot)
                            and part.question_key == question.key
                            for item in part.criteria
                        ),
                        frontend_entrypoint=(
                            question.frontend_entrypoint
                            if isinstance(
                                question, CurriculumReactFastifyQuestionSnapshot
                            )
                            else None
                        ),
                        api_entrypoint=(
                            question.api_entrypoint
                            if isinstance(
                                question, CurriculumReactFastifyQuestionSnapshot
                            )
                            else None
                        ),
                        frontend_command_id=(
                            question.frontend_command_id
                            if isinstance(
                                question, CurriculumReactFastifyQuestionSnapshot
                            )
                            else None
                        ),
                        api_command_id=(
                            question.api_command_id
                            if isinstance(
                                question, CurriculumReactFastifyQuestionSnapshot
                            )
                            else None
                        ),
                        http_examples=(
                            question.http_examples
                            if isinstance(
                                question, CurriculumReactFastifyQuestionSnapshot
                            )
                            else ()
                        ),
                        additional_file_policy=(
                            question.additional_file_policy
                            if isinstance(
                                question,
                                (
                                    CurriculumReactQuestionSnapshot,
                                    CurriculumReactFastifyQuestionSnapshot,
                                ),
                            )
                            else None
                        ),
                    )
                    if isinstance(
                        question,
                        (
                            CurriculumJavascriptStdinQuestionSnapshot,
                            CurriculumReactQuestionSnapshot,
                            CurriculumHtmlCssJsQuestionSnapshot,
                            CurriculumReactFastifyQuestionSnapshot,
                        ),
                    )
                    else TranslationQuestionDetail(
                        key=question.key,
                        kind=question.kind,
                        prompt=question.prompt,
                        source_language=question.source_language,
                        target_language=question.target_language,
                        source_text=question.source_text,
                        criteria=tuple(
                            TranslationQuestionCriterionDetail(
                                key=item.key,
                                name=item.name,
                                weight_percentage=item.weight_percentage,
                            )
                            for part in (() if diagnostic else snapshot.parts)
                            if isinstance(part, CurriculumTranslationRubricPartSnapshot)
                            and part.question_key == question.key
                            for item in part.criteria
                        ),
                    )
                    if isinstance(question, CurriculumTranslationQuestionSnapshot)
                    else PairMatchingQuestionDetail(
                        key=question.key,
                        prompt=question.prompt,
                        source_language=question.source_language,
                        target_language=question.target_language,
                        words=tuple(
                            PairMatchingItemDetail(key=item.key, text=item.text)
                            for item in question.words
                        ),
                        translations=tuple(
                            PairMatchingItemDetail(key=item.key, text=item.text)
                            for item in question.translations
                        ),
                    )
                    if isinstance(question, CurriculumPairMatchingQuestionSnapshot)
                    else self.image_choice_question_detail(question)
                    if isinstance(question, CurriculumImageChoiceQuestionSnapshot)
                    else self.practical_question_detail(question)
                    if isinstance(
                        question, CurriculumPracticalPreparationQuestionSnapshot
                    )
                    else ChoiceQuestionDetail(
                        key=question.key,
                        kind=question.kind,
                        prompt=question.prompt,
                        options=tuple(
                            ChoiceOptionDetail(key=option.key, text=option.text)
                            for option in question.options
                        ),
                    )
                    for question in snapshot.questions
                ),
                can_submit=unresolved_attempt_id is None,
                latest_attempt_id=latest_attempt.id if latest_attempt else None,
                unresolved_attempt_id=unresolved_attempt_id,
                is_diagnostic=diagnostic,
                activity_revision=(
                    snapshot.diagnostic_revision
                    if diagnostic
                    else active_passage.activity_revision
                    if active_passage is not None
                    else snapshot.revision
                ),
                ordering_passage_key=(
                    active_passage.passage_key if active_passage is not None else None
                ),
            )

    @staticmethod
    def _ordering_question_detail(
        question: CurriculumOrderingQuestionSnapshot,
        revision: str,
        verified: VerifiedOrdering | None,
    ) -> OrderingQuestionDetail:
        return OrderingQuestionDetail(
            key=question.key,
            kind='ordering',
            prompt=question.prompt,
            steps=tuple(
                OrderingStepDetail(key=step.key, text=step.text)
                for step in question.steps
            ),
            initial_ordered_step_keys=OrderingAnswerValidation.initial_order(
                question, revision
            ),
            verified=(
                VerifiedOrderingDetail(
                    ordered_step_keys=verified.ordered_step_keys,
                    score=verified.score,
                    is_correct=verified.is_correct,
                    explanation=verified.explanation,
                )
                if verified is not None
                else None
            ),
        )

    @staticmethod
    def image_choice_question_detail(
        question: CurriculumImageChoiceQuestionSnapshot,
    ) -> ImageChoiceQuestionDetail:
        return ImageChoiceQuestionDetail(
            key=question.key,
            kind='image_choice',
            prompt=question.prompt,
            options=tuple(
                ImageChoiceOptionDetail(
                    key=option.key,
                    image_path=option.image_path,
                    description=option.description,
                )
                for option in question.options
            ),
        )

    @staticmethod
    def practical_question_detail(
        question: CurriculumPracticalPreparationQuestionSnapshot,
    ) -> PracticalPreparationQuestionDetail:
        """Public projection of the rubric: levels, comments and insufficiency rules stay private."""
        return PracticalPreparationQuestionDetail(
            key=question.key,
            prompt=question.prompt,
            guidance=question.guidance,
            references=tuple(
                PracticalPreparationReferenceDetail(
                    label=item.label, accessible_text=item.accessible_text
                )
                for item in question.references
            ),
            difficulty=question.difficulty,
            records=tuple(
                PracticalPreparationRecordDetail(
                    key=item.key, label=item.label, must_show=item.must_show
                )
                for item in question.records
            ),
            criteria=tuple(
                PracticalPreparationCriterionDetail(
                    key=item.key,
                    name=item.name,
                    description=item.description,
                    weight=item.weight,
                )
                for item in question.criteria
            ),
        )

    @staticmethod
    def fill_blanks_question_detail(
        question: CurriculumFillBlanksQuestionSnapshot,
    ) -> FillBlanksQuestionDetail:
        return FillBlanksQuestionDetail(
            key=question.key,
            prompt=question.prompt,
            content_language=question.content_language,
            segments=tuple(
                FillBlanksSegmentDetail(text=item.text, blank_key=item.blank_key)
                for item in question.segments
            ),
            bank=tuple(
                FillBlanksWordDetail(key=item.key, word=item.word)
                for item in question.bank
            ),
        )

    @staticmethod
    def is_eligible(
        snapshot: CurriculumChoiceActivitySnapshot | CurriculumLearningActivitySnapshot,
        *,
        diagnostic: bool = False,
    ) -> bool:
        question_keys = tuple(question.key for question in snapshot.questions)
        part_keys = tuple(part.question_key for part in snapshot.parts)
        is_practical = any(
            isinstance(question, CurriculumPracticalPreparationQuestionSnapshot)
            for question in snapshot.questions
        )
        return (
            (
                bool(snapshot.questions)
                if diagnostic
                else (
                    # A practical question stands alone or joins a mix of three to five.
                    len(snapshot.questions) == 1 or 3 <= len(snapshot.questions) <= 5
                )
                if is_practical
                else 3 <= len(snapshot.questions) <= 5
            )
            and len(set(question_keys)) == len(question_keys)
            and len(part_keys) == len(question_keys)
            and set(part_keys) == set(question_keys)
            and sum(part.weight_percentage for part in snapshot.parts) == 100
        )
