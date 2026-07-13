"""Fuzzy membership functions (pure Python, no scikit-fuzzy dependency)."""


def triangular(x, a, b, c):
    """Triangular membership: rises a->b, falls b->c."""
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)


def trapezoidal(x, a, b, c, d):
    """Trapezoidal membership: rises a->b, flat b->c, falls c->d."""
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (d - x) / (d - c)


# ---- Rating (1-5 stars) membership functions ----

def rating_low(x):
    return trapezoidal(x, 0, 1, 1.5, 2.5)


def rating_medium(x):
    return triangular(x, 2, 3, 4)


def rating_high(x):
    return trapezoidal(x, 3.5, 4.5, 5, 6)


# ---- Sentiment polarity (0-1, mapped from Negative/Neutral/Positive) ----

def sentiment_negative(x):
    return trapezoidal(x, -0.1, 0, 0, 0.35)


def sentiment_neutral(x):
    return triangular(x, 0.15, 0.5, 0.85)


def sentiment_positive(x):
    return trapezoidal(x, 0.65, 1, 1, 1.1)


# ---- Output: satisfaction (0-100) membership functions for defuzzification ----

SATISFACTION_SETS = {
    "low": (0, 0, 25, 45),       # trapezoidal
    "medium": (30, 50, 70),      # triangular
    "high": (55, 75, 100, 100),  # trapezoidal
}


def output_membership(name, x):
    params = SATISFACTION_SETS[name]
    if len(params) == 3:
        return triangular(x, *params)
    return trapezoidal(x, *params)
