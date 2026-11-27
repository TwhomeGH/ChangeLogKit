/* 深/淺色主題：在 <head> 同步載入以避免閃爍；切換鈕為 #theme（可選）。 */
(function () {
  var KEY = "theme";
  function preferred() {
    try {
      var t = localStorage.getItem(KEY);
      if (t === "dark" || t === "light") return t;
    } catch (e) {}
    return matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light";
  }
  function apply(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem(KEY, t); } catch (e) {}
    var b = document.getElementById("theme");
    if (b) {
      b.textContent = t === "dark" ? "☀️" : "🌙";
      b.title = t === "dark" ? "切換淺色" : "切換深色";
    }
  }
  apply(preferred());
  window.toggleTheme = function () {
    apply(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  };
  /* 靜態頁尾：<time datetime=UTC> 由瀏覽器換成觀看者本地時間；
     沒有 JS 時仍顯示伺服器產生的 UTC 位移文字。 */
  function localizeTimes(root) {
    var nodes = (root || document).querySelectorAll("time[data-ck-time]");
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      if (node.getAttribute("data-ck-time-fixed") === "1") continue;
      var value = node.getAttribute("datetime");
      var when = new Date(value);
      if (isNaN(when.getTime())) continue;
      try {
        node.textContent = new Intl.DateTimeFormat(undefined, {
          year: "numeric", month: "2-digit", day: "2-digit",
          hour: "2-digit", minute: "2-digit", hour12: false,
        }).format(when);
        node.title = value;
      } catch (_) { /* 保留 fallback 文字 */ }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    localizeTimes(document);
    var b = document.getElementById("theme");
    if (b) { b.onclick = window.toggleTheme; apply(document.documentElement.dataset.theme); }
  });
})();
