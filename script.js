/* ============================================================
   Vyral Labs — TikTok Downloader  |  Frontend Logic
   ============================================================ */

const API = window.location.origin;

// --- DOM refs ---
const urlsInput      = document.getElementById("urls");
const urlCountEl     = document.getElementById("url-count");
const downloadBtn    = document.getElementById("download-btn");
const clearBtn       = document.getElementById("clear-btn");
const errorBanner    = document.getElementById("error-banner");
const errorText      = document.getElementById("error-text");
const errorClose     = document.getElementById("error-close");
const progressSec    = document.getElementById("progress-section");
const progressBar    = document.getElementById("progress-bar");
const progressSumm   = document.getElementById("progress-summary");
const videoList      = document.getElementById("video-list");
const zipSection     = document.getElementById("zip-section");
const zipBtn         = document.getElementById("zip-btn");
const retrySection   = document.getElementById("retry-section");
const retryBtn       = document.getElementById("retry-btn");
const reportSection  = document.getElementById("report-section");
const reportBody     = document.getElementById("report-body");
const copyBtn        = document.getElementById("copy-btn");

let currentJobId = null;
let pollTimer    = null;

// ============================================================
// Helpers
// ============================================================

function parseUrls(text) {
    return text
        .split(/[\n,]+/)
        .map(u => u.trim())
        .filter(u => u.length > 0 && u.includes("tiktok.com"));
}

function truncate(str, max = 65) {
    return str.length > max ? str.slice(0, max) + "\u2026" : str;
}

function showError(msg) {
    errorText.textContent = msg;
    errorBanner.classList.remove("hidden");
}

function hideError() {
    errorBanner.classList.add("hidden");
}

function formatViews(n) {
    if (n == null) return "—";
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
    if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
    return n.toLocaleString();
}

function formatDate(d) {
    if (!d || d.length !== 8) return d || "—";
    return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
}

// Status icons
const STATUS_ICON = {
    pending:     `<span style="color:var(--text-dim)">&#9679;</span>`,       // grey dot
    downloading: `<span style="color:var(--accent)">&#11015;</span>`,        // down arrow
    done:        `<span style="color:var(--success)">&#10003;</span>`,       // checkmark
    failed:      `<span style="color:var(--error)">&#10007;</span>`,         // cross
};

// ============================================================
// URL counter
// ============================================================

urlsInput.addEventListener("input", () => {
    const n = parseUrls(urlsInput.value).length;
    urlCountEl.textContent = `${n} URL${n !== 1 ? "s" : ""}`;
});

// ============================================================
// Clear button
// ============================================================

clearBtn.addEventListener("click", () => {
    urlsInput.value = "";
    urlCountEl.textContent = "0 URLs";
    urlsInput.focus();
});

// ============================================================
// Error close
// ============================================================

errorClose.addEventListener("click", hideError);

// ============================================================
// Start download
// ============================================================

downloadBtn.addEventListener("click", async () => {
    hideError();

    const urls = parseUrls(urlsInput.value);

    if (urls.length === 0) {
        showError("Paste at least one TikTok URL to get started.");
        return;
    }

    // Disable button and show loading state
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = `
        <svg class="spin" width="18" height="18" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        Starting\u2026`;

    try {
        const res = await fetch(`${API}/api/download`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ urls }),
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || "Server error");
        }

        currentJobId = data.job_id;

        // Show progress section, hide zip/retry/report
        progressSec.classList.remove("hidden");
        zipSection.classList.add("hidden");
        retrySection.classList.add("hidden");
        reportSection.classList.add("hidden");
        reportBody.innerHTML = "";

        startPolling();

    } catch (err) {
        showError(err.message);
        resetButton();
    }
});

// ============================================================
// Polling
// ============================================================

function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    checkStatus();                         // fire immediately
    pollTimer = setInterval(checkStatus, 2000);
}

async function checkStatus() {
    if (!currentJobId) return;

    try {
        const res  = await fetch(`${API}/api/status/${currentJobId}`);
        const data = await res.json();

        if (!res.ok) throw new Error(data.error || "Polling failed");

        renderProgress(data);

        if (data.status === "completed") {
            clearInterval(pollTimer);
            pollTimer = null;
            resetButton();

            if (data.zip_ready) {
                zipSection.classList.remove("hidden");
            }

            // Show retry if any failed
            const failed = data.videos.filter(v => v.status === "failed");
            if (failed.length > 0) {
                retrySection.classList.remove("hidden");
            }

            // Render report table for successful downloads
            const done = data.videos.filter(v => v.status === "done");
            if (done.length > 0) {
                renderReport(done);
            }
        }
    } catch (err) {
        console.error("Poll error:", err);
    }
}

// ============================================================
// Render progress
// ============================================================

function renderProgress(data) {
    const total    = data.videos.length;
    const done     = data.videos.filter(v => v.status === "done").length;
    const failed   = data.videos.filter(v => v.status === "failed").length;
    const finished = done + failed;

    // Summary text
    let summary = `${done}/${total} complete`;
    if (failed > 0) summary += ` \u00b7 ${failed} failed`;
    progressSumm.textContent = summary;

    // Progress bar
    const pct = total > 0 ? Math.round((finished / total) * 100) : 0;
    progressBar.style.width = `${pct}%`;

    // Change bar colour if everything failed
    if (finished === total && done === 0) {
        progressBar.style.background = "var(--error)";
    } else {
        progressBar.style.background = "var(--accent)";
    }

    // Video items
    videoList.innerHTML = data.videos.map((v) => {
        const icon     = STATUS_ICON[v.status] || STATUS_ICON.pending;
        const username = v.username ? `<span class="video-username">@${v.username}</span>` : "";
        const error    = v.error   ? `<span class="error-msg">${v.error}</span>` : "";

        return `
            <div class="video-item ${v.status}">
                <span class="status-icon">${icon}</span>
                <div class="video-info">
                    <span class="video-url">${truncate(v.url)}</span>
                    ${username}
                    ${error}
                </div>
            </div>`;
    }).join("");
}

// ============================================================
// Report table
// ============================================================

function renderReport(videos) {
    reportBody.innerHTML = videos.map(v => {
        const username = v.username ? `@${v.username}` : "—";
        const caption  = v.caption  || "—";
        const views    = formatViews(v.views);
        const date     = formatDate(v.upload_date);
        return `
            <tr>
                <td class="col-username">${username}</td>
                <td class="col-caption">${caption}</td>
                <td class="col-url"><a href="${v.url}" target="_blank" rel="noopener">${truncate(v.url, 45)}</a></td>
                <td class="col-views">${views}</td>
                <td class="col-date">${date}</td>
            </tr>`;
    }).join("");

    reportSection.classList.remove("hidden");
}

copyBtn.addEventListener("click", () => {
    const rows = [["Username", "Caption", "URL", "Views", "Date"]];
    reportBody.querySelectorAll("tr").forEach(tr => {
        const cells = tr.querySelectorAll("td");
        // For URL cell, get the href rather than truncated display text
        const url = cells[2]?.querySelector("a")?.href || cells[2]?.textContent || "";
        rows.push([
            cells[0]?.textContent || "",
            cells[1]?.textContent || "",
            url,
            cells[3]?.textContent || "",
            cells[4]?.textContent || "",
        ]);
    });
    const tsv = rows.map(r => r.join("\t")).join("\n");
    navigator.clipboard.writeText(tsv).then(() => {
        const orig = copyBtn.innerHTML;
        copyBtn.textContent = "Copied!";
        setTimeout(() => { copyBtn.innerHTML = orig; }, 2000);
    });
});

// ============================================================
// Download ZIP
// ============================================================

zipBtn.addEventListener("click", () => {
    if (currentJobId) {
        window.location.href = `${API}/api/download-zip/${currentJobId}`;
    }
});

// ============================================================
// Retry failed
// ============================================================

retryBtn.addEventListener("click", () => {
    // Grab failed URLs from the current progress display
    const failedUrls = [];
    document.querySelectorAll(".video-item.failed .video-url").forEach(el => {
        // The URL might be truncated in display, so we read from the data
        failedUrls.push(el.textContent.replace("\u2026", ""));
    });

    // Actually, get them from last poll data — safer approach:
    // Re-fetch status to get full URLs
    fetch(`${API}/api/status/${currentJobId}`)
        .then(r => r.json())
        .then(data => {
            const urls = data.videos
                .filter(v => v.status === "failed")
                .map(v => v.url);

            if (urls.length > 0) {
                urlsInput.value = urls.join("\n");
                urlCountEl.textContent = `${urls.length} URL${urls.length !== 1 ? "s" : ""}`;
                progressSec.classList.add("hidden");
                urlsInput.focus();
            }
        });
});

// ============================================================
// Reset button state
// ============================================================

function resetButton() {
    downloadBtn.disabled = false;
    downloadBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        Download All`;
}

// ============================================================
// Spinner animation (CSS injected via JS so no extra file)
// ============================================================

const style = document.createElement("style");
style.textContent = `
    @keyframes spin { to { transform: rotate(360deg); } }
    .spin { animation: spin 0.8s linear infinite; }
`;
document.head.appendChild(style);
