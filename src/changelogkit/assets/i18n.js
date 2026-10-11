/* 前端 i18n：字串由 server／export 注入的 window.CK_I18N 提供。
   CK_T(key, ...args)：查表；找不到回 key 本身；帶 {n}／{0} 佔位時做簡單替換。 */
window.CK_T = function (key, ...args) {
  const dict = window.CK_I18N || {};
  let text = dict[key] !== undefined ? dict[key] : key;
  args.forEach((value, index) => {
    text = text.replace(new RegExp("\\{" + index + "\\}", "g"), value);
  });
  return text;
};
