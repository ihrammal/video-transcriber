# Accessible Media Transcriber 1.3.1

## English — 1.3.1

- Maintenance release: Settings no longer puts keyboard focus on unnamed scroll groups. Each page has a translated name and clearer keyboard instructions. The startup checkbox explicitly says it checks for updates in both languages.

- Renamed the app to reflect audio and video transcription. Existing profile and executable names remain compatible with previous installations.
- Audio and video selection share English and Arabic terminology. Audio can be exported as text/subtitles or rendered as a captioned video with a plain background.
- Accessibility options live in Preferences; Ctrl+Shift+A opens that page directly without a duplicate menu.
- Express installation uses the default folder, Start menu shortcut and Base model. Custom installation offers a destination, optional Start menu/desktop shortcuts, and Tiny, Base, Small or API-only setup.
- Preferences offer offline model selection and cloud provider/model selection with API keys.
- Help → Report a Problem now offers email to iman.rammal@gmail.com, copying the address, and GitHub reporting. Email opens a draft for the user to review and send.
- Welcome and farewell panels close within three seconds and have saved opt-out checkboxes, both in the panels and in Preferences. Their delayed focus helper respects a user interacting with the checkbox.
- Clean exits skip the extra confirmation; unsaved transcripts and active tasks still require confirmation.
- Added batch transcription, transcript recovery, and adjustable interface text size.
- Automated regression checks and local recording trials cover transcription and captioned-video rendering. Comparison reports also cover Whisper Small and Qwen3-ASR 0.6B. These are exploratory results without human reference transcripts, not an accuracy benchmark; retain Whisper as the offline default.
- Screen-reader verification status and remaining manual checks are recorded in ACCESSIBILITY_REVIEW.md.

## العربية — 1.3.1

- إصدار إصلاحات: لم يعد التنقل بلوحة المفاتيح يتوقف على مجموعات تمرير غير مسماة في التفضيلات. لكل صفحة اسم مترجم وتعليمات تنقل أوضح، ويذكر خيار بدء التشغيل صراحةً التحقق من وجود تحديثات.

- أصبح اسم التطبيق «مفرّغ الوسائط الميسّر» ليشمل تفريغ الصوت والفيديو، مع الحفاظ على توافق الإعدادات السابقة.
- وُحّدت المصطلحات في الواجهتين، ويمكن تصدير الصوت كنص أو تسميات توضيحية، أو إنشاء فيديو بالتسميات على خلفية بسيطة.
- جُمعت خيارات إمكانية الوصول في التفضيلات، ويفتحها الاختصار Ctrl+Shift+A مباشرة دون قائمة مكررة.
- يختار التثبيت السريع المجلد الافتراضي واختصار قائمة ابدأ ونموذج Base. يتيح التثبيت المخصص اختيار المجلد والاختصارات ونموذج Tiny أو Base أو Small، أو العمل بمفاتيح API فقط.
- يمكن اختيار النموذج المحلي أو مزوّد الخدمة السحابية ونموذجه من التفضيلات.
- يتيح خيار «الإبلاغ عن مشكلة» مراسلة iman.rammal@gmail.com أو نسخ العنوان أو الإبلاغ عبر GitHub. يفتح البريد مسودة ليراجعها المستخدم ويرسلها بنفسه.
- تختفي رسالتا الترحيب والوداع خلال ثلاث ثوانٍ، ويمكن تعطيلهما وحفظ الاختيار.
- أُضيف التفريغ الدفعي واستعادة النصوص غير المكتملة وتكبير نص الواجهة.
- نجح ١٥٤ اختبارًا آليًا، ويشمل التحقق المحلي تفريغ تسجيلات صوت وفيديو وإنشاء فيديو بالنصوص المصاحبة منها. تظل Whisper الخيار المحلي الافتراضي؛ فالمقارنة الاستكشافية مع Qwen لا تكفي لإثبات تفوّقه دون نصوص مرجعية بشرية واختبار التوقيت.

---

# Previous release: Accessible Video Transcriber 1.3.0

## English

