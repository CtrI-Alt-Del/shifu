from fastapi import Request

from shifu.learning.core.interfaces import LearningDatabase


class LearningPipe:
    @staticmethod
    def get_database(request: Request) -> LearningDatabase:
        return request.app.state.learning_database
