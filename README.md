"""
PROJECT: PDF Parser API (Flask + pdfplumber)

GOAL:
We are building a simple backend service in Python (Flask) that:
1. Accepts a PDF upload over HTTP (POST /parse).
2. Parses the first page in the PDF where the header starts with "Weekly Terminal Transactions"
   (header detection should be flexible: case-insensitive, ignores extra spaces).
3. Extracts only these columns from each row in the table:
   - Terminal Serial
   - Payment Value
   - Days Since Last Transaction
4. Returns the extracted data as JSON in this structure:
   {
     "page_number": <int>,
     "count": <int>,   # number of rows parsed
     "data": [
        {
          "Terminal Serial": "P260301190391",
          "Payment Value": "2,819,280.00",
          "Days Since Last Transaction": "0"
        },
        ...
     ]
   }

BACKEND DETAILS:
- Use Flask as the web framework.
- Use flask-cors to allow requests from a frontend (browser-based React/HTML app).
- Use pdfplumber for PDF parsing and regex for table extraction.
- Limit uploads to ~15MB to prevent abuse.
- Provide a /health endpoint that returns {"status": "ok"} for quick checks.

FRONTEND PLAN:
- Later, we’ll build a simple frontend (HTML/JS or React) to:
  - Upload a PDF
  - Call this API
  - Display the returned data in a table
  - Optionally download results as JSON/CSV

FUTURE IMPROVEMENTS (Copilot suggestions welcome):
- Allow scanning all pages, not just the first match.
- Handle more complex tables (multi-line Business Names, etc.).
- Add authentication if needed for production.
- Add pagination and CSV/Excel export.
"""
