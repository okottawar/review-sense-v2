"""Orchestrates fuzzy analysis over a full dataset."""

from collections import Counter
import pandas as pd

from core.engine import analyze_batch


REQUIRED_COLUMNS = ["rating", "sentiment"]
MAX_ROWS = 200_000  # safety cap so a single serverless invocation doesn't time out


def validate_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Expected at least: {', '.join(REQUIRED_COLUMNS)}"
        )


def analyze_dataframe(df: pd.DataFrame):
    validate_columns(df)

    sampled = False
    original_count = len(df)
    if len(df) > MAX_ROWS:
        df = df.sample(n=MAX_ROWS, random_state=42).reset_index(drop=True)
        sampled = True

    ratings = df["rating"].fillna(3.0).values
    sentiments = df["sentiment"].fillna("Neutral").values

    scores, categories, rule_hits = analyze_batch(ratings, sentiments)

    df_out = df.copy()
    df_out["satisfaction_score"] = scores
    df_out["satisfaction_category"] = categories

    distribution = Counter(categories.tolist())
    total = len(categories) or 1
    rule_counter = Counter(rule_hits)

    summary = {
        "record_count": original_count,
        "analyzed_count": len(df),
        "sampled": sampled,
        "column_count": len(df.columns),
        "missing_values": int(df.isna().sum().sum()),
        "average_satisfaction_score": round(float(scores.mean()), 2) if len(scores) else 0,
        "satisfaction_distribution": {
            "Low": distribution.get("Low", 0),
            "Medium": distribution.get("Medium", 0),
            "High": distribution.get("High", 0),
        },
        "satisfaction_distribution_pct": {
            k: round(v / total * 100, 1)
            for k, v in {
                "Low": distribution.get("Low", 0),
                "Medium": distribution.get("Medium", 0),
                "High": distribution.get("High", 0),
            }.items()
        },
        "top_fired_rules": [
            {"rule": rule, "count": count}
            for rule, count in rule_counter.most_common(5)
        ],
        "preview_rows": df.head(5).fillna("").to_dict(orient="records"),
        "insights": generate_insights(distribution, total, scores),
    }

    return df_out, summary


def generate_insights(distribution, total, scores):
    insights = []
    low_pct = distribution.get("Low", 0) / total * 100
    high_pct = distribution.get("High", 0) / total * 100
    avg = float(scores.mean()) if len(scores) else 0

    if high_pct >= 60:
        insights.append(
            f"The majority of reviews ({high_pct:.1f}%) reflect high satisfaction, "
            "suggesting strong overall product perception."
        )
    if low_pct >= 30:
        insights.append(
            f"A notable share of reviews ({low_pct:.1f}%) fall into the low "
            "satisfaction band, worth investigating for recurring complaints."
        )
    if avg >= 70:
        insights.append(f"Average satisfaction score is {avg:.1f}/100, indicating generally positive reception.")
    elif avg <= 40:
        insights.append(f"Average satisfaction score is {avg:.1f}/100, indicating widespread dissatisfaction.")
    else:
        insights.append(f"Average satisfaction score is {avg:.1f}/100, indicating mixed sentiment overall.")

    if not insights:
        insights.append("Satisfaction scores are broadly distributed across categories with no dominant trend.")

    return insights
