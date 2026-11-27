# توسيع المعاجم في حزمة الترجمة EN↔AR: لماذا لا ننزّل قواميس ضخمة؟

**التاريخ:** 2026-11-27
**المشروع:** `translator-analysis` — حزمة ترجمة إنجليزية ↔ عربية محمولة
**السؤال:** لماذا لا ننزّل معاجم «دقيقة وقوية» لتضريب عدد المصطلحات، وأي معجم أمريكي «معترف به» يضيف الكلمات الإنجليزية الجديدة فور ظهورها؟
**المنهج:** مصادر أولية فقط (صفحات الناشرين الرسمية، وثائق الحكومة، صفوف/واجهات المشاريع themselves، صفحات الترخيص الرسمية). كل ادعاء خارجي موثّق برابط مضمّن، وتنتهي الوثيقة بقائمة المصادر.

---

## 1) الإجابة المختصرة

- المعجم الذي يقصده السائل على الأرجح هو **Merriam-Webster**، لأنه يعلن بنفسه إضافة دفعات كبيرة من الكلمات الجديدة إلى قاموسه الإلكتروني — آخرها 1,400 كلمة وتعريف في سبتمبر 2026 ([Merriam-Webster، 25 سبتمبر 2026](https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary))، ويصف نفسه بأنه «أكثر قاموس موثوق في أمريكا» ([الصفحة الرئيسية](https://www.merriam-webster.com/)) و«أبرز ناشر أمريكي لأعمال المراجع اللغوية» ([الأسئلة الشائعة](https://www.merriam-webster.com/about-us/faq)).
- لكن **لا يوجد معجم «معتمد رسمياً» من الحكومة الأمريكية بالمعنى العام**؛ ما يوجد هو اختيار أسلوبي داخلي: دليل أسلوب مكتب النشر الحكومي (GPO Style Manual) ينصّ على أن GPO يستخدم *Webster's Third New International Dictionary* مرجعاً **لتهجئة** الكلمات غير الواردة في الدليل ([§5.1](https://www.govinfo.gov/content/pkg/GPO-STYLEMANUAL-2016/pdf/GPO-STYLEMANUAL-2016-7.pdf))، صادراً بموجب 44 U.S.C. §1105 ([مقدمة الدليل](https://www.govinfo.gov/content/pkg/GPO-STYLEMANUAL-2016/pdf/GPO-STYLEMANUAL-2016-1.pdf)). هذا قرار تحريري فيبدرالي للمنشورات الحكومية، لا تعيين «معجم وطني» ولا إجازة لكلمات جديدة.
- الكلمات لا تُضاف «لحظة ظهورها»؛ Merriam-Webster نفسه يقول إن الكلمات تُضاف أو تُحذف بناءً على البيانات و«الاستخدام الواسع على مدى زمن» ([قواعد اللعبة المعجمية](https://www.merriam-webster.com/wordplay/dictionary-facts-and-trivia)؛ [مقال الإضافة الأخيرة](https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary)).
- الأسباب العملية لعدم تنزيل قواميس تجارية ضخمة: تراخيصها تمنع التوزيع بالجملة ([شروط Merriam-Webster](https://www.merriam-webster.com/i/terms-of-use)، [شروط Oxford](https://languages.oup.com/legal-notice/)، [شروط Collins](https://www.collinsdictionary.com/terms-and-conditions))، ولو كان مسموحاً لكانت أحجامDump تتجاوز حدود Git/GitHub ([وثائق GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)). البديل هو **قواميس مفتوحة + انتقاء مُنسّق + تنزيل عند الطلب**، كما يوضّح القسم 3.

---

## 2) أيّ معجم تعنيه المسألة؟ (الموقف في الولايات المتحدة)

### 2.1 Merriam-Webster: المكانة والإضافات الجديدة

- تقول الصفحة الرسمية «منذ أكثر من 180 عاماً، Merriam-Webster هو المزوّد الرائد في أمريكا للمعلومات اللغوية»، وتذكر أن فريق محرريها هو «أكبر فريق من محرري المعاجم والكتّاب المحترفين في أمريكا» ([About Us](https://www.merriam-webster.com/about-us)).
- وتصف الأسئلة الشائعة الرسمية الشركة بأنها «أبرز ناشر أمريكي لأعمال المراجع اللغوية»، وتوضّح أن قاموس Merriam-Webster.com «مرجع إلكتروني فريد، يُحدَّث بانتظام»، وأنه «يقدّم عادةً المعلومات الأكثر حداثة» عند الاختلاف مع طبعة Collegiate الورقية ([Merriam-Webster FAQ](https://www.merriam-webster.com/about-us/faq)).
- في 25 سبتمبر 2026 أعلن المحرّرون إضافة **1,400 كلمة وتعريف** دفعة واحدة، من بينها `vibe coding` و`AGI` و`parasocial` و`Rickroll` و`Mandela Effect`، وعلّلوا ذلك بأن المداخل «أظهرت استخداماً واسعاً على مدى زمن» ([الإعلان الرسمي](https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary)). سبقها إعلان عن 200 كلمة في أكتوبر 2024 ([صفحة 2024](https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary-october-2024)) و690 كلمة في سبتمبر 2023 ([صفحة 2023](https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary-september-2023)) — أي أن التحديث **دفات دورية** لا لحظي.
- يؤكد المعجم رسمياً أن «لا وجود لشيء اسمه *القاموس*»، وأن «معجميّي المعاجم لا يقرّرون ما هي الكلمة»؛ فالإضافة تتم استناداً إلى بيانات الاستخدام، ولا يمكن لأي معجم أن يحتوي كل كلمات الإنجليزية ([Become a True Dictionary Buff](https://www.merriam-webster.com/wordplay/dictionary-facts-and-trivia)). إذن حتى المعجم الذي يقصده السائل لا يدّعي احتكار الصحة أو الاكتمال.

### 2.2 هل هناك معجم تعيّنه الحكومة الأمريكية رسمياً؟

- **النتيجة المستندة إلى المصادر التي راجعناها:** لم نجد قانوناً اتحادياً أو قرار وكالة يعيّن معجماً واحداً «رسمياً» للغة الإنجليزية الأمريكية بصورة عامة. أقرب نصّ رسمي هو ما ورد في دليل GPO:
  > «GPO uses Webster’s Third New International Dictionary as its guide for the spelling of words not appearing in the GPO Style Manual» ([GPO Style Manual 2016، الفصل 5، §5.1](https://www.govinfo.gov/content/pkg/GPO-STYLEMANUAL-2016/pdf/GPO-STYLEMANUAL-2016-7.pdf)).
- نطاق هذا التعيين محدود: الدليل الصادر بعنوان «دليل رسمي لشكل وأسلوب منشورات الحكومة الاتحادية» ([الغلاف/بيان النشر](https://www.govinfo.gov/content/pkg/GPO-STYLEMANUAL-2016/pdf/GPO-STYLEMANUAL-2016-1.pdf)) يستند إلى 44 U.S.C. §1105 الذي يخول مدير GPO تحديد «شكل وأسلوب» الطباعة، ويصف نفسه بأنه «دليل عام» لا قواعد جامدة لأن «الاستخدام يتغيّر مع تطوّر اللغة» ([مقدمة الدليل](https://www.govinfo.gov/content/pkg/GPO-STYLEMANUAL-2016/pdf/GPO-STYLEMANUAL-2016-1.pdf)). فهو مرجع **للتهجئة** للمنشورات الفيدرالية، لا معجم معتمد للترجمة ولا مصدر للكلمات الجديدة.
- *Webster's Third* نفسه هو منتج تجاري من Merriam-Webster: متجر الشركة يعرضه بأكثر من 476,000 مدخل و«قسم ملاحق محدَّث للكلمات والمعاني الجديدة» ([متجر Merriam-Webster](https://shop.merriam-webster.com/products/websters-third-new-international-dictionary-unabridged))، والشركة تقول إن قاموسها غير المختصر الإلكتروني هو «خليفة» *Webster's Third* ([FAQ](https://www.merriam-webster.com/about-us/faq)). إذاً التقاء «المعجم المعتمد حكومياً» و«المعجم الذي يضيف كلمات جديدة» في Merriam-Webster تقريباً صحيح، لكنه ليس نفس الإصدار ولا نفس المنتج.
- تنبيه إضافي: ليست كل معاجم «Webster's» صادرة عن Merriam-Webster؛ الشركة نفسها تشرح أن شركات استخدمت الاسم تاريخياً ([Help FAQ](https://www.merriam-webster.com/help/faq-websters-dictionaries)).

---

## 3) ما الذي يمكن تنزيله وشحنه قانونياً؟

### 3.1 المصادر المفتوحة

| المورد | الحجم/العدد (من مصدره الرسمي) | الترخيص والقيود | المصدر |
|---|---|---|---|
| Wiktionary الإنجليزية | 10,468,807 صفحة في النطاق الرئيسي (`articles`) حسب إحصاءات API في 2026-11-27 | نصوص المداخل مرخّصة **مرتين**: CC BY-SA 4.0 وGFDL (بلا أقسام ثابتة ولا أغلفة). في حالة CC BY-SA: يجب النسب وترخيص المشتقّات بترخيص متوافق؛ GFDL يضيف التزام «النسخة الشفّافة» | [API الإحصاءات](https://en.wiktionary.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json) · [سياسة الحقوق](https://en.wiktionary.org/wiki/Wiktionary:Copyrights) |
| Dump Wiktionary الإنجليزية (2026-11-01) | `pages-articles.xml.bz2` ≈ **1.6 GB**؛ نسخة multistream ≈ **1.9 GB** | نفس الترخيص؛ صفحة Dumps تحذّر من محتوى بموجب «الاستخدام العادل» ومن انتهاكات حقوق لم تُكتشف بعد، والاستخدام «على مسؤوليتك» | [صفحة الـ dump](https://dumps.wikimedia.org/enwiktionary/20261101/) · [شروط Dumps](https://dumps.wikimedia.org/legal.html) |
| Wiktionary العربية | 457,264 مدخلاً (`articles`) و529,616 صفحة؛ dump المقالات ≈ **21.7 MB** (21,694,139 بايت) | نفس ترخيص Wiktionary (CC BY-SA 4.0 / GFDL) | [API الإحصاءات](https://ar.wiktionary.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json) · [فهرس الـ dump](https://dumps.wikimedia.org/arwiktionary/latest/) · [سياسة الحقوق](https://en.wiktionary.org/wiki/Wiktionary:Copyrights) |
| Open English WordNet (OEWN) 2025+ | **161,875** كلمة، **120,564** synset، **419,226** علاقة؛ الإصدار الأساسي 2025: 135,969 كلمة. ملف WNDB المضغوط لهذا الإصدار حوالي **11 MB** (قياس إصدار 2024: 10.9 MB) | **CC BY 4.0**: النسب مطلوب، وليس Share-Alike؛ مشتقّ من Princeton WordNet | [README المستودع](https://github.com/globalwordnet/english-wordnet) · [صفحة التنزيلات](https://en-word.net/downloads) |
| Princeton WordNet | 3.1: **159,015** كلمة و**117,791** synset (حسب جدول OEWN الرسمي) | رخصة Princeton تسمح «الاستخدام، النسخ، التعديل والتوزيع لأي غرض بدون رسوم أو إتاوة» بشرط إرفاق إشعار الحقوق وبيان «AS IS» بكل نسخة، ومنع استخدام اسم Princeton في الإعلانات | [رخصة WordNet](https://wordnet.princeton.edu/license-and-commercial-use) · [جدول الأحجام](https://github.com/globalwordnet/english-wordnet) |
| Wikidata | 124,186,260 عنصراً في النطاق الرئيسي؛ `latest-all.json.gz` ≈ **157 GB** (157,426,750,831 بايت)؛ `latest-lexemes.json.gz` ≈ **672 MB** | البيانات المهيكلة في نطاق العناصر/الخصائص/Lexeme/EntitySchema تحت **CC0** (Public Domain)؛ النصوص في النطاقات الأخرى CC BY-SA 4.0. التحديثات الكاملة أسبوعية، وهناك dumps تزايدية أصغر | [إحصاءات API](https://www.wikidata.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json) · [فهرس Dumps](https://dumps.wikimedia.org/wikidatawiki/entities/) · [سياسة الترخيص](https://www.wikidata.org/wiki/Wikidata:Licensing) |

**ملاحظة تفسيرية مهمة:** أرقام Wiktionary هي عدد **صفحات/مداخل**، وليست بالضرورة عدد كلمات إنجليزية مختلفة أو أزواج ثنائية اللغة؛ وأرقام WordNet هي كلمات/معانٍ (synsets) إنجليزية بلا مقابل عربي. أزواج `en↔ar` الجاهزة للإدراج في Term Base لا تنتجها هذه المصادر إلا بعد استخراج قسم الترجمات العربية من مداخل Wiktionary الإنجليزية أو الربط اليدوي. أمّا Wikidata فهي قاعدة معرفة (كيانات وتسميات) لا معجم سياقات استخدام، رغم أن CC0 يجعلها الأسهل قانونياً.

### 3.2 ما لا يمكن تنزيله وشحنه (تراخيص تجارية)

- **Merriam-Webster (الموقع):** تنص الشروط على أن استخدام المحتوى «للاستخدام الشخصي غير التجاري فقط» فقط، وتحظر «تنقيب البيانات، والروبوتات، وكشط الشاشة، وأدوات جمع واستخراج مماثلة، بما في ذلك الذكاء الاصطناعي لأغراض تطويره أو تدريبه أو إجراء تحليل حاسوبي، إلا بموافقة كتابية صريحة»، وتنصّ على أنه لا يجوز نسخ أي جزء من صفحات الويب بأي وسيلة دون إذن كتابي ([شروط الاستخدام](https://www.merriam-webster.com/i/terms-of-use)).
- **Merriam-Webster (API):** الترخيص المجاني مشروط بـ«تطبيق غير تجاري» و«≤1000 استعلام/يوم/عمل مرجعي» و«عملين مرجعيين كحد أقصى»، ويمنع الاستعلامات الآلية أو المسجّلة دون موافقة خطية، والنسخ/التوزيع/إنشاء مشتقّات من البرمجيات؛ التجاوز يتطلب ترتيباً مدفوعاً ([شروط API](https://dictionaryapi.com/info/terms-of-service)، [الأسئلة الشائعة](https://dictionaryapi.com/info/frequently-asked-questions)). أي «تنزيل شامل» للبيانات يتجاوز هذا الترخيص.
- **Oxford:** يسمح الإشعار القانوني بالبحث والعرض والحفظ الإلكتروني لـ«أجزاء» من المحتوى وطباعة نسخة مفردة، لكنه يمنع «عمل نسخ متكرّرة من مقتطفات متعددة» و«عرض أو توزيع أي جزء على شبكة إلكترونية» وأي استخدام تجاري ([Oxford Languages Legal Notice](https://languages.oup.com/legal-notice/)). شروط API للبحث غير التجاري تمنع النسخ/التنزيل المنهجي، والروبوتات والكاشطات، واستخدام المحتوى مع أدوات الذكاء الاصطناعي، وإعادة توزيعه دون موافقة كتابية ([Oxford API Terms](https://developer.oxforddictionaries.com/api-terms-and-conditions))؛ والتخزين المؤقت/التخزين دون اتصال مشروط برخصة Enterprise ([FAQ](https://developer.oxforddictionaries.com/faq)).
- **Collins:** شروط الموقع تقول إن المحتوى «للاستخدام الشخصي غير التجاري فقط»، ولا يجوز تنزيله أو نسخه أو إعادة إنتاجه أو توزيعه دون إذن كتابي، ويُسمح فقط بـ«مقتطفات غير جوهرية» ([Collins Terms](https://www.collinsdictionary.com/terms-and-conditions)). شروط WordbanksOnline تقيّد البيانات بالبحث غير التجاري وتمنع إتاحتها لأطراف ثالثة ([Wordbanks Terms](https://blog.collinsdictionary.com/wordbanksonline-terms-and-conditions-of-use/)).

**الخلاصة القانونية:** لا نستطيع تحويل قواميس Merriam-Webster/Oxford/Collins إلى ملفات بيانات داخل المستودع؛ الاستخدام المسموح هو استعلام عند الطلب ضمن حصص وقيود، وحتى نتائج الاستعلام لا تُوزَّع بالجملة.

---

## 4) الحكم العملي لهذا المستودع

### 4.1 الوضع الحالي (ملاحظات محلية، بلا تعديل على الكود)

- `data/glossary.tbx` يحتوي حالياً على **10 مداخل `termEntry`** (عدّ مباشر من الملف) — أي أن مضاعفة الأرقام لا تتطلب «قاموساً ضخماً» بقدر ما تتطلب عملية انتقاء وتوثيق مصطلحات.
- `src/glossary.py` يقرأ TBX/UTX/JSON ويحقن المصطلحات ذات الصلة في مسار الترجمة وفحص الالتزام (`get_relevant_terms` / `check_adherence`)، ويدعم حقل `subjectField` كوسم مجالي ([المصدر المحلي](src/glossary.py)). أي توسيع يجب أن يحافظ على هذا الشكل لا أن يستبدل به جدولاً ضخماً.
- `src/dictionary.py` يعتمد بالفعل نهج «أوفلاين أولاً»: ملفات محلية لـ OEWN وWiktionary وRoget تحت `data/dictionaries/`، وواجهات Merriam-Webster/Collins/Oxford مقنّنة بمفاتيح وذاكرة تخزين SQLite تحت `data/cache/` ([المصدر المحلي](src/dictionary.py)). التصميم المقترح أدناه يوسّع هذا النمط ولا يخالفه.

### 4.2 الأرقام المتاحة مقابل ما يُشحن فعلياً

| المصدر | متاح نظرياً | ما الذي يعنيه للمستودع |
|---|---|---|
| Glossary الحالي | 10 أزواج | يبقى المرجع المعتمد (`canonical`) |
| OEWN 2025+ | ~162 ألف كلمة / ~120 ألف synset، ملف ~11 MB ([المصدر](https://github.com/globalwordnet/english-wordnet)) | مرشّح عملي للتنزيل عند الطلب؛ يعطي تعريفات ومرادفات إنجليزية فقط |
| Wiktionary EN | ~10.5 مليون صفحة، dump ~1.6 GB ([API](https://en.wiktionary.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json)، [Dump](https://dumps.wikimedia.org/enwiktionary/20261101/)) | مصدر الأزواج EN↔AR، لكن لا يُخزَّن خاماً في Git |
| Wiktionary AR | ~457 ألف مدخل، dump ~21.7 MB ([API](https://ar.wiktionary.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json)، [Dump](https://dumps.wikimedia.org/arwiktionary/latest/)) | مفيد للتحقق العكسي؛ يُستخرج منه المطلوب فقط |
| Wikidata | ~124 مليون عنصر، dump ~157 GB أو lexemes ~672 MB ([API](https://www.wikidata.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json)، [Dumps](https://dumps.wikimedia.org/wikidatawiki/entities/)) | لا يُشحن؛ إن استُخدم فلتسميات الكيانات فقط |

### 4.3 مخاطر إيداع الـ dumps الكبيرة

- GitHub يحذّر عند الملفات الأكبر من 50 MiB ويحظر الملفات الأكبر من 100 MiB، ويوصي بأن تبقى المستودعات أقل من 1 GB ([وثائق GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)). dump الإنجليزية (1.6 GB) وWikidata (157 GB) مستحيلان عملياً؛ حتى ملف OEWN الصغير يصبح عبئاً إذا أُضيفت كل إصدار منه إلى التاريخ.
- الترخيص ينتقل إلى المشتقّات: أي TBX أو JSON مستخرج من Wiktionary يخضع لـ CC BY-SA 4.0 (أو GFDL إن اخترنا هذا المسار) ويحتاج نسباً واضحاً ([سياسة الحقوق](https://en.wiktionary.org/wiki/Wiktionary:Copyrights)، [شروط Dumps](https://dumps.wikimedia.org/legal.html)). ويجب ألا يُفهم أن «المصطلح نفسه» مملوك؛ النصّ التفسيري والاقتباسات قد تخضع لشروط منفصلة، وانتهاكات غير مكتشفة على مسؤولية المستخدم ([شروط Dumps](https://dumps.wikimedia.org/legal.html)).
- فقدان القابلية للمراجعة: مئات الآلاف من الأزواج المُولَّدة آلياً تُغرق فحص الالتزام وتُضعف «المنهجية البشرية» التي يقوم عليها المشروع؛ `[GLOSSARY.md](GLOSSARY.md)` يعرّف Term Base بأنها المصطلحات **المعتمدة**، لا كل ما ورد في معجم.

### 4.4 التصميم الموصى به: «انتقاء مُنسّق + تنزيل عند الطلب»

1. **طبقة canonical صغيرة:** الاحتفاظ بـ `data/glossary.tbx` كمصدر معتمد، والتوسّع التدريجي إلى مئات ثم آلاف الأزواج المُحرَّرة يدوياً، مع حقول `subjectField` و`termType` وحقل provenance/ترخيص لكل مدخل (الشكل الحالي يدعم `descrip` ويمكن إضافة وسم مصدر دون كسر المحلّل في `src/glossary.py`).
2. **downloader اختياري (لم يُنفَّذ في هذه الدراسة):** سكربت عند الطلب يجلب `english-wordnet-2025` (~11 MB، [رابط التنزيل](https://en-word.net/downloads)) أو Dump Wiktionary مؤرخة ([الرابط](https://dumps.wikimedia.org/enwiktionary/20261101/))، يتحقق من الحجم/مجموع التحقق المنشور، يبقي الملف الخام **خارج** المستودع، ويكتب جدولاً مضغوطاً في `data/dictionaries/` بالحقول التي يقرأها `src/dictionary.py` بالفعل. يُضاف نمط تجاهل للـ dumps الخام إلى `.gitignore` (الذي يتجاهل `data/cache/` بالفعل، [الملف](.gitignore)) دون تعديله الآن.
3. **قاعدة Wiktionary EN↔AR:** بدلاً من إيداع 1.6 GB، يُشغَّل تدفق لمرة واحدة على الـ dump ويُستخرج منه فقط قسم «Arabic» لقائمة رؤوس كلمات مُختارة، مع كتابة إشعارات CC BY-SA 4.0 واسم المصدر وتاريخ الـ dump في ملف `NOTICE`؛ أو استعلام MediaWiki API لكل كلمة عند الطلب ([API](https://en.wiktionary.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json) كدليل على وجود الواجهة الرسمية). العربية: الـ dump أصغر (~21.7 MB) لكن يُعامل بالمثل.
4. **Wikidata:** لا يُنزَّل كاملاً؛ إن لزم، يُستخدم `latest-lexemes.json.gz` (~672 MB، [الفهرس](https://dumps.wikimedia.org/wikidatawiki/entities/)) خارج المستودع لإثراء التسميات فقط، مستفيداً من CC0 ([الترخيص](https://www.wikidata.org/wiki/Wikidata:Licensing)).
5. **واجهات القواميس التجارية:** تبقى خلف مفتاح وحصّة، على سبيل المثال Merriam-Webster ≤1000 استعلام/يوم ([الشروط](https://dictionaryapi.com/info/terms-of-service))، مع عدم حفظ مخرجاتها في Git وعدم استخدامها لتدريب نماذج أو بناء قاموس مشتقّ؛ تخزين Oxford دون اتصال يتطلب رخصة Enterprise ([FAQ](https://developer.oxforddictionaries.com/faq)).
6. **بوابات الجودة:** `scripts/validate_pack.py` / CI يتحققان من أن أي ملف بيانات جديد يحمل مصدراً وترخيصاً، ويبقى تحت حدّ حجم متفق عليه (مثلاً بضعة ميغابايتات)، ولا يحتوي نصّاً من مواقع تجارية ([السكربت](scripts/validate_pack.py)، [سير العمل](.github/workflows/ci.yml)).

**الحكم النهائي:** نعم، يمكن مضاعفة عدد المصطلحات كثيراً — لكن بمصادر مفتوحة (OEWN + Wiktionary + Wikidata) وبعدد مُنسّق يُختبر، لا بتنزيل «قاموس أمريكي موثوق»؛ فذاك إما مرخّص استعلام فقط أو محدّد رسمياً لغرض ضيّق (تهجئة منشورات GPO) ولا يمنح حق الشحن بالجملة.

---

## Sources

1. Merriam-Webster — “1,400 New Words And Definitions Added To Merriam-Webster.com” (25 Sep 2026): https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary
2. Merriam-Webster — “200 New Words…” (Oct 2024): https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary-october-2024
3. Merriam-Webster — “690 New Words…” (Sep 2023): https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary-september-2023
4. Merriam-Webster — About Us: https://www.merriam-webster.com/about-us
5. Merriam-Webster — About Us FAQ: https://www.merriam-webster.com/about-us/faq
6. Merriam-Webster — Become a True Dictionary Buff: https://www.merriam-webster.com/wordplay/dictionary-facts-and-trivia
7. Merriam-Webster — Are all “Webster's” dictionaries published by Merriam-Webster?: https://www.merriam-webster.com/help/faq-websters-dictionaries
8. Merriam-Webster Shop — Webster's Third New International Dictionary, Unabridged: https://shop.merriam-webster.com/products/websters-third-new-international-dictionary-unabridged
9. Merriam-Webster — Terms of Use: https://www.merriam-webster.com/i/terms-of-use
10. Merriam-Webster Dictionary API — Terms of Service: https://dictionaryapi.com/info/terms-of-service ; FAQ: https://dictionaryapi.com/info/frequently-asked-questions
11. U.S. GPO — Style Manual 2016, ch. 5 §5.1: https://www.govinfo.gov/content/pkg/GPO-STYLEMANUAL-2016/pdf/GPO-STYLEMANUAL-2016-7.pdf
12. U.S. GPO — Style Manual 2016, front matter/About: https://www.govinfo.gov/content/pkg/GPO-STYLEMANUAL-2016/pdf/GPO-STYLEMANUAL-2016-1.pdf
13. Wiktionary — Copyrights/licensing: https://en.wiktionary.org/wiki/Wiktionary:Copyrights
14. Wikimedia — Dump license information: https://dumps.wikimedia.org/legal.html
15. en.wiktionary API — site statistics: https://en.wiktionary.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json
16. ar.wiktionary API — site statistics: https://ar.wiktionary.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json
17. Wikimedia Dumps — enwiktionary 2026-11-01: https://dumps.wikimedia.org/enwiktionary/20261101/
18. Wikimedia Dumps — arwiktionary latest: https://dumps.wikimedia.org/arwiktionary/latest/
19. Open English WordNet — README/size table & license: https://github.com/globalwordnet/english-wordnet ; downloads: https://en-word.net/downloads
20. Princeton University — License and Commercial Use of WordNet: https://wordnet.princeton.edu/license-and-commercial-use
21. Wikidata — Licensing: https://www.wikidata.org/wiki/Wikidata:Licensing ; Database download: https://www.wikidata.org/wiki/Wikidata:Dumps
22. Wikidata API — site statistics: https://www.wikidata.org/w/api.php?action=query&meta=siteinfo&siprop=statistics&format=json
23. Wikimedia Dumps — Wikidata entities index: https://dumps.wikimedia.org/wikidatawiki/entities/
24. Oxford Languages — Legal Notice: https://languages.oup.com/legal-notice/
25. Oxford Dictionaries — API Terms and Conditions: https://developer.oxforddictionaries.com/api-terms-and-conditions ; FAQ: https://developer.oxforddictionaries.com/faq
26. Collins Dictionary — Terms & Conditions: https://www.collinsdictionary.com/terms-and-conditions ; WordbanksOnline Terms: https://blog.collinsdictionary.com/wordbanksonline-terms-and-conditions-of-use/
27. GitHub Docs — About large files on GitHub: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
