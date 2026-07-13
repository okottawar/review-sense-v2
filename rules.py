"""Fuzzy rule base mapping (rating, sentiment) -> satisfaction category.

Each rule: (rating_term, sentiment_term) -> output_term
Rule strength = min(rating_membership, sentiment_membership)  [AND / Mamdani min]
"""

RULES = [
    (("low", "negative"), "low"),
    (("low", "neutral"), "low"),
    (("low", "positive"), "medium"),
    (("medium", "negative"), "low"),
    (("medium", "neutral"), "medium"),
    (("medium", "positive"), "high"),
    (("high", "negative"), "medium"),
    (("high", "neutral"), "high"),
    (("high", "positive"), "high"),
]

RULE_LABELS = {
    ("low", "negative"): "Low rating + negative sentiment -> Low satisfaction",
    ("low", "neutral"): "Low rating + neutral sentiment -> Low satisfaction",
    ("low", "positive"): "Low rating + positive sentiment -> Medium satisfaction",
    ("medium", "negative"): "Medium rating + negative sentiment -> Low satisfaction",
    ("medium", "neutral"): "Medium rating + neutral sentiment -> Medium satisfaction",
    ("medium", "positive"): "Medium rating + positive sentiment -> High satisfaction",
    ("high", "negative"): "High rating + negative sentiment -> Medium satisfaction",
    ("high", "neutral"): "High rating + neutral sentiment -> High satisfaction",
    ("high", "positive"): "High rating + positive sentiment -> High satisfaction",
}
