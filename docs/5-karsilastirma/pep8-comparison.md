# PEP 8 (flake8) önce-sonra karşılaştırması

Bu dosya `scripts/compare_reports.py` ile ham raporlardan üretilir; elle düzenlenmez. Ham raporlar değiştirilmez.

- Başlangıç: `reports/baseline/` · commit `6e840acb` (upstream `master`, `docs/1-kapsam/baseline-commit.txt`)
- Son: `reports/final/` · commit `830d3a80` (`project-analysis`, 24 Kasım 2026, K10)
- Aynı araç sürümü, aynı kapsam (`cps/` + `cps.py`), aynı parametreler (CLAUDE.md → "Tarama komutları"; `docs/surec/environment-notes.md` → "Tarama kayıtları").
- Eşleştirme: normalize yol + kural kodu + kod parçası (kaynak satırın metni). Satırı yeniden biçimlenip aynı mesajla süren uyarılar "devam eden (satırı değişti)" sayılır.
- Susturma: bu dönemde `# nosec`, `# noqa` veya `# pylint: disable` eklenmedi (K6); aşağıdaki tüm kapanışlar kod düzeltmesidir.
- flake8 `--isolated --select=E,W`, satır uzunluğu 79 (K4). Toplam ihlal, raporun ihlal satırlarından sayıldı (`--statistics` özetiyle aynı).


## 1. Özet

| Ölçü | Başlangıç | Son | Fark |
| --- | --- | --- | --- |
| Toplam ihlal | 3409 | 3393 | -16 |
| İhlal kodu sayısı | 42 | 41 | -1 |
| Kapanan |  | 16 |  |
| Devam eden (aynı satır) |  | 3387 |  |
| Devam eden (satırı değişti) |  | 6 |  |
| Yeni çıkan |  | 0 |  |

Kontrol: 3409 = 16 + 3387 + 6; 3393 = 3387 + 6 + 0.

## 2. Kod bazında

| Kod | Açıklama | Başlangıç | Son | Fark |
| --- | --- | --- | --- | --- |
| `E111` | indentation is not a multiple of 4 | 1 | 1 | 0 |
| `E117` | over-indented | 5 | 5 | 0 |
| `E121` | continuation line under-indented for hanging indent | 4 | 4 | 0 |
| `E123` | closing bracket does not match indentation of opening bracket's line | 2 | 2 | 0 |
| `E124` | closing bracket does not match visual indentation | 2 | 2 | 0 |
| `E126` | continuation line over-indented for hanging indent | 22 | 22 | 0 |
| `E127` | continuation line over-indented for visual indent | 26 | 26 | 0 |
| `E128` | continuation line under-indented for visual indent | 56 | 56 | 0 |
| `E129` | visually indented line with same indent as next logical line | 2 | 2 | 0 |
| `E202` | whitespace before ')' | 2 | 2 | 0 |
| `E203` | whitespace before ',' | 5 | 5 | 0 |
| `E221` | multiple spaces before operator | 63 | 63 | 0 |
| `E222` | multiple spaces after operator | 11 | 11 | 0 |
| `E225` | missing whitespace around operator | 19 | 19 | 0 |
| `E226` | missing whitespace around arithmetic operator | 20 | 17 | -3 |
| `E231` | missing whitespace after ',' | 63 | 63 | 0 |
| `E241` | multiple spaces after ',' | 3 | 3 | 0 |
| `E251` | unexpected spaces around keyword / parameter equals | 13 | 13 | 0 |
| `E252` | missing whitespace around parameter equals | 2 | 2 | 0 |
| `E261` | at least two spaces before inline comment | 11 | 11 | 0 |
| `E262` | inline comment should start with '# ' | 5 | 5 | 0 |
| `E265` | block comment should start with '# ' | 12 | 12 | 0 |
| `E275` | missing whitespace after keyword | 9 | 9 | 0 |
| `E301` | expected 1 blank line, found 0 | 1 | 1 | 0 |
| `E302` | expected 2 blank lines, found 1 | 33 | 32 | -1 |
| `E303` | too many blank lines | 15 | 15 | 0 |
| `E305` | expected 2 blank lines after class or function definition, found 1 | 2 | 2 | 0 |
| `E306` | expected 1 blank line before a nested definition, found 0 | 2 | 2 | 0 |
| `E402` | module level import not at top of file | 2 | 2 | 0 |
| `E501` | line too long | 2879 | 2869 | -10 |
| `E711` | comparison to None should be 'if cond is None:' | 17 | 17 | 0 |
| `E712` | comparison to True should be 'if cond is True:' or 'if cond:' | 18 | 18 | 0 |
| `E713` | test for membership should be 'not in' | 3 | 3 | 0 |
| `E722` | do not use bare 'except' | 1 | 0 | -1 |
| `E731` | do not assign a lambda expression, use a def | 2 | 2 | 0 |
| `E741` | ambiguous variable name 'l' | 1 | 1 | 0 |
| `W291` | trailing whitespace | 9 | 9 | 0 |
| `W292` | no newline at end of file | 1 | 1 | 0 |
| `W293` | blank line contains whitespace | 6 | 6 | 0 |
| `W391` | blank line at end of file | 10 | 9 | -1 |
| `W503` | line break before binary operator | 28 | 28 | 0 |
| `W504` | line break after binary operator | 21 | 21 | 0 |
| **Toplam** |  | 3409 | 3393 | -16 |

