/* 開發索引：功能／API 宣告／文件／近期改動。資料來自 /development/data。 */
const $ = (s) => document.querySelector(s);
let data = null, tab = "features", lang = "", kind = "";

const LABELS = {
  features: "tab.features",
  symbols: "tab.symbols",
  documents: "tab.documents",
  repos: "tab.repos",
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

/* 行內 markdown（用於註釋、摘要）：跳脫後套用 code/bold/link。 */
function mdInline(s) {
  s = esc(s);
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return s;
}

/* 把相鄰 /// 註釋字串轉成簡單段落／條列。 */
function mdDoc(text) {
  if (!text) return "";
  const lines = text.split("\n");
  let out = "", list = [];
  const flush = () => { if (list.length) { out += "<ul>" + list.map((x) => "<li>" + mdInline(x) + "</li>").join("") + "</ul>"; list = []; } };
  for (const l of lines) {
    const m = l.match(/^\s*[-*]\s+(.*)$/);
    if (m) { list.push(m[1]); continue; }
    flush();
    if (l.trim()) out += "<p>" + mdInline(l) + "</p>";
  }
  flush();
  return out;
}

function kindOf(name) {
  const m = name.match(/\b(func|struct|class|enum|protocol|actor)\b/);
  return m ? m[1] : "decl";
}

function links(items) {
  return items.map((p) => `<a href="/development/file?repo=app&path=${encodeURIComponent(p)}">${esc(p)}</a>`).join("");
}

/* ── 近期改動：提交卡片與 lazy 差異 ── */

function commitCard(repo, c) {
  const files = (c.files || []).map((f) =>
    `<a class="cfile" href="#" data-repo="${esc(repo)}" data-hash="${esc(c.hash)}" data-path="${esc(f)}">${esc(f)}</a>`
  ).join("");
  const when = (c.date || "").slice(0, 16).replace("T", " ");
  return `<div class="commit" data-repo="${esc(repo)}" data-hash="${esc(c.hash)}">` +
    `<button class="commit-head" type="button"><span class="commit-top"><code class="hash">${esc(c.hash)}</code>` +
    `<span class="when">${esc(when)}</span></span>` +
    `<span class="subject">${esc(c.subject)}</span></button>` +
    `<div class="commit-files">${files || `<span class="muted">${CK_T("dev.no_files")}</span>`}</div>` +
    `<div class="diff" hidden></div></div>`;
}

function diffLineClass(l) {
  if (l.startsWith("@@")) return "d-hunk";
  if (l.startsWith("+++") || l.startsWith("---") || l.startsWith("diff --git")) return "d-file";
  if (l.startsWith("+")) return "d-add";
  if (l.startsWith("-")) return "d-del";
  if (/^(index |new file|deleted file|similarity|rename |old mode|new mode|Binary files)/.test(l) ||
      l.startsWith("\\ No newline")) return "d-meta";
  if (l.startsWith(" ")) return "d-ctx";
  return "d-plain";
}

function renderDiff(j) {
  if (j.empty) return '<p class="muted">' + CK_T("dev.diff_empty") + "</p>";
  const hl = window.HL;
  const swift = hl ? hl.swift : (t) => esc(t);
  const esc2 = hl ? hl.esc : esc;
  const state = { block: false };
  const body = j.diff.split("\n").map((l) => {
    const cls = diffLineClass(l);
    if (cls === "d-file") state.block = false;
    if (cls === "d-add" || cls === "d-del" || cls === "d-ctx") {
      const mark = l[0] || " ";
      return `<span class="dline ${cls}"><span class="dmark">${esc2(mark)}</span>${swift(l.slice(1), state)}</span>`;
    }
    return `<span class="dline ${cls}"><span class="dmark"> </span>${esc2(l)}</span>`;
  }).join("");
  return '<pre class="dpre">' + body + "</pre>" +
    (j.truncated ? '<p class="muted">' + CK_T("dev.diff_truncated") + "</p>" : "");
}

const diffCache = new Map();
async function loadDiff(box, params) {
  const qs = params.toString();
  if (diffCache.has(qs)) { box.innerHTML = diffCache.get(qs); box.hidden = false; return; }
  box.hidden = false;
  box.innerHTML = '<p class="muted">' + CK_T("dev.diff_loading") + "</p>";
  try {
    const res = await fetch("/development/diff?" + qs);
    const j = await res.json();
    if (!res.ok) throw Error(j.error || res.statusText);
    const html = renderDiff(j);
    diffCache.set(qs, html);
    box.innerHTML = html;
  } catch (e) {
    box.innerHTML = '<p class="empty">' + CK_T("dev.load_failed") + esc(e.message) + "</p>";
  }
}

/* 「API 宣告」頁的篩選列：支援語言 + 語言 chips + 種類下拉。 */
function renderFilters() {
  const box = $("#filters");
  if (tab !== "symbols") { box.hidden = true; box.innerHTML = ""; return; }
  box.hidden = false;
  const symbols = data.symbols || [];
  const langs = [...new Set(symbols.map((s) => s.lang).filter(Boolean))];
  const kinds = [...new Set(symbols.map((s) => s.kind).filter(Boolean))].sort();
  const chip = (value, label) =>
    `<button class="chip${value === lang ? " on" : ""}" data-lang="${esc(value)}">${esc(label)}</button>`;
  box.innerHTML =
    `<div class="supported">${CK_T("filter.supported")}${esc((data.languages || []).join("、"))}</div>` +
    `<div class="chips">${chip("", CK_T("filter.all_langs"))}${langs.map((l) => chip(l, l)).join("")}</div>` +
    `<label class="kindfilter">${CK_T("filter.kind")} <select id="kindsel"><option value="">${CK_T("filter.all")}</option>` +
    kinds.map((k) => `<option value="${esc(k)}"${k === kind ? " selected" : ""}>${esc(k)}</option>`).join("") +
    `</select></label>`;
}

function render() {
  if (!data) return;
  document.querySelectorAll("#tabs button").forEach((b) =>
    b.setAttribute("aria-pressed", b.dataset.key === tab));
  renderFilters();
  const q = $("#search").value.toLowerCase();
  const repo = $("#repo").value;
  const match = (r) => JSON.stringify(r).toLowerCase().includes(q) &&
    (!repo || r.repo === repo || (r.id && tab === "features")) &&
    (tab !== "symbols" || ((!lang || r.lang === lang) && (!kind || r.kind === kind)));

  const rows = (data[tab] || []).filter(match);
  const suffix = tab === "symbols" ? CK_T("dev.filter_hint") : "";
  $("#message").textContent = CK_T("dev.result", rows.length) + suffix;

  let out = "";
  if (tab === "repos") {
    const deps = (data.lockedPackages || []).map((p) =>
      `<code>${esc(p.identity)}</code><code>${esc((p.revision || "").slice(0, 12))}</code>`).join("");
    out += '<article class="card"><h2>' + CK_T("dev.locked") + '</h2><div class="deps">' + (deps || "<code>（無）</code><code></code>") + "</div>" +
      '<p class=muted>' + CK_T("dev.locked_note") + "</p></article>";
  }
  for (const r of rows.slice(0, 250)) {
    if (tab === "features") {
      out += `<article class="card"><h2>${esc(r.name)}</h2><div class="meta">${esc(r.id)}</div>` +
        `<p>${mdInline(r.summary)}</p><dl>` +
        [["ReplayKit", r.replaykit], ["ScreenCaptureKit", r.screencapturekit], [CK_T("dev.ui_entry"), r.ui], [CK_T("dev.verification"), r.verification]]
          .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("") +
        `</dl><h3>${CK_T("dev.files")}</h3><div class="files">${links(r.files)}${links(r.docs)}</div></article>`;
    } else if (tab === "symbols") {
      out += `<article class="card"><h2><a href="${esc(r.url)}">${esc(r.name)}</a></h2>` +
        `<div class="meta"><span class="kind">${esc(r.kind || kindOf(r.name))}</span>${esc(r.repo)} · ${esc(r.file)}:${r.line}</div>` +
        (r.signature ? `<pre class="sig">${esc(r.signature)}</pre>` : "") +
        `<div class="doc">${r.comment ? mdDoc(r.comment) : '<p class="muted">' + CK_T("dev.no_comment") + '</p>'}</div></article>`;
    } else if (tab === "documents") {
      out += `<article class="card"><h2><a href="${esc(r.url)}">${esc(r.name)}</a></h2>` +
        `<div class="meta">${esc(r.repo)}</div><div class="preview">${esc(r.text.slice(0, 260))}${r.text.length > 260 ? " …" : ""}</div></article>`;
    } else {
      const list = (r.commits || []).map((c) => commitCard(r.name, c)).join("");
      out += `<article class="card"><h2>${esc(r.name)}</h2><div class="meta">HEAD：${esc(r.head)}</div>` +
        `<h3>${CK_T("dev.uncommitted")}</h3><pre class="blob">${esc(r.changes || CK_T("dev.clean"))}</pre>` +
        `<div class="wt-wrap"><button class="wt-btn" type="button" data-repo="${esc(r.name)}">${CK_T("dev.worktree")}</button>` +
        `<div class="diff" hidden></div></div>` +
        `<h3>${CK_T("dev.commits20")}</h3><div class="commits">${list}</div></article>`;
    }
  }
  if (rows.length > 250) out += '<p class="muted">' + CK_T("dev.more") + "</p>";
  $("#results").innerHTML = out || '<p class="empty">' + CK_T("dev.no_data") + "</p>";
}

async function load() {
  $("#message").textContent = CK_T("dev.loading");
  diffCache.clear();
  try {
    const response = await fetch("/development/data");
    const result = await response.json();
    if (!response.ok) throw Error(result.error);
    data = result;
    const repos = [...new Set((data.symbols.concat(data.documents)).map((r) => r.repo))].sort();
    const sel = $("#repo");
    sel.innerHTML = '<option value="">' + CK_T("dev.repo_all") + '</option>' +
      repos.map((r) => `<option value="${esc(r)}">${esc(r)}</option>`).join("");
    render();
  } catch (e) {
    $("#message").textContent = CK_T("dev.load_failed") + e.message;
  }
}

for (const [key, title] of Object.entries(LABELS)) {
  const b = document.createElement("button");
  b.textContent = CK_T(title); b.dataset.key = key;
  b.onclick = () => { tab = key; render(); };
  $("#tabs").append(b);
}
$("#search").oninput = render;
$("#repo").onchange = render;
$("#reload").onclick = load;

$("#filters").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) { lang = chip.dataset.lang; render(); }
});
$("#filters").addEventListener("change", (e) => {
  if (e.target.id === "kindsel") { kind = e.target.value; render(); }
});

/* 事件委派：提交標題、檔名、工作區差異鈕（#results 每次 render 會重建）。 */
$("#results").addEventListener("click", (e) => {
  const file = e.target.closest("a.cfile");
  if (file) {
    e.preventDefault();
    loadDiff(file.closest(".commit").querySelector(".diff"),
      new URLSearchParams({ repo: file.dataset.repo, hash: file.dataset.hash, path: file.dataset.path }));
    return;
  }
  const head = e.target.closest(".commit-head");
  if (head) {
    const box = head.parentElement.querySelector(".diff");
    if (!box.hidden && box.innerHTML) { box.hidden = true; return; }
    loadDiff(box, new URLSearchParams({ repo: head.parentElement.dataset.repo, hash: head.parentElement.dataset.hash }));
    return;
  }
  const wt = e.target.closest(".wt-btn");
  if (wt) loadDiff(wt.parentElement.querySelector(".diff"), new URLSearchParams({ repo: wt.dataset.repo, worktree: "1" }));
});

load();
