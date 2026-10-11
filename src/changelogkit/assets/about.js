/* 關於頁：向 /api/buildinfo 取版本與來源 commit（commit 連到 GitHub）。 */
const REPO = "https://github.com/TwhomeGH/ChangeLogKit";

fetch("/api/buildinfo")
  .then((r) => r.json())
  .then((b) => {
    document.getElementById("version").textContent = b.version || CK_T("about.na");
    /* UI 語系清單，* 標示目前生效者。 */
    document.getElementById("locales").textContent =
      (b.locales || []).map((l) => l + (l === b.locale ? " *" : "")).join("   ");
    const raw = b.commit || "";
    if (!raw) {
      document.getElementById("commit").textContent = CK_T("about.unknown");
      return;
    }
    const hash = raw.replace(/\+dirty$/, "");
    document.getElementById("commit").innerHTML =
      '<a href="' + REPO + "/commit/" + hash + '"><code>' + raw + "</code></a>";
  })
  .catch(() => {
    document.getElementById("version").textContent = CK_T("about.load_failed");
  });
