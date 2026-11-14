from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shifu.curriculum.core.domain.entities import Activity
    from shifu.curriculum.core.domain.structures import CurriculumSequence


def make_activity() -> tuple[Activity, CurriculumSequence]:
    from shifu.curriculum.core.domain.entities import Activity
    from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
    from shifu.curriculum.core.domain.structures import (
        ActivitySequenceItem,
        ChoiceOption,
        CodeConceptCriterion,
        CodeInconclusiveComment,
        CodeInconclusiveObservation,
        CodeLevelObservation,
        CodeRubricComment,
        CodeRubricCriterion,
        CodeRubricEvaluationPart,
        CorrectnessEvaluationPart,
        CurriculumSequence,
        EvaluationRule,
        HtmlCssJsDependency,
        HtmlCssJsInitialFile,
        HtmlCssJsPermittedCommand,
        HtmlCssJsQuestion,
        SingleChoiceQuestion,
    )
    from shifu.curriculum.database.logic_programming_seed import (
        LOGIC_DECISIONS_COMPETENCY_ID,
        build_logic_programming_seed,
    )

    seed = build_logic_programming_seed()
    competency = next(
        item for item in seed.competencies if item.id == LOGIC_DECISIONS_COMPETENCY_ID
    )
    concept = next(
        item for item in seed.concepts if item.competency_id == competency.id
    )
    activity_id = '01SHF000000000000000000993'
    question_key = 'html-todo-list'
    question = HtmlCssJsQuestion(
        key=question_key,
        prompt=(
            'Complete a lista de tarefas. Permita adicionar uma tarefa pelo '
            'formulário e marcar cada item como concluído.'
        ),
        initial_files=(
            HtmlCssJsInitialFile(
                path='index.html',
                editable=True,
                content=(
                    '<!doctype html>\n<html lang="pt-BR">\n<head>\n'
                    '  <meta charset="utf-8">\n  <meta name="viewport" '
                    'content="width=device-width, initial-scale=1">\n'
                    '  <title>Minha lista</title>\n  <link rel="stylesheet" '
                    'href="styles.css">\n</head>\n<body>\n  <main>\n'
                    '    <h1>Minha lista de tarefas</h1>\n'
                    '    <form id="task-form">\n'
                    '      <label for="task-input">Nova tarefa</label>\n'
                    '      <input id="task-input" name="task" required>\n'
                    '      <button type="submit">Adicionar</button>\n'
                    '    </form>\n    <ul id="task-list" aria-live="polite"></ul>\n'
                    '  </main>\n  <script src="script.js"></script>\n'
                    '</body>\n</html>\n'
                ),
            ),
            HtmlCssJsInitialFile(
                path='styles.css',
                editable=True,
                content=(
                    'body { font-family: system-ui, sans-serif; margin: 2rem; }\n'
                    'main { max-width: 40rem; margin: auto; }\n'
                    'form { display: flex; gap: .75rem; flex-wrap: wrap; }\n'
                    'input, button { min-height: 2.75rem; }\n'
                    'li { margin-block: .75rem; }\n'
                ),
            ),
            HtmlCssJsInitialFile(
                path='script.js',
                editable=True,
                content=(
                    "const form = document.querySelector('#task-form')\n"
                    "const input = document.querySelector('#task-input')\n"
                    "const list = document.querySelector('#task-list')\n\n"
                    "form.addEventListener('submit', (event) => {\n"
                    '  event.preventDefault()\n'
                    '  // TODO: crie a tarefa e adicione-a à lista.\n'
                    '})\n'
                ),
            ),
            HtmlCssJsInitialFile(
                path='package.json',
                editable=False,
                content='{"scripts":{"dev":"vite --host 0.0.0.0"}}',
            ),
        ),
        entrypoint='index.html',
        fixed_dependencies=(HtmlCssJsDependency(name='vite', version='7.0.0'),),
        permitted_commands=(
            HtmlCssJsPermittedCommand(
                id='start-preview', executable='npm', arguments=('run', 'dev')
            ),
        ),
        concept_criteria=(
            CodeConceptCriterion(
                concept_id=concept.id,
                description='Manipula elementos da página em resposta a eventos.',
                level_observations=tuple(
                    CodeLevelObservation(
                        id=f'{activity_id}-dom-{level}',
                        level=level,
                        evidence=(
                            'A tarefa é adicionada e pode ser marcada como concluída.'
                            if level == 100
                            else f'A implementação demonstra nível {level} de interação com o DOM.'
                        ),
                        interpretation_limit='Considera somente a interação desta lista.',
                    )
                    for level in (0, 25, 50, 75, 100)
                ),
                inconclusive_observation=CodeInconclusiveObservation(
                    id=f'{activity_id}-dom-inconclusive',
                    text='Não foi possível observar a interação com segurança.',
                ),
            ),
        ),
    )
    rubric = CodeRubricCriterion(
        key='todo-list-behavior',
        name='Comportamento da lista',
        description='Adiciona tarefas e permite marcá-las como concluídas.',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(
                id=f'{activity_id}-comment-{level}',
                level=level,
                text=f'Comportamento da lista no nível {level}.',
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id=f'{activity_id}-inconclusive',
            text='Não foi possível avaliar a lista; tente novamente.',
        ),
    )
    activity = Activity(
        id=activity_id,
        competency_id=competency.id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.MEDIUM,
        title='Prática HTML: lista de tarefas',
        objective='Crie uma interação simples com HTML, CSS e JavaScript.',
        questions=(
            SingleChoiceQuestion(
                key='q1',
                prompt='Qual elemento agrupa uma lista não ordenada?',
                correct_explanation='ul representa uma lista não ordenada.',
                incorrect_explanation='O elemento ul representa a lista.',
                options=(
                    ChoiceOption(key='a', text='ul', is_correct=True),
                    ChoiceOption(key='b', text='div', is_correct=False),
                    ChoiceOption(key='c', text='span', is_correct=False),
                ),
            ),
            question,
            SingleChoiceQuestion(
                key='q2',
                prompt='Qual evento é emitido ao enviar um formulário?',
                correct_explanation='O formulário emite o evento submit.',
                incorrect_explanation='O evento do formulário é submit.',
                options=(
                    ChoiceOption(key='a', text='click', is_correct=False),
                    ChoiceOption(key='b', text='submit', is_correct=True),
                    ChoiceOption(key='c', text='change', is_correct=False),
                ),
            ),
        ),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(question_key='q1', weight_percentage=25),
                CodeRubricEvaluationPart(
                    question_key=question_key,
                    weight_percentage=50,
                    criteria=(rubric,),
                ),
                CorrectnessEvaluationPart(question_key='q2', weight_percentage=25),
            )
        ),
    )
    existing_sequence = next(
        item
        for item in seed.curriculum_sequences
        if item.competency_id == competency.id
    )
    next_position = (
        max((item.position for item in existing_sequence.items), default=0) + 1
    )
    sequence = CurriculumSequence(
        competency_id=existing_sequence.competency_id,
        items=(
            *existing_sequence.items,
            ActivitySequenceItem(position=next_position, activity_id=activity.id),
        ),
    )
    return activity, sequence
