import os
import pytest
from scripts.visualization.generate_visuals import generate_visuals

def test_generate_visuals_creates_expected_files(tmp_path):
    # Arrange: valid sample data
    data = [
        {"x": [1, 2, 3], "y": [4, 5, 6]},
        {"x": [10, 20, 30], "y": [40, 50, 60]}
    ]
    output_dir = tmp_path / "charts"
    output_dir.mkdir()
    # Act
    result = generate_visuals(data, output_dir, title="Sample Chart")
    # Assert: function returns a list of file paths
    assert isinstance(result, list)
    # Each returned path should exist on disk
    for path in result:
        assert os.path.isfile(path)
    # At least one file was created
    assert len(result) >= 1

def test_generate_visuals_empty_data_raises_value_error(tmp_path):
    # Arrange: empty data list
    data = []
    output_dir = tmp_path / "empty"
    output_dir.mkdir()
    # Act & Assert
    with pytest.raises(ValueError):
        generate_visuals(data, output_dir)

def test_generate_visuals_invalid_structure_raises_key_error(tmp_path):
    # Arrange: malformed data
    data = [{"foo": [1, 2, 3], "bar": [4, 5, 6]}]
    output_dir = tmp_path / "invalid"
    output_dir.mkdir()
    # Act & Assert
    with pytest.raises(KeyError):
        generate_visuals(data, output_dir)

def test_generate_visuals_default_title_and_format(tmp_path):
    # Arrange: minimal valid data
    data = [{"x": [0, 1], "y": [1, 0]}]
    output_dir = tmp_path / "default"
    output_dir.mkdir()
    # Act
    result = generate_visuals(data, output_dir)
    # Assert
    assert isinstance(result, list) and result
    # Check default filename contains expected substrings
    for path in result:
        name = os.path.basename(path)
        assert "chart" in name or name.endswith(".png")

def test_generate_visuals_monkeypatch_savefig(tmp_path, monkeypatch):
    data = [{"x": [1], "y": [1]}]
    output_dir = tmp_path / "mock"
    output_dir.mkdir()
    # Prevent actual file writing
    class DummyFig:
        saved = None
        def savefig(self, path, *args, **kwargs):
            DummyFig.saved = path
    monkeypatch.setattr(
        "scripts.visualization.generate_visuals.plt.Figure",
        lambda *args, **kwargs: DummyFig()
    )
    # Act
    result = generate_visuals(data, output_dir)
    # Assert that savefig was called with a path in output_dir
    assert DummyFig.saved is not None
    assert DummyFig.saved.startswith(str(output_dir))