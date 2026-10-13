/* 變更歷史 GUI：清單／檢視／編輯／新增。深淺色由 theme.js 處理。 */
const $ = (s) => document.querySelector(s);
let sel = null;

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
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
    '<textarea id="raw" spellcheck="false"></textarea>';
  const ta = $("#raw"); ta.value = e.raw;
  const autosize = () => { ta.style.height = "auto"; ta.style.height = Math.max(320, ta.scrollHeight + 6) + "px"; };
  ta.addEventListener("input", autosize); autosize(); ta.focus();
  ta.addEventListener("keydown", (ev) => { if ((ev.ctrlKey || ev.metaKey) && ev.key === "s") { ev.preventDefault(); $("#save").click(); } });
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
