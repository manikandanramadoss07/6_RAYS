# Normal clinical ranges used to score each parameter individually.
# Each parameter gets a risk score (0 = normal, 1 = mild, 2 = high risk)
# before being averaged — so one badly abnormal reading pulls the
# score up rather than getting diluted by a raw average of values.

NORMAL_RANGES = {
    "BP_SYSTOLIC": (90, 120),
    "BP_DIASTOLIC": (60, 80),
    "SPO2": (95, 100),
    "HEART_RATE": (60, 100),
    "TEMPERATURE": (97.0, 99.0),   # Fahrenheit
    "GLUCOSE": (70, 140),           # mg/dL, random/postprandial-ish band
    "HEMOGLOBIN": (12.0, 16.0),     # g/dL
    "RESPIRATORY_RATE": (12, 20),
}


def score_parameter(parameter_name, value):
    """Return an individual risk score (0, 1, or 2) for one parameter."""
    key = parameter_name.upper().replace(" ", "_")
    if key not in NORMAL_RANGES:
        return 0  # unknown parameter — don't penalize, just skip

    low, high = NORMAL_RANGES[key]

    if low <= value <= high:
        return 0  # normal

    # how far outside the range, as a fraction of the range width
    range_width = high - low
    if value < low:
        deviation = (low - value) / range_width
    else:
        deviation = (value - high) / range_width

    if deviation <= 0.25:
        return 1  # mild deviation
    return 2  # significant deviation — high risk


def calculate_risk_score(parameter_values):
    """
    parameter_values: dict like {"SPO2": 92, "HEART_RATE": 110, ...}
    Returns: dict with overall risk score (0-2 scale), risk label,
             and the per-parameter breakdown.
    """
    if not parameter_values:
        return {
            "risk_score": None,
            "risk_label": "INSUFFICIENT_DATA",
            "breakdown": {}
        }

    breakdown = {}
    total = 0
    count = 0

    for param, value in parameter_values.items():
        if value is None:
            continue
        s = score_parameter(param, value)
        breakdown[param] = s
        total += s
        count += 1

    if count == 0:
        return {
            "risk_score": None,
            "risk_label": "INSUFFICIENT_DATA",
            "breakdown": {}
        }

    avg_score = round(total / count, 2)

    if avg_score == 0:
        label = "NORMAL"
    elif avg_score <= 0.75:
        label = "MILD_RISK"
    elif avg_score <= 1.5:
        label = "MODERATE_RISK"
    else:
        label = "HIGH_RISK"

    return {
        "risk_score": avg_score,
        "risk_label": label,
        "breakdown": breakdown
    }
