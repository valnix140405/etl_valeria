import re
from datetime import datetime

def to_snake_case(text):
    text = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', text)
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
    return text.lower().replace(" ", "_")

def normalize_keys_to_snake_case(record):
    return {to_snake_case(k): v for k, v in record.items()}

def safe_parse_date(date_str, fmt="%Y-%m-%d"):
    try:
        return datetime.strptime(date_str, fmt)
    except Exception:
        return None

def remove_duplicates_by_key(data, key_fn):
    seen = set()
    output = []
    for item in data:
        key = key_fn(item)
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output
