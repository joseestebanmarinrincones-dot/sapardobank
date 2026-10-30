from libreta.ui import theme


def test_all_palettes_apply_and_restore():
    original = theme.ACTIVE_PALETTE
    for item in theme.theme_choices():
        applied = theme.apply_palette(item["key"])
        assert applied == item["key"]
        assert theme.GREEN.startswith("#")
        assert theme.PAPER.startswith("#")
        assert theme.INK.startswith("#")
    theme.apply_palette(original)
    assert theme.ACTIVE_PALETTE == original


def test_invalid_palette_falls_back():
    applied = theme.apply_palette("no-existe")
    assert applied == "esmeralda"
    theme.apply_palette("esmeralda")
