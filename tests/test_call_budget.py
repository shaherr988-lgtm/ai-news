from apps.pipeline.call_budget import CallBudget


def test_spend_allows_calls_above_the_reserve():
    budget = CallBudget(total=5, reserved_for_digest=1)
    assert budget.spend() is True
    assert budget.spend() is True
    assert budget.spend() is True
    assert budget.spend() is True  # remaining=1, equals reserve -> this call brings it to the edge
    # remaining is now 1, which equals the reserve, so spend() must refuse
    assert budget.spend() is False


def test_spend_for_digest_can_use_the_reserved_call():
    budget = CallBudget(total=1, reserved_for_digest=1)
    assert budget.spend() is False  # only the reserved call is left
    assert budget.spend_for_digest() is True  # digest is allowed to use it
    assert budget.spend_for_digest() is False  # now truly exhausted


def test_zero_total_budget_refuses_everything_except_nothing():
    budget = CallBudget(total=0)
    assert budget.spend() is False
    assert budget.spend_for_digest() is False


def test_negative_total_is_treated_as_zero():
    budget = CallBudget(total=-5)
    assert budget.spend() is False
    assert budget.spend_for_digest() is False
