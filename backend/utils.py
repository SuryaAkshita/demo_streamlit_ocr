# backend/utils.py

import json
import re


def clean_model_json(text: str) -> str:
    """Enhanced JSON cleaning"""
    if not isinstance(text, str):
        return text
    cleaned = text.strip()

    # Remove markdown code blocks
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("```", "")

    # Extract JSON object
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1:
        cleaned = cleaned[first:last + 1]

    # Fix common JSON errors (trailing commas)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    return cleaned.strip()


def try_parse_json_strict(obj):
    if isinstance(obj, dict):
        return obj, True
    if isinstance(obj, str):
        cleaned = clean_model_json(obj)
        try:
            parsed = json.loads(cleaned)
            return parsed, True
        except Exception:
            return obj, False
    return obj, False


def remove_empty_values(data):
    """Smart removal that preserves explicit values like 'N/A'"""
    if isinstance(data, dict):
        return {
            k: remove_empty_values(v)
            for k, v in data.items()
            if (v is not None and v != "" and v != [] and v != {})
            or v == "N/A"
            or v == 0
            or v is False
        }
    elif isinstance(data, list):
        cleaned = [
            remove_empty_values(item)
            for item in data
            if item is not None and item != "" and item != {} and item != []
        ]
        return cleaned if cleaned else None
    else:
        return data


def pretty_console(obj, max_chars=None):
    if isinstance(obj, dict):
        s = json.dumps(obj, indent=2, ensure_ascii=False)
    else:
        s = str(obj)
    if max_chars and len(s) > max_chars:
        s = s[:max_chars] + " ... [truncated]"
    print(s)


def save_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def normalize_extracted_data(parsed):
    """
    Your exact normalize logic, preserved.
    Requires remove_empty_values().
    """
    if not parsed or not isinstance(parsed, dict):
        parsed = {"section": "UNKNOWN SECTION"}

    if "section" not in parsed:
        parsed["section"] = "UNKNOWN SECTION"

    if "form_fields" in parsed and "tables" in parsed:
        tables = parsed["tables"]

        # Handle tables as list or dict
        if isinstance(tables, list):
            merged = {}
            for t in tables:
                if isinstance(t, dict):
                    merged.update(t)
            tables = merged
            parsed["tables"] = tables

        if isinstance(tables, dict):
            table_fields = set()
            for table_name, table_data in tables.items():
                if isinstance(table_data, list) and table_data:
                    first_row = table_data[0]
                    if isinstance(first_row, dict):
                        table_fields.update(first_row.keys())

            # Remove duplicate fields
            fields_to_remove = []
            for field_name, field_value in parsed.get("form_fields", {}).items():
                if field_name in table_fields and isinstance(field_value, list):
                    fields_to_remove.append(field_name)

            for field_name in fields_to_remove:
                del parsed["form_fields"][field_name]

            if not parsed["form_fields"]:
                del parsed["form_fields"]

    return remove_empty_values(parsed)