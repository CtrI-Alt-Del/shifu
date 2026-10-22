from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shifu.curriculum.core.domain.entities import Activity
    from shifu.curriculum.core.domain.structures import CurriculumSequence


def _make_activity() -> tuple[Activity, CurriculumSequence]:
    from shifu.curriculum.core.domain.entities import Activity
    from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
    from shifu.curriculum.core.domain.structures import (
        ActivitySequenceItem,
        ChoiceOption,
        CodeConceptCriterion,
        CodeInconclusiveComment,
        CodeInconclusiveObservation,
        CodeLevelObservation,
        CodeRubricCriterion,
        CodeRubricEvaluationPart,
        CodeRubricComment,
        CorrectnessEvaluationPart,
        CurriculumSequence,
        EvaluationRule,
        ReactAdditionalFilePolicy,
        ReactDependency,
        ReactInitialFile,
        ReactPermittedCommand,
        ReactQuestion,
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
    activity_id = '01SHF000000000000000000992'
    question_key = 'react-counter'
    concept_criterion = CodeConceptCriterion(
        concept_id=concept.id,
        description='Atualiza o estado do componente e apresenta o valor atualizado.',
        level_observations=tuple(
            CodeLevelObservation(
                id=f'{activity_id}-state-{level}',
                level=level,
                evidence=(
                    'O botão atualiza o estado e a interface apresenta o novo valor.'
                    if level == 100
                    else f'A implementação demonstra nível {level} do uso observável de estado.'
                ),
                interpretation_limit='Avalia apenas o comportamento observável deste componente.',
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_observation=CodeInconclusiveObservation(
            id=f'{activity_id}-state-inconclusive',
            text='Não foi possível observar com segurança a atualização de estado.',
        ),
    )
    react_question = ReactQuestion(
        key=question_key,
        prompt=(
            'Implemente um contador. Ao clicar em “Adicionar”, o número deve '
            'aumentar em 1; “Reiniciar” deve voltar o número a zero. Use estado '
            'do React e mantenha os dois botões acessíveis por teclado.'
        ),
        initial_files=(
            ReactInitialFile(
                path='src/main.jsx',
                editable=True,
                content=(
                    "import React from 'react'\n"
                    "import { createRoot } from 'react-dom/client'\n"
                    "import App from './App.jsx'\n"
                    "import './style.css'\n\n"
                    "createRoot(document.getElementById('root')).render(<App />)\n"
                ),
            ),
            ReactInitialFile(
                path='src/App.jsx',
                editable=True,
                content=(
                    "import React, { useState } from 'react'\n\n"
                    'export default function App() {\n'
                    '  return (\n'
                    '    <main className="counter">\n'
                    '      <h1>Contador</h1>\n'
                    '      <p aria-live="polite">0</p>\n'
                    '      <button type="button">Adicionar</button>\n'
                    '      <button type="button">Reiniciar</button>\n'
                    '    </main>\n'
                    '  )\n'
                    '}\n'
                ),
            ),
            ReactInitialFile(
                path='src/style.css',
                editable=True,
                content=(
                    'body { font-family: system-ui, sans-serif; margin: 2rem; }\n'
                    '.counter { display: grid; gap: 1rem; max-width: 24rem; }\n'
                    'button { min-height: 2.75rem; }\n'
                ),
            ),
        ),
        entrypoint='src/main.jsx',
        fixed_dependencies=(
            ReactDependency(name='react', version='18.3.1'),
            ReactDependency(name='react-dom', version='18.3.1'),
            ReactDependency(name='vite', version='6.3.5'),
        ),
        permitted_commands=(
            ReactPermittedCommand(
                id='start-preview', executable='npm', arguments=('run', 'dev')
            ),
        ),
        concept_criteria=(concept_criterion,),
        additional_file_policy=ReactAdditionalFilePolicy(
            allowed_directories=('src/components',),
            allowed_extensions=('.js', '.jsx', '.css'),
            max_files=4,
        ),
    )
    rubric = CodeRubricCriterion(
        key='react-counter-behavior',
        name='Comportamento do contador',
        description='Os botões atualizam e reiniciam o estado exibido.',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(
                id=f'{activity_id}-counter-comment-{level}',
                level=level,
                text={
                    0: 'O contador não apresenta o comportamento solicitado.',
                    25: 'A interface começou a ser implementada, mas os controles não funcionam.',
                    50: 'Um dos controles funciona; revise a outra ação.',
                    75: 'As ações estão quase corretas; confira reinício e acessibilidade.',
                    100: 'Adicionar e reiniciar atualizam corretamente o estado do contador.',
                }[level],
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id=f'{activity_id}-counter-inconclusive',
            text='Não foi possível avaliar o contador; tente enviar novamente.',
        ),
    )
    questions = (
        SingleChoiceQuestion(
            key='q1',
            prompt='Qual valor é exibido depois de let total = 2; total = total + 3?',
            correct_explanation='A atribuição soma 3 ao valor inicial 2.',
            incorrect_explanation='Após a atribuição, total passa a valer 5.',
            options=(
                ChoiceOption(key='a', text='2', is_correct=False),
                ChoiceOption(key='b', text='5', is_correct=True),
                ChoiceOption(key='c', text='6', is_correct=False),
            ),
        ),
        SingleChoiceQuestion(
            key='q2',
            prompt='Qual hook React mantém um valor entre renderizações?',
            correct_explanation='useState mantém o estado entre renderizações.',
            incorrect_explanation='O hook para esse estado é useState.',
            options=(
                ChoiceOption(key='a', text='useState', is_correct=True),
                ChoiceOption(key='b', text='useMemo', is_correct=False),
                ChoiceOption(key='c', text='createRoot', is_correct=False),
            ),
        ),
        react_question,
    )
    activity = Activity(
        id=activity_id,
        competency_id=competency.id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.MEDIUM,
        title='Prática React: estado e contador',
        objective='Revise conceitos e implemente uma pequena interação React.',
        questions=questions,
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(question_key='q1', weight_percentage=25),
                CorrectnessEvaluationPart(question_key='q2', weight_percentage=25),
                CodeRubricEvaluationPart(
                    question_key=question_key,
                    weight_percentage=50,
                    criteria=(rubric,),
                ),
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
