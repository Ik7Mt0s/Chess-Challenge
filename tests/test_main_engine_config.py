import main


def test_competition_engine_uses_winning_search_config(
    monkeypatch,
):
    captured = {}

    monkeypatch.setattr(
        main,
        "NeuralEvaluator",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        main,
        "HybridEvaluator",
        lambda **kwargs: object(),
    )

    class CapturingEngine:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        main,
        "ChessEngine",
        CapturingEngine,
    )

    main.create_competition_engine()

    assert captured["use_pvs"] is True
    assert captured["early_stop_enabled"] is False
