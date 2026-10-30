from libreta.services.categorizer import suggest_category


def test_suggest_categories():
    assert suggest_category("Café latte") == "coffee"
    assert suggest_category("UBER TRIP") == "transport"
    assert suggest_category("Soriana súper") == "groceries"
    assert suggest_category("Nómina octubre") == "income"
    assert suggest_category("algo raro") == "other"
    assert suggest_category(None) == "other"
