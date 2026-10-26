"""Integrated curricular content for HTTP and disposable browser journeys."""

from typing import ClassVar

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.structures import (
    ReactAdditionalFilePolicy,
    ReactDependency,
    ReactFastifyHttpExample,
    ReactFastifyQuestion,
    ReactInitialFile,
    ReactPermittedCommand,
)
from tests.fixtures.react_activity_fixture import ReactControllerFixture


class ReactFastifyActivityFixture:
    ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000093'
    SECOND_ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000094'
    FRONTEND_SOURCE: ClassVar[str] = """import React from 'react';
import { createRoot } from 'react-dom/client';
function App() {
  const [tasks, setTasks] = React.useState([]);
  const load = () => fetch('/api/tasks').then(r => r.json()).then(setTasks);
  React.useEffect(() => { load(); }, []);
  const complete = async id => {
    await fetch('/api/tasks/' + id, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({done: true})
    });
    load();
  };
  return <main><h1>Minhas tarefas</h1>{tasks.map(task =>
    <p key={task.id}>{task.title}: {task.done ? 'Concluída' : 'Pendente'}
    <button onClick={() => complete(task.id)}>Concluir tarefa</button></p>
  )}</main>;
}
createRoot(document.getElementById('root')).render(<App />);
"""
    API_SOURCE: ClassVar[str] = """import Fastify from 'fastify';
const app = Fastify();
const tasks = [{id: '1', title: 'Aprender React e Fastify', done: false}];
app.get('/api/tasks', async () => tasks);
app.patch('/api/tasks/:id', async (request, reply) => {
  const task = tasks.find(item => item.id === request.params.id);
  if (!task) return reply.code(404).send({error: 'Tarefa ausente'});
  task.done = request.body.done === true;
  return task;
});
await app.listen({host: '0.0.0.0', port: 3000});
"""
    FIXED_HTML: ClassVar[str] = '<div id="root"></div>'

    @staticmethod
    def activity(
        *,
        with_policy: bool = True,
        integrated_last: bool = True,
        activity_id: str | None = None,
    ) -> Activity:
        activity = ReactControllerFixture.activity(with_policy=with_policy)
        activity.title = 'Projeto integrado React e Fastify'
        activity.objective = 'Consultar e concluir tarefas fictícias'
        integrated = ReactFastifyQuestion(
            key='q3',
            prompt='Consulte as tarefas pela API e permita concluí-las.',
            initial_files=(
                ReactInitialFile(
                    path='src/App.jsx',
                    content=ReactFastifyActivityFixture.FRONTEND_SOURCE,
                    editable=True,
                ),
                ReactInitialFile(
                    path='api.js',
                    content=ReactFastifyActivityFixture.API_SOURCE,
                    editable=True,
                ),
                ReactInitialFile(
                    path='index.html',
                    content=ReactFastifyActivityFixture.FIXED_HTML,
                    editable=False,
                ),
            ),
            frontend_entrypoint='src/App.jsx',
            api_entrypoint='api.js',
            fixed_dependencies=(
                ReactDependency(name='react', version='19.2.0'),
                ReactDependency(name='react-dom', version='19.2.0'),
                ReactDependency(name='vite', version='6.3.5'),
                ReactDependency(name='fastify', version='5.6.2'),
            ),
            permitted_commands=(
                ReactPermittedCommand(
                    id='web', executable='npm', arguments=('run', 'dev:web')
                ),
                ReactPermittedCommand(
                    id='api', executable='npm', arguments=('run', 'dev:api')
                ),
            ),
            frontend_command_id='web',
            api_command_id='api',
            http_examples=(
                ReactFastifyHttpExample(
                    key='list', title='Listar tarefas', method='GET', path='/api/tasks'
                ),
                ReactFastifyHttpExample(
                    key='complete',
                    title='Concluir tarefa',
                    method='PATCH',
                    path='/api/tasks/1',
                    body='{"done":true}',
                ),
            ),
            concept_criteria=(),
            additional_file_policy=(
                ReactAdditionalFilePolicy(
                    allowed_directories=('src/components', 'routes'),
                    allowed_extensions=('.jsx', '.js'),
                    max_files=2,
                )
                if with_policy
                else None
            ),
        )
        choices = activity.questions[:2]
        activity.questions = (
            (*choices, integrated)
            if integrated_last
            else (choices[0], integrated, choices[1])
        )
        return Activity.create(
            id=activity_id or ReactFastifyActivityFixture.ACTIVITY_ID,
            competency_id=activity.competency_id,
            activity_type=activity.activity_type,
            difficulty=activity.difficulty,
            title=activity.title,
            objective=activity.objective,
            questions=activity.questions,
            evaluation_rule=activity.evaluation_rule,
        )

    @staticmethod
    def activity_path() -> str:
        return ReactControllerFixture.activity_path().replace(
            ReactControllerFixture.ACTIVITY_ID, ReactFastifyActivityFixture.ACTIVITY_ID
        )

    @staticmethod
    def answer_files(*, with_additional: bool = True) -> list[dict[str, str]]:
        files = [
            {
                'path': 'src/App.jsx',
                'content': ReactFastifyActivityFixture.FRONTEND_SOURCE,
            },
            {'path': 'api.js', 'content': ReactFastifyActivityFixture.API_SOURCE},
        ]
        if with_additional:
            files.append(
                {'path': 'routes/example.js', 'content': 'export const value = 1;'}
            )
        return files

    @staticmethod
    def submission(revision: str, *, with_additional: bool = True) -> dict[str, object]:
        body = ReactControllerFixture.submission(revision)
        body['answers'] = [
            {
                'kind': 'single_choice',
                'question_key': key,
                'selected_option_keys': ['a'],
            }
            for key in ('q1', 'q2')
        ] + [
            {
                'kind': 'react_fastify',
                'question_key': 'q3',
                'files': ReactFastifyActivityFixture.answer_files(
                    with_additional=with_additional
                ),
            }
        ]
        return body
