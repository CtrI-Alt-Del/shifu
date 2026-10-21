from enum import StrEnum


class MentorIntent(StrEnum):
    EXPLAIN_CONCEPT = 'explain_concept'
    REQUEST_HINT = 'request_hint'
    CONSULT_PROGRESS = 'consult_progress'
    FIND_MATERIALS_ACTIVITIES = 'find_materials_activities'
    EXPLAIN_ASSESSMENT = 'explain_assessment'
    SEARCH_CURRICULUM = 'search_curriculum'
    CONSULT_GAMIFICATION = 'consult_gamification'
    LEARNING_CONVERSATION = 'learning_conversation'
