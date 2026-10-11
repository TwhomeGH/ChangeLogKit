/* 開發索引：功能／API 宣告／文件／近期改動。資料來自 /development/data。 */
const $ = (s) => document.querySelector(s);
let data = null, tab = "features", lang = "", kind = "", group = "file";
let rows = [], shown = 0, lastGroup = null;   /* 目前篩選結果與已渲染進度（lazy） */
const CHUNK = 80;                              /* 每次追加渲染的筆數 */
const STORE = "changelogkit.devstate";         /* localStorage：記住分頁／篩選／分組 */

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

function kindOf(name) {
  const m = name.match(/\b(func|struct|class|enum|protocol|actor)\b/);
  return m ? m[1] : "decl";
}

function links(items) {
  return items.map((p) => `<a href="/development/file?repo=app&path=${encodeURIComponent(p)}">${esc(p)}</a>`).join("");
}

/* ── 記住上次瀏覽狀態（分頁／語言／種類／分組） ── */

function saveState() {
  try { localStorage.setItem(STORE, JSON.stringify({ tab, lang, kind, group })); } catch (e) { /* 私密模式等 */ }
}

function loadState() {
  try {
    const s = JSON.parse(localStorage.getItem(STORE) || "{}");
    if (LABELS[s.tab]) tab = s.tab;
    if (typeof s.lang === "string") lang = s.lang;
    if (typeof s.kind === "string") kind = s.kind;
    if (s.group === "file" || s.group === "none") group = s.group;
  } catch (e) { /* 壞資料就忽略 */ }
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

/* 「API 宣告」頁的篩選列：支援語言 + 語言 chips + 種類下拉 + 分組下拉。 */
function renderFilters() {
  const box = $("#filters");
  if (tab !== "symbols") { box.hidden = true; box.innerHTML = ""; return; }
  box.hidden = false;
  const symbols = data.symbols || [];
  const langs = [...new Set(symbols.map((s) => s.lang).filter(Boolean))];
  const kinds = [...new Set(symbols.map((s) => s.kind).filter(Boolean))].sort();
  const chip = (value, label) =>
    `<button class="chip${value === lang ? " on" : ""}" data-lang="${esc(value)}">${esc(label)}</button>`;
  const opt = (v, label) => `<option value="${esc(v)}"${v === group ? " selected" : ""}>${esc(label)}</option>`;
  box.innerHTML =
    `<div class="supported">${CK_T("filter.supported")}${esc((data.languages || []).join("、"))}</div>` +
    `<div class="frow"><div class="chips">${chip("", CK_T("filter.all_langs"))}${langs.map((l) => chip(l, l)).join("")}</div>` +
    `<label class="kindfilter">${CK_T("filter.kind")} <select id="kindsel"><option value="">${CK_T("filter.all")}</option>` +
    kinds.map((k) => `<option value="${esc(k)}"${k === kind ? " selected" : ""}>${esc(k)}</option>`).join("") +
    `</select></label>` +
    `<label class="groupfilter">${CK_T("filter.group")} <select id="groupsel">` +
    opt("file", CK_T("filter.by_file")) + opt("none", CK_T("filter.no_group")) +
    `</select></label></div>`;
}

/* 符號卡片：型別若有 members，收進可展開的「成員」區塊；成員卡片縮排呈現。 */
function symbolCard(r, nested) {
  const head = `<h2><a href="${esc(r.url)}">${esc(r.name)}</a></h2>` +
    `<div class="meta"><span class="kind">${esc(r.kind || kindOf(r.name))}</span>` +
    `${esc(r.repo)} · ${esc(r.file)}:${r.line}</div>` +
    (r.signature ? `<pre class="sig">${esc(r.signature)}</pre>` : "") +
    `<div class="doc rendered">${r.comment ? window.renderMarkdown(r.comment) : '<p class="muted">' + CK_T("dev.no_comment") + '</p>'}</div>`;
  const members = r.members || [];
  const memberHtml = members.length
    ? `<details class="members"><summary>${CK_T("dev.members")} (${members.length})</summary>` +
      members.map((m) => symbolCard(m, true)).join("") + "</details>" : "";
  return `<article class="card${nested ? " member" : ""}">${head}${memberHtml}</article>`;
}

/* 單一資料列的 HTML（依分頁型別）。 */
function rowHtml(r) {
  if (tab === "features") {
    /* 通用渲染：保留鍵以外的所有欄位逐列列出；標籤可用該筆的 labels 對照，預設用 key。 */
    const reserved = new Set(["id", "name", "summary", "files", "docs", "labels"]);
    const labels = r.labels || {};
    const fields = Object.keys(r).filter((k) => !reserved.has(k))
      .map((k) => [labels[k] || k, Array.isArray(r[k]) ? r[k].join("、") : r[k]])
      .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
    return `<article class="card"><h2>${esc(r.name)}</h2><div class="meta">${esc(r.id)}</div>` +
      (r.summary ? `<p>${mdInline(r.summary)}</p>` : "") +
      (fields ? `<dl>${fields}</dl>` : "") +
      `<h3>${CK_T("dev.files")}</h3><div class="files">${links(r.files)}${links(r.docs)}</div></article>`;
  }
  if (tab === "symbols") return symbolCard(r);
  if (tab === "documents") {
    return `<article class="card"><h2><a href="${esc(r.url)}">${esc(r.name)}</a></h2>` +
      `<div class="meta">${esc(r.repo)}</div><div class="preview">${esc(r.text.slice(0, 260))}${r.text.length > 260 ? " …" : ""}</div></article>`;
  }
  const list = (r.commits || []).map((c) => commitCard(r.name, c)).join("");
  return `<article class="card"><h2>${esc(r.name)}</h2><div class="meta">HEAD：${esc(r.head)}</div>` +
    `<h3>${CK_T("dev.uncommitted")}</h3><pre class="blob">${esc(r.changes || CK_T("dev.clean"))}</pre>` +
    `<div class="wt-wrap"><button class="wt-btn" type="button" data-repo="${esc(r.name)}">${CK_T("dev.worktree")}</button>` +
    `<div class="diff" hidden></div></div>` +
    `<h3>${CK_T("dev.commits20")}</h3><div class="commits">${list}</div></article>`;
}

/* 「近期改動／版本」頁開頭的鎖定套件卡片。 */
function lockedHtml() {
  const deps = (data.lockedPackages || []).map((p) =>
    `<code>${esc(p.identity)}</code><code>${esc((p.revision || "").slice(0, 12))}</code>`).join("");
  return '<article class="card"><h2>' + CK_T("dev.locked") + '</h2><div class="deps">' + (deps || "<code>（無）</code><code></code>") + "</div>" +
    '<p class=muted>' + CK_T("dev.locked_note") + "</p></article>";
}

/* 量測頂部固定列的高度，寫入 CSS 變數（appbar 會換行，高度不固定，別寫死）。 */
function measureBars() {
  const s = document.documentElement.style;
  const appbar = document.querySelector(".appbar");
  const tabs = document.getElementById("tabs");
  const filters = document.getElementById("filters");
  if (appbar) s.setProperty("--appbar-h", appbar.offsetHeight + "px");
  if (tabs) s.setProperty("--tabs-h", tabs.offsetHeight + "px");
  if (filters && !filters.hidden) s.setProperty("--filters-h", filters.offsetHeight + "px");
}

function render() {
  if (!data) return;
  document.querySelectorAll("#tabs button").forEach((b) =>
    b.setAttribute("aria-pressed", b.dataset.key === tab));
  renderFilters();
  saveState();
  measureBars();
  const q = $("#search").value.toLowerCase();
  const repo = $("#repo").value;
  const match = (r) => JSON.stringify(r).toLowerCase().includes(q) &&
    (!repo || r.repo === repo || (r.id && tab === "features")) &&
    (tab !== "symbols" || ((!lang || r.lang === lang) && (!kind || r.kind === kind || (r.members || []).some((m) => m.kind === kind))));

  rows = (data[tab] || []).filter(match);
  shown = 0;
  lastGroup = null;
  const box = $("#results");
  box.innerHTML = "";
  if (!rows.length) { box.innerHTML = '<p class="empty">' + CK_T("dev.no_data") + "</p>"; updateStatus(); return; }
  if (tab === "repos") box.insertAdjacentHTML("beforeend", lockedHtml());
  appendChunk();   /* 先渲染第一批，其餘捲到底再追加 */
}

/* 追加下一批（lazy）；symbols＋依檔案分組時，於檔案切換處插入 sticky 小標題。 */
function appendChunk() {
  const slice = rows.slice(shown, shown + CHUNK);
  let out = "";
  for (const r of slice) {
    if (tab === "symbols" && group === "file" && r.file !== lastGroup) {
      lastGroup = r.file;
      out += `<h3 class="group">${esc(r.file)}</h3>`;
    }
    out += rowHtml(r);
  }
  if (out) $("#results").insertAdjacentHTML("beforeend", out);
  shown += slice.length;
  updateStatus();
}

/* 更新結果訊息與「回到頂端」鈕的可見度。 */
function updateStatus() {
  const suffix = tab === "symbols" ? CK_T("dev.filter_hint") : "";
  const more = shown < rows.length ? "　" + CK_T("dev.showing", shown, rows.length) : "";
  $("#message").textContent = CK_T("dev.result", rows.length) + suffix + more;
  const el = $("#totop");
  if (el) el.hidden = window.scrollY < 400;
}

window.addEventListener("scroll", () => {
  updateStatus();
  if (shown < rows.length &&
      window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 700) {
    appendChunk();
  }
});

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

/* ── 初始化 ── */

loadState();
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
  if (e.target.id === "groupsel") { group = e.target.value; render(); }
});

const totop = $("#totop");
if (totop) totop.onclick = () => window.scrollTo({ top: 0, behavior: "smooth" });
window.addEventListener("resize", measureBars);

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
