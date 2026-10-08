"""Check the changed-code gate against a small real Git and coverage fixture."""

from pathlib import Path
import shutil
import subprocess

from coverage import Coverage
import pytest

from scripts import check_changed_coverage as checker


def _write(root: Path, name: str, contents: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)
    return path


def _git(root: Path, *arguments: str) -> None:
    git = shutil.which('git')
    assert git is not None
    subprocess.run(  # noqa: S603 - test-owned repository and fixed Git executable.
        [git, '-C', str(root), *arguments], check=True, capture_output=True
    )


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    _git(tmp_path, 'init', '-b', 'main')
    _git(tmp_path, 'config', 'user.email', 'test@example.invalid')
    _git(tmp_path, 'config', 'user.name', 'Test')
    _write(tmp_path, 'apps/server/src/shifu/sample.py', 'value = 1\n')
    _git(tmp_path, 'add', '.')
    _git(tmp_path, 'commit', '-m', 'baseline')
    return tmp_path / 'apps/server'


class TestChangedCoverage:
    def test_should_find_only_new_lines_in_changed_and_untracked_files(
        self, repository: Path
    ) -> None:
        _write(
            repository,
            'src/shifu/sample.py',
            'value = 2\nkeep = 1\n',
        )
        extra = _write(repository, 'src/shifu/extra.py', 'first = 1\nsecond = 2\n')
        _write(repository, 'tests/test_irrelevant.py', 'assert True\n')

        assert checker.changed_lines(repository, 'HEAD') == {
            repository / 'src/shifu/sample.py': {1, 2},
            extra: {1, 2},
        }

    def test_should_count_executable_lines_functions_and_branch_exits(
        self, repository: Path
    ) -> None:
        source = _write(
            repository,
            'src/shifu/sample.py',
            'def choose(value: bool) -> int:\n'
            '    if value:\n'
            '        return 1\n'
            '    return 0\n',
        )
        data = repository / '.coverage.fixture'
        cov = Coverage(data_file=str(data), branch=True, config_file=False)
        cov.start()
        namespace: dict[str, object] = {}
        exec(compile(source.read_text(), str(source), 'exec'), namespace)  # noqa: S102
        choose = namespace['choose']
        assert callable(choose)
        assert choose(value=True) == 1
        cov.stop()
        cov.save()

        changed = checker.changed_lines(repository, 'HEAD')
        metrics = checker.measure(changed, data)[source]

        assert metrics['statements'].covered < metrics['statements'].total
        assert metrics['lines'] == metrics['statements']
        assert metrics['functions'] == checker.Metric(1, 1)
        assert metrics['branches'] == checker.Metric(1, 2)

    def test_should_fail_unmeasured_executable_changes(self, repository: Path) -> None:
        source = _write(
            repository,
            'src/shifu/sample.py',
            'def skipped() -> int:\n    return 2\n',
        )
        data = repository / '.coverage.fixture'
        cov = Coverage(data_file=str(data), branch=True, config_file=False)
        cov.start()
        exec(compile('value = 1\n', str(repository / 'other.py'), 'exec'), {})  # noqa: S102
        cov.stop()
        cov.save()

        metrics = checker.measure(checker.changed_lines(repository, 'HEAD'), data)[
            source
        ]

        assert metrics['statements'].total > 0
        assert metrics['statements'].covered == 0
        assert metrics['functions'] == checker.Metric(0, 1)
        assert source.is_file()

    def test_should_count_a_new_branch_destination_when_origin_is_unchanged(
        self, repository: Path
    ) -> None:
        source = _write(
            repository,
            'src/shifu/sample.py',
            'def choose(value: bool) -> int | None:\n    if value:\n        return 1\n',
        )
        _git(repository, 'add', '.')
        _git(repository, 'commit', '-m', 'existing branch')
        source.write_text(source.read_text() + '    return 0\n')
        data = repository / '.coverage.fixture'
        cov = Coverage(data_file=str(data), branch=True, config_file=False)
        cov.start()
        namespace: dict[str, object] = {}
        exec(compile(source.read_text(), str(source), 'exec'), namespace)  # noqa: S102
        choose = namespace['choose']
        assert callable(choose)
        assert choose(value=True) == 1
        cov.stop()
        cov.save()

        changed = checker.changed_lines(repository, 'HEAD')
        assert changed == {source: {4}}
        assert checker.measure(changed, data)[source]['branches'] == checker.Metric(
            0, 1
        )

    def test_should_ignore_comment_only_changes_inside_a_function(
        self, repository: Path
    ) -> None:
        source = _write(
            repository,
            'src/shifu/sample.py',
            'def value() -> int:\n    # old\n    return 1\n',
        )
        _git(repository, 'add', '.')
        _git(repository, 'commit', '-m', 'function baseline')
        source.write_text(source.read_text().replace('# old', '# new'))
        data = repository / '.coverage.fixture'
        cov = Coverage(data_file=str(data), branch=True, config_file=False)
        cov.start()
        exec(compile(source.read_text(), str(source), 'exec'), {})  # noqa: S102
        cov.stop()
        cov.save()

        metrics = checker.measure(checker.changed_lines(repository, 'HEAD'), data)[
            source
        ]

        assert all(metric.total == 0 for metric in metrics.values())

    def test_should_require_branch_data(self, repository: Path) -> None:
        data = repository / '.coverage.fixture'
        cov = Coverage(data_file=str(data), config_file=False)
        cov.start()
        exec(compile('value = 1\n', str(repository / 'other.py'), 'exec'), {})  # noqa: S102
        cov.stop()
        cov.save()

        with pytest.raises(ValueError, match='--branch'):
            checker.measure({}, data)

    def test_should_fail_each_file_without_coverage(
        self,
        repository: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        source = _write(
            repository,
            'src/shifu/sample.py',
            'def skipped() -> int:\n    return 2\n',
        )
        data = repository / '.coverage.fixture'
        cov = Coverage(data_file=str(data), branch=True, config_file=False)
        cov.start()
        exec(compile('value = 1\n', str(repository / 'other.py'), 'exec'), {})  # noqa: S102
        cov.stop()
        cov.save()
        monkeypatch.setattr(checker, 'SERVER', repository)

        assert checker.main(['--base', 'HEAD', '--coverage-file', str(data)]) == 1
        assert str(source.relative_to(repository)) in capsys.readouterr().out

    def test_should_skip_empty_scope_without_coverage_file(
        self, repository: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(checker, 'SERVER', repository)

        assert checker.main(['--base', 'HEAD']) == 0

    def test_should_reject_test_path_outside_test_tree(self, repository: Path) -> None:
        with pytest.raises(ValueError, match='Expected an existing'):
            checker.run_tests(
                repository, ['src/shifu/sample.py'], repository / '.coverage'
            )

    def test_should_run_explicit_tests_with_branch_coverage(
        self, repository: Path
    ) -> None:
        source = _write(
            repository,
            'src/shifu/sample.py',
            'def choose(value: bool) -> int:\n'
            '    if value:\n'
            '        return 1\n'
            '    return 0\n',
        )
        _write(
            repository,
            'pyproject.toml',
            '[tool.coverage.run]\npatch = ["subprocess"]\nsigterm = true\n',
        )
        _write(
            repository,
            'tests/test_sample.py',
            'import subprocess\n'
            'import sys\n\n'
            'def test_choose() -> None:\n'
            '    process = subprocess.Popen(\n'
            '        [sys.executable, "-c", "import runpy; "\n'
            "         \"choose = runpy.run_path('src/shifu/sample.py')['choose']; \"\n"
            '         "assert choose(value=True) == 1; "\n'
            '         "print(\\"ready\\", flush=True); "\n'
            '         "import time; time.sleep(10)"],\n'
            '        stdout=subprocess.PIPE, text=True,\n'
            '    )\n'
            '    assert process.stdout is not None\n'
            '    assert process.stdout.readline() == "ready\\n"\n'
            '    process.terminate()\n'
            '    assert process.wait(timeout=5) != 0\n',
        )
        data = repository / '.coverage.fixture'

        checker.run_tests(repository, ['tests/test_sample.py'], data)

        assert checker.measure({source: {1, 2, 3, 4}}, data)[source]['branches'] == (
            checker.Metric(1, 2)
        )
