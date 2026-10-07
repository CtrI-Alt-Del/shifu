"""Behavioral checks for scope selection without loading application fixtures."""

from pathlib import Path
import shutil
import subprocess
import sys

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
