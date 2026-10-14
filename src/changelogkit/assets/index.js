/* 變更歷史 GUI：清單／檢視／編輯／新增。深淺色由 theme.js 處理。 */
const $ = (s) => document.querySelector(s);
let sel = null;

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

/* Tab 縮排／Shift-Tab 反縮排（2 空白，與 #raw 的 tab-size 一致）。
   多行選取時逐行縮排；用 execCommand insertText 以保留原生復原（Ctrl+Z）。 */
const INDENT = "  ";
function indentSelection(ta, outdent) {
  const value = ta.value;
  const start = ta.selectionStart, end = ta.selectionEnd;

  if (start === end && !outdent) {              // 游標處：插入縮排
    document.execCommand("insertText", false, INDENT);
    return;
  }

  const lineStart = value.lastIndexOf("\n", start - 1) + 1;
  const nextNl = value.indexOf("\n", end);
  const lineEnd = nextNl === -1 ? value.length : nextNl;
  const block = value.slice(lineStart, lineEnd);
  const changes = [];
  const out = block.split("\n").map((line) => {
    if (outdent) {
      const match = line.match(/^(?:\t| {1,2})/);   // 移除最多一個縮排單位
      const removed = match ? match[0].length : 0;
      changes.push(-removed);
      return line.slice(removed);
    }
    changes.push(INDENT.length);
    return INDENT + line;
  });
  const newBlock = out.join("\n");
  if (newBlock === block) return;               // 無變化（例如反縮排已無縮排）

  // 某位置之前累積的位移（以「已縮排的行」為界；行首不計入該行自身）。
  const shiftAt = (pos) => {
    const count = value.slice(lineStart, pos).split("\n").length - (pos === lineStart || value[pos - 1] === "\n" ? 1 : 0);
    return changes.slice(0, count).reduce((sum, n) => sum + n, 0);
  };

  ta.setSelectionRange(lineStart, lineEnd);
  document.execCommand("insertText", false, newBlock);
  ta.setSelectionRange(Math.max(lineStart, start + shiftAt(start)),
                       Math.max(lineStart, end + shiftAt(end)));
}

async function load() {
  const q = encodeURIComponent($("#q").value), t = encodeURIComponent($("#type").value);
  const r = await fetch("/api/entries?q=" + q + "&type=" + t);
  const items = await r.json();
  $("#list").innerHTML = items.length
    ? items.map((e) => `<div class="item${e.i === sel ? " sel" : ""}" data-i="${e.i}"><div class="d">${e.date ? esc(e.date + (e.time ? " " + e.time : "")) : CK_T("history.no_date")}</div><div class="t">${esc(e.title)}</div></div>`).join("")
    : '<div class="empty">' + CK_T("history.no_match") + "</div>";
  document.querySelectorAll(".item").forEach((el) => (el.onclick = () => show(+el.dataset.i)));
}

