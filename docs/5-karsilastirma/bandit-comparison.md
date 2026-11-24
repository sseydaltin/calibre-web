# Bandit önce-sonra karşılaştırması

Bu dosya `scripts/compare_reports.py` ile ham raporlardan üretilir; elle düzenlenmez. Ham raporlar değiştirilmez.

- Başlangıç: `reports/baseline/` · commit `6e840acb` (upstream `master`, `docs/1-kapsam/baseline-commit.txt`)
- Son: `reports/final/` · commit `830d3a80` (`project-analysis`, 24 Kasım 2026, K10)
- Aynı araç sürümü, aynı kapsam (`cps/` + `cps.py`), aynı parametreler (CLAUDE.md → "Tarama komutları"; `docs/surec/environment-notes.md` → "Tarama kayıtları").
- Eşleştirme: normalize yol + kural kodu + kod parçası (kaynak satırın metni). Satırı yeniden biçimlenip aynı mesajla süren uyarılar "devam eden (satırı değişti)" sayılır.
- Susturma: bu dönemde `# nosec`, `# noqa` veya `# pylint: disable` eklenmedi (K6); aşağıdaki tüm kapanışlar kod düzeltmesidir.
- Bandit varsayılan ayarlarla, tüm testler (K4). İki rapor birlikte değerlendirildi: `bandit-cps.json` (`-r cps`) ve `bandit-entrypoint.json` (`cps.py`).


## 1. Özet

| Ölçü | Başlangıç | Son | Fark |
| --- | --- | --- | --- |
| Toplam bulgu | 43 | 38 | -5 |
| HIGH önem | 0 | 0 | 0 |
| MEDIUM önem | 14 | 9 | -5 |
| LOW önem | 29 | 29 | 0 |
| `bandit-cps.json` | 42 | 37 | -5 |
| `bandit-entrypoint.json` | 1 | 1 | 0 |
| Taranan satır (LOC) | 31597 | 31608 | +11 |
| `# nosec` satırı | 10 | 10 | 0 |
| Kapanan |  | 5 |  |
| Devam eden |  | 38 |  |
| Yeni çıkan |  | 0 |  |

`# nosec` sayısı değişmedi: bu dönemde susturma yorumu eklenmedi (K6). LOC artışı, düzeltmelerde satır bölmelerinden kaynaklanıyor.

## 2. Önem × güven matrisi

**Başlangıç**

| Önem \ Güven | HIGH | MEDIUM | LOW | Toplam |
| --- | --- | --- | --- | --- |
| **HIGH** | 0 | 0 | 0 | 0 |
| **MEDIUM** | 8 | 1 | 5 | 14 |
| **LOW** | 19 | 10 | 0 | 29 |
| **Toplam** | 27 | 11 | 5 | 43 |

**Son**

| Önem \ Güven | HIGH | MEDIUM | LOW | Toplam |
| --- | --- | --- | --- | --- |
| **HIGH** | 0 | 0 | 0 | 0 |
| **MEDIUM** | 8 | 1 | 0 | 9 |
| **LOW** | 19 | 10 | 0 | 29 |
| **Toplam** | 27 | 11 | 0 | 38 |

## 3. Test kimliği (test_id) bazında

| test_id | Ad | Önem | Başlangıç | Son | Fark |
| --- | --- | --- | --- | --- | --- |
| `B101` | assert_used | LOW | 12 | 12 | 0 |
| `B103` | set_bad_file_permissions | MEDIUM | 2 | 2 | 0 |
| `B104` | hardcoded_bind_all_interfaces | MEDIUM | 1 | 1 | 0 |
| `B105` | hardcoded_password_string | LOW | 8 | 8 | 0 |
| `B107` | hardcoded_password_default | LOW | 1 | 1 | 0 |
| `B110` | try_except_pass | LOW | 4 | 4 | 0 |
| `B112` | try_except_continue | LOW | 1 | 1 | 0 |
| `B113` | request_without_timeout | MEDIUM | 5 | 0 | -5 |
| `B307` | blacklist | MEDIUM | 1 | 1 | 0 |
| `B310` | blacklist | MEDIUM | 1 | 1 | 0 |
| `B403` | blacklist | LOW | 1 | 1 | 0 |
| `B404` | blacklist | LOW | 1 | 1 | 0 |
| `B606` | start_process_with_no_shell | LOW | 1 | 1 | 0 |
| `B704` | markupsafe_markup_xss | MEDIUM | 4 | 4 | 0 |

## 4. Kapanan bulgular (5)

