from pathlib import Path

import pytest

from scripts.check_changed_coverage import (
    function_entries,
    has_function_entry_arc,
    main,
    normalize_source_path,
)


@pytest.mark.parametrize('workflow_name', ('web-app-ci.yaml', 'server-app-ci.yaml'))
def test_coverage_workflow_propagates_checker_failure(workflow_name: str) -> None:
    repository_root = Path(__file__).resolve().parents[4]
    workflow = (repository_root / '.github' / 'workflows' / workflow_name).read_text(
        encoding='utf-8'
    )
    gate = workflow.split(
        '      - name: Enforce thresholds for every changed production file\n', 1
    )[1].split('      - name:', 1)[0]

    # GitHub's explicit bash shell enables pipefail, preserving a failed checker
    # status when its report is also piped into tee.
    assert '\n        shell: bash\n' in f'\n{gate}'


def test_normalize_source_path_accepts_git_repository_root_paths(
    tmp_path: Path,
) -> None:
    server_root = tmp_path / 'apps' / 'server'
    source = server_root / 'src' / 'shifu' / 'module.py'

    assert (
        normalize_source_path(Path('apps/server/src/shifu/module.py'), server_root)
        == source
    )
    assert normalize_source_path(Path('src/shifu/module.py'), server_root) == source
    assert normalize_source_path(Path('apps/web/src/module.py'), server_root) is None


def test_base_with_no_eligible_changed_files_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    server_root = tmp_path / 'apps' / 'server'
    server_root.mkdir(parents=True)
    monkeypatch.chdir(server_root)
    monkeypatch.setattr(
        'sys.argv', ['check_changed_coverage.py', '--base', 'origin/main']
    )

    def changed_paths(_base: str | None) -> list[Path]:
        return [Path('apps/web/src/module.ts')]

    monkeypatch.setattr('scripts.check_changed_coverage.changed_paths', changed_paths)

    assert main() == 2
    assert 'No changed eligible Server production files.' in capsys.readouterr().err


def test_function_entry_matches_a_multiline_first_statement_arc(tmp_path: Path) -> None:
    source = tmp_path / 'sample.py'
    source.write_text(
        'def decorate(function):\n'
        '    return function\n'
        '\n'
        '@decorate\n'
        'def sample():\n'
        '    if (\n'
        '        True\n'
        '    ):\n'
        '        return True\n',
        encoding='utf-8',
    )

    entry = next(item for item in function_entries(source) if item.name == 'sample')

    assert entry.code_start_line == 4
    assert entry.first_body_line == 6
    assert entry.first_body_end_line == 9
    assert has_function_entry_arc(entry, {(-4, 7)})
    assert not has_function_entry_arc(entry, {(-4, 10)})


def test_function_entry_includes_decorators_on_first_nested_function(
    tmp_path: Path,
) -> None:
    source = tmp_path / 'sample.py'
    source.write_text(
        'class Controller:\n'
        '    @staticmethod\n'
        '    def handle(router):\n'
        "        @router.get('/')\n"
        '        def endpoint():\n'
        '            return None\n',
        encoding='utf-8',
    )

    entry = next(item for item in function_entries(source) if item.name == 'handle')

    assert entry.code_start_line == 2
    assert entry.first_body_line == 4
    assert entry.first_body_end_line == 6
    assert has_function_entry_arc(entry, {(-2, 4)})


def test_function_entries_exclude_declaration_only_stubs(tmp_path: Path) -> None:
    source = tmp_path / 'sample.py'
    source.write_text(
        'def declared_only():\n    ...\n\ndef implemented():\n    return None\n',
        encoding='utf-8',
    )

    assert [entry.name for entry in function_entries(source)] == ['implemented']