## 3. Düzeltilen dosyalar

| Dosya | Önce | Sonra | Fark | Kapanan | Yeni |
| --- | --- | --- | --- | --- | --- |
| `cps/admin.py` | 337 | 337 | 0 | - | - |
| `cps/file_helper.py` | 6 | 5 | -1 | E722 ×1 | - |
| `cps/jinjia.py` | 16 | 4 | -12 | E226 ×3, E302 ×1, E501 ×7, W391 ×1 | - |
| `cps/metadata_provider/google.py` | 11 | 11 | 0 | - | - |
| `cps/services/goodreads_support.py` | 13 | 13 | 0 | - | - |
| `cps/shelf.py` | 98 | 98 | 0 | - | - |
| `cps/updater.py` | 85 | 84 | -1 | E501 ×1 | - |
| `cps/web.py` | 398 | 396 | -2 | E501 ×2 | - |

**`cps/jinjia.py` (FIND-117, PR #26): 16 → 4.** Dosya elle temizlendi (black/autopep8 kullanılmadı, K5). Kalan 4 ihlalin hepsi `E501` ve GPL lisans/telif başlığında (satır 3, 5, 6, 7). CLAUDE.md lisans bildirimlerinin değiştirilmesini yasakladığı için bu satırlara dokunulmadı; susturulmadılar da (K6).

## 4. Kapanan ihlaller (16)

| Konum (başlangıç) | Kod | Mesaj | Kod parçası | Bulgu (PR) |
| --- | --- | --- | --- | --- |
| `cps/file_helper.py:85` | `E722` | do not use bare 'except' | `except:` | FIND-109 (PR #16) |
| `cps/jinjia.py:63` | `E501` | line too long (105 > 79 characters) | `# if word longer than 20 chars truncate line and append '...', otherwi` | FIND-117 (PR #26) |
| `cps/jinjia.py:66` | `E226` | missing whitespace around arithmetic operator | `res += line[:(nchar-3)] + '[..] '` | FIND-117 (PR #26) |
| `cps/jinjia.py:67` | `E226` | missing whitespace around arithmetic operator | `suml += nchar+3` | FIND-117 (PR #26) |
| `cps/jinjia.py:84` | `E501` | line too long (82 > 79 characters) | `log.error('Babel error: %s, Current user locale: %s, Current User: %s'` | FIND-117 (PR #26) |
| `cps/jinjia.py:93` | `E501` | line too long (80 > 79 characters) | `input_date = val.isoformat().split('T', 1)[0]  # Hack to support dates` | FIND-117 (PR #26) |
| `cps/jinjia.py:100` | `E226` | missing whitespace around arithmetic operator | `int(date)/1000` | FIND-117 (PR #26) |
| `cps/jinjia.py:138` | `E501` | line too long (88 > 79 characters) | `return str(int(datetime.datetime.today().replace(hour=1, minute=1).tim` | FIND-117 (PR #26) |
| `cps/jinjia.py:142` | `E501` | line too long (86 > 79 characters) | `return str(int(datetime.datetime.today().replace(month=1, day=1).times` | FIND-117 (PR #26) |
| `cps/jinjia.py:159` | `E501` | line too long (105 > 79 characters) | `url = url_for('web.get_cover', book_id=book.id, resolution=shortname, ` | FIND-117 (PR #26) |
| `cps/jinjia.py:173` | `E501` | line too long (109 > 79 characters) | `url = url_for('web.get_series_cover', series_id=series.id, resolution=` | FIND-117 (PR #26) |
| `cps/jinjia.py:186` | `E302` | expected 2 blank lines, found 1 | `@jinjia.app_template_filter('clean_string')` | FIND-117 (PR #26) |
| `cps/jinjia.py:190` | `W391` | blank line at end of file | - | FIND-117 (PR #26) |
| `cps/updater.py:155` | `E501` | line too long (83 > 79 characters) | `return [x.strip() for x in open(filelist, 'r') if not x.startswith('#E` | FIND-069 (PR #25) yan etkisi |
| `cps/web.py:1436` | `E501` | line too long (101 > 79 characters) | `flash(_(u"An unknown error occurred. Please try again later."), catego` | FIND-126 (PR #18) yan etkisi |
| `cps/web.py:1438` | `E501` | line too long (92 > 79 characters) | `flash(_(u"Please enter valid username to reset password"), category="e` | FIND-126 (PR #18) yan etkisi |

`jinjia.py`'deki ihlaller FIND-117'nin (PR #26) parçası, `E722` FIND-109'dur (PR #16). "Yan etki" satırları, kayıtta kendi satırı olmayan ama bir düzeltme PR'ının değiştirdiği (silinen ya da bölünen) satırda kapanan ihlallerdir.

## 5. Devam eden ihlaller

- Aynı satırda süren: **3387**.
- Satırı değişen ama aynı mesajla süren: **6**:

| Başlangıç | Son | Kod | Mesaj (son) |
| --- | --- | --- | --- |
| `cps/admin.py:1374` | `cps/admin.py:1375` | `E501` | line too long (99 > 79 characters) |
| `cps/admin.py:1377` | `cps/admin.py:1378` | `E501` | line too long (99 > 79 characters) |
| `cps/metadata_provider/google.py:54` | `cps/metadata_provider/google.py:54` | `E501` | line too long (82 > 79 characters) |
| `cps/services/goodreads_support.py:91` | `cps/services/goodreads_support.py:91` | `E501` | line too long (83 > 79 characters) |
| `cps/shelf.py:287` | `cps/shelf.py:287` | `E501` | line too long (99 > 79 characters) |
| `cps/updater.py:411` | `cps/updater.py:412` | `E501` | line too long (99 > 79 characters) |

## 6. Yeni çıkan ihlaller (0)

Yok.

## W503 / W504 notu

`W503` (ikili operatörden **önce** satır kırma) ve `W504` (ikili operatörden **sonra** satır kırma) birbirinin tersidir: PEP 8 bugün `W503` biçimini öneriyor ve flake8 varsayılanında ikisi de kapalıdır. Bu projede flake8 `--select=E,W` ile çalıştığı için (K4) ikisi de açık; bu yüzden operatörde bölünen **her** satır bu iki uyarıdan birini mutlaka verir. Başlangıç `W503` 28 / `W504` 21, son `W503` 28 / `W504` 21.

Bu iki kod düzeltme hedefi olarak seçilmedi: birini düzeltmek diğerini doğurur. Ayrıca PEP 8 tarafından gerçek ihlal sayılmazlar. Bu ihlaller FIND-112 grup satırında "Kabul edildi (düzeltilmeyecek)" olarak duruyor.

## K5 gerekçesi (PEP 8 kısmı)

Bu dönemde düzeltilen flake8 türleri: `E722` (FIND-109, PR #16), `E501`, `E226`, `E302` ve `W391` (FIND-117, PR #26). Toplam **5 PEP 8 türü**; Pylint'teki 7 türle birlikte K5'in "en az 5 kod kalitesi / PEP 8 türü" hedefi karşılanıyor (`docs/5-karsilastirma/pylint-comparison.md`).

Toplam ihlalin yalnızca 16 azalması beklenen bir sonuç: K5 gereği toplu biçimlendirme yapılmadı. Seçilen tek dosya (`jinjia.py`) elle ve lisans başlığı korunarak temizlendi.

