# Testing framework: pytest
# Shared fixtures: no_save

import pytest
import matplotlib.pyplot as plt
from scripts.visualization.plots import create_line_plot, create_bar_chart, preprocess_data

@pytest.fixture(autouse=True)
def no_save(monkeypatch):
    monkeypatch.setattr(plt, "savefig", lambda *args, **kwargs: None)

def test_create_line_plot_happy_path(tmp_path):
    data = [1, 2, 3]
    labels = ["a", "b", "c"]
    out_file = tmp_path / "line.png"
    # Should complete without error under monkeypatched savefig
    create_line_plot(data, labels, title="Test", output_path=str(out_file))

@pytest.mark.parametrize("data, labels", [
    ([], []),
    ([1, 2, 3], []),
    ([], ["x", "y"])
])
def test_create_line_plot_invalid_inputs_raises(data, labels):
    with pytest.raises(ValueError):
        create_line_plot(data, labels, title="Bad", output_path="unused.png")

def test_create_bar_chart_happy_path(tmp_path):
    data = [10, 20, 30]
    categories = ["x", "y", "z"]
    out_file = tmp_path / "bar.png"
    create_bar_chart(data, categories, title="Bars", output_path=str(out_file))

@pytest.mark.parametrize("data, categories", [
    ([], []),
    ([1, 2, 3], []),
    ([], ["x", "y"])
])
def test_create_bar_chart_invalid_inputs_raises(data, categories):
    with pytest.raises(ValueError):
        create_bar_chart(data, categories, title="Bad", output_path="unused.png")

def test_preprocess_data_happy_path():
    raw = [1, 2, 3]
    processed = preprocess_data(raw)
    assert isinstance(processed, list)
    assert len(processed) == len(raw)

@pytest.mark.parametrize("invalid_input", [None, "string", 123])
def test_preprocess_data_invalid_inputs_raises(invalid_input):
    with pytest.raises(ValueError):
        preprocess_data(invalid_input)