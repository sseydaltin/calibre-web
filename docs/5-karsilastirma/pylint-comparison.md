# Pylint önce-sonra karşılaştırması

Bu dosya `scripts/compare_reports.py` ile ham raporlardan üretilir; elle düzenlenmez. Ham raporlar değiştirilmez.

- Başlangıç: `reports/baseline/` · commit `6e840acb` (upstream `master`, `docs/1-kapsam/baseline-commit.txt`)
- Son: `reports/final/` · commit `830d3a80` (`project-analysis`, 24 Kasım 2026, K10)
- Aynı araç sürümü, aynı kapsam (`cps/` + `cps.py`), aynı parametreler (CLAUDE.md → "Tarama komutları"; `docs/surec/environment-notes.md` → "Tarama kayıtları").
- Eşleştirme: normalize yol + kural kodu + kod parçası (kaynak satırın metni). Satırı yeniden biçimlenip aynı mesajla süren uyarılar "devam eden (satırı değişti)" sayılır.
- Susturma: bu dönemde `# nosec`, `# noqa` veya `# pylint: disable` eklenmedi (K6); aşağıdaki tüm kapanışlar kod düzeltmesidir.


## 1. Özet

| Ölçü | Başlangıç | Son | Fark |
| --- | --- | --- | --- |
| Puan (score) | 6.42/10 | 6.44/10 | +0.02 |
| Toplam mesaj (ham rapor) | 3999 | 3985 | -14 |
|   içinde `R0401` cyclic-import (bkz. not) | 43 | 49 | +6 |
| **Toplam mesaj, `R0401` hariç** | 3956 | 3936 | -20 |
| Kapanan |  | 20 |  |
| Devam eden (aynı satır) |  | 3934 |  |
| Devam eden (satırı değişti) |  | 2 |  |
| Yeni çıkan |  | 0 |  |

Kontrol (`R0401` hariç): başlangıç = kapanan + devam eden → 3956 = 20 + 3934 + 2; son = devam eden + yeni → 3936 = 3934 + 2 + 0.

**`R0401` (cyclic-import) notu.** Ham raporlarda `R0401` sayısı 43 → 49 görünüyor, ama bu düzeltmelerden kaynaklanmıyor: başlangıç ile son commit arasında hiçbir `import`/`from` satırı değişmedi (`git diff` ile kontrol edildi). Pylint'in döngüsel import raporu çalıştırmadan çalıştırmaya değişiyor: aynı parametrelerle yapılan doğrulama çalıştırmalarında başlangıç commit'i 43 ve 48, son commit 49 ve 44 `R0401` verdi; diğer tüm mesajlar ve puan iki çalıştırmada da aynıydı. Bu doğrulama çalıştırmaları yalnızca kontrol içindir, rapor olarak kaydedilmedi ve baseline'ı değiştirmez (kural 11). Bu yüzden `R0401` eşleştirmeye katılmadı; tablolarda ham sayısıyla gösterildi.

Puan artışının küçük olması beklenen bir sonuç: K5 kararı gereği toplu biçimlendirme yapılmadı, yalnızca seçilmiş bulgular elle düzeltildi. 3956 mesajdan (`R0401` hariç) 20 tanesi kapandı; puan tüm projenin mesaj yoğunluğuna göre hesaplanır.

## 2. Kategori bazında

| Kategori | Başlangıç | Son | Fark |
| --- | --- | --- | --- |
| convention (C) | 2646 | 2641 | -5 |
| refactor (R) | 537 | 543 | +6 |
| warning (W) | 454 | 442 | -12 |
| error (E) | 324 | 321 | -3 |
| information (I) | 38 | 38 | 0 |
| **Toplam** | 3999 | 3985 | -14 |

`refactor` satırındaki farkın +6 mesajlık kısmı `R0401` oynamasıdır (bkz. not).

## 3. Mesaj kodu bazında (yalnızca sayısı değişen kodlar)

