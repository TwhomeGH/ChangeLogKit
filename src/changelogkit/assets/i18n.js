/* 前端 i18n：可依瀏覽器偏好從多語系中選擇，並支援執行期切換。
 *
 * 資料來源（由 server／export 注入）：
 *   window.CK_LOCALES = { "<locale>": { "<key>": "<text>", ... }, ... }  全部語系
 *   window.CK_LOCALE  = "<locale>"                                       預設／後端語系
 * 相容舊版：只有 window.CK_I18N（單一語系字典）時仍可運作。
 *
 * 對外：
 *   CK_T(key, ...args)   查表取字串（找不到回 key；支援 {0}／{1} 佔位）
 *   CK_setLocale(name)   切換語系（存入 localStorage）並重新套用
 *   CK_getLocale()       目前語系
 *   CK_applyI18n()       依 data-i18n／data-i18n-title／data-i18n-aria 重新套用
 */
(function () {
  const STORE = "ck-locale";
  const locales = window.CK_LOCALES || {};
  const names = Object.keys(locales);
  const fallback = window.CK_LOCALE && locales[window.CK_LOCALE]
    ? window.CK_LOCALE : (names[0] || "en");

  /* 把瀏覽器語言標籤對到我們支援的語系（只比對主要子標籤）。 */
  function match(tag) {
    if (!tag) return null;
    const low = tag.toLowerCase();
    if (low.startsWith("zh")) return names.find((n) => n.toLowerCase().startsWith("zh")) || null;
    const main = low.split("-")[0];
    return names.find((n) => n.toLowerCase().split("-")[0] === main) || null;
  }

  function pick() {
    let saved = null;
    try { saved = localStorage.getItem(STORE); } catch (e) {}
    if (saved && locales[saved]) return saved;
    for (const tag of navigator.languages || [navigator.language]) {
      const hit = match(tag);
      if (hit) return hit;
    }
    return fallback;
  }

  let active = pick();

  function dict(name) {
    return locales[name] || (name === fallback && window.CK_I18N ? window.CK_I18N : {}) || {};
  }

  window.CK_T = function (key, ...args) {
    let text = dict(active)[key];
    if (text === undefined) text = dict(fallback)[key];
    if (text === undefined) text = key;
    args.forEach((value, index) => {
      text = text.replace(new RegExp("\\{" + index + "\\}", "g"), value);
    });
    return text;
  };

  window.CK_getLocale = function () { return active; };

  window.CK_setLocale = function (name) {
    if (!name || (!locales[name] && name !== fallback)) return;
    active = name;
    try { localStorage.setItem(STORE, name); } catch (e) {}
    apply();
    /* 僅在「使用者主動切換」時通知（初始載入不通知，避免無限重載）。 */
    document.dispatchEvent(new CustomEvent("ck-locale-change", { detail: { locale: active } }));
  };

  function label(name) {
    return name.toLowerCase().startsWith("zh") ? "中" : name.split("-")[0].toUpperCase();
  }

  function apply() {
    document.documentElement.lang = active.toLowerCase().startsWith("zh") ? "zh-Hant" : active;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = window.CK_T(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      el.title = window.CK_T(el.getAttribute("data-i18n-title"));
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      el.setAttribute("aria-label", window.CK_T(el.getAttribute("data-i18n-aria")));
    });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
      el.placeholder = window.CK_T(el.getAttribute("data-i18n-ph"));
    });
    const btn = document.getElementById("locale");
    if (btn) { btn.textContent = "🌐 " + label(active); btn.title = names.join(" / "); }
  }

  window.CK_applyI18n = apply;

  /* 切換鈕：點一下循環到下一個語系。 */
  document.addEventListener("click", (event) => {
    if (event.target && event.target.id === "locale" && names.length > 1) {
      window.CK_setLocale(names[(names.indexOf(active) + 1) % names.length]);
    }
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply);
  else apply();
})();
