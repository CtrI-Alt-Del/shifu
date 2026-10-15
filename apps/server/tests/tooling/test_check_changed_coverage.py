from pathlib import Path

from scripts.check_changed_coverage import function_entries, has_function_entry_arc


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


def test_function_entries_exclude_declaration_only_stubs(tmp_path: Path) -> None:
    source = tmp_path / 'sample.py'
    source.write_text(
        'def declared_only():\n    ...\n\ndef implemented():\n    return None\n',
        encoding='utf-8',
    )

    assert [entry.name for entry in function_entries(source)] == ['implemented']
