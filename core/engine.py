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
