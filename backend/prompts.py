# backend/prompts.py

# ✅ IMPROVED: More detailed extraction prompt for forms
EXTRACTION_PROMPT = """
Extract ALL information from this document page into structured JSON.

Required JSON structure:
{
  "section": "page title or section heading",
  "form_fields": {
    "field_name": "exact value"
  },
  "tables": {
    "table_name": [{"column": "value"}]
  },
  "checkboxes": {
    "checkbox_label": "checked/unchecked"
  },
  "signatures": {
    "signer_name": "name",
    "date": "MM/DD/YYYY"
  }
}

CRITICAL RULES:
1. Extract EVERY field with its value (use null if empty)
2. For form labels , extract as {"name": "value"}
3. For checkboxes marked X or ☑, extract as "checked"
4. For tables, extract ALL rows with column headers as keys
5. For multi-line addresses, extract complete address
6. For dates, preserve exact format
7. For currency/amounts, preserve symbols and decimals
8. Extract field numbers when present
9. If field says "N/A", extract as "N/A" not null

Return ONLY valid JSON. No markdown, no backticks, no explanations.
Extract verbatim - do not abbreviate.
""".strip()

METADATA_PROMPT = """
Extract document metadata from this first page and return ONLY valid JSON.

{
  "document_type": "full form name/title",
  "envelope_id": "document ID",
  "total_pages_in_doc": "page count from 'Page X of Y'",
  "organization": "company/organization name",
  "form_number": "form number if visible",
  "primary_contact": "main person named on page 1"
}

Extract from headers, footers, and prominent text.
Return null for fields not found.
Return ONLY valid JSON with no markdown.
""".strip()