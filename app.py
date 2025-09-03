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
    """
    Extract only the section starting from 'Weekly Terminal Transactions' up to the last valid row, ignoring any further headers or S/N resets.
    """
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
        all_tables = []
        with pdfplumber.open(pdf_bytes) as pdf:
            for idx, page in enumerate(pdf.pages):
                page_tables = []
                text = page.extract_text() or ""
                # Find all headers in the page text
                header_regex = re.compile(r"(Weekly Terminal Transactions|Non[-\s]?Transacting Terminals|Other Header Name)", re.IGNORECASE)
                headers = [(m.group(0), m.start()) for m in header_regex.finditer(text)]
                tables = page.extract_tables()
                # Pair each table with its preceding header
                for t_idx, table in enumerate(tables):
                    # Find header for this table
                    header_for_table = None
                    if headers:
                        # Find the closest header before the table's first row
                        # (approximate by using the order of tables and headers)
                        header_for_table = headers[min(t_idx, len(headers)-1)][0]
                    # Convert table rows to dicts if possible, else keep as list
                    table_rows = []
                    if table and len(table) > 1:
                        th = table[0]
                        for row in table[1:]:
                            row_dict = {th[i]: row[i] for i in range(len(th)) if i < len(row)}
                            table_rows.append(row_dict)
                    page_tables.append({
                        "header": header_for_table,
                        "table": table_rows
                    })
                all_tables.append({
                    "page_number": idx + 1,
                    "table_count": len(tables),
                    "tables": page_tables
                })
        # Dump all tables to logs/all_tables_<timestamp>.json
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"all_tables_{ts}.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(all_tables, f, ensure_ascii=False, indent=2)
        return jsonify({"message": "All tables extracted and saved with headers.", "pages": len(all_tables), "log_file": log_path}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)