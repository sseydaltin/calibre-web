# Calibre-Web Üzerinde Güvenlik İçin Statik Kod Analizi

**Fırat Üniversitesi Mühendislik Fakültesi Yazılım Mühendisliği · YMÜ 415 Yazılım Geçerleme ve Sınama · Proje Raporu**

| Öğrenci | Numara |
| --- | --- |
| Şeyda Altın | [numara] |
| Dilara Yıldırım | [numara] |
| Hasan Kurt | [numara] |
| Emre Bulut | [numara] |

## 1. Giriş

**Amaç.** Bu projede gerçek ve yeterli büyüklükte bir açık kaynak Python uygulaması, kod **çalıştırılmadan** statik analiz araçlarıyla incelendi. Güvenlik için Bandit, kod kalitesi için Pylint, PEP 8 uygunluğu için flake8 kullanıldı. Araç bulguları elle doğrulandı ve gerçek sorun, düşük öncelikli uyarı ya da yanlış pozitif olarak sınıflandırıldı. Seçilen sorunlar küçük, davranışı koruyan değişikliklerle düzeltildi. Son olarak araçlar aynı sürüm ve parametrelerle yeniden çalıştırılıp başlangıç ile son durum karşılaştırıldı.

**İncelenen proje.** Calibre-Web, bir Calibre e-kitap kitaplığını web üzerinden tarama, okuma, indirme ve yönetme imkânı veren bir Flask uygulamasıdır [1]. Kullanıcı ve yönetici yetkilendirmesi, OPDS beslemesi, kitap yükleme ve biçim dönüştürme (harici Calibre ikili dosyalarıyla), harici servislerden metadata indirme, Kobo senkronizasyonu, Google Drive entegrasyonu ile LDAP/OAuth girişi gibi özellikler içerir. Kimlik doğrulama, dosya işleme, harici süreç çağrısı ve ağ isteği gibi güvenlik açısından kritik alanları bir arada barındırdığı için seçildi. Proje GPL v3 lisanslıdır; lisans ve telif bildirimlerine dokunulmadı.

**Kapsam.** Analiz, upstream [1] `master` dalının `6e840acb` commit'i (20 Eylül 2026) üzerinde yapıldı. Otomatik tarama kapsamı uygulama paketi `cps/` ile giriş noktası `cps.py`'dir. `test/`, örnek kitaplık verisi ve JavaScript/CSS/HTML şablonları Python statik analizinin hedefi olmadığı için kapsam dışında bırakıldı. Taranan kodun büyüklüğü Tablo 1'de verilmiştir. En büyük dosya, otomatik üretilmiş bir dil adı sözlüğü olan `iso_language_names.py`'dir (11.732 satır). İş mantığı ağırlıkla `admin.py` (2.211), `editbooks.py` (1.762), `web.py` (1.675), `kobo.py` (1.320), `db.py` (1.206) ve `helper.py` (1.165) dosyalarındadır.

**Tablo 1.** Taranan kapsamın büyüklüğü (`cps/` + `cps.py`)

| Ölçü | Değer |
| --- | --- |
| Python dosyası | 101 |
| Toplam satır | 37.831 |
| Kod satırı (boş satır ve tam satır yorumlar hariç) | 31.597 |

Uygulama katmanlı bir yapıya sahiptir. Rota katmanı (`web.py`, `admin.py`, `editbooks.py`, `opds.py`, `shelf.py`, `kobo.py`) HTTP isteklerini ve yetki dekoratörlerini taşır. `ub.py` kullanıcı ve oturum veritabanını, `db.py` Calibre'nin `metadata.db` dosyasını modeller. `services/` isteğe bağlı dış entegrasyonları, `tasks/` ise dönüştürme ve e-posta gibi arka plan işlerini içerir. `cps/cw_login/` ve `cps/cw_advocate/` uygulamaya gömülü üçüncü taraf koddur. Bu iki dizin taramaya dahil edildi, ancak içlerinde düzeltme yapılmadı. Dizin yapısı ve güvenlik açısından kritik bölgelerin haritası `docs/architecture.md` dosyasındadır.

**Çözülmek istenen problem.** Statik analiz araçları çok sayıda uyarı üretir. Bu uyarıların önemli bir kısmı yanlış pozitif ya da düşük önceliklidir; bazı gerçek sorunlar ise araçlar tarafından hiç görülmez. Projenin sorusu şudur: araç çıktısı ile elle yapılan kod incelemesi birlikte kullanıldığında gerçek riskler nasıl ayırt edilir, hangileri güvenle düzeltilebilir ve düzeltmenin etkisi aynı araçlarla nasıl ölçülür?

## 2. Yöntem

**Araçlar ve ortam.** Tüm taramalar Windows üzerinde, PowerShell'de ve sabitlenmiş bir sanal ortamda (`requirements-lock.txt`) yapıldı. Araç sürümleri ve görevleri Tablo 2'de verilmiştir. Uygulamanın bağımlılıkları da Pylint'in importları çözebilmesi için kuruldu; ancak uygulama hiçbir aşamada çalıştırılmadı. Windows'ta derlenemeyen iki LDAP paketi (`python-ldap`, `Flask-SimpleLDAP`) kurulamadı. Bu paketlerden kaynaklanan 2 `E0401 import-error` mesajı bulgu sayılmadı, ortam sorunu olarak `docs/environment-notes.md` dosyasına kaydedildi.

