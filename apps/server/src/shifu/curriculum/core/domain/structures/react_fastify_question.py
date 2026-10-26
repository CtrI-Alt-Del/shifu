import re
from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures.structure import structure
from shifu.curriculum.core.domain.structures.react_question import (
    ReactQuestion,
    ReactInitialFile,
    ReactDependency,
    ReactPermittedCommand,
    ReactAdditionalFilePolicy,
)
from shifu.curriculum.core.domain.structures.code_concept_criterion import (
    CodeConceptCriterion,
)
from shifu.curriculum.core.domain.structures.react_fastify_http_example import (
    ReactFastifyHttpExample,
)


@structure
class ReactFastifyQuestion:
    key: str
    prompt: str
    initial_files: tuple[ReactInitialFile, ...]
    frontend_entrypoint: str
    api_entrypoint: str
    fixed_dependencies: tuple[ReactDependency, ...]
    permitted_commands: tuple[ReactPermittedCommand, ...]
    frontend_command_id: str
    api_command_id: str
    http_examples: tuple[ReactFastifyHttpExample, ...]
    concept_criteria: tuple[CodeConceptCriterion, ...]
    additional_file_policy: ReactAdditionalFilePolicy | None
    kind: Literal['react_fastify'] = 'react_fastify'

    def __post_init__(self) -> None:
        # Both programs obey the existing curricular source/path invariants.
        for entrypoint in (self.frontend_entrypoint, self.api_entrypoint):
            ReactQuestion(
                key=self.key,
                prompt=self.prompt,
                initial_files=self.initial_files,
                entrypoint=entrypoint,
                fixed_dependencies=self.fixed_dependencies,
                permitted_commands=self.permitted_commands,
                concept_criteria=self.concept_criteria,
                additional_file_policy=self.additional_file_policy,
            )
        commands = {item.id: item for item in self.permitted_commands}
        dependencies = {item.name: item.version for item in self.fixed_dependencies}
        if (
            self.kind != 'react_fastify'
            or self.frontend_entrypoint == self.api_entrypoint
            or self.frontend_command_id == self.api_command_id
            or not {'react', 'react-dom', 'vite', 'fastify'}.issubset(dependencies)
            or any(
                re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?', version)
                is None
                for version in dependencies.values()
            )
            or len(self.http_examples) != len({item.key for item in self.http_examples})
            or len(self.http_examples)
            != len({item.title for item in self.http_examples})
        ):
            raise InvalidActivityError
        for command_id, script in (
            (self.frontend_command_id, 'dev:web'),
            (self.api_command_id, 'dev:api'),
        ):
            command = commands.get(command_id)
            if (
                command is None
                or command.executable != 'npm'
                or command.arguments != ('run', script)
            ):
                raise InvalidActivityError
