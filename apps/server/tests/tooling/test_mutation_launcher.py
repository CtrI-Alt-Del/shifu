"""Behavioral checks for scope selection without loading application fixtures."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

import pytest

from scripts import test_mutation as launcher


class TestMutationLauncher:
    def write(self, root: Path, name: str, contents: str = 'value = 1\n') -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        return path

    def test_should_follow_transitive_imports_and_package_barrels(
        self, tmp_path: Path
    ) -> None:
        target = self.write(tmp_path, 'src/shifu/math.py')
        consumer = self.write(
            tmp_path, 'src/shifu/consumer.py', 'from shifu.math import value\n'
        )
        self.write(tmp_path, 'src/shifu/__init__.py', 'from .consumer import value\n')
        related = self.write(
            tmp_path, 'tests/test_consumer.py', 'from shifu import value\n'
        )
        self.write(tmp_path, 'tests/test_other.py', 'import unrelated\n')
        targets, tests = launcher.select(tmp_path, {target}, full=False)

        assert targets == [target]
        assert tests == [related]
        assert consumer in launcher.dependencies(
            related, launcher.import_graph(tmp_path)
        )

    def test_should_map_changed_tests_to_runtime_dependencies(
        self, tmp_path: Path
    ) -> None:
        target = self.write(tmp_path, 'src/shifu/math.py')
        changed = self.write(
            tmp_path, 'tests/test_math.py', 'from shifu.math import value\n'
        )

        assert launcher.select(tmp_path, {changed}, full=False) == ([target], [changed])

    def test_should_keep_an_empty_scope_empty(self, tmp_path: Path) -> None:
        self.write(tmp_path, 'src/shifu/math.py')
        self.write(tmp_path, 'tests/test_math.py', 'from shifu.math import value\n')

        assert launcher.select(tmp_path, set(), full=False) == ([], [])

    def test_should_select_all_runtime_source_only_when_explicit(
        self, tmp_path: Path
    ) -> None:
        target = self.write(tmp_path, 'src/shifu/math.py')
        for name in (
            'src/shifu/__init__.py',
            'src/shifu/fakers/fake.py',
            'src/shifu/providers/generated/code.py',
        ):
            self.write(tmp_path, name)
        test = self.write(tmp_path, 'tests/test_math.py')

        assert launcher.select(tmp_path, set(), full=True) == ([target], [test])

    @pytest.mark.parametrize(
        'name', ['../escape.py', 'src/*.py', 'tests/test_missing.py']
    )
    def test_should_reject_invalid_paths(self, tmp_path: Path, name: str) -> None:
        with pytest.raises(ValueError, match=r'Expected|exact paths'):
            launcher.checked_paths([name], tmp_path, 'src')

    def test_should_reject_symlink_escape(self, tmp_path: Path) -> None:
        outside = self.write(tmp_path, 'outside.py')
        (tmp_path / 'src').mkdir()
        (tmp_path / 'src/link.py').symlink_to(outside)
        with pytest.raises(ValueError, match='Expected'):
            launcher.checked_paths(['src/link.py'], tmp_path, 'src')

    def test_should_include_staged_unstaged_untracked_and_branch_changes(
        self, tmp_path: Path
    ) -> None:
        git = shutil.which('git')

        assert git is not None

        def command(*arguments: str) -> None:
            subprocess.run(  # noqa: S603 - literal test Git commands.
                [git, '-C', str(tmp_path), *arguments], check=True, capture_output=True
            )

        command('init', '-b', 'main')
        command('config', 'user.email', 'test@example.invalid')
        command('config', 'user.name', 'Test')
        branch = self.write(tmp_path, 'branch.py')
        unstaged = self.write(tmp_path, 'unstaged.py')
        staged = self.write(tmp_path, 'staged.py')
        command('add', '.')
        command('commit', '-m', 'baseline')
        command('tag', 'baseline')
        branch.write_text('value = 2\n')
        command('add', 'branch.py')
        command('commit', '-m', 'branch change')
        unstaged.write_text('value = 2\n')
        staged.write_text('value = 2\n')
        command('add', 'staged.py')
        untracked = self.write(tmp_path, 'untracked.py')

        assert launcher.git_paths(tmp_path, None) == {unstaged, staged, untracked}
        assert launcher.git_paths(tmp_path, 'baseline') == {
            branch,
            unstaged,
            staged,
            untracked,
        }
        command('branch', 'origin/main', 'baseline')
        command('switch', '-c', 'codex/scope')

        assert launcher.git_paths(tmp_path, None) == {
            branch,
            unstaged,
            staged,
            untracked,
        }
        with pytest.raises(subprocess.CalledProcessError):
            launcher.git_paths(tmp_path, '--invalid-ref')

    def test_should_reject_glob_metacharacters_in_git_source_names(
        self, tmp_path: Path
    ) -> None:
        target = self.write(tmp_path, 'src/shifu/[math].py')
        with pytest.raises(ValueError, match='regular exact path'):
            launcher.select(tmp_path, {target}, full=False)

    def test_should_reject_unknown_options(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, 'argv', ['test_mutation.py', '--unsupported'])
        with pytest.raises(SystemExit) as error:
            launcher.main()

        assert error.value.code == 2

    def test_should_reject_non_test_files_as_test_selectors(
        self, tmp_path: Path
    ) -> None:
        self.write(tmp_path, 'tests/conftest.py')
        with pytest.raises(ValueError, match=r'Expected a test_'):
            launcher.checked_paths(['tests/conftest.py'], tmp_path, 'tests')

    def test_should_require_explicit_scope_for_changed_fixtures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        configuration = self.write(tmp_path, 'pyproject.toml')
        monkeypatch.setattr(launcher, 'SERVER', tmp_path)

        def changed_paths(root: Path, base: str | None) -> set[Path]:
            return {configuration}

        monkeypatch.setattr(launcher, 'git_paths', changed_paths)
        monkeypatch.setattr(sys, 'argv', ['test_mutation.py', '--dry-run'])
        with pytest.raises(SystemExit) as error:
            launcher.main()

        assert error.value.code == 2

    def test_should_allow_all_on_shallow_ci_without_git_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.write(tmp_path, 'src/shifu/math.py')
        self.write(tmp_path, 'tests/test_math.py')
        monkeypatch.setattr(launcher, 'SERVER', tmp_path)
        monkeypatch.setattr(sys, 'argv', ['test_mutation.py', '--all', '--dry-run'])

        assert launcher.main() == 0

    def test_should_select_all_core_including_shared_without_excluded_source(
        self, tmp_path: Path
    ) -> None:
        target = self.write(
            tmp_path, 'src/shifu/identity/core/use_cases/account_use_case.py'
        )
        shared = self.write(tmp_path, 'src/shifu/shared/core/use_cases/id_use_case.py')
        for name in (
            'src/shifu/identity/providers/password.py',
            'src/shifu/identity/core/__init__.py',
            'src/shifu/identity/core/fakers/account.py',
            'src/shifu/identity/core/generated/account.py',
            'src/shifu/core/unowned.py',
            'src/shifu/identity/core/domain/account.py',
        ):
            self.write(tmp_path, name)
        test = self.write(
            tmp_path, 'tests/identity/core/use_cases/test_account_use_case.py'
        )
        legacy = self.write(tmp_path, 'tests/core/use_cases/test_id_use_case.py')
        for name in (
            'tests/identity/server/controllers/test_account.py',
            'tests/messaging/inngest/jobs/test_account.py',
            'tests/tooling/test_account.py',
            'tests/identity/core/domain/test_account.py',
        ):
            self.write(tmp_path, name)

        assert launcher.select(tmp_path, set(), full=True, core=True) == (
            [target, shared],
            [legacy, test],
        )

    def test_should_select_only_changed_core_and_related_tests(
        self, tmp_path: Path
    ) -> None:
        target = self.write(
            tmp_path, 'src/shifu/identity/core/use_cases/account_use_case.py'
        )
        provider = self.write(tmp_path, 'src/shifu/identity/providers/password.py')
        self.write(tmp_path, 'src/shifu/shared/core/use_cases/id_use_case.py')
        related = self.write(
            tmp_path,
            'tests/identity/core/use_cases/test_account_use_case.py',
            'from shifu.identity.core.use_cases.account_use_case import value\n',
        )
        self.write(
            tmp_path,
            'tests/test_password.py',
            'from shifu.identity.providers.password import value\n',
        )
        self.write(
            tmp_path,
            'tests/identity/server/controllers/test_account.py',
            'from shifu.identity.core.use_cases.account_use_case import value\n',
        )

        assert launcher.select(tmp_path, {target, provider}, full=False, core=True) == (
            [target],
            [related],
        )

    def test_should_keep_changes_outside_core_empty(self, tmp_path: Path) -> None:
        self.write(tmp_path, 'src/shifu/identity/core/use_cases/account_use_case.py')
        provider = self.write(tmp_path, 'src/shifu/identity/providers/password.py')
        self.write(tmp_path, 'tests/test_account.py')

        assert launcher.select(tmp_path, {provider}, full=False, core=True) == (
            [],
            [],
        )

    def test_should_reject_explicit_source_outside_core(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.write(tmp_path, 'src/shifu/identity/providers/password.py')
        monkeypatch.setattr(launcher, 'SERVER', tmp_path)
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'test_mutation.py',
                '--core',
                '--files',
                'src/shifu/identity/providers/password.py',
                '--dry-run',
            ],
        )

        with pytest.raises(SystemExit) as error:
            launcher.main()

        assert error.value.code == 2

    @pytest.mark.parametrize(
        'test_path',
        [
            'tests/identity/server/controllers/test_account.py',
            'tests/identity/core/domain/test_account.py',
        ],
    )
    def test_should_reject_explicit_tests_outside_core_use_cases(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, test_path: str
    ) -> None:
        self.write(tmp_path, 'src/shifu/identity/core/use_cases/account_use_case.py')
        self.write(tmp_path, test_path)
        monkeypatch.setattr(launcher, 'SERVER', tmp_path)
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'test_mutation.py',
                '--core',
                '--files',
                'src/shifu/identity/core/use_cases/account_use_case.py',
                '--tests',
                test_path,
                '--dry-run',
            ],
        )

        with pytest.raises(SystemExit) as error:
            launcher.main()

        assert error.value.code == 2

    @pytest.mark.parametrize(
        'runner_code,export_code,expected_code', [(0, 0, 0), (0, 2, 2), (3, 2, 3)]
    )
    def test_should_run_core_without_application_fixtures_or_containers(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        runner_code: int,
        export_code: int,
        expected_code: int,
    ) -> None:
        target = self.write(
            tmp_path, 'src/shifu/identity/core/use_cases/account_use_case.py'
        )
        test = self.write(
            tmp_path, 'tests/identity/core/use_cases/test_account_use_case.py'
        )
        fixture = self.write(tmp_path, 'tests/conftest.py', 'raise RuntimeError()\n')
        self.write(tmp_path, 'pyproject.toml', '[project]\nname = "mutation-test"\n')
        self.write(tmp_path, 'alembic.ini', '')
        monkeypatch.setenv('SHIFU_RUN_REAL_INNGEST_TESTS', '1')
        monkeypatch.setenv('PYTEST_PLUGINS', 'tests.fixtures.inngest_fixture')
        monkeypatch.setitem(sys.modules, 'testcontainers.community.redis', None)
        commands: list[list[str]] = []

        def command(
            arguments: list[str],
            *,
            cwd: Path,
            env: dict[str, str],
            capture_output: bool = False,
            text: bool = False,
        ) -> subprocess.CompletedProcess[str]:
            commands.append(arguments)
            assert not (cwd / 'tests/conftest.py').exists()
            assert (cwd / test.relative_to(tmp_path)).exists()
            assert 'SHIFU_RUN_REAL_INNGEST_TESTS' not in env
            assert 'PYTEST_PLUGINS' not in env
            configuration = tomllib.loads((cwd / 'pyproject.toml').read_text())
            mutation = configuration['tool']['mutmut']
            assert mutation['only_mutate'] == [str(target.relative_to(tmp_path))]
            assert mutation['pytest_add_cli_args_test_selection'] == [
                str(test.relative_to(tmp_path))
            ]
            code = runner_code if arguments[3] == 'run' else export_code
            return subprocess.CompletedProcess(arguments, code, stdout='', stderr='')

        monkeypatch.setattr(launcher.subprocess, 'run', command)

        assert launcher.run(tmp_path, [target], [test], core=True) == expected_code
        summary = json.loads(
            (launcher.report_directory(tmp_path) / 'module-results.json').read_text()
        )
        assert summary['results_exit_code'] == export_code
        assert summary['status'] == ('complete' if export_code == 0 else 'failed')
        assert commands[1][3:] == ['results', '--all', 'true']
        assert [arguments[3] for arguments in commands] == [
            'run',
            'results',
            'export-cicd-stats',
        ]
        assert fixture.exists()

    def test_should_partition_all_targets_stably(self, tmp_path: Path) -> None:
        targets = [
            self.write(
                tmp_path,
                f'src/shifu/identity/core/use_cases/case_{i}.py',
                'value = 1\n' * size,
            )
            for i, size in enumerate([16, 8, 7, 6, 5, 4, 3, 2, 1])
        ]
        shards = [
            launcher.shard_targets(tmp_path, targets, (i, 4)) for i in range(1, 5)
        ]
        assert set().union(*map(set, shards)) == set(targets)
        assert sum(map(len, shards)) == len(targets)
        assert shards == [
            launcher.shard_targets(tmp_path, list(reversed(targets)), (i, 4))
            for i in range(1, 5)
        ]
        assert shards[0] == [targets[0]]
        assert all(shards)

    @pytest.mark.parametrize(
        'value', ['0/4', '5/4', '1/0', '-1/4', '1', 'a/4', '1/4/5']
    )
    def test_should_reject_invalid_shard_ranges(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setattr(
            sys, 'argv', ['test_mutation.py', '--all', '--core', '--shard', value]
        )
        with pytest.raises(SystemExit) as error:
            launcher.main()
        assert error.value.code == 2

    @pytest.mark.parametrize(
        'scope',
        [
            [],
            ['--all'],
            ['--core'],
            ['--all', '--core', '--tests', 'tests/test_case.py'],
        ],
    )
    def test_should_restrict_sharding_to_full_core_suite(
        self, monkeypatch: pytest.MonkeyPatch, scope: list[str]
    ) -> None:
        monkeypatch.setattr(sys, 'argv', ['test_mutation.py', *scope, '--shard', '1/4'])
        with pytest.raises(SystemExit) as error:
            launcher.main()
        assert error.value.code == 2

    def test_should_keep_all_unit_tests_and_isolate_reports(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        targets = [
            self.write(tmp_path, f'src/shifu/identity/core/use_cases/case_{i}.py')
            for i in range(4)
        ]
        tests = [
            self.write(tmp_path, f'tests/identity/core/use_cases/test_case_{i}.py')
            for i in range(4)
        ]
        monkeypatch.setattr(launcher, 'SERVER', tmp_path)
        calls: list[tuple[list[Path], list[Path], Path]] = []

        def run(
            root: Path,
            selected: list[Path],
            selected_tests: list[Path],
            core: bool = False,
            shard: tuple[int, int] | None = None,
        ) -> int:
            assert core
            calls.append(
                (selected, selected_tests, launcher.report_directory(root, shard))
            )
            return 0

        monkeypatch.setattr(launcher, 'run', run)
        for i in range(1, 5):
            monkeypatch.setattr(
                sys,
                'argv',
                ['test_mutation.py', '--all', '--core', '--shard', f'{i}/4'],
            )
            assert launcher.main() == 0
        assert {path for selected, _, _ in calls for path in selected} == set(targets)
        assert all(selected_tests == sorted(tests) for _, selected_tests, _ in calls)
        assert len({report for _, _, report in calls}) == 4
        assert calls[0][2] == tmp_path / 'test-results/mutation/shard-1-of-4'
        assert launcher.report_directory(tmp_path) == tmp_path / 'test-results/mutation'

    def test_should_mark_empty_shard_not_applicable(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self.write(tmp_path, 'src/shifu/identity/core/use_cases/case.py')
        self.write(tmp_path, 'tests/identity/core/use_cases/test_case.py')
        monkeypatch.setattr(launcher, 'SERVER', tmp_path)
        monkeypatch.setattr(
            sys, 'argv', ['test_mutation.py', '--all', '--core', '--shard', '4/4']
        )
        assert launcher.main() == 0
        assert 'not applicable' in capsys.readouterr().out
        assert (
            'not-applicable'
            in (
                launcher.report_directory(tmp_path, (4, 4)) / 'selection.json'
            ).read_text()
        )

    def test_should_select_legacy_module_use_case_tests(self, tmp_path: Path) -> None:
        target = self.write(tmp_path, 'src/shifu/identity/core/use_cases/case.py')
        legacy = self.write(tmp_path, 'tests/core/identity/use_cases/test_case.py')
        self.write(tmp_path, 'tests/core/identity/domain/test_case.py')
        assert launcher.select(tmp_path, set(), full=True, core=True) == (
            [target],
            [legacy],
        )

    def test_should_label_selection_with_module_ownership(self, tmp_path: Path) -> None:
        target = self.write(tmp_path, 'src/shifu/identity/core/use_cases/case.py')
        modern = self.write(tmp_path, 'tests/identity/core/use_cases/test_case.py')
        legacy = self.write(tmp_path, 'tests/core/identity/use_cases/test_other.py')
        unknown = self.write(tmp_path, 'tests/test_unknown.py')
        grouped = launcher.selection_by_module(
            tmp_path, [target], [modern, legacy, unknown]
        )
        assert grouped['identity']['mutate'] == [
            'src/shifu/identity/core/use_cases/case.py'
        ]
        assert set(grouped['identity']['tests']) == {
            str(p.relative_to(tmp_path)) for p in [modern, legacy]
        }
        assert grouped['unattributed']['tests'] == ['tests/test_unknown.py']

    def test_should_count_all_module_outcomes_including_unknown_results(self) -> None:
        results = '\n'.join(
            [
                'shifu.identity.core.use_cases.case.x__mutmut_1: killed',
                'shifu.identity.core.use_cases.case.x__mutmut_2: survived',
                'shifu.learning.core.use_cases.case.x__mutmut_1: not checked',
                'external.case.x__mutmut_1: future status',
                'Saved CI/CD stats to mutants/mutmut-cicd-stats.json',
            ]
        )
        assert launcher.module_outcomes(results) == {
            'identity': {'total': 2, 'killed': 1, 'survived': 1},
            'learning': {'total': 1, 'not checked': 1},
            'unattributed': {'total': 1, 'future status': 1},
        }
