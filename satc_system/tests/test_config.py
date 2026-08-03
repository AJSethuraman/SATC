"""Loading hand-edited config: what happens when it will not parse."""

import pytest

# --- a hand-edited config that will not parse --------------------------------
#
# Every config in this system is edited by hand on purpose — prices, promises,
# cutoffs, workflows — so a stray space is an ordinary event. Ten modules each
# called yaml.safe_load directly and let YAMLError escape, so a typo surfaced as
# a stack trace naming a line in "<unicode string>" rather than as a sentence
# naming the file the owner had just saved.

def test_a_yaml_syntax_error_names_the_file_and_the_line(tmp_path):
    from satc.config import ConfigError, read_yaml

    broken = tmp_path / "firm_policy.yaml"
    broken.write_text("cutoffs:\n  form_1040: {month: 3, day: 1}\n   bad: [\n",
                      encoding="utf-8")
    with pytest.raises(ConfigError) as refusal:
        read_yaml(broken)

    said = str(refusal.value)
    assert "firm_policy.yaml" in said          # WHICH file
    assert "line" in said                      # and where in it
    assert "indentation" in said               # and what to look for


def test_no_module_parses_yaml_behind_the_shared_reader():
    """Mutation-proof by construction: a new module calling yaml.safe_load
    directly reintroduces the raw-traceback path, and only a sweep catches it.

    satc/config.py is the one place allowed to, because it IS the reader.
    """
    import pathlib

    import satc

    root = pathlib.Path(satc.__file__).parent
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "config.py":
            continue
        if "yaml.safe_load" in path.read_text(encoding="utf-8"):
            offenders.append(path.relative_to(root).as_posix())
    assert not offenders, (
        f"these parse YAML without the named-refusal wrapper: {offenders}. "
        f"Use satc.config.read_yaml — a stray space in a hand-edited config "
        f"should be a sentence, not a stack trace.")