| Kod | Sembol | Başlangıç | Son | Fark | İlgili bulgu (PR) |
| --- | --- | --- | --- | --- | --- |
| `W1514` | unspecified-encoding | 10 | 4 | -6 | FIND-069 (PR #25) |
| `C0301` | line-too-long | 911 | 907 | -4 | - |
| `E1101` | no-member | 39 | 37 | -2 | FIND-049 (PR #20) |
| `W1406` | redundant-u-string-prefix | 69 | 67 | -2 | - |
| `C0305` | trailing-newlines | 10 | 9 | -1 | - |
| `E1305` | too-many-format-args | 1 | 0 | -1 | FIND-056 (PR #24) |
| `W0702` | bare-except | 1 | 0 | -1 | FIND-080 (PR #16) |
| `W0715` | raising-format-tuple | 1 | 0 | -1 | FIND-078 (PR #22) |
| `W1116` | isinstance-second-argument-not-valid-type | 1 | 0 | -1 | FIND-081 (PR #23) |
| `W3101` | missing-timeout | 1 | 0 | -1 | FIND-085 (PR #21) |
| `R0401` | cyclic-import | 43 | 49 | +6 | - |

Diğer 95 mesaj kodunun sayısı değişmedi.

## 4. Düzeltilen dosyalarda dosya bazlı puan

Her dosya için `python -m pylint <dosya>` ayrı ayrı çalıştırıldı (başlangıç commit'i ve son commit, geçici worktree'lerde). Resmi tarama değildir; dosya düzeyindeki etkiyi gösterir. `cps/metadata_provider/` dosyaları resmi taramada yer almadığı için (bkz. "`cps/metadata_provider/` kapsam notu") yalnızca burada görünür.

| Dosya | Düzeltme | Puan önce | Puan sonra | Fark | Mesaj önce | Mesaj sonra | Fark |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `cps/admin.py` | FIND-049, 069, 078 (PR #20, #25, #22) | 5.29 | 5.34 | +0.05 | 401 | 398 | -3 |
| `cps/shelf.py` | FIND-049 (PR #20) | 5.98 | 6.12 | +0.14 | 126 | 125 | -1 |
| `cps/helper.py` | FIND-081, 056 (PR #23, #24) | 5.16 | 5.24 | +0.08 | 246 | 244 | -2 |
| `cps/file_helper.py` | FIND-080/109 (PR #16) | 5.74 | 5.93 | +0.19 | 19 | 18 | -1 |
| `cps/web.py` | FIND-150, 126 (PR #17, #18) | 3.06 | 3.08 | +0.02 | 392 | 389 | -3 |
| `cps/dep_check.py` | FIND-069 (PR #25) | 6.88 | 7.08 | +0.20 | 26 | 24 | -2 |
| `cps/kobo.py` | FIND-069 (PR #25) | 5.75 | 5.77 | +0.02 | 207 | 206 | -1 |
| `cps/updater.py` | FIND-069 (PR #25) | 7.83 | 7.87 | +0.04 | 97 | 95 | -2 |
| `cps/jinjia.py` | FIND-117 (PR #26) | 6.28 | 6.70 | +0.42 | 31 | 27 | -4 |
| `cps/services/goodreads_support.py` | FIND-014, 085 (PR #21) | 7.31 | 7.41 | +0.10 | 27 | 26 | -1 |
| `cps/metadata_provider/comicvine.py` | FIND-010 (PR #21) | 5.91 | 6.14 | +0.23 | 10 | 9 | -1 |
| `cps/metadata_provider/google.py` | FIND-011 (PR #21) | 6.03 | 6.18 | +0.15 | 15 | 14 | -1 |
| `cps/metadata_provider/lubimyczytac.py` | FIND-012, 013 (PR #21) | 8.34 | 8.43 | +0.09 | 24 | 22 | -2 |
| `cps/metadata_provider/amazon.py` | FIND-116 (PR #21) | 5.60 | 5.60 | +0.00 | 25 | 25 | 0 |

## 5. Kapanan mesajlar (20)

| Konum (başlangıç) | Kod | Mesaj | Kod parçası | Bulgu (PR) |
| --- | --- | --- | --- | --- |
| `cps/admin.py:1169` | `W1514` | Using open without explicitly specifying an encoding (unspecified-encoding) | `with open(gdriveutils.CLIENT_SECRETS, 'r') as settings:` | FIND-069 (PR #25) |
| `cps/admin.py:1377` | `E1101` | Instance of 'Exception' has no 'orig' member (no-member) | `flash(_("Oops! Database Error: %(error)s.", error=e.orig), category="e` | FIND-049 (PR #20) |
| `cps/admin.py:2206` | `W0715` | Exception arguments suggest string formatting might be intended (raising-format-tuple) | `raise Exception("Could Not Parse LDAP Userfield: {}", user)` | FIND-078 (PR #22) |
| `cps/dep_check.py:29` | `W1514` | Using open without explicitly specifying an encoding (unspecified-encoding) | `with open(pip_installed) as f:` | FIND-069 (PR #25) |
| `cps/dep_check.py:39` | `W1514` | Using open without explicitly specifying an encoding (unspecified-encoding) | `with open(req_path, 'r') as f:` | FIND-069 (PR #25) |
| `cps/file_helper.py:85` | `W0702` | No exception type(s) specified (bare-except) | `except:` | FIND-080 (PR #16) |
| `cps/helper.py:302` | `W1116` | Second argument of isinstance is not a type (isinstance-second-argument-not-valid-type) | `if isinstance(list, value2):` | FIND-081 (PR #23) |
| `cps/helper.py:417` | `E1305` | Too many arguments for format string (too-many-format-args) | `log.error("File {} not found on gdrive"` | FIND-056 (PR #24) |
| `cps/jinjia.py:63` | `C0301` | Line too long (105/100) (line-too-long) | `# if word longer than 20 chars truncate line and append '...', otherwi` | FIND-117 (PR #26) yan etkisi |
| `cps/jinjia.py:159` | `C0301` | Line too long (105/100) (line-too-long) | `url = url_for('web.get_cover', book_id=book.id, resolution=shortname, ` | FIND-117 (PR #26) yan etkisi |
| `cps/jinjia.py:173` | `C0301` | Line too long (109/100) (line-too-long) | `url = url_for('web.get_series_cover', series_id=series.id, resolution=` | FIND-117 (PR #26) yan etkisi |
| `cps/jinjia.py:190` | `C0305` | Trailing newlines (trailing-newlines) | - | FIND-117 (PR #26) yan etkisi |
| `cps/kobo.py:1158` | `W1514` | Using open without explicitly specifying an encoding (unspecified-encoding) | `with open(kobo_file, "r") as f:` | FIND-069 (PR #25) |
| `cps/services/goodreads_support.py:89` | `W3101` | Missing timeout argument for method 'requests.get' can cause your program to hang indefinitely (missing-timeout) | `resp = requests.get(self.host+self.path, params=self.params,` | FIND-085 (PR #21) |
| `cps/shelf.py:287` | `E1101` | Instance of 'InvalidRequestError' has no 'orig' member (no-member) | `flash(_("Oops! Database Error: %(error)s.", error=e.orig), category="e` | FIND-049 (PR #20) |
| `cps/updater.py:155` | `W1514` | Using open without explicitly specifying an encoding (unspecified-encoding) | `return [x.strip() for x in open(filelist, 'r') if not x.startswith('#E` | FIND-069 (PR #25) |
| `cps/updater.py:411` | `W1514` | Using open without explicitly specifying an encoding (unspecified-encoding) | `with open(os.path.join(constants.BASE_DIR, "exclude.txt"), "r") as f:` | FIND-069 (PR #25) |
| `cps/web.py:1436` | `C0301` | Line too long (101/100) (line-too-long) | `flash(_(u"An unknown error occurred. Please try again later."), catego` | FIND-126 (PR #18) yan etkisi |
| `cps/web.py:1436` | `W1406` | The u prefix for strings is no longer necessary in Python >=3.0 (redundant-u-string-prefix) | `flash(_(u"An unknown error occurred. Please try again later."), catego` | FIND-126 (PR #18) yan etkisi |
| `cps/web.py:1438` | `W1406` | The u prefix for strings is no longer necessary in Python >=3.0 (redundant-u-string-prefix) | `flash(_(u"Please enter valid username to reset password"), category="e` | FIND-126 (PR #18) yan etkisi |

## 6. Devam eden mesajlar

- Aynı satırda süren: **3934**.
- Satırı değişen ama aynı mesajla süren: **2**. Bunlar düzeltilen satırlarda ya da onların hemen yanında; uyarı kodun yeni halinde de geçerli:

| Başlangıç | Son | Kod | Mesaj (son) |
| --- | --- | --- | --- |
| `cps/admin.py:2206` | `cps/admin.py:2207` | `W0719` | Raising too general exception: Exception (broad-exception-raised) |
| `cps/helper.py:417` | `cps/helper.py:417` | `C0209` | Formatting a regular string which could be an f-string (consider-using-f-string) |

## 7. Yeni çıkan mesajlar (0)

Yeni çıkan mesaj yok: düzeltmeler hiçbir dosyada yeni Pylint uyarısı doğurmadı.

## K5 gerekçesi (kod kalitesi / PEP 8: en az 5 tür)

K5, en az 5 kod kalitesi / PEP 8 bulgu **türünün** düzeltilmesini istiyor. Bu dönemde düzeltilen Pylint türleri ve son taramadaki karşılıkları:

| Tür | Sembol | Bulgu | PR | Son tarama |
| --- | --- | --- | --- | --- |
| `W0702` | bare-except | FIND-080 | #16 | Kapandı |
| `E1101` | no-member (`e.orig`) | FIND-049 | #20 | Kapandı (2 mesaj) |
| `W0715` | raising-format-tuple | FIND-078 | #22 | Kapandı |
| `W1116` | isinstance-second-argument-not-valid-type | FIND-081 | #23 | Kapandı |
| `E1305` | too-many-format-args | FIND-056 | #24 | Kapandı |
| `W1514` | unspecified-encoding | FIND-069 | #25 | Kapandı (6/10; kalan 4 kapsam dışı) |
| `W3101` | missing-timeout | FIND-085 | #21 | Kapandı |

Toplam **7 Pylint türü**. Buna ek olarak flake8'de 5 PEP 8 türü (E722, E501, E226, E302, W391) düzeltildi (`docs/5-karsilastirma/pep8-comparison.md`). Hedef karşılanıyor.

Sayım notu: `W0702` (Pylint) ile `E722` (flake8) aynı satırın iki aracın gözünden görünümü; tek değişiklikle kapandılar. Karşılaştırmada ayrı uyarı olarak sayılırlar, ama ayrı düzeltme sayılmazlar. Aynı şekilde `W3101`, B113 düzeltmesinin (PR #21) yan etkisidir.

Bazı mesajlar düzeltmenin dolaylı sonucu olarak da kapandı: silinen veya bölünen satırlardaki `C0301` (line-too-long), `W1406` (redundant-u-string-prefix) ve `jinjia.py`'deki `C0305` (trailing-newlines). Bunlar ayrı düzeltme türü olarak sayılmadı.

## `cps/metadata_provider/` kapsam notu

`cps/metadata_provider/` dizininde `__init__.py` yok. Bu yüzden `python -m pylint cps.py cps` komutu bu dizindeki 6 dosyaya (amazon, comicvine, douban, google, lubimyczytac, scholar) girmiyor: başlangıç ve son `pylint.txt`'de bu dizine ait **0 mesaj** var. Bandit (`-r cps`) ve flake8 ise dizini tarıyor.

Sonuç: B113 düzeltmesi (PR #21) bu dizindeki 4 `missing-timeout` (W3101) uyarısını da kapattı (dosya bazlı çalıştırmada görülüyor, bölüm 4), ama resmi karşılaştırmada yalnızca `cps/services/goodreads_support.py`'deki 1 `W3101` (FIND-085) kapanmış görünüyor. Tarama parametreleri baseline ile aynı kalsın diye kapsam değiştirilmedi; bu bir araç kullanım sınırlılığı olarak final rapora (bölüm 10) yazılır.

