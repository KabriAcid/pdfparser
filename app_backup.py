# Backup of original app.py
# This file is a direct copy of your working app.py as of now.

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pdfplumber, re, io, json, os

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15 MB

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

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
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    start_idx = None
    for i, ln in enumerate(lines):
        if re.search(r"Weekly\s+Terminal\s+Transactions", ln, re.IGNORECASE):
            start_idx = i + 1
            break
    if start_idx is None:
        return []
    results = []
    for ln in lines[start_idx:]:
        m = ROW_PATTERN.match(ln)
        if m:
            results.append({
                "Terminal Serial": m.group("serial"),
                "Payment Value": m.group("payment"),
                "Days Since Last Transaction": m.group("days")
            })
            if len(results) >= 366:
                break
    return results

@app.route("/parse", methods=["POST"])
def parse_pdf():
    file = request.files.get("pdf")
    if not file:
        return jsonify({"error": "No file uploaded. Use form field 'pdf'."}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400
    pdf_bytes = io.BytesIO(file.read())
    try:
        with pdfplumber.open(pdf_bytes) as pdf:
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if HEADER_PATTERN.search(text):
                    data = extract_rows_from_page_text(text)
                    result = {
                        "page_number": idx + 1,
                        "count": len(data),
                        "data": data
                    }
                    log_dir = os.path.join(os.path.dirname(__file__), "logs")
                    os.makedirs(log_dir, exist_ok=True)
                    from datetime import datetime
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    log_path = os.path.join(log_dir, f"parsed_{ts}.json")
                    with open(log_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    return jsonify(result), 200
            result = {
                "page_number": None,
                "count": 0,
                "data": [],
                "message": "No page found with header starting 'Weekly Terminal Transactions'."
            }
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
            os.makedirs(log_dir, exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = os.path.join(log_dir, f"parsed_{ts}.json")
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
