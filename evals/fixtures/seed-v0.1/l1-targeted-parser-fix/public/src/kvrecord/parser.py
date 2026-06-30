class ParseError(ValueError):
    pass


def parse_record(text: str) -> dict[str, str]:
    if text == "":
        return {}
    result = {}
    for field in text.split(";"):
        if "=" not in field:
            raise ParseError(f"missing '=' in {field!r}")
        key, value = field.split("=")
        if not key:
            raise ParseError("empty key")
        if key in result:
            raise ParseError(f"duplicate key: {key}")
        result[key] = value
    return result
