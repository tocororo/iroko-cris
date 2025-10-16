import re


def sanitize_str_value(value):
    if isinstance(value, str):
        if re.search(r'\\u[0-9a-fA-F]{4}', value):
            value = value.encode().decode('unicode_escape')
        return re.sub(r"[\"\'`]", " ", value)
    return value
