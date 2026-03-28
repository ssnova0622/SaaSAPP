# services/ai/helpers/config.py

AI_DEFAULTS = {
    "forecast": {
        "min_days": 7,
        "max_days": 120,
        "lead_time": 3,
        "safety_days": 2,
        "top": 50,
    },
    "sales": {
        "top_sellers": 20,
        "timeseries_days": 30,
    },
    "carts": {
        "window_hours": 24,
        "top": 10,
    },
    "customers": {
        "days": 30,
    },
    "categories": {
        "days": 30,
    },
    "professionals": {
        "days": 30,
    }
}
