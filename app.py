from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber, re, io

app = Flask(__name__)
CORS(app)  # let your frontend (even on a different port) call this API

# Optional: limit uploads to 15 MB to prevent huge files
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15 MB

HEADER_PATTERN = re.compile(
    r"^\s*Weekly\s+Terminal\s+Transactions", re.IGNORECASE | re.MULTILINE
)

ROW_PATTERN = re.compile(r"""
    ^\s*
    \d+\s+                 # S/N
    \S+\s+                 # Terminal ID
    (?P<serial>\S+)\s+     # Terminal Serial
    .*?                    # Business Name (variable width)
    (?P<payment>[\d,]+\.\d{2})\s+   # Payment Value
    \d+\s+                 # Payment Volume
    (?:[\d,]+\.\d{2}|0\.00)\s+      # Transfer Value (ignored)
    \d+\s+                 # Transfer Volume
    [\d,]+\.\d{2}\s+       # Target Payment Value (ignored)
    (?:True|False)\s+      # Target Met (ignored)
    (?P<days>\d+)\s*$
""", re.VERBOSE)

def extract_rows_from_page_text(text: str):
    """Return list of dicts with Terminal Serial, Payment Value, Days Since Last Transaction."""
    # split and keep only non-empty lines
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

    # Optional: drop footer lines like "August 15, 2025 Page 36 of 59"
    if lines and re.search(r"Page\s+\d+\s+of\s+\d+", lines[-1], re.IGNORECASE):
        lines = lines[:-1]

    results = []
    for ln in lines:
        m = ROW_PATTERN.match(ln)
        if m:
            results.append({
                "Terminal Serial": m.group("serial"),
                "Payment Value": m.group("payment"),
                "Days Since Last Transaction": m.group("days")
            })
    return results

@app.post("/parse")
def parse_pdf():
    """
    Multipart form upload: field name 'file'
    Returns JSON with the first page whose header starts with 'Weekly Terminal Transactions'.
    """
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded. Use form field 'file'."}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    # Read into memory (no temp file on disk)
    pdf_bytes = io.BytesIO(file.read())

    try:
        with pdfplumber.open(pdf_bytes) as pdf:
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if HEADER_PATTERN.search(text):
                    data = extract_rows_from_page_text(text)
                    return jsonify({
                        "page_number": idx + 1,
                        "count": len(data),
                        "data": data
                    }), 200

        # If we get here, no matching header was found
        return jsonify({
            "page_number": None,
            "count": 0,
            "data": [],
            "message": "No page found with header starting 'Weekly Terminal Transactions'."
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500

@app.get("/health")
def health():
    return jsonify({"status": "ok"})
    
if __name__ == "__main__":
    # Dev server
    app.run(host="127.0.0.1", port=5000, debug=True)
