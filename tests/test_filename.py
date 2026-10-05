"""Pure-logic tests for the _build_relpath filename template (subfolders + path-traversal guard)."""
from pathlib import Path

from ig_live_detector.recorder import DEFAULT_FILENAME, _build_relpath

_FIELDS = dict(
    username="username1",
    user_id="100",
    broadcast_id="123",
    datetime_str="20261005_1430",
)


def _rel(template, part=1):
    return _build_relpath(
        template,
        username=_FIELDS["username"],
        user_id=_FIELDS["user_id"],
        broadcast_id=_FIELDS["broadcast_id"],
        datetime=_FIELDS["datetime_str"],
        part=part,
    )


def test_default_template():
    assert str(_rel(DEFAULT_FILENAME)) == "ig_live_username1_20261005_1430_part01"


def test_subfolder_template():
    assert _rel("{username}/part_{part:02d}", part=2) == Path("username1") / "part_02"


def test_path_traversal_blocked():
    rel = _rel("../../etc/{username}")
    assert ".." not in rel.parts
    assert rel == Path("etc") / "username1"


def test_illegal_chars_sanitised():
    rel = _rel("a b:c*{part}")
    assert str(rel) == "a_b_c_1"


def test_bad_template_falls_back_to_default():
    # unknown field in template -> fall back to the default template
    assert str(_rel("{nope}")) == "ig_live_username1_20261005_1430_part01"
