"""Mamdani-style fuzzy inference engine with centroid defuzzification."""

from core import membership as mf
from core.rules import RULES, RULE_LABELS

SENTIMENT_MAP = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}

RATING_FUNCS = {
    "low": mf.rating_low,
    "medium": mf.rating_medium,
    "high": mf.rating_high,
}

SENTIMENT_FUNCS = {
    "negative": mf.sentiment_negative,
    "neutral": mf.sentiment_neutral,
    "positive": mf.sentiment_positive,
}

OUTPUT_TERMS = ["low", "medium", "high"]


def fuzzify(rating, sentiment_score):
    rating_degrees = {k: f(rating) for k, f in RATING_FUNCS.items()}
    sentiment_degrees = {k: f(sentiment_score) for k, f in SENTIMENT_FUNCS.items()}
    return rating_degrees, sentiment_degrees


def apply_rules(rating_degrees, sentiment_degrees):
    """Return list of (rule_key, strength, output_term) for fired rules, plus
    an aggregated dict of max strength per output term."""
    fired = []
    aggregated = {term: 0.0 for term in OUTPUT_TERMS}

    for (r_term, s_term), out_term in RULES:
        strength = min(rating_degrees[r_term], sentiment_degrees[s_term])
        if strength > 0:
            fired.append(((r_term, s_term), strength, out_term))
            if strength > aggregated[out_term]:
                aggregated[out_term] = strength

    return fired, aggregated


def defuzzify_centroid(aggregated, resolution=1.0, domain=(0, 100)):
    """Centroid (center of gravity) defuzzification over the discretized
    output domain, clipping each output set's membership at its rule strength."""
    lo, hi = domain
    numerator = 0.0
    denominator = 0.0

    x = lo
    while x <= hi:
        # Aggregated membership at x = max over output terms of
        # min(rule_strength, output_set_membership(x))
        agg_y = 0.0
        for term, strength in aggregated.items():
            if strength <= 0:
                continue
            y = min(strength, mf.output_membership(term, x))
            if y > agg_y:
                agg_y = y
        numerator += x * agg_y
        denominator += agg_y
        x += resolution

    if denominator == 0:
        return 50.0  # neutral fallback if nothing fired
    return numerator / denominator


def categorize(score):
    if score < 40:
        return "Low"
    elif score < 65:
        return "Medium"
    else:
        return "High"


import numpy as np


def _tri(x, a, b, c):
    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)
    left = (x > a) & (x <= b) & (b > a)
    y[left] = (x[left] - a) / (b - a)
    right = (x > b) & (x < c) & (c > b)
    y[right] = (c - x[right]) / (c - b)
    y[x == b] = 1.0
    return y


def _trap(x, a, b, c, d):
    x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)
    left = (x > a) & (x < b) & (b > a)
    y[left] = (x[left] - a) / (b - a)
    flat = (x >= b) & (x <= c)
    y[flat] = 1.0
    right = (x > c) & (x < d) & (d > c)
    y[right] = (d - x[right]) / (d - c)
    return y


_OUT_DOMAIN = np.arange(0, 101, 1.0)
_OUT_SETS = {
    "low": _trap(_OUT_DOMAIN, 0, 0, 25, 45),
    "medium": _tri(_OUT_DOMAIN, 30, 50, 70),
    "high": _trap(_OUT_DOMAIN, 55, 75, 100, 100),
}


def analyze_batch(ratings, sentiment_labels):
    """Vectorized fuzzy inference for large datasets (numpy-based).

    ratings: array-like of numeric ratings (1-5)
    sentiment_labels: array-like of 'Positive'/'Neutral'/'Negative' strings
    Returns: (scores: np.ndarray, categories: np.ndarray[str], rule_hits: dict[str,int])
    """
    r = np.clip(np.asarray(ratings, dtype=float), 1.0, 5.0)
    labels = np.array([str(s).strip().lower() if s == s else "neutral" for s in sentiment_labels])
    s = np.vectorize(lambda k: SENTIMENT_MAP.get(k, 0.5))(labels)

    r_deg = {
        "low": _trap(r, 0, 1, 1.5, 2.5),
        "medium": _tri(r, 2, 3, 4),
        "high": _trap(r, 3.5, 4.5, 5, 6),
    }
    s_deg = {
        "negative": _trap(s, -0.1, 0, 0, 0.35),
        "neutral": _tri(s, 0.15, 0.5, 0.85),
        "positive": _trap(s, 0.65, 1, 1, 1.1),
    }

    n = len(r)
    agg = {"low": np.zeros(n), "medium": np.zeros(n), "high": np.zeros(n)}
    rule_hits = {}

    for (r_term, s_term), out_term in RULES:
        strength = np.minimum(r_deg[r_term], s_deg[s_term])
        agg[out_term] = np.maximum(agg[out_term], strength)
        count = int((strength > 0).sum())
        if count:
            rule_hits[RULE_LABELS[(r_term, s_term)]] = count

    # Centroid defuzzification, vectorized across all rows at once.
    # For each output point x, aggregated membership = max over terms of min(strength, set(x))
    numer = np.zeros(n)
    denom = np.zeros(n)
    for term in OUTPUT_TERMS:
        clipped = np.minimum(agg[term][:, None], _OUT_SETS[term][None, :])  # (n, 101)
        numer += (clipped * _OUT_DOMAIN[None, :]).sum(axis=1)
        denom += clipped.sum(axis=1)

    scores = np.where(denom > 0, numer / denom, 50.0)
    scores = np.round(scores, 2)

    categories = np.where(scores < 40, "Low", np.where(scores < 65, "Medium", "High"))

    return scores, categories, rule_hits


def analyze_record(rating, sentiment_label):
    """Run full fuzzy inference for a single record.

    rating: numeric 1-5
    sentiment_label: 'Positive' | 'Neutral' | 'Negative' (case-insensitive)
    """
    sentiment_key = str(sentiment_label).strip().lower()
    sentiment_score = SENTIMENT_MAP.get(sentiment_key, 0.5)

    rating = max(1.0, min(5.0, float(rating)))

    rating_degrees, sentiment_degrees = fuzzify(rating, sentiment_score)
    fired, aggregated = apply_rules(rating_degrees, sentiment_degrees)
    score = defuzzify_centroid(aggregated)
    category = categorize(score)

    fired_labels = [RULE_LABELS[key] for key, strength, _ in
                    sorted(fired, key=lambda r: -r[1])]

    return {
        "satisfaction_score": round(score, 2),
        "satisfaction_category": category,
        "fired_rules": fired_labels,
    }