function renderView(e) {
  // 內文 markdown 交由共用的 markdown.js 渲染；「相關文件」等相對連結依歷史檔所在目錄改寫。
  const H = window.CK_HISTORY || {};
  const resolve = window.markdownResolver(H.repo, H.path);
  $("#detail").innerHTML =
    '<div class="toolbar"><button id="edit">' + CK_T("btn.edit") + '</button><button id="del">' + CK_T("btn.delete") + "</button></div>" +
    '<div id="content">' + window.renderMarkdown(e.raw, resolve) + "</div>";
  $("#edit").onclick = () => renderEdit(e);
  let armed = false;
  $("#del").onclick = () => {
    if (!armed) {
      armed = true; $("#del").textContent = CK_T("history.confirm_delete"); $("#del").classList.add("danger");
      setTimeout(() => { armed = false; $("#del").textContent = CK_T("btn.delete"); $("#del").classList.remove("danger"); }, 3000);
      return;
    }
    fetch("/api/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ i: e.i }) })
      .then(() => { sel = null; $("#detail").innerHTML = '<div class="empty">' + CK_T("history.deleted") + "</div>"; load(); });
  };
}

function renderEdit(e) {
  $("#detail").innerHTML =
    '<div class="toolbar"><button id="save" class="primary">' + CK_T("btn.save") + '</button><button id="cancel-edit">' + CK_T("btn.cancel") + "</button></div>" +
    '<div class="editor"><pre id="raw-view" aria-hidden="true"></pre>' +
    '<textarea id="raw" spellcheck="false" aria-label="Markdown"></textarea></div>';
  const ta = $("#raw"), view = $("#raw-view");
  ta.value = e.raw;
  // 透明 textarea 疊在「上色後的 <pre>」上：textarea 只負責輸入與游標，
  // 顏色由後方的 HL.markdownLine（無損、只加色）呈現；兩者字體與尺寸一致。
  const sync = () => {
    view.innerHTML = ta.value.split("\n").map((line) => window.HL.markdownLine(line)).join("\n") + "\n";
    ta.style.height = "auto";
    ta.style.height = Math.max(320, ta.scrollHeight + 6) + "px";
    view.scrollTop = ta.scrollTop;
    view.scrollLeft = ta.scrollLeft;
  };
  ta.addEventListener("input", sync);
  ta.addEventListener("scroll", () => { view.scrollTop = ta.scrollTop; view.scrollLeft = ta.scrollLeft; });
  ta.addEventListener("keydown", (ev) => {
    if (ev.key === "Tab") { ev.preventDefault(); indentSelection(ta, ev.shiftKey); return; }
    if ((ev.ctrlKey || ev.metaKey) && ev.key === "s") { ev.preventDefault(); $("#save").click(); }
  });
  sync(); ta.focus();
  $("#cancel-edit").onclick = () => renderView(e);
  $("#save").onclick = async () => {
    await fetch("/api/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ i: e.i, raw: ta.value }) });
    const ne = await (await fetch("/api/entry?i=" + e.i)).json(); ne.i = e.i;
    await load(); renderView(ne);
  };
}

async function show(i) {
  sel = i;
  const e = await (await fetch("/api/entry?i=" + i)).json(); e.i = i;
  document.querySelectorAll(".item").forEach((el) => el.classList.toggle("sel", +el.dataset.i === i));
  renderView(e);
}

$("#q").oninput = () => load();
$("#type").onchange = () => load();
$("#reload").onclick = () => load();

/* 相關文件：可動態新增/移除的 label + url 列。 */
function makeRefRow(label, url) {
  const d = document.createElement("div"); d.className = "ref-row";
  d.innerHTML = '<input class="ref-label" placeholder="' + CK_T("form.ref_label") + '"><input class="ref-url" placeholder="' + CK_T("form.ref_url") + '"><button type="button" class="ref-del" title="' + CK_T("form.ref_remove") + '">✕</button>';
  d.querySelector(".ref-label").value = label || "";
  d.querySelector(".ref-url").value = url || "";
  d.querySelector(".ref-del").onclick = () => d.remove();
  return d;
}
function clearRefs() { const c = $("#refs"); c.innerHTML = ""; c.appendChild(makeRefRow()); }
function collectRefs() {
  return [...$("#refs").querySelectorAll(".ref-row")].map((r) => {
    const label = r.querySelector(".ref-label").value.trim();
    const url = r.querySelector(".ref-url").value.trim();
    if (!url) return label;
    return `[${label || url}](${url})`;
  }).filter(Boolean);
}
$("#add-ref").onclick = () => $("#refs").appendChild(makeRefRow());

$("#add").onclick = async () => {
  const now = new Date(), p = (n) => String(n).padStart(2, "0");
  $("#f-date").value = `${now.getFullYear()}.${p(now.getMonth() + 1)}.${p(now.getDate())}`;
  $("#f-time").value = `${p(now.getHours())}:${p(now.getMinutes())}`;
  ["f-title", "f-file", "f-problem", "f-cause", "f-changes"].forEach((id) => ($("#" + id).value = ""));
  clearRefs();
  const files = await (await fetch("/api/gitdiff")).json();
  $("#gitfiles").innerHTML = files.map((f) => `<option value="${f}">`).join("");
  $("#chips").innerHTML = files.slice(0, 12).map((f) => `<span class="chip">${esc(f)}</span>`).join("");
  document.querySelectorAll(".chip").forEach((c) => (c.onclick = () => ($("#f-file").value = c.textContent)));
  $("#form-err").textContent = ""; $("#modal").hidden = false; $("#f-title").focus();
};
$("#cancel").onclick = () => ($("#modal").hidden = true);
$("#submit").onclick = async () => {
  const title = $("#f-title").value.trim();
  if (!title) { $("#form-err").textContent = CK_T("form.err_title"); $("#f-title").focus(); return; }
  $("#form-err").textContent = "";
  const body = {
    title, date: $("#f-date").value.trim(), time: $("#f-time").value.trim(), type: $("#f-type").value,
    file: $("#f-file").value.trim(),
    problem: $("#f-problem").value.trim(), root_cause: $("#f-cause").value.trim(),
    changes: $("#f-changes").value.split("\n").map((s) => s.replace(/^\s*[-*]\s*/, "").trim()).filter(Boolean),
    refs: collectRefs(),
  };
  await fetch("/api/add", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  $("#modal").hidden = true; await load(); show(0);
};

load();
