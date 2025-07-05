import pytest
import os
from main import get_structure, get_file_contents, format_output

def test_get_structure(tmp_path):
    # Create a temporary directory structure
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello")
    file2 = subdir / "file2.py"
    file2.write_text("import os")

    structure = get_structure(str(tmp_path))
    assert "[DIR] subdir" in structure
    assert "[FILE] file1.txt" in structure
    assert "[FILE] file2.py" in structure

def test_get_file_contents_keyword(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("Hello import")
    file2 = tmp_path / "file2.txt"
    file2.write_text("World")

    contents = get_file_contents(str(tmp_path), keyword="import")
    assert "file1.txt" in contents
    assert "file2.txt" not in contents

def test_format_output_json():
    structure = "test structure"
    contents = "test contents"
    output = format_output(structure, contents, "json")
    assert '"folder_structure": "test structure"' in output
    assert '"file_contents": "test contents"' in output