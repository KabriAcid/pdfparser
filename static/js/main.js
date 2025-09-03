document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("uploadForm");
  const fileInput = document.getElementById("pdfFile");
  const resultDiv = document.getElementById("result");

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    resultDiv.innerHTML = "";
    resultDiv.className = "";

    const file = fileInput.files[0];

    if (!file) {
      resultDiv.textContent = "Please select a PDF file.";
      resultDiv.className = "response-info";
      return;
    }

    const formData = new FormData();
    formData.append("pdf", file);

    resultDiv.textContent = "Uploading and parsing...";
    resultDiv.className = "response-info";

    try {
      const response = await fetch("http://127.0.0.1:5000/parse", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Server error: " + response.status);
      }

      const data = await response.json();
      displayResult(data);
      addDownloadButton(data);
    } catch (err) {
      resultDiv.textContent = "Error: " + err.message;
      resultDiv.className = "response-error";
    }
  });

  function addDownloadButton(data) {
    // Remove any previous button
    let oldBtn = document.getElementById("downloadJsonBtn");
    if (oldBtn) oldBtn.remove();

    const btn = document.createElement("button");
    btn.id = "downloadJsonBtn";
    btn.textContent = "Download JSON";
    btn.style.marginTop = "1em";
    btn.onclick = function () {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "parsed_result.json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };
    resultDiv.parentNode.insertBefore(btn, resultDiv.nextSibling);
  }

  function displayResult(data) {
    if (!data || !Array.isArray(data.data)) {
      resultDiv.textContent = "No data found in PDF.";
      resultDiv.className = "response-info";
      return;
    }

    let html = `<h2>Results (Page ${data.page_number})</h2>`;
    html += `<p>Rows parsed: <b>${data.count}</b></p>`;
    html += "<table><thead><tr>";
    html +=
      "<th>Terminal Serial</th><th>Payment Value</th><th>Days Since Last Transaction</th>";
    html += "</tr></thead><tbody>";
    for (const row of data.data) {
      html += `<tr><td>${row["Terminal Serial"]}</td><td>${row["Payment Value"]}</td><td>${row["Days Since Last Transaction"]}</td></tr>`;
    }
    html += "</tbody></table>";
    resultDiv.innerHTML = html;
    resultDiv.className = "response-success";
  }
});
