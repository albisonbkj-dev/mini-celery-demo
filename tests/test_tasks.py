from app.tasks import aggregate_results


def test_aggregate_results_sums_squares():
    rows = [
        {"input": 1, "square": 1},
        {"input": 2, "square": 4},
        {"input": 3, "square": 9},
    ]
    out = aggregate_results.run(rows)
    assert out["items"] == rows
    assert out["sum_of_squares"] == 14
