// VideoFix platform-download UI language helper.
// The active page currently embeds this logic in templates/index.html.
const videoFixTranslations = {
  ar: { title: "تنزيل الفيديوهات<br>بسهولة.", description: "حمّل الفيديوهات من TikTok وInstagram وFacebook وYouTube عبر الرابط مباشرة.", section: "تنزيل الفيديوهات", choose: "اختر المنصة", chooseText: "اختر المنصة ثم ألصق رابط الفيديو لبدء التنزيل.", footer: "VideoFix · تنزيل الفيديوهات من المنصات المدعومة." },
  en: { title: "Download videos<br>with ease.", description: "Download videos from TikTok, Instagram, Facebook and YouTube using a link.", section: "Video downloads", choose: "Choose a platform", chooseText: "Select a platform, then paste the video link to start downloading.", footer: "VideoFix · Video downloads from supported platforms." }
};

function applyVideoFixLanguage(lang) {
  const t = videoFixTranslations[lang];
  if (!t) return;
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.querySelector(".hero h1").innerHTML = t.title;
  document.querySelector(".hero p").textContent = t.description;
  document.querySelector(".card-title").textContent = t.section;
  document.querySelector(".download-tool b").textContent = t.choose;
  document.querySelector(".download-tool span").textContent = t.chooseText;
  document.querySelector(".footer").textContent = t.footer;
}
