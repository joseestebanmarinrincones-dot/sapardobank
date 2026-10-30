from libreta.services.updates import is_newer, version_tuple


def test_version_tuple():
    assert version_tuple("v1.10.2") == (1, 10, 2)
    assert version_tuple("1.1.0") == (1, 1, 0)


def test_is_newer():
    assert is_newer("v1.1.0", "1.0.0")
    assert is_newer("1.0.10", "1.0.9")
    assert not is_newer("1.0.0", "1.0.0")
    assert not is_newer("0.9.9", "1.0.0")