**Tablo 2.** Kullanılan araçlar

| Araç | Sürüm | Ölçtüğü | Parametreler |
| --- | --- | --- | --- |
| Python | 3.12.10 | – | `.venv` |
| Bandit [3] | 1.9.4 | Güvenlik açığı örüntüleri; önem × güven | Varsayılan, tüm testler; `-r cps` ve `cps.py` ayrı |
| Pylint [4] | 4.1.3 (astroid 4.3.4) | Kod kalitesi; 10 üzerinden puan | Varsayılan (yapılandırma dosyası yok) |
| flake8 [5] | 7.4.1 | PEP 8 [6] stil kuralları | `--isolated --select=E,W`, satır uzunluğu 79 |

**Çalışma ilkeleri.** Ekip kararları kayıt altına alındı (K1–K10, `CLAUDE.md`).

- **Değişmeyen tarama:** Başlangıç ve son taramada aynı araç sürümü, aynı kapsam ve aynı komutlar kullanıldı. Başlangıç raporları (`reports/baseline/`) kaynak kodda herhangi bir değişiklik yapılmadan önce commit edildi ve sonradan değiştirilmedi.
- **Statik doğrulama:** Kod çalıştırılmadı (K2). Bir kütüphanenin davranışını doğrulamak gerektiğinde, uygulamayı başlatmadan yalnızca o kütüphane veya fonksiyon küçük bir Python parçasıyla denendi (K9 "yalıtılmış deneme"; ör. `zipfile`'ın bozuk arşivde hangi istisnaları fırlattığı).
- **Bulgu kaydı:** Her bulgu `docs/findings-register.csv` dosyasında tek satır oldu. Her satırda doğrulama sonucu, kodla desteklenmiş gerekçe, inceleyen ve gözden geçiren kişi yer alır. Yüzlerce benzer stil uyarısı kural koduna göre gruplandı.
- **Sınıflandırma ölçütü:** "Gerçek sorun" için kod yolunun izlenip zararın gösterilebilmesi gerekti. "Düşük öncelikli uyarı", etkisi sınırlı ya da başka bir korumayla örtülü durumlar için kullanıldı. "Yanlış pozitif" kararı için uyarının bu kodda oluşamayacağının kodla gösterilmesi şart koşuldu.
- **Düzeltme yaklaşımı:** Yalnızca seçilmiş, anlamlı bulgular küçük ve davranışı koruyan değişikliklerle düzeltildi. Projenin black/autopep8 gibi araçlarla toplu biçimlendirilmesi bilinçli olarak yapılmadı, çünkü binlerce satırlık bir diff önce-sonra karşılaştırmasını anlamsızlaştırır (K5). Bu yaklaşım ders yürütücüsüyle teyit edildi. Hedef en az 3 güvenlik bulgusu ile en az 5 kod kalitesi/PEP 8 türüydü.
- **Susturma düzeltme değildir:** `# nosec`, `# noqa` veya `# pylint: disable` eklenmedi (K6). Raporda görülen bütün kapanışlar kod düzeltmesidir.
- **Değişiklik süreci:** Her düzeltme ayrı bir dalda yapıldı ve Pull Request ile birleştirildi. Düzeltmeyi yapan kişiden farklı bir ekip üyesi her değişikliği inceledi. Doğrulama için `py_compile` ve ilgili araçla dosya bazlı önce/sonra taraması kullanıldı.
- **Karşılaştırma yöntemi:** Önce-sonra eşleştirmesi `scripts/compare_reports.py` ile yapıldı. Satır numaraları kaydığı için her uyarı "normalize dosya yolu + kural kodu + kaynak satırın metni" anahtarıyla eşlendi. Satırı değişen ama aynı uyarıyı taşıyan durumlar "devam eden" sayıldı.
- **Bağımsız tekrar:** Son taramalar `830d3a80` commit'i üzerinde yapıldı. Emre Bulut aynı taramaları kendi bilgisayarında, aynı commit ve aynı sürümlerle bağımsız olarak tekrarladı ve birebir aynı sonuçları aldı.
- **Yapay zekâ desteği:** Analiz, doğrulama ve dokümantasyon sürecinde yapay zekâ destekli kodlama asistanı (Claude Code) [12] kullanılmıştır. Araç çıktıları, bulgu gerekçeleri ve düzeltmeler ekip üyelerince gözden geçirilmiş; her düzeltme farklı bir ekip üyesi tarafından incelenmiştir.

**İş bölümü.** Şeyda Altın: depo yönetimi, kapsam ve mimari, Pylint/PEP 8 analizi ve düzeltmeleri. Dilara Yıldırım: Bandit taramaları, bulgu kaydı, B113 düzeltmesi. Emre Bulut: kimlik doğrulama ve yetki incelemesi. Hasan Kurt: dosya işleme, harici süreç ve ağ çağrıları incelemesi. Ekip deposu [2]'dir.

## 3. Uygulama / Geliştirim Aşamaları

Çalışma altı adımda ilerledi. İlk adımda başlangıç taramaları yapıldı (3.1, 3.2, 3.4). Ardından Bandit bulguları ve iki kritik alan elle incelendi (3.3). Tüm bulgular kayda alınıp sınıflandırıldı (3.5). Seçilen sorunlar düzeltildi (3.6). Son adımda araçlar yeniden çalıştırıldı (bölüm 4).

### 3.1 Pylint ile başlangıç kalite analizi

Başlangıç taraması **6.42/10** puan ve **3999** mesaj verdi (Tablo 3). Mesajların yaklaşık üçte ikisi biçim ve adlandırma kurallarına ilişkin `convention` mesajlarıdır. En sık kodlar `C0301` line-too-long (911), `C0116` missing-function-docstring (779), `C0209` consider-using-f-string (303) ve `E0611` no-name-in-module (252) oldu. En çok mesaj alan dosyalar `admin.py` (336) ve `web.py` (333) idi.

**Tablo 3.** Pylint başlangıç kategori dağılımı

| Kategori | Adet |
| --- | --- |
| convention (C) | 2646 |
| refactor (R) | 537 |
| warning (W) | 454 |
| error (E) | 324 |
| information (I) | 38 |
| **Toplam** | **3999** |

`error` kategorisindeki mesajların büyük kısmı gerçek hata değildir. 252 `E0611` mesajının 250'si, `cps/__init__.py`'nin alt modülleri çalışma zamanında paket özniteliği olarak atamasından kaynaklanır: astroid bu dinamik atamayı göremediği için var olan adları "yok" sayar. Bu mesajlar yanlış pozitif olarak tek satırda kaydedildi (FIND-045). Buna karşılık bazı `warning` ve `error` mesajları gerçek hatalara işaret etti. Örneğin `get_sorted_author` içindeki ters `isinstance` çağrısı (`W1116`), hata işleyicisinin her durumda kendisinin çökmesine yol açıyordu (FIND-081).

### 3.2 Bandit ile güvenlik analizi ve risk sınıflandırması

Bandit `cps/` dizininde 42, `cps.py` dosyasında 1 olmak üzere toplam **43** bulgu verdi. Bunların **0'ı HIGH**, **14'ü MEDIUM** ve 29'u LOW önemdedir. Önem × güven dağılımı Tablo 4'te verilmiştir. MEDIUM bulgular şu kurallardan geldi: `B113` zaman aşımsız dış istek (5), `B704` `Markup` ile olası XSS (4), `B103` dosya izni (2), `B104` tüm arayüzlerde dinleme (1), `B307` `eval` (1) ve `B310` `urlopen` (1). LOW bulguların en sık kuralları `B101` assert (12; 9'u gömülü üçüncü taraf kodda) ve `B105` sabit parola dizgisi (8) idi. Upstream kodunda önceden eklenmiş 10 `# nosec` satırı vardı. Bu satırlar Bandit raporunda görünmediği için ayrıca elle incelendi.

**Tablo 4.** Bandit başlangıç önem × güven matrisi

| Önem \ Güven | HIGH | MEDIUM | LOW | Toplam |
| --- | --- | --- | --- | --- |
| HIGH | 0 | 0 | 0 | 0 |
| MEDIUM | 8 | 1 | 5 | 14 |
| LOW | 19 | 10 | 0 | 29 |
| **Toplam** | 27 | 11 | 5 | 43 |

Başlangıç Bandit raporları ilk denemede yanlışlıkla 1.8.6 sürümüyle üretilmişti. Bu fark, kod değişikliği yapılmadan önce fark edildi. Raporlar aynı commit ve aynı parametrelerle 1.9.4 sürümüyle yeniden üretildi, eski raporlar kanıt olarak saklandı (K8, `evidence/bandit-1.8.6-original/`).

### 3.3 Önemli güvenlik bulgularının kod üzerinden incelenmesi

**Bandit bulguları.** 14 MEDIUM bulgunun tamamı kod parçasıyla incelendi (`docs/review-bandit.md`):

- **B704 (4):** XSS'e yol açmıyor. `Markup` ile işaretlenen yorum HTML'i önce `nh3` kütüphanesiyle temizleniyor. Yalıtılmış denemede betik, olay öznitelikleri ve `javascript:` adresleri temizlendi. Bu bulgular yanlış pozitif olarak işaretlendi.
- **B103 (2):** Unix soketine verilen `0o660` izni diğer kullanıcılara erişim vermiyor; tasarım gereği olduğu için yanlış pozitif sayıldı.
- **B310 (1):** `urlopen`'a ulaşan değer kullanıcıdan gelmiyor; yanlış pozitif sayıldı.
- **B307 ve B104 (birer):** Sömürülebilir bir yol bulunmadı; düşük öncelikli uyarı olarak kaydedildi. B104'ün varsayılan yönetici hesabıyla (FIND-044) birlikte riski artırdığı not edildi.
- **B113 (5):** Metadata sağlayıcılarındaki ve Goodreads servisindeki zaman aşımsız `requests.get` çağrıları **gerçek sorun** olarak değerlendirildi (FIND-010–014). Dış servis yanıt vermezse istek süresiz bekler ve sunucu kaynağı tükenebilir (CWE-400 [7]). Goodreads çağrısı, anonim gezinme açıksa girişsiz de tetiklenebiliyor.

**Kimlik doğrulama ve yetki (Emre Bulut).** Bu alanda 20 kontrol noktası incelendi: 2 gerçek sorun, 7 düşük öncelikli uyarı ve 11 noktada sorun yok. Yönetici rotalarının 49'unun 46'sı giriş ve yönetici dekoratörleriyle korunuyor; kalan üçü varsayılan olarak kapalı ya da yalnızca kullanıcının kendi verisine dokunuyor. Parolalar `scrypt` ile saklanıyor, `next` parametresi üzerinden açık yönlendirme yapılamıyor. Bulunan iki gerçek sorun şunlardır:

- **FIND-044:** İlk kurulumda `admin`/`admin123` hesabı açılıyor ve parola değişikliği zorlanmıyor. Bu satır upstream'de `# nosec` ile susturulduğu için Bandit raporunda görünmüyor.
- **FIND-126:** "Parolamı unuttum" seçeneği var olan ve olmayan kullanıcı adına farklı mesaj gösteriyor. Bu fark kullanıcı adlarının tahmin edilmesine izin veriyor (CWE-204 [8]).

**Dosya işleme, harici süreçler ve ağ (Hasan Kurt).** Bu alanda 23 kontrol noktası incelendi: 3 gerçek sorun, 8 düşük öncelikli uyarı ve 12 noktada sorun yok. İndirmede dizin geçişi (path traversal) yok, çünkü dosya yolu veritabanından geliyor ve gönderim `send_from_directory` ile yapılıyor. Arşivler diske açılmadığı için "zip slip" saldırısı mümkün değil. Tek `Popen` çağrısı `shell=False` ve liste argümanla çalışıyor; URL'den kapak indirmede SSRF koruması etkin. Bulunan gerçek sorunlar şunlardır:

- **FIND-150:** E-okuyucuya gönderme rotası kitabı filtresiz `get_book()` ile alıyor. Bu yüzden içerik kısıtlaması olan bir kullanıcı, göremediği bir kitabı kitap numarasını vererek kendi e-posta adresine gönderebiliyor (CWE-285 [9]).
- **FIND-151:** Yöneticinin "yüklemeye izin ver" ayarı yalnızca arayüzde uygulanıyor, sunucu tarafında kontrol edilmiyor.
- **FIND-152:** Google Drive kurulumlarında seri küçük resmi üretimi, dosya içeriğini URL sanıp `urlopen()`'a verdiği için her zaman hata veriyor (işlev hatası).

Ayrıca B113 düzeltmesi incelenirken aynı türden ama Bandit'in görmediği zaman aşımsız istekler bulundu. `amazon.py`'de iki (FIND-116), `douban.py`'de üç (FIND-160) `requests.Session` çağrısı vardı. Bandit B113 kuralı `Session` nesnesi üzerinden yapılan çağrıları tanımıyor. Ayrıntılar `docs/report-part-auth.md` ve `docs/report-part-file-handling.md` dosyalarındadır.

### 3.4 PEP 8 uygunluk analizi

flake8 başlangıçta **3409** ihlal ve 42 farklı ihlal kodu verdi. Bu ihlallerin **2879'u (%84) `E501`** satır uzunluğu ihlalidir; PEP 8'in 79 karakter sınırı, projede yaygın olan 100–120 karakterlik satırlarla çakışıyor. Sonraki sıklar `E221` operatör öncesi fazla boşluk (63), `E231` virgül sonrası eksik boşluk (63), `E128` devam satırı girintisi (56) ve `E302` iki boş satır kuralı (33) oldu. En çok ihlal içeren dosyalar `web.py` (398), `admin.py` (337) ve `editbooks.py` (290) idi. PEP 8 ihlalleri büyük ölçüde okunabilirlik sorunudur; tek gerçek davranış etkisi olan ihlal, çıplak `except:` kullanımıydı (`E722`, FIND-109).

### 3.5 Bulguların değerlendirilmesi

Bulgu kaydında 137 satır bulunuyor (Tablo 5). Pylint ve flake8 satırları kural koduna göre gruplanmıştır; örneğin tek bir satır 2879 `E501` ihlalini temsil eder. Bu yüzden satır sayısı mesaj sayısı değil, değerlendirilmiş bulgu grubu sayısıdır. Gömülü üçüncü taraf kodda 11 satır var; bunlar incelendi ama düzeltilmedi (K7). Her satırda gerekçe kodla destekleniyor ve inceleyen kişi ile gözden geçiren kişi farklı.

**Tablo 5.** Bulgu kaydında kaynağa göre doğrulama sonuçları

| Kaynak | Gerçek sorun | Düşük öncelikli | Yanlış pozitif | Toplam |
| --- | --- | --- | --- | --- |
| Bandit | 5 | 7 | 31 | 43 |
| Pylint | 10 | 40 | 10 | 60 |
| flake8 (PEP 8) | 2 | 8 | 2 | 12 |
| Manuel inceleme | 7 | 15 | 0 | 22 |
| **Toplam** | **24** | **70** | **43** | **137** |

Bandit bulgularının 31'i (%72) kodla gerekçelendirilmiş yanlış pozitiftir. Buna karşılık manuel incelemede bulunan 7 gerçek sorunun hiçbiri Bandit uyarısı olarak görünmedi. Bunların kimi yetki veya mantık hatası (FIND-126, 150, 151), biri işlev hatası (FIND-152), biri `# nosec` ile susturulmuş (FIND-044), ikisi de aracın kuralının kapsamadığı türden (FIND-116, 160). 24 gerçek sorunun 17'si düzeltildi (3.6). Kalan 7'si (FIND-044, 057, 082, 101, 151, 152, 160) ve 70 düşük öncelikli uyarının tamamı K10 kod dondurması ve kapsam nedeniyle "Kabul edildi (düzeltilmeyecek)" olarak kapatıldı; bunlar raporda öneri olarak yer alıyor (bölüm 5).

### 3.6 Düzeltmeler

Tablo 6, birleştirilen düzeltmeleri özetler. Her biri ayrı bir PR'dır ve her birinde `py_compile` ile ilgili araçların dosya bazlı önce/sonra taraması çalıştırıldı. Hedeflenen uyarıların hepsi kapandı ve hiçbir PR yeni bir uyarı doğurmadı.

**Tablo 6.** Düzeltmeler

| Bulgu | Tür | PR | Düzelten | Gözden geçiren |
| --- | --- | --- | --- | --- |
| FIND-010–014, 116, 085 | Güvenlik (B113, `Session` zaman aşımı) / kalite (W3101) | #21 | Dilara Yıldırım | Hasan Kurt |
| FIND-150 | Güvenlik (yetki) | #17 | Hasan Kurt | Emre Bulut |
| FIND-126 | Güvenlik (bilgi sızıntısı) | #18 | Emre Bulut | Şeyda Altın |
| FIND-080 (+FIND-109) | Kalite (W0702, E722) | #16 | Hasan Kurt | Emre Bulut |
| FIND-049 | Kalite (E1101) | #20 | Emre Bulut | Dilara Yıldırım |
| FIND-078 | Kalite (W0715) | #22 | Şeyda Altın | Dilara Yıldırım |
| FIND-081 | Kalite (W1116) | #23 | Şeyda Altın | Dilara Yıldırım |
| FIND-056 | Kalite (E1305) | #24 | Şeyda Altın | Dilara Yıldırım |
| FIND-069 | Kalite (W1514) | #25 | Şeyda Altın | Dilara Yıldırım |
| FIND-117 | PEP 8 (`jinjia.py`) | #26 | Şeyda Altın | Dilara Yıldırım |

**FIND-010–014, FIND-116 (PR #21): dış isteklere zaman aşımı.** 5 dosyada 7 çağrıya aynı değer eklendi (örnek `lubimyczytac.py:215`):

```python
response = requests.get(match.url)                       # önce
response = requests.get(match.url, timeout=(5, 30))      # sonra
```

Bağlantı için 5 saniye, okuma için 30 saniye sınır kondu [10]. Zaman aşımında fırlatılan istisna her yolda zaten mevcut `except` bloklarıyla yakalanıyor ve fonksiyon boş sonuç dönüyor; bu yüzden davranış değişmedi, yalnızca süresiz bekleme kalktı. Bandit'te 5 `B113`, Pylint'te 1 `W3101` kapandı.

**FIND-150 (PR #17): e-okuyucuya göndermede içerik kısıtlaması.**

```python
book = calibre_db.get_book(book_id)                                        # önce
book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)     # sonra
```

Gönderme rotası artık indirme rotasıyla aynı filtreyi (dil, etiket ve özel sütun kısıtlamaları) uyguluyor. Kısıtlı bir kitap için mevcut "biçim desteklenmiyor" yanıtı dönüyor; yeni bir hata yolu eklenmedi.

**FIND-126 (PR #18): parola sıfırlamada tek mesaj.**

```python
flash(_(u"Please enter valid username to reset password"), category="error")  # önce (kullanıcı yoksa)
flash(_(u"New Password was sent to your email address"), category="info")      # sonra (her durumda)
```

Var olan kullanıcı, olmayan kullanıcı ve hata durumlarında artık aynı mesaj ve aynı HTTP kodu dönüyor. Yöneticinin gerçek durumu görebilmesi için log satırları korundu. Kullanıcı adı tahmini kapandı. Onay bağlantısı olmadan parola sıfırlanması sorunu ise büyük bir değişiklik gerektirdiği için öneri olarak kaldı.

**FIND-080 / FIND-109 (PR #16): çıplak `except` daraltıldı** (`file_helper.py:85`).

```python
        except:                                                                  # önce
        except (zipfile.BadZipFile, OSError, ValueError, NotImplementedError):  # sonra
```

İstisna listesi standart kütüphane `zipfile` [11] üzerinde yalıtılmış denemeyle doğrulandı: 60.000 bozuk ZIP örneğinde bu dört tür dışında istisna çıkmadı. Değişiklik Pylint `W0702` ve flake8 `E722` uyarılarını birlikte kapattı.

**FIND-049 (PR #20): hata işleyicisinde `AttributeError`** (`admin.py:1374, 1377`, `shelf.py:287`).

```python
flash(_("Oops! Database Error: %(error)s.", error=e.orig), ...)                  # önce
flash(_("Oops! Database Error: %(error)s.", error=getattr(e, 'orig', e)), ...)   # sonra
```

Yakalanan istisnanın `orig` özniteliği yoksa kullanıcıya hata mesajı yerine 500 hatası dönüyordu. Yeni kod, projede `editbooks.py`'de zaten kullanılan örüntüyle aynıdır.

**FIND-078 (PR #22): hata mesajı biçimlendirilmiyordu** (`admin.py:2206`).

```python
raise Exception("Could Not Parse LDAP Userfield: {}", user)    # önce
raise Exception(f"Could Not Parse LDAP Userfield: {user}")     # sonra
```

`.format()` kullanmak yeni bir `C0209` uyarısı doğurduğu için f-string tercih edildi.

**FIND-081 (PR #23): ters `isinstance`** (`helper.py:302`).

```python
if isinstance(list, value2):    # önce: her zaman TypeError
if isinstance(value, list):     # sonra
```

**FIND-056 (PR #24): eksik yer tutucu** (`helper.py:417`). Log mesajı iki argüman alıyor ama biçim dizgisinde tek yer tutucu vardı, bu yüzden dosya adı kayboluyordu.

```python
log.error("File {} not found on gdrive".format(old_path, name))      # önce
log.error("File {}/{} not found on gdrive".format(old_path, name))   # sonra
```

**FIND-069 (PR #25): açık dosya kodlaması.** 4 dosyada 6 `open()` çağrısına `encoding='utf-8'` eklendi (örnek `dep_check.py:39`):

```python
with open(req_path, 'r') as f:                     # önce
with open(req_path, 'r', encoding='utf-8') as f:   # sonra
```

Kodlama belirtilmediğinde Windows'ta yerel ayarın kodlaması kullanılır (Türkçe Windows'ta cp1254). Açılan dosyaların hepsinin ASCII ya da JSON (UTF-8) olduğu doğrulandı. Google Drive modüllerindeki 4 çağrıya dokunulmadı, çünkü karşı tarafı okuyan PyDrive2 kodlama belirtmiyor ve tek tarafı değiştirmek davranışı korumazdı.

**FIND-117 (PR #26): `jinjia.py` PEP 8 temizliği.** Dosya elle temizlendi: uzun satırlar parantez içinde bölündü, operatörlere boşluk eklendi, boş satır kuralları uygulandı (örnek):

```python
suml += nchar+3      # önce (E226)
suml += nchar + 3    # sonra
```

İhlal sayısı 16'dan 4'e indi. Kalan 4 `E501` GPL lisans başlığındadır ve lisans bildirimlerine dokunulmaması kuralı gereği değiştirilmedi.

## 4. Sonuçlar

Son taramalar 24 Kasım 2026'da `830d3a80` commit'i üzerinde, başlangıçla aynı sürüm, kapsam ve parametrelerle yapıldı. Emre Bulut'un bağımsız tekrarı birebir aynı sonucu verdi. Özet Tablo 7'de verilmiştir.

**Tablo 7.** Başlangıç ve son tarama karşılaştırması

| Araç | Ölçü | Başlangıç | Son | Kapanan | Yeni çıkan |
| --- | --- | --- | --- | --- | --- |
| Pylint | Puan | 6.42/10 | 6.44/10 | – | – |
| Pylint | Mesaj (`R0401` hariç) | 3956 | 3936 | 20 | 0 |
| flake8 | İhlal | 3409 | 3393 | 16 | 0 |
| Bandit | Bulgu | 43 | 38 | 5 | 0 |
| Bandit | MEDIUM önem | 14 | 9 | 5 | 0 |
| Bandit | `# nosec` satırı | 10 | 10 | – | – |

- **Bandit:** Kapanan 5 bulgunun hepsi `B113`'tür (FIND-010–014). HIGH bulgu başlangıçta da sonda da yoktu. Kalan 38 bulgunun her biri kayıtta kodla incelenmiş ve yanlış pozitif ya da düşük öncelikli olarak kabul edilmiştir.
- **Pylint:** Kapanan 20 mesajın 13'ü doğrudan hedeflenen uyarılardır: `W1514` ×6, `E1101` ×2, `W0702`, `W0715`, `W1116`, `E1305` ve `W3101`. Kalan 7'si düzeltilen satırların yan etkisiyle kapandı (`C0301` ×4, `W1406` ×2, `C0305` ×1). Ayrıca 2 mesaj, değişen satırda aynı haliyle sürüyor (`W0719`, `C0209`). Kategori bazında `warning` 454'ten 442'ye, `error` 324'ten 321'e, `convention` 2646'dan 2641'e indi.
- **flake8:** Kapanan 16 ihlalin 12'si `jinjia.py`'den (`E501` ×7, `E226` ×3, `E302`, `W391`), 1'i `file_helper.py`'deki `E722`'den geldi; 3'ü (`E501`) düzeltilen satırların yan etkisiyle kapandı.

**Tablo 8.** Düzeltilen dosyalarda dosya bazlı Pylint puanı

| Dosya | Düzeltme (PR) | Önce | Sonra | Mesaj önce → sonra |
| --- | --- | --- | --- | --- |
| `admin.py` | #20, #22, #25 | 5.29 | 5.34 | 401 → 398 |
| `shelf.py` | #20 | 5.98 | 6.12 | 126 → 125 |
| `helper.py` | #23, #24 | 5.16 | 5.24 | 246 → 244 |
| `file_helper.py` | #16 | 5.74 | 5.93 | 19 → 18 |
| `web.py` | #17, #18 | 3.06 | 3.08 | 392 → 389 |
| `dep_check.py` | #25 | 6.88 | 7.08 | 26 → 24 |
| `kobo.py` | #25 | 5.75 | 5.77 | 207 → 206 |
| `updater.py` | #25 | 7.83 | 7.87 | 97 → 95 |
| `jinjia.py` | #26 | 6.28 | 6.70 | 31 → 27 |
| `services/goodreads_support.py` | #21 | 7.31 | 7.41 | 27 → 26 |
| `metadata_provider/comicvine.py` | #21 | 5.91 | 6.14 | 10 → 9 |
| `metadata_provider/google.py` | #21 | 6.03 | 6.18 | 15 → 14 |
| `metadata_provider/lubimyczytac.py` | #21 | 8.34 | 8.43 | 24 → 22 |
| `metadata_provider/amazon.py` | #21 | 5.60 | 5.60 | 25 → 25 |

Tablo 8'deki puanlar, her dosyanın başlangıç ve son commit'te ayrı ayrı `pylint <dosya>` ile taranmasıyla elde edildi.

**Ders hedefleriyle karşılaştırma (K5):**

- **Güvenlik:** 8 güvenlik bulgusu düzeltildi: B113 ×5, FIND-116, FIND-150 ve FIND-126 (kısmi). Buna ek olarak 31 Bandit bulgusu kodla yanlış pozitif olarak gösterildi. Hedef en az 3 bulguydu.
- **Kod kalitesi / PEP 8:** 7 Pylint türü (`W0702`, `E1101`, `W0715`, `W1116`, `E1305`, `W1514`, `W3101`) ve 5 flake8 türü (`E722`, `E501`, `E226`, `E302`, `W391`) düzeltildi. Hedef en az 5 türdü.

**Karşılaşılan sorunlar ve çözümleri:**

- **Yanlış Bandit sürümü (K8):** İlk başlangıç raporları sürüm belirtilmeden kurulan Bandit 1.8.6 ile üretilmişti. Kod değişikliğinden önce 1.9.4 ile yeniden üretildi. Bundan sonra her taramadan önce araç sürümleri doğrulandı.
- **LDAP paketleri:** Windows'ta derlenemedikleri için kurulamadılar. Kaynaklandıkları 2 `E0401` mesajı ortam sorunu olarak kaydedildi; LDAP kodu yine de tarandı.
- **`R0401` oynaması:** Pylint'in döngüsel import mesajı aynı kod üzerinde çalıştırmadan çalıştırmaya değişiyor (başlangıç commit'inde 43 ve 48, son commit'te 49 ve 44). Başlangıç ile son arasında hiçbir import satırı değişmediği halde ham rapor 43 → 49 gösteriyor. Bu nedenle `R0401` eşleştirmenin dışında tutuldu. Puan ve diğer mesajlar tekrarlarda birebir aynıydı.
- **Pylint kapsam boşluğu:** `cps/metadata_provider/` dizininde `__init__.py` olmadığı için Pylint bu dizindeki 6 dosyayı resmi taramada atlıyor. Bu yüzden B113 düzeltmesinin bu dizindeki 4 `W3101` etkisi yalnızca dosya bazlı taramada (Tablo 8) görülebiliyor. Tarama parametreleri başlangıçla aynı kalsın diye kapsam değiştirilmedi.
- **Araç kuralının kör noktası:** Bandit `B113` kuralı `requests.Session` çağrılarını tanımıyor. Bu türden çağrılar elle bulundu ve kayda eklendi (FIND-116 düzeltildi, FIND-160 öneri olarak kaldı).
- **Yeni uyarı doğuran düzeltme adayları:** FIND-078'de `.format()` kullanmak yeni bir `C0209` uyarısı doğurduğu için f-string seçildi. FIND-069'da uzayan iki satır, yeni `E501`/`C0301` doğurmasın diye bölündü. FIND-057'de (istisna sırası) iki `except` bloğunun yer değiştirmesi Pylint uyarısını kapatmadı: `E0701` ayna biçimde geri geldi, `W0705` sürdü. Bunun nedeni, ilgili kütüphaneler kurulu değilken iki istisna adının da `BaseException`'a bağlanmasıdır (`helper.py:53, 80`). Bu sonuç önce Hasan Kurt'un denemesinde görüldü (`docs/report-part-file-handling.md`), rapor için geçici bir kopyada dosya bazlı Pylint ile yeniden ölçüldü. Düzeltme K10 kapsamında uygulanmadı.
- **Takvim kayması (K10):** Kod dondurma ekip kararıyla 24 Kasım'a alındı. Kapsama yalnızca o tarihe kadar açılmış düzeltmeler dahil edildi.

## 5. Değerlendirme ve Sonuç

Proje, dersin istediği adımların tamamını tamamladı: yeterli büyüklükte bir projenin seçilip tanıtılması, Pylint ve Bandit başlangıç analizleri, önemli bulguların kod üzerinden incelenmesi, PEP 8 analizi, bulguların sınıflandırılması, seçilmiş düzeltmeler ve aynı koşullarda yeniden analiz. Güvenlik ve kalite düzeltme hedeflerinin ikisi de aşıldı. Hiçbir düzeltme yeni bir uyarı doğurmadı ve hiçbir uyarı susturularak kapatılmadı.

En önemli çıkarım, araç sayıları ile gerçek riskin örtüşmemesidir. Bandit bulgularının yaklaşık dörtte üçü kodla incelendiğinde yanlış pozitif çıktı. Buna karşılık en anlamlı güvenlik sorunları araçların hiç görmediği yerlerdeydi: yetki mantığı (FIND-150), bilgi sızıntısı (FIND-126), susturulmuş bir varsayılan parola (FIND-044) ve aracın kuralının kapsamadığı çağrılar (FIND-116, 160). Bu yüzden Bandit sayısındaki 43 → 38 düşüş, yapılan güvenlik iyileştirmesinin yalnızca bir kısmını gösteriyor. Aynı şekilde Pylint puanındaki küçük artış (6.42 → 6.44), toplu biçimlendirme yapılmamasının beklenen sonucudur; düzeltilen dosyalarda etki daha belirgindir (Tablo 8). Statik analiz, ancak elle yapılan kod incelemesi ve gerekçeli bir bulgu kaydıyla birlikte kullanıldığında güvenilir sonuç veriyor.

**Sınırlılıklar.** Analiz tamamen statiktir; düzeltmelerin çalışma zamanı davranışı test edilmedi, kod okuma ve yalıtılmış kütüphane denemeleriyle doğrulandı. Pylint `cps/metadata_provider/` dizinini taramadı ve `R0401` sayısı tekrarlanabilir değildi. LDAP paketleri kurulamadığı için ilgili kod importları çözülmeden tarandı. Gömülü üçüncü taraf kod yalnızca incelendi. Araç sayıları, bulgu kaydındaki gruplama nedeniyle satır sayısıyla birebir karşılaştırılamaz.

**Geliştirilebilecek yönler.** Kabul edilip düzeltilmeyen gerçek sorunlar öncelikli adaylardır:

- İlk girişte varsayılan yönetici parolasının değiştirilmesinin zorunlu kılınması (FIND-044).
- Parola sıfırlamanın onay bağlantısıyla yapılması (FIND-126'nın kalan kısmı).
- `douban.py`'deki üç isteğe zaman aşımı eklenmesi (FIND-160).
- Yükleme ayarının sunucu tarafında da uygulanması (FIND-151).
- Google Drive seri küçük resmi hatasının giderilmesi (FIND-152).
- `helper.py`'deki istisna sırasının düzeltilmesi (FIND-057/082).

Araç tarafında `cps/metadata_provider/` dizinine `__init__.py` eklenmesi Pylint kapsamını tamamlar. Bandit, `Session` çağrılarını da kapsayan ek bir kural ya da bir semgrep kuralıyla desteklenebilir.

## Kaynakça

[1] janeczku, "Calibre-Web," GitHub. [Çevrimiçi]. Erişim: https://github.com/janeczku/calibre-web (Erişim tarihi: 24 Kasım 2026).

[2] Ş. Altın, D. Yıldırım, H. Kurt ve E. Bulut, "calibre-web (ekip çatalı, `project-analysis` dalı)," GitHub. [Çevrimiçi]. Erişim: https://github.com/sseydaltin/calibre-web (Erişim tarihi: 24 Kasım 2026).

[3] PyCQA, "Bandit documentation," sürüm 1.9.4. [Çevrimiçi]. Erişim: https://bandit.readthedocs.io/ (Erişim tarihi: 24 Kasım 2026).

[4] PyCQA, "Pylint documentation," sürüm 4.1. [Çevrimiçi]. Erişim: https://pylint.readthedocs.io/ (Erişim tarihi: 24 Kasım 2026).

[5] PyCQA, "Flake8: Your Tool For Style Guide Enforcement," sürüm 7.4. [Çevrimiçi]. Erişim: https://flake8.pycqa.org/ (Erişim tarihi: 24 Kasım 2026).

[6] G. van Rossum, B. Warsaw ve A. Coghlan, "PEP 8 – Style Guide for Python Code," Python Enhancement Proposals, 2001. [Çevrimiçi]. Erişim: https://peps.python.org/pep-0008/ (Erişim tarihi: 24 Kasım 2026).

[7] MITRE, "CWE-400: Uncontrolled Resource Consumption," Common Weakness Enumeration. [Çevrimiçi]. Erişim: https://cwe.mitre.org/data/definitions/400.html (Erişim tarihi: 24 Kasım 2026).

[8] MITRE, "CWE-204: Observable Response Discrepancy," Common Weakness Enumeration. [Çevrimiçi]. Erişim: https://cwe.mitre.org/data/definitions/204.html (Erişim tarihi: 24 Kasım 2026).

[9] MITRE, "CWE-285: Improper Authorization," Common Weakness Enumeration. [Çevrimiçi]. Erişim: https://cwe.mitre.org/data/definitions/285.html (Erişim tarihi: 24 Kasım 2026).

[10] Python Software Foundation, "Requests: Timeouts," Requests documentation. [Çevrimiçi]. Erişim: https://requests.readthedocs.io/en/latest/user/advanced/#timeouts (Erişim tarihi: 24 Kasım 2026).

[11] Python Software Foundation, "zipfile — Work with ZIP archives," Python 3.12 documentation. [Çevrimiçi]. Erişim: https://docs.python.org/3.12/library/zipfile.html (Erişim tarihi: 24 Kasım 2026).

[12] Anthropic, "Claude Code overview," Claude Docs. [Çevrimiçi]. Erişim: https://docs.claude.com/en/docs/claude-code/overview (Erişim tarihi: 24 Kasım 2026).
