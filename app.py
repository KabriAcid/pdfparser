from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pdfplumber, re, io, json, os
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15 MB


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# Regex patterns
HEADER_PATTERN = re.compile(
    r"^\s*Weekly\s+Terminal\s+Transactions", re.IGNORECASE | re.MULTILINE
)

ROW_PATTERN = re.compile(r"""
    ^\s*
    (?P<sn>\d+)\s+             # S/N
    \S+\s+                     # Terminal ID
    (?P<serial>\S+)\s+         # Terminal Serial
    .*?                        # Business Name (variable width)
    (?P<payment>[\d,]+\.\d{2})\s+  # Payment Value
    \d+\s+                     # Payment Volume
    (?:[\d,]+\.\d{2}|0\.00)\s+ # Transfer Value (ignored)
    \d+\s+                     # Transfer Volume
    [\d,]+\.\d{2}\s+           # Target Payment Value (ignored)
    (?:True|False)\s+          # Target Met (ignored)
    (?P<days>\d+)\s*$          # Days Since Last Transaction
""", re.VERBOSE)


def extract_weekly_rows(pdf_bytes):
    """
    Parse the entire PDF, starting from the first "Weekly Terminal Transactions"
    header, and keep extracting rows across multiple pages until we see S/N reset
    to 1 (indicating a new table). Ignores footers and unrelated text.
    """
    weekly_rows = []
    in_weekly_section = False

    with pdfplumber.open(pdf_bytes) as pdf:
        for idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

            for i, ln in enumerate(lines):
                # Start parsing when we see the header
                if not in_weekly_section and HEADER_PATTERN.search(ln):
                    in_weekly_section = True
                    continue

                if in_weekly_section:
                    m = ROW_PATTERN.match(ln)
                    if m:
                        sn_val = int(m.group("sn"))

                        # If S/N resets to 1 and we already have rows, stop completely
                        if sn_val == 1 and weekly_rows:
                            return weekly_rows

                        # Add valid row
                        weekly_rows.append({
                            "S/N": sn_val,
                            "Terminal Serial": m.group("serial"),
                            "Payment Value": m.group("payment"),
                            "Days Since Last Transaction": m.group("days"),
                            "Page": idx + 1
                        })
    return weekly_rows


@app.route("/parse", methods=["POST"])
def parse_pdf():
    file = request.files.get("pdf")
    if not file:
        return jsonify({"error": "No file uploaded. Use form field 'pdf'."}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    pdf_bytes = io.BytesIO(file.read())
    try:
        rows = extract_weekly_rows(pdf_bytes)

        # Save to logs
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"weekly_rows_{ts}.json")

        output_json = {
            "message": "Weekly section extracted successfully.",
            "count": len(rows),
            "rows": rows
        }
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(output_json, f, ensure_ascii=False, indent=2)

        return jsonify(output_json), 200
    except Exception as e:
        return jsonify({"error": f"Failed to parse PDF: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
