from dataclasses import fields
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import (
    CompetencyProgressFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.fakers.learning.structures import SkillCompletionSummaryFaker
from shifu.learning.core.domain.entities import CompetencyProgress, SkillExperience
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
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import GetLearningPanoramaUseCase
from shifu.shared.core.domain.structures import (
    CurriculumCompetencySnapshot,
    CurriculumSkillOverview,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider

ACCOUNT_ID = 'account-1'
SAO_PAULO = 'America/Sao_Paulo'
NOW = datetime(2026, 11, 18, 15, 0, tzinfo=UTC)  # a Wednesday
WEEKS = (
    date(2026, 9, 28),
    date(2026, 10, 5),
    date(2026, 10, 12),
    date(2026, 10, 19),
    date(2026, 10, 26),
    date(2026, 11, 2),
    date(2026, 11, 9),
    date(2026, 11, 16),
)
UTC_WINDOW_START = datetime(2026, 9, 28, 0, 0, tzinfo=UTC)
SAO_PAULO_WINDOW_START = datetime(2026, 9, 28, 3, 0, tzinfo=UTC)

PYTHON_SKILL_ID = 'skill-python'
LOGIC_SKILL_ID = 'skill-logic'
DATA_GOAL_ID = 'goal-data'
CODING_GOAL_ID = 'goal-coding'


def _at(month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


def _skill(
    skill_id: str,
    name: str,
    competencies: tuple[tuple[str, str], ...],
) -> CurriculumSkillSnapshot:
    return CurriculumSkillSnapshot(
        id=skill_id,
        name=name,
        competencies=tuple(
            CurriculumCompetencySnapshot(
                id=competency_id,
                skill_id=skill_id,
                name=competency_name,
                position=position,
                items=(),
            )
            for position, (competency_id, competency_name) in enumerate(
                competencies, start=1
            )
        ),
    )


def _experience(
    experience_id: str,
    status: SkillExperienceStatus,
    *,
    goal_id: str = DATA_GOAL_ID,
    skill_id: str = PYTHON_SKILL_ID,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    final_result: Decimal = Decimal('90'),
) -> SkillExperience:
    created_at = _at(9, 1)
    started = started_at or (
        None if status is SkillExperienceStatus.NOT_STARTED else created_at
    )
    return SkillExperienceFaker.fake(
        id=experience_id,
        goal_id=goal_id,
        skill_id=skill_id,
        status=status,
        created_at=created_at,
        started_at=started,
        completed_at=completed_at,
        completion_summary=(
            SkillCompletionSummaryFaker.fake(
                final_progress=final_result,
                started_at=started or created_at,
                completed_at=completed_at or created_at,
            )
            if status is SkillExperienceStatus.COMPLETED
            else None
        ),
    )


def _mastered(
    experience_id: str,
    competency_id: str,
    mastered_at: datetime,
    *,
    verification_cause: str | None = None,
) -> CompetencyProgress:
    return CompetencyProgressFaker.fake(
        skill_experience_id=experience_id,
        competency_id=competency_id,
        status=CompetencyProgressStatus.MASTERED,
        mastered_at=mastered_at,
        verification_cause=verification_cause,
    )


def _progress(
    experience_id: str,
    competency_id: str,
    status: CompetencyProgressStatus = CompetencyProgressStatus.LEARNING,
) -> CompetencyProgress:
    return CompetencyProgressFaker.fake(
        skill_experience_id=experience_id,
        competency_id=competency_id,
        status=status,
    )


def _weekly(counts: dict[int, int] | None = None) -> tuple[WeeklyCount, ...]:
    """Eight local weeks, oldest first; ``counts`` maps a week index to its count."""
    by_index = counts or {}
    return tuple(
        WeeklyCount(week_start=week, count=by_index.get(index, 0))
        for index, week in enumerate(WEEKS)
    )


class TestGetLearningPanoramaUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.catalog: dict[str, CurriculumSkillSnapshot] = {}

        def overviews(
            skill_ids: tuple[str, ...],
        ) -> tuple[CurriculumSkillOverview, ...]:
            return tuple(
                CurriculumSkillOverview(
                    skill_id=skill.id,
                    name=skill.name,
                    competency_ids=tuple(item.id for item in skill.competencies),
                    foundation_skill_ids=(),
                )
                for skill_id in skill_ids
                if (skill := self.catalog.get(skill_id)) is not None
            )

        self.provider.get_skill_overviews.side_effect = overviews
        self.provider.get_skill_content.side_effect = self.catalog.get
        self._store()
        self.subject = GetLearningPanoramaUseCase(
            self.database, self.provider, self.clock
        )

    def _store(
        self,
        *,
        goal_ids: tuple[str, ...] = (),
        experiences: tuple[SkillExperience, ...] = (),
        progresses: tuple[CompetencyProgress, ...] = (),
        latest: dict[str, datetime] | None = None,
        evaluated: tuple[datetime, ...] = (),
    ) -> None:
        titles = {
            DATA_GOAL_ID: 'Carreira em dados',
            CODING_GOAL_ID: 'Aprender a programar',
        }
        self.repositories.goals.find_many_by_account_id.return_value = [
            GoalFaker.fake(
                id=goal_id,
                account_id=ACCOUNT_ID,
                title=titles.get(goal_id, f'Objetivo {goal_id}'),
            )
            for goal_id in goal_ids
        ]
        self.repositories.skill_experiences.find_many_by_account_id.return_value = list(
            experiences
        )
        self.repositories.competency_progresses.find_many_by_skill_experience_ids.return_value = list(
            progresses
        )
        self.repositories.activity_attempts.find_many_latest_submitted_at_by_skill_experience_ids.return_value = (
            latest or {}
        )
        self.repositories.activity_attempts.find_many_evaluated_submitted_at_by_skill_experience_ids.return_value = list(
            evaluated
        )

    def _register_skills(self) -> None:
        self.catalog[PYTHON_SKILL_ID] = _skill(
            PYTHON_SKILL_ID,
            'Python para análise de dados',
            (('competency-1', 'Limpeza de tabelas'), ('competency-2', 'Agregações')),
        )
        self.catalog[LOGIC_SKILL_ID] = _skill(
            LOGIC_SKILL_ID,
            'Lógica de programação',
            (('competency-3', 'Variáveis'), ('competency-4', 'Condições')),
        )

    def test_should_return_an_empty_panorama_when_the_account_has_no_objective(
        self,
    ) -> None:
        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result == LearningPanorama(
            has_goals=False,
            completed_skill_count=0,
            mastered_competency_count=0,
            stage_distribution=StageDistribution(
                not_started=0, diagnosing=0, learning=0, completed=0, goal_count=0
            ),
            resume_items=(),
            weekly_evaluated_activities=_weekly(),
            evolution_options=(),
            default_evolution_skill_experience_id=None,
            completed_skills=(),
            recent_masteries=(),
        )
        self.repositories.goals.find_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.repositories.skill_experiences.find_many_by_account_id.assert_called_once_with(
            ACCOUNT_ID
        )
        self.provider.get_skill_overviews.assert_not_called()
        self.provider.get_skill_content.assert_not_called()

    def test_should_report_objectives_without_experiences_and_count_no_stage(
        self,
    ) -> None:
        self._store(goal_ids=(DATA_GOAL_ID,))

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.has_goals is True
        assert result.stage_distribution == StageDistribution(
            not_started=0, diagnosing=0, learning=0, completed=0, goal_count=0
        )

    @pytest.mark.parametrize('time_zone', [None, '', 'Mars/Olympus_Mons'])
    def test_should_resolve_weeks_in_utc_when_the_time_zone_is_absent_empty_or_invalid(
        self, time_zone: str | None
    ) -> None:
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('experience-1', SkillExperienceStatus.LEARNING),),
            evaluated=(datetime(2026, 11, 16, 2, 30, tzinfo=UTC),),
        )
        self._register_skills()

        result = self.subject.execute(ACCOUNT_ID, time_zone=time_zone)

        assert result.weekly_evaluated_activities == _weekly({7: 1})
        self.repositories.activity_attempts.find_many_evaluated_submitted_at_by_skill_experience_ids.assert_called_once_with(
            ['experience-1'], since=UTC_WINDOW_START
        )

    def test_should_start_the_window_at_the_local_monday_of_the_oldest_week(
        self,
    ) -> None:
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('experience-1', SkillExperienceStatus.LEARNING),),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=SAO_PAULO)

        assert [item.week_start for item in result.weekly_evaluated_activities] == list(
            WEEKS
        )
        self.repositories.activity_attempts.find_many_evaluated_submitted_at_by_skill_experience_ids.assert_called_once_with(
            ['experience-1'], since=SAO_PAULO_WINDOW_START
        )

    def test_should_split_a_sunday_night_and_a_monday_morning_attempt_by_local_date(
        self,
    ) -> None:
        sunday_2330_local = datetime(2026, 11, 16, 2, 30, tzinfo=UTC)
        monday_0030_local = datetime(2026, 11, 16, 3, 30, tzinfo=UTC)
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('experience-1', SkillExperienceStatus.LEARNING),),
            evaluated=(sunday_2330_local, monday_0030_local),
        )

        local = self.subject.execute(ACCOUNT_ID, time_zone=SAO_PAULO)
        utc = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert local.weekly_evaluated_activities == _weekly({6: 1, 7: 1})
        assert utc.weekly_evaluated_activities == _weekly({7: 2})

    def test_should_count_the_attempt_exactly_at_the_window_start_and_drop_the_one_just_before(
        self,
    ) -> None:
        at_window_start = datetime(2026, 9, 28, 3, 0, tzinfo=UTC)
        just_before = datetime(2026, 9, 28, 2, 59, 59, tzinfo=UTC)
        older_than_eight_weeks = datetime(2026, 9, 1, 15, 0, tzinfo=UTC)
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('experience-1', SkillExperienceStatus.LEARNING),),
            evaluated=(older_than_eight_weeks, just_before, at_window_start),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=SAO_PAULO)

        assert result.weekly_evaluated_activities == _weekly({0: 1})

    def test_should_sum_the_evaluated_attempts_of_every_experience_per_local_week(
        self,
    ) -> None:
        self._store(
            goal_ids=(DATA_GOAL_ID, CODING_GOAL_ID),
            experiences=(
                _experience('experience-1', SkillExperienceStatus.LEARNING),
                _experience(
                    'experience-2',
                    SkillExperienceStatus.COMPLETED,
                    goal_id=CODING_GOAL_ID,
                    skill_id=LOGIC_SKILL_ID,
                    completed_at=_at(10, 1),
                ),
            ),
            evaluated=(
                _at(10, 14),
                _at(10, 15),
                _at(10, 16),
                _at(11, 18, 10),
                _at(11, 19, 10),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=SAO_PAULO)

        assert result.weekly_evaluated_activities == _weekly({2: 3, 7: 2})
        self.repositories.activity_attempts.find_many_evaluated_submitted_at_by_skill_experience_ids.assert_called_once_with(
            ['experience-1', 'experience-2'], since=SAO_PAULO_WINDOW_START
        )

    def test_should_report_each_stage_and_the_objectives_that_contain_experiences(
        self,
    ) -> None:
        self._store(
            goal_ids=(DATA_GOAL_ID, CODING_GOAL_ID, 'goal-third', 'goal-empty'),
            experiences=(
                _experience('e-1', SkillExperienceStatus.NOT_STARTED),
                _experience('e-2', SkillExperienceStatus.DIAGNOSING),
                _experience(
                    'e-3', SkillExperienceStatus.LEARNING, goal_id=CODING_GOAL_ID
                ),
                _experience(
                    'e-4', SkillExperienceStatus.LEARNING, goal_id=CODING_GOAL_ID
                ),
                _experience(
                    'e-5',
                    SkillExperienceStatus.COMPLETED,
                    goal_id=CODING_GOAL_ID,
                    completed_at=_at(10, 2),
                ),
                _experience(
                    'e-6',
                    SkillExperienceStatus.COMPLETED,
                    goal_id='goal-third',
                    completed_at=_at(10, 3),
                ),
                _experience(
                    'e-7',
                    SkillExperienceStatus.COMPLETED,
                    goal_id='goal-third',
                    skill_id=LOGIC_SKILL_ID,
                    completed_at=_at(10, 4),
                ),
                _experience(
                    'e-8',
                    SkillExperienceStatus.NOT_STARTED,
                    goal_id='goal-third',
                ),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.has_goals is True
        assert result.stage_distribution == StageDistribution(
            not_started=2, diagnosing=1, learning=2, completed=3, goal_count=3
        )

    def test_should_count_the_same_skill_completed_in_two_objectives_once(
        self,
    ) -> None:
        self._store(
            goal_ids=(DATA_GOAL_ID, CODING_GOAL_ID),
            experiences=(
                _experience(
                    'e-1', SkillExperienceStatus.COMPLETED, completed_at=_at(10, 2)
                ),
                _experience(
                    'e-2',
                    SkillExperienceStatus.COMPLETED,
                    goal_id=CODING_GOAL_ID,
                    completed_at=_at(10, 3),
                ),
                _experience(
                    'e-3',
                    SkillExperienceStatus.COMPLETED,
                    skill_id=LOGIC_SKILL_ID,
                    completed_at=_at(10, 4),
                ),
                _experience('e-4', SkillExperienceStatus.LEARNING),
            ),
        )
        self._register_skills()

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.completed_skill_count == 2
        assert result.stage_distribution.completed == 3

    def test_should_count_a_competency_mastered_in_three_experiences_once_and_keep_open_verifications(
        self,
    ) -> None:
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(
                _experience('e-1', SkillExperienceStatus.LEARNING),
                _experience('e-2', SkillExperienceStatus.LEARNING),
                _experience('e-3', SkillExperienceStatus.LEARNING),
            ),
            progresses=(
                _mastered('e-1', 'competency-1', _at(10, 1)),
                _mastered('e-2', 'competency-1', _at(10, 2)),
                _mastered('e-3', 'competency-1', _at(10, 3)),
                _mastered(
                    'e-1', 'competency-2', _at(10, 4), verification_cause='evidence'
                ),
                _progress('e-2', 'competency-2', CompetencyProgressStatus.DEVELOPING),
                _progress('e-3', 'competency-3', CompetencyProgressStatus.PROFICIENT),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.mastered_competency_count == 2

    def test_should_return_the_five_newest_stable_masteries_without_lost_or_unverified_ones(
        self,
    ) -> None:
        competencies = tuple(
            (f'competency-{n}', f'Competência {n}') for n in range(1, 10)
        )
        self.catalog[PYTHON_SKILL_ID] = _skill(
            PYTHON_SKILL_ID, 'Python para análise de dados', competencies
        )
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('e-1', SkillExperienceStatus.LEARNING),),
            progresses=(
                *(
                    _mastered('e-1', f'competency-{n}', _at(9, n + 1, 1))
                    for n in range(1, 8)
                ),
                _progress('e-1', 'competency-8', CompetencyProgressStatus.DEVELOPING),
                _mastered(
                    'e-1', 'competency-9', _at(9, 20), verification_cause='evidence'
                ),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=SAO_PAULO)

        assert result.mastered_competency_count == 8
        assert result.recent_masteries == tuple(
            RecentMastery(
                skill_experience_id='e-1',
                goal_id=DATA_GOAL_ID,
                goal_title='Carreira em dados',
                skill_id=PYTHON_SKILL_ID,
                skill_name='Python para análise de dados',
                competency_id=f'competency-{n}',
                competency_name=f'Competência {n}',
                mastered_on=date(2026, 9, n),
            )
            for n in (7, 6, 5, 4, 3)
        )

    @pytest.mark.parametrize(('mastered', 'listed'), [(1, 1), (5, 5), (7, 5)])
    def test_should_cap_the_recent_masteries_at_five(
        self, mastered: int, listed: int
    ) -> None:
        self.catalog[PYTHON_SKILL_ID] = _skill(
            PYTHON_SKILL_ID,
            'Python para análise de dados',
            tuple((f'competency-{n}', f'Competência {n}') for n in range(1, 8)),
        )
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('e-1', SkillExperienceStatus.LEARNING),),
            progresses=tuple(
                _mastered('e-1', f'competency-{n}', _at(9, n + 1))
                for n in range(1, mastered + 1)
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert len(result.recent_masteries) == listed

    def test_should_list_the_three_newest_submissions_and_ignore_completed_and_attempt_less_experiences(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID, CODING_GOAL_ID),
            experiences=(
                _experience('e-1', SkillExperienceStatus.LEARNING),
                _experience('e-2', SkillExperienceStatus.DIAGNOSING),
                _experience('e-3', SkillExperienceStatus.LEARNING),
                _experience('e-4', SkillExperienceStatus.LEARNING),
                _experience('e-5', SkillExperienceStatus.DIAGNOSING),
                _experience(
                    'e-6',
                    SkillExperienceStatus.COMPLETED,
                    completed_at=_at(11, 17),
                ),
                _experience(
                    'e-7',
                    SkillExperienceStatus.DIAGNOSING,
                    started_at=_at(11, 16),
                ),
            ),
            latest={
                'e-1': _at(11, 10),
                'e-2': _at(11, 12),
                'e-3': _at(11, 9),
                'e-4': _at(11, 11),
                'e-5': _at(11, 8),
                'e-6': _at(11, 17),
            },
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert [item.skill_experience_id for item in result.resume_items] == [
            'e-2',
            'e-4',
            'e-1',
        ]
        assert [item.last_submitted_at for item in result.resume_items] == [
            _at(11, 12),
            _at(11, 11),
            _at(11, 10),
        ]

    @pytest.mark.parametrize(('candidates', 'listed'), [(0, 0), (1, 1), (3, 3), (4, 3)])
    def test_should_list_at_most_three_continue_items(
        self, candidates: int, listed: int
    ) -> None:
        self._register_skills()
        experiences = tuple(
            _experience(f'e-{n}', SkillExperienceStatus.LEARNING)
            for n in range(1, candidates + 1)
        )
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=experiences,
            latest={f'e-{n}': _at(11, n) for n in range(1, candidates + 1)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert len(result.resume_items) == listed

    def test_should_complete_the_continue_list_with_attempt_less_experiences_newest_start_first(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(
                _experience('e-1', SkillExperienceStatus.LEARNING),
                _experience(
                    'e-2', SkillExperienceStatus.DIAGNOSING, started_at=_at(10, 1)
                ),
                _experience(
                    'e-3', SkillExperienceStatus.DIAGNOSING, started_at=_at(11, 1)
                ),
                _experience(
                    'e-4', SkillExperienceStatus.DIAGNOSING, started_at=_at(10, 20)
                ),
            ),
            latest={'e-1': _at(11, 5)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert [item.skill_experience_id for item in result.resume_items] == [
            'e-1',
            'e-3',
            'e-4',
        ]
        assert [item.last_submitted_at for item in result.resume_items] == [
            _at(11, 5),
            None,
            None,
        ]

    def test_should_describe_each_continue_item_with_its_context_and_no_activity(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID, CODING_GOAL_ID),
            experiences=(
                _experience('e-1', SkillExperienceStatus.DIAGNOSING),
                _experience(
                    'e-2',
                    SkillExperienceStatus.LEARNING,
                    goal_id=CODING_GOAL_ID,
                    skill_id=LOGIC_SKILL_ID,
                ),
            ),
            latest={'e-1': _at(11, 12, 8), 'e-2': _at(11, 11, 9)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.resume_items == (
            ResumeItem(
                skill_experience_id='e-1',
                goal_id=DATA_GOAL_ID,
                goal_title='Carreira em dados',
                skill_id=PYTHON_SKILL_ID,
                skill_name='Python para análise de dados',
                status=SkillExperienceStatus.DIAGNOSING,
                focus_competency_name=None,
                last_submitted_at=_at(11, 12, 8),
            ),
            ResumeItem(
                skill_experience_id='e-2',
                goal_id=CODING_GOAL_ID,
                goal_title='Aprender a programar',
                skill_id=LOGIC_SKILL_ID,
                skill_name='Lógica de programação',
                status=SkillExperienceStatus.LEARNING,
                focus_competency_name='Variáveis',
                last_submitted_at=_at(11, 11, 9),
            ),
        )
        assert {field.name for field in fields(ResumeItem)} == {
            'skill_experience_id',
            'goal_id',
            'goal_title',
            'skill_id',
            'skill_name',
            'status',
            'focus_competency_name',
            'last_submitted_at',
        }

    def test_should_focus_the_second_competency_when_the_first_is_mastered_and_stable(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('e-1', SkillExperienceStatus.LEARNING),),
            progresses=(
                _mastered('e-1', 'competency-1', _at(11, 1)),
                _progress('e-1', 'competency-2'),
            ),
            latest={'e-1': _at(11, 2)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert [item.focus_competency_name for item in result.resume_items] == [
            'Agregações'
        ]

    def test_should_focus_a_mastered_competency_that_has_an_open_verification(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('e-1', SkillExperienceStatus.LEARNING),),
            progresses=(
                _mastered(
                    'e-1', 'competency-1', _at(11, 1), verification_cause='evidence'
                ),
                _mastered('e-1', 'competency-2', _at(11, 1)),
            ),
            latest={'e-1': _at(11, 2)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert [item.focus_competency_name for item in result.resume_items] == [
            'Limpeza de tabelas'
        ]

    def test_should_have_no_focus_when_every_competency_is_mastered_and_stable(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('e-1', SkillExperienceStatus.LEARNING),),
            progresses=(
                _mastered('e-1', 'competency-1', _at(11, 1)),
                _mastered('e-1', 'competency-2', _at(11, 1)),
            ),
            latest={'e-1': _at(11, 2)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert [item.focus_competency_name for item in result.resume_items] == [None]

    def test_should_offer_every_started_experience_and_select_the_newest_submission(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID, CODING_GOAL_ID),
            experiences=(
                _experience('e-1', SkillExperienceStatus.NOT_STARTED),
                _experience('e-2', SkillExperienceStatus.DIAGNOSING),
                _experience(
                    'e-3',
                    SkillExperienceStatus.COMPLETED,
                    goal_id=CODING_GOAL_ID,
                    skill_id=LOGIC_SKILL_ID,
                    completed_at=_at(11, 15),
                ),
                _experience('e-4', SkillExperienceStatus.LEARNING),
            ),
            latest={'e-2': _at(11, 10), 'e-3': _at(11, 15), 'e-4': _at(11, 12)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.evolution_options == (
            EvolutionOption(
                skill_experience_id='e-3',
                goal_title='Aprender a programar',
                skill_name='Lógica de programação',
                status=SkillExperienceStatus.COMPLETED,
            ),
            EvolutionOption(
                skill_experience_id='e-4',
                goal_title='Carreira em dados',
                skill_name='Python para análise de dados',
                status=SkillExperienceStatus.LEARNING,
            ),
            EvolutionOption(
                skill_experience_id='e-2',
                goal_title='Carreira em dados',
                skill_name='Python para análise de dados',
                status=SkillExperienceStatus.DIAGNOSING,
            ),
        )
        assert result.default_evolution_skill_experience_id == 'e-3'

    def test_should_not_select_an_experience_when_none_has_a_submission(self) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('e-1', SkillExperienceStatus.DIAGNOSING),),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert [item.skill_experience_id for item in result.evolution_options] == [
            'e-1'
        ]
        assert result.default_evolution_skill_experience_id is None

    def test_should_list_the_completions_of_one_skill_in_two_objectives_newest_first_with_local_dates(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID, CODING_GOAL_ID),
            experiences=(
                _experience(
                    'e-1',
                    SkillExperienceStatus.COMPLETED,
                    skill_id=LOGIC_SKILL_ID,
                    completed_at=datetime(2026, 9, 13, 2, 0, tzinfo=UTC),
                    final_result=Decimal('91.00'),
                ),
                _experience(
                    'e-2',
                    SkillExperienceStatus.COMPLETED,
                    goal_id=CODING_GOAL_ID,
                    skill_id=LOGIC_SKILL_ID,
                    completed_at=datetime(2026, 10, 2, 15, 0, tzinfo=UTC),
                    final_result=Decimal('84.50'),
                ),
                _experience('e-3', SkillExperienceStatus.LEARNING),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=SAO_PAULO)

        assert result.completed_skills == (
            CompletedSkill(
                skill_experience_id='e-2',
                goal_id=CODING_GOAL_ID,
                goal_title='Aprender a programar',
                skill_id=LOGIC_SKILL_ID,
                skill_name='Lógica de programação',
                final_result=Decimal('84.50'),
                completed_on=date(2026, 10, 2),
            ),
            CompletedSkill(
                skill_experience_id='e-1',
                goal_id=DATA_GOAL_ID,
                goal_title='Carreira em dados',
                skill_id=LOGIC_SKILL_ID,
                skill_name='Lógica de programação',
                final_result=Decimal('91.00'),
                completed_on=date(2026, 9, 12),
            ),
        )

    def test_should_keep_an_experience_of_an_unknown_skill_in_counts_but_out_of_named_lists(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(
                _experience(
                    'e-1',
                    SkillExperienceStatus.COMPLETED,
                    skill_id='skill-gone',
                    completed_at=_at(11, 17),
                ),
                _experience(
                    'e-2', SkillExperienceStatus.LEARNING, skill_id='skill-gone'
                ),
                _experience('e-3', SkillExperienceStatus.LEARNING),
            ),
            progresses=(_mastered('e-2', 'competency-x', _at(11, 3)),),
            latest={'e-1': _at(11, 17), 'e-2': _at(11, 16), 'e-3': _at(11, 15)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.stage_distribution == StageDistribution(
            not_started=0, diagnosing=0, learning=2, completed=1, goal_count=1
        )
        assert result.completed_skill_count == 1
        assert result.mastered_competency_count == 1
        assert [item.skill_experience_id for item in result.resume_items] == ['e-3']
        assert [item.skill_experience_id for item in result.evolution_options] == [
            'e-3'
        ]
        assert result.default_evolution_skill_experience_id == 'e-3'
        assert result.completed_skills == ()
        assert result.recent_masteries == ()

    def test_should_ignore_experiences_whose_objective_is_no_longer_the_accounts(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(
                _experience('e-1', SkillExperienceStatus.LEARNING),
                _experience(
                    'e-2', SkillExperienceStatus.LEARNING, goal_id='goal-removed'
                ),
            ),
            latest={'e-1': _at(11, 2), 'e-2': _at(11, 3)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.stage_distribution.learning == 1
        assert result.stage_distribution.goal_count == 1
        assert [item.skill_experience_id for item in result.resume_items] == ['e-1']

    def test_should_read_only_what_the_repositories_return_after_an_experience_removal(
        self,
    ) -> None:
        self._register_skills()
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('e-kept', SkillExperienceStatus.LEARNING),),
            progresses=(_progress('e-kept', 'competency-1'),),
            latest={'e-kept': _at(11, 2)},
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=None)

        assert result.stage_distribution == StageDistribution(
            not_started=0, diagnosing=0, learning=1, completed=0, goal_count=1
        )
        assert result.completed_skill_count == 0
        assert result.mastered_competency_count == 0
        self.repositories.competency_progresses.find_many_by_skill_experience_ids.assert_called_once_with(
            ['e-kept']
        )
        self.repositories.activity_attempts.find_many_latest_submitted_at_by_skill_experience_ids.assert_called_once_with(
            ['e-kept']
        )

    def test_should_not_expose_an_average_or_result_of_objectives_or_of_the_user(
        self,
    ) -> None:
        assert {field.name for field in fields(LearningPanorama)} == {
            'has_goals',
            'completed_skill_count',
            'mastered_competency_count',
            'stage_distribution',
            'resume_items',
            'weekly_evaluated_activities',
            'evolution_options',
            'default_evolution_skill_experience_id',
            'completed_skills',
            'recent_masteries',
        }
        assert {field.name for field in fields(StageDistribution)} == {
            'not_started',
            'diagnosing',
            'learning',
            'completed',
            'goal_count',
        }

    def test_should_read_the_current_instant_from_the_injected_clock(self) -> None:
        self.clock.now.return_value = datetime(2026, 11, 22, 23, 30, tzinfo=UTC)
        self._store(
            goal_ids=(DATA_GOAL_ID,),
            experiences=(_experience('e-1', SkillExperienceStatus.LEARNING),),
        )

        result = self.subject.execute(ACCOUNT_ID, time_zone=SAO_PAULO)

        # 2026-11-22 23:30 UTC is still Sunday 20:30 in Sao Paulo, so the current
        # week is the one that starts on Monday 2026-11-16.
        assert result.weekly_evaluated_activities[-1].week_start == date(2026, 11, 16)
        self.clock.now.assert_called_once_with()