- Bundled multilingual Whisper Tiny, Base and Small for local transcription without API keys or a model download.
- Migrated to PySide6; third-party LGPL rights remain independent of app terms.

- All preferences now share one window with General, Speech and translation,
  API keys, and Accessibility tabs. Open it with Ctrl+, or use Ctrl+Shift+A to
  open its Accessibility page.
- Use Left/Right Arrow while focused on the tabs, or Ctrl+Tab and
  Ctrl+Shift+Tab from any page. Tab and Shift+Tab move between controls.
- Turn off **Read control hints and details** to reduce screen-reader verbosity.
  Control names, values, errors and completion messages remain available.
  Hints stay enabled by default for existing users.
- General preferences include interface language, timestamps and automatic
  update checking. Accessibility includes contrast, focus visibility,
  simplified layout, progress announcements and sounds.
- API-key test results are announced once in the result dialog.
- English and Arabic labels and right-to-left settings layout are supported.
- Arabic mode now refreshes group and menu descriptions when switching languages,
  translates welcome/farewell and update dialogs, and uses «إمكانية الوصول»
  consistently. Qt standard dialog buttons also use Arabic.
- Updated the English and Arabic user agreements to application version 1.3.0,
  corrected the Arabic author name, and linked the full agreement from Help.
- Added LinkedIn and Instagram contact links; removed phone and WhatsApp references.
- Fixed a packaged Qt startup failure caused by an incompatible bundled ICU DLL.

Install the attached AccessibleVideoTranscriber_Setup_1.3.0.exe. Existing
preferences are retained. Version 1.2 users can choose Help > Check for Updates
(Ctrl+U); automatic checks follow the saved startup preference.

## العربية

- يتضمن المثبّت نماذج Whisper Tiny وBase وSmall متعددة اللغات للتفريغ المحلي دون مفاتيح API أو تنزيل نموذج.
- انتقل التطبيق إلى PySide6، مع الحفاظ على الحقوق التي تمنحها تراخيص المكوّنات التابعة لأطراف ثالثة.

- جُمعت التفضيلات في نافذة واحدة تضم علامات التبويب: عام، والتفريغ والترجمة،
  ومفاتيح API، وإمكانية الوصول. افتحها باستخدام Ctrl+, أو افتح صفحة إمكانية
  الوصول باستخدام Ctrl+Shift+A.
- تنقل بين علامات التبويب بالسهمين الأيسر والأيمن عند التركيز عليها، أو
  باستخدام Ctrl+Tab وCtrl+Shift+Tab من أي صفحة. استخدم Tab وShift+Tab للتنقل
  بين عناصر التحكم.
- أوقف خيار «قراءة تلميحات عناصر التحكم وتفاصيلها» لتقليل المعلومات التي
  يقرؤها قارئ الشاشة. تبقى أسماء العناصر والقيم والأخطاء ورسائل اكتمال المهام
  متاحة. التلميحات مفعّلة افتراضيًا.
- تشمل الإعدادات العامة لغة الواجهة والطوابع الزمنية والتحقق التلقائي من
  التحديثات، وتشمل إعدادات الوصول التباين والتركيز والتخطيط المبسط وإعلانات
  التقدم والأصوات.
- تظهر نتائج اختبار مفاتيح API مرة واحدة في مربع النتيجة.
- صُححت الأسماء والأوصاف عند تبديل لغة الواجهة، وتُرجمت رسائل الترحيب والوداع
  والتحديثات وأزرار مربعات الحوار إلى العربية، ووُحّد مصطلح «إمكانية الوصول».
- حُدثت اتفاقية المستخدم إلى إصدار التطبيق 1.3.0، وصُحح اسم المؤلف، وأضيفت
  روابط لينكدإن وإنستغرام، وأزيلت معلومات الهاتف وواتساب.
- أُصلح خلل كان يمنع النسخة المجمعة من بدء التشغيل.

ثبّت الملف AccessibleVideoTranscriber_Setup_1.3.0.exe المرفق. تُحفظ التفضيلات
الحالية. للتحقق من التحديثات استخدم قائمة المساعدة أو Ctrl+U.
