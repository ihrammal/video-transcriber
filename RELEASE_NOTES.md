# Accessible Video Transcriber 1.3.0

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