| Konum (başlangıç) | test_id | Önem/Güven | Kod parçası | Bulgu (PR) |
| --- | --- | --- | --- | --- |
| `cps/metadata_provider/comicvine.py:53` | `B113` | MEDIUM/LOW | `result = requests.get(` | FIND-010 (PR #21) |
| `cps/metadata_provider/google.py:54` | `B113` | MEDIUM/LOW | `results = requests.get(Google.SEARCH_URL + query + Google.AP` | FIND-011 (PR #21) |
| `cps/metadata_provider/lubimyczytac.py:121` | `B113` | MEDIUM/LOW | `result = requests.get(self._prepare_query(title=query))` | FIND-012 (PR #21) |
| `cps/metadata_provider/lubimyczytac.py:215` | `B113` | MEDIUM/LOW | `response = requests.get(match.url)` | FIND-013 (PR #21) |
| `cps/services/goodreads_support.py:89` | `B113` | MEDIUM/LOW | `resp = requests.get(self.host+self.path, params=self.params,` | FIND-014 (PR #21) |

Hepsi PR #21'de `timeout=(5, 30)` eklenerek kod düzeyinde kapandı (susturma yok). Aynı PR, Pylint `W3101` (FIND-085) uyarısını da kapattı.

## 5. Devam eden ve yeni çıkan bulgular

- Devam eden: **38** (aynı satırda 38, satırı değişen 0).

- Yeni çıkan: **0**.


Devam eden bulguların test_id dağılımı: `B101` ×12, `B103` ×2, `B104` ×1, `B105` ×8, `B107` ×1, `B110` ×4, `B112` ×1, `B307` ×1, `B310` ×1, `B403` ×1, `B404` ×1, `B606` ×1, `B704` ×4. Bu bulguların her biri kayıtta kodla incelendi (`docs/3-inceleme/review-bandit.md`, `docs/findings-register.csv`): yanlış pozitif ya da düşük öncelikli olarak kabul edildi.

## 6. Güvenlik düzeltmeleri ve K5 (en az 3 güvenlik bulgusu)

| Bulgu | Tür | Dosya | PR | Bandit'te görünür mü? | Son tarama |
| --- | --- | --- | --- | --- | --- |
| FIND-010…014 | B113 zaman aşımsız dış istek | `metadata_provider/*`, `services/goodreads_support.py` | #21 | Evet (MEDIUM/LOW) | Kapandı (5) |
| FIND-116 | Zaman aşımsız `requests.Session` isteği | `metadata_provider/amazon.py:61, 121` | #21 | **Hayır** | Kod düzeltildi; araç uyarısı yok |
| FIND-150 | İçerik kısıtlaması e-okuyucuya göndermede aşılıyor | `web.py` (`send_to_ereader`) | #17 | Hayır (yetki mantığı) | Kod düzeltildi; araç uyarısı yok |
| FIND-126 | Parola sıfırlamada kullanıcı adı tahmini | `web.py` (`login_post`) | #18 | Hayır (mantık hatası) | Kısmi: tahmin kapandı, onaysız sıfırlama öneri |

Toplam 8 güvenlik bulgusu düzeltildi (B113 ×5, FIND-116, FIND-150, FIND-126); K5'in "en az 3 güvenlik bulgusu" hedefi karşılanıyor. Buna ek olarak 31 Bandit kaydı kodla incelenip **yanlış pozitif** olarak gerekçelendirildi (`docs/findings-register.csv`).

## 7. Araç sınırlılığı: B113 `requests.Session` çağrılarını görmüyor

Bandit B113 (`request_without_timeout`) yalnızca modül düzeyindeki `requests.get/post/...` çağrılarını tanıyor; bir `requests.Session()` nesnesi üzerinden yapılan `session.get(...)` çağrılarını yakalamıyor. Manuel incelemede bu türden iki dosya bulundu:

- **FIND-116** — `cps/metadata_provider/amazon.py:61, 121`: iki `session.get` çağrısı. Baseline Bandit raporunda bu dosya için hiç sonuç yok. PR #21'de aynı `timeout=(5, 30)` değeriyle düzeltildi.
- **FIND-160** — `cps/metadata_provider/douban.py:105, 127, 154`: `douban.py:65`'te oluşturulan `requests.Session` ile üç zaman aşımsız istek. PR #21 incelemesi sırasında bulundu; K10 kod dondurması nedeniyle düzeltilmedi, kayıtta "Kabul edildi (düzeltilmeyecek)", raporda öneri.

Bu yüzden Bandit sayısındaki düşüş (42 → 37), yapılan güvenlik düzeltmelerinin tamamını göstermez: FIND-116, FIND-150 ve FIND-126 araç sayılarında görünmeyen düzeltmelerdir. Tersine, son taramada B113 kalmaması projede zaman aşımsız dış istek kalmadığı anlamına gelmez (FIND-160).

Ayrıca iki gerçek risk upstream'de `# nosec` ile susturulmuş olduğu için Bandit raporunda hiç görünmüyor: FIND-044 (`constants.py:140`, varsayılan `admin/admin123`) ve FIND-159'un iki parçası (`gdrive.py:48` B105, `gdrive.py:143` B324). Bunlar manuel incelemeyle bulundu.

