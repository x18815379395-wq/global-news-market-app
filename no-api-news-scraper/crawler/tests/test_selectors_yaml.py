import yaml, pathlib

def test_selectors_yaml_loads():
    p = pathlib.Path("config/selectors.yaml")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "x" in data and "truth" in data
    for k in ("article","link_contains","time"):
        assert k in data["x"]
        assert k in data["truth"]
