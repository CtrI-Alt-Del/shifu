from collections import Counter
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from shifu.learning.core.domain.entities import (
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    CompletedSkill,
    EvolutionOption,
    LearningPanorama,
    RecentMastery,
    ResumeItem,
    StageDistribution,
    WeeklyCount,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.local_week_start import local_week_start
from shifu.shared.core.domain.resolved_time_zone import resolved_time_zone
from shifu.shared.core.domain.structures import CurriculumSkillSnapshot
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider

_WEEK_COUNT = 8
_RESUME_LIMIT = 3
_MASTERY_LIMIT = 5
_RESUMABLE_STATUSES = frozenset(
    {SkillExperienceStatus.DIAGNOSING, SkillExperienceStatus.LEARNING}
)


class GetLearningPanoramaUseCase:
    def __init__(
        self,
        database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        clock: ClockProvider,
    ) -> None:
        self._database = database
        self._curriculum_content_provider = curriculum_content_provider
        self._clock = clock

    def execute(self, account_id: str, *, time_zone: str | None) -> LearningPanorama:
        zone = ZoneInfo(resolved_time_zone(time_zone))
        current_week = local_week_start(self._clock.now().astimezone(zone).date())
        weeks = tuple(
            current_week - timedelta(weeks=offset)
            for offset in range(_WEEK_COUNT - 1, -1, -1)
        )
        window_start = datetime.combine(weeks[0], time.min, tzinfo=zone).astimezone(UTC)

        with self._database.transaction() as repositories:
            goals = repositories.goals.find_many_by_account_id(account_id)
            goals_by_id = {goal.id: goal for goal in goals}
            experiences = [
                experience
                for experience in repositories.skill_experiences.find_many_by_account_id(
                    account_id
                )
                if experience.goal_id in goals_by_id
            ]
            experience_ids = [experience.id for experience in experiences]
            progresses = (
                repositories.competency_progresses.find_many_by_skill_experience_ids(
                    experience_ids
                )
            )
            latest_submissions = repositories.activity_attempts.find_many_latest_submitted_at_by_skill_experience_ids(
                experience_ids
            )
            evaluated_submissions = repositories.activity_attempts.find_many_evaluated_submitted_at_by_skill_experience_ids(
                experience_ids, since=window_start
            )

        names = self._skill_names(experiences)
        contents = _ContentLookup(self._curriculum_content_provider)
        progresses_by_experience: dict[str, dict[str, CompetencyProgress]] = {}
        for progress in progresses:
            progresses_by_experience.setdefault(progress.skill_experience_id, {})[
                progress.competency_id
            ] = progress

        recency_order = _by_recency(experiences, latest_submissions)
        started = [
            experience
            for experience in recency_order
            if experience.status is not SkillExperienceStatus.NOT_STARTED
            and experience.skill_id in names
        ]
        evolution_options = tuple(
            EvolutionOption(
                skill_experience_id=experience.id,
                goal_title=goals_by_id[experience.goal_id].title,
                skill_name=names[experience.skill_id],
                status=experience.status,
            )
            for experience in started
        )
        default_selection = next(
            (
                experience.id
                for experience in started
                if experience.id in latest_submissions
            ),
            None,
        )
        weekly_counts = Counter(
            local_week_start(instant.astimezone(zone).date())
            for instant in evaluated_submissions
        )

        return LearningPanorama(
            has_goals=bool(goals),
            completed_skill_count=len(
                {
                    experience.skill_id
                    for experience in experiences
                    if experience.status is SkillExperienceStatus.COMPLETED
                }
            ),
            mastered_competency_count=len(
                {
                    progress.competency_id
                    for progress in progresses
                    if progress.status is CompetencyProgressStatus.MASTERED
                }
            ),
            stage_distribution=_stage_distribution(experiences),
            resume_items=tuple(
                self._resume_items(
                    recency_order,
                    goals_by_id,
                    names,
                    contents,
                    progresses_by_experience,
                    latest_submissions,
                )
            ),
            weekly_evaluated_activities=tuple(
                WeeklyCount(week_start=week, count=weekly_counts.get(week, 0))
                for week in weeks
            ),
            evolution_options=evolution_options,
            default_evolution_skill_experience_id=default_selection,
            completed_skills=tuple(
                _completed_skills(experiences, goals_by_id, names, zone)
            ),
            recent_masteries=tuple(
                _recent_masteries(
                    experiences, progresses, goals_by_id, names, contents, zone
                )
            ),
        )

    def _skill_names(self, experiences: list[SkillExperience]) -> dict[str, str]:
        skill_ids = tuple(sorted({experience.skill_id for experience in experiences}))
        if not skill_ids:
            return {}

        return {
            overview.skill_id: overview.name
            for overview in self._curriculum_content_provider.get_skill_overviews(
                skill_ids
            )
        }

    @staticmethod
    def _resume_items(
        recency_order: list[SkillExperience],
        goals_by_id: dict[str, Goal],
        names: dict[str, str],
        contents: '_ContentLookup',
        progresses_by_experience: dict[str, dict[str, CompetencyProgress]],
        latest_submissions: dict[str, datetime],
    ) -> list[ResumeItem]:
        candidates = [
            experience
            for experience in recency_order
            if experience.status in _RESUMABLE_STATUSES and experience.skill_id in names
        ][:_RESUME_LIMIT]
        return [
            ResumeItem(
                skill_experience_id=experience.id,
                goal_id=experience.goal_id,
                goal_title=goals_by_id[experience.goal_id].title,
                skill_id=experience.skill_id,
                skill_name=names[experience.skill_id],
                status=experience.status,
                focus_competency_name=(
                    _focus_competency_name(
                        contents.get(experience.skill_id),
                        progresses_by_experience.get(experience.id, {}),
                    )
                    if experience.status is SkillExperienceStatus.LEARNING
                    else None
                ),
                last_submitted_at=latest_submissions.get(experience.id),
            )
            for experience in candidates
        ]


class _ContentLookup:
    """Fetches each Habilidade's content once, only when a block needs it."""

    def __init__(self, provider: CurriculumContentProvider) -> None:
        self._provider = provider
        self._cache: dict[str, CurriculumSkillSnapshot | None] = {}

    def get(self, skill_id: str) -> CurriculumSkillSnapshot | None:
        if skill_id not in self._cache:
            self._cache[skill_id] = self._provider.get_skill_content(skill_id)
        return self._cache[skill_id]


def _by_recency(
    experiences: list[SkillExperience],
    latest_submissions: dict[str, datetime],
) -> list[SkillExperience]:
    """Experiences with a submission first (newest first), then the others by
    newest start. Ties resolve by identifier so the order is deterministic."""
    by_id = sorted(experiences, key=lambda experience: experience.id)
    submitted = sorted(
        (item for item in by_id if item.id in latest_submissions),
        key=lambda item: latest_submissions[item.id],
        reverse=True,
    )
    unsubmitted = sorted(
        (item for item in by_id if item.id not in latest_submissions),
        key=lambda item: item.started_at or item.created_at,
        reverse=True,
    )
    return [*submitted, *unsubmitted]


def _stage_distribution(experiences: list[SkillExperience]) -> StageDistribution:
    counts = Counter(experience.status for experience in experiences)
    return StageDistribution(
        not_started=counts[SkillExperienceStatus.NOT_STARTED],
        diagnosing=counts[SkillExperienceStatus.DIAGNOSING],
        learning=counts[SkillExperienceStatus.LEARNING],
        completed=counts[SkillExperienceStatus.COMPLETED],
        goal_count=len({experience.goal_id for experience in experiences}),
    )


def _focus_competency_name(
    content: CurriculumSkillSnapshot | None,
    progress_by_competency: dict[str, CompetencyProgress],
) -> str | None:
    if content is None:
        return None

    for competency in sorted(content.competencies, key=lambda item: item.position):
        progress = progress_by_competency.get(competency.id)
        if (
            progress is None
            or progress.status is not CompetencyProgressStatus.MASTERED
            or progress.verification_cause is not None
        ):
            return competency.name
    return None


def _local_date(instant: datetime, zone: ZoneInfo) -> date:
    return instant.astimezone(zone).date()


def _completed_skills(
    experiences: list[SkillExperience],
    goals_by_id: dict[str, Goal],
    names: dict[str, str],
    zone: ZoneInfo,
) -> Iterable[CompletedSkill]:
    def completed_at(experience: SkillExperience) -> datetime:
        if experience.completed_at is not None:
            return experience.completed_at
        if experience.completion_summary is not None:
            return experience.completion_summary.completed_at
        return experience.updated_at

    completed = sorted(
        sorted(
            (
                experience
                for experience in experiences
                if experience.status is SkillExperienceStatus.COMPLETED
                and experience.skill_id in names
            ),
            key=lambda experience: experience.id,
        ),
        key=completed_at,
        reverse=True,
    )
    for experience in completed:
        summary = experience.completion_summary
        yield CompletedSkill(
            skill_experience_id=experience.id,
            goal_id=experience.goal_id,
            goal_title=goals_by_id[experience.goal_id].title,
            skill_id=experience.skill_id,
            skill_name=names[experience.skill_id],
            final_result=summary.final_progress if summary is not None else None,
            completed_on=_local_date(completed_at(experience), zone),
        )


def _recent_masteries(
    experiences: list[SkillExperience],
    progresses: list[CompetencyProgress],
    goals_by_id: dict[str, Goal],
    names: dict[str, str],
    contents: _ContentLookup,
    zone: ZoneInfo,
) -> list[RecentMastery]:
    experiences_by_id = {experience.id: experience for experience in experiences}
    stable: list[tuple[CompetencyProgress, datetime]] = [
        (progress, progress.mastered_at)
        for progress in progresses
        if progress.status is CompetencyProgressStatus.MASTERED
        and progress.mastered_at is not None
        and progress.verification_cause is None
        and progress.skill_experience_id in experiences_by_id
    ]
    stable.sort(key=lambda item: (item[0].skill_experience_id, item[0].competency_id))
    stable.sort(key=lambda item: item[1], reverse=True)

    masteries: list[RecentMastery] = []
    for progress, mastered_at in stable:
        experience = experiences_by_id[progress.skill_experience_id]
        skill_name = names.get(experience.skill_id)
        content = contents.get(experience.skill_id) if skill_name else None
        competency_name = next(
            (
                competency.name
                for competency in (content.competencies if content else ())
                if competency.id == progress.competency_id
            ),
            None,
        )
        if skill_name is None or competency_name is None:
            continue

        masteries.append(
            RecentMastery(
                skill_experience_id=experience.id,
                goal_id=experience.goal_id,
                goal_title=goals_by_id[experience.goal_id].title,
                skill_id=experience.skill_id,
                skill_name=skill_name,
                competency_id=progress.competency_id,
                competency_name=competency_name,
                mastered_on=_local_date(mastered_at, zone),
            )
        )
        if len(masteries) == _MASTERY_LIMIT:
            break

    return masteries
