# Final rapor payı — 4. kişi (Hasan Kurt): dosya işleme, harici süreçler ve düzeltmeler

Bu dosya `docs/final-report.md` içine aktarılmak üzere hazırlandı. 5. bölümün dosya işleme ve harici süreç kısmını, 8. bölümdeki FIND-150 ve FIND-080 düzeltmelerini ve 10. bölüm için sınırlılık notlarını içerir. Ayrıntılı kanıtlar: `docs/3-inceleme/review-file-handling.md`, `docs/findings-register.csv`, PR #16, #17, #21.

---

## 5. Önemli güvenlik bulgularının kod incelemesi — dosya işleme ve harici süreçler

**Kapsam ve yöntem.** Kitap yükleme ve indirme, dosya yolları, arşivler, dönüştürme, harici süreçler ve ağ çağrıları kod okumayla incelendi; uygulama çalıştırılmadı (K2). İnceleme beş başlıkta 23 kontrol noktasından oluşuyor: yükleme (A, 7), yol ve indirme (B, 5), arşiv ve dönüştürme (C, 3), harici süreçler (D, 4), ağ ve güncelleme (E, 4). Üç noktada yalnızca kütüphane davranışı yalıtılmış denemeyle doğrulandı (K9): `nh3.clean()` (A7), `urllib.request.urlopen()` (E3) ve `zipfile` (FIND-080). Sonuç: **3 gerçek sorun, 8 düşük öncelikli uyarı, 12 sorun yok**. Kayda FIND-150…FIND-159 eklendi; PR #21 incelemesi sırasında bulunan FIND-160 (`douban.py`) sonradan eklendi.

**Sağlam bulunan noktalar:**
- **Path traversal yok.** İndirmede istekten yalnızca `book_id` (int) ve biçim alınıyor; dizin ve dosya adı veritabanından geliyor, gönderim Werkzeug `safe_join` kullanan `send_from_directory()` ile yapılıyor (B2). Yazar/başlık gibi kullanıcı verisi yola girerken `/`, `\`, `:` gibi karakterler `_` yapılıyor; `.` ve `..` adları oluşamıyor (B1).
- **Zip slip yok.** Yüklenen arşivlerin üyeleri yalnızca belleğe okunuyor; `extract()` / `extractall()` çağrılmıyor (C1).
- **Komut enjeksiyonu yok.** Tek `Popen` çağrısı `shell=False` ve liste argümanlı (D1). Dönüştürmede biçimler beyaz listeyle sınırlı, kullanıcıdan serbest metin argüman geçmiyor (C3). Harici program yollarını yalnızca yönetici ayarlayabiliyor (D3).
- **SSRF koruması çalışıyor.** URL'den kapak indirme varsayılan olarak `cw_advocate` ile yapılıyor; yerel ve özel adresler reddediliyor, yönlendirme kapalı, zaman aşımı tanımlı (A6).
- **Yükleme denetimi iki katmanlı.** Yönetici ayarına bağlı uzantı listesi ve python-magic ile içerik tipi kontrolü birlikte çalışıyor (A2).

**Gerçek sorunlar:**

| FIND | Konum | Sorun | Sonuç |
| --- | --- | --- | --- |
| FIND-150 | `cps/web.py:1265` (`send_to_ereader`) | E-okuyucuya gönderme route'u kitabı filtresiz `get_book()` ile alıyor. İndirme route'ları kullanıcının dil/etiket/özel sütun kısıtlamalarını uyguluyor, bu route uygulamıyor. Kısıtlanmış bir kullanıcı, göremediği bir kitabı id'siyle kendi e-okuyucu adresine gönderebiliyordu. | **Düzeltildi** (bölüm 8, PR #17). |
| FIND-151 | `cps/editbooks.py:57-64, 105-108` | Yöneticinin global "yüklemeye izin ver" ayarı yalnızca arayüzde uygulanıyor; yükleme rolü olan kullanıcı ayar kapalıyken de doğrudan istekle yükleme yapabiliyor. | Kabul edildi (düzeltilmeyecek, K10); öneri: `upload_required` içinde `role_upload() and config.config_uploading`. |
| FIND-152 | `cps/tasks/thumbnail.py:380-386` | İşlev hatası: Google Drive kurulumlarında seri küçük resmi, dosya içeriğini (bytes) URL sanıp `urlopen()`'a veriyor ve her zaman hata alıyor (yalıtılmış deneme ile doğrulandı). | Kabul edildi (düzeltilmeyecek, K10); öneri: `io.BytesIO(...)`. |
| FIND-160 | `cps/metadata_provider/douban.py:105, 127, 154` | `requests.Session` üzerinden zaman aşımsız üç dış istek (FIND-116 ile aynı tür). Dış servis yanıt vermezse metadata araması süresiz bekleyebilir. Bandit B113 `Session` çağrılarını görmüyor. | Kabul edildi (düzeltilmeyecek, K10); öneri: `timeout=(5, 30)`. |

**Düşük öncelikli uyarılar** (K10 kod dondurması ve kapsam nedeniyle hepsi "Kabul edildi (düzeltilmeyecek)"; raporda öneri olarak kalıyor):
- **FIND-153:** Geçici yükleme dosyasının adı yalnızca dosya adının MD5'i; eşzamanlı aynı adlı yüklemelerde çakışma olabilir.
- **FIND-154:** Arşiv üyesi ve URL'den kapak okumada boyut sınırı yok; küçük ama açıldığında çok büyük bir kapak üyesi bellek tüketebilir (yükleme rolü gerekli).
- **FIND-155:** İndirme yanıtındaki `Content-Disposition` başlığında `"` kaçışlanmıyor.
- **FIND-156:** Yorum HTML'i nh3 ile temizleniyor ve betik çalıştırma yolları kapanıyor (FIND-002…005 yanlış pozitif kararı destekleniyor), ama `style` özniteliği ve dış `img src` serbest: arayüz manipülasyonu ve takip pikseli mümkün. XSS değil.
- **FIND-157:** Güncelleyici, indirilen paketin imzasını veya özetini doğrulamıyor (tedarik zinciri riski, tasarım tercihi).
- **FIND-158:** Windows'ta komut tek string'e birleştirilirken 0. eleman tırnaklanmıyor. Enjeksiyon yok; FIND-028'in yanlış pozitif kararı geçerli.
- **FIND-159:** Google Drive bildirim geri çağrısı yalnızca kaynakta sabit yazılı bir başlıkla korunuyor; ayrıca MD5 karşılaştırması dosya içeriği yerine yol metnini özetlediği için her bildirimde veritabanı yedeklenip yeniden indiriliyor. Yedekler bir sonraki geçici dizin temizliğine kadar birikiyor. Veri sızıntısı veya içerik enjeksiyonu yok.

**Statik analiz araçlarıyla ilişki.**
- Bu alandaki Bandit uyarılarının çoğu kodla incelendi ve **yanlış pozitif** kararları desteklendi: B404/B603 (FIND-028; liste argümanlı, `shell=False`), B310 (FIND-008), B704 (FIND-002…005; nh3 temizliği). FIND-016 (B112, yönetici yol seçici) düşük öncelikli ve tasarıma uygun.
- Bu alandaki gerçek sorunların hiçbiri Bandit uyarısı olarak görünmedi:
  - FIND-150 ve FIND-151 birer yetki mantığı hatası; örüntü tabanlı araçlar bunları yakalayamaz.
  - FIND-159'un iki parçası upstream'de `# nosec` ile susturulmuş (`gdrive.py:48` B105, `gdrive.py:143` B324); kural kodları yalnızca `--ignore-nosec` ile yapılan bir doğrulama çalıştırmasında göründü.
  - Bandit B113, `requests.Session` üzerinden yapılan zaman aşımsız istekleri görmüyor (FIND-116 `amazon.py`, FIND-160 `douban.py`).
- Buna karşılık Pylint bu alanda iki gerçek hata yakaladı: `helper.py`'de yanlış sıralı `except` blokları (E0701, FIND-057) ve `file_helper.py`'de çıplak `except` (W0702, FIND-080).

---

## 8. Düzeltmeler — FIND-150 ve FIND-080

### FIND-150: E-okuyucuya göndermede içerik kısıtlaması (güvenlik)

**PR:** #17 · **Dal:** `fix/find-150` · **Dosya:** `cps/web.py` (`send_to_ereader`) · **Gözden geçiren:** Emre Bulut

**Önceki kod**
```python
def send_to_ereader(book_id, book_format, convert):
    book = calibre_db.get_book(book_id)
    allowed_formats = check_send_to_ereader(book) if book else []
```

**Yeni kod**
```python
def send_to_ereader(book_id, book_format, convert):
    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    allowed_formats = check_send_to_ereader(book) if book else []
```

**Gerekçe.**
- `get_filtered_book()` → `common_filters(allow_show_archived=True)` (`db.py:775-804`) dil, izin verilen/yasak etiket ve kısıtlı özel sütun filtrelerini uyguluyor. İndirme yolu (`get_download_link`, `helper.py:1106`) aynı çağrıyı aynı argümanla kullanıyor; iki yol artık tutarlı.
- `allow_show_archived=True` yalnızca arşiv filtresini kapatıyor. Arşivlenmiş kitaplar daha önce de gönderilebiliyordu, bu davranış korundu.
- Kitap filtreye takılırsa `book` `None` oluyor; mevcut `... if book else []` satırı sayesinde mevcut "Book format not supported" yanıtı dönüyor. Yeni hata yolu yok.
- `helper.send_mail()` (`helper.py:218`) da filtresiz `get_book` kullanıyor, ama tek çağıranı bu route (`web.py:1276`); ek değişiklik gerekmedi.
- Bu bir manuel bulgu: kapanacak bir araç uyarısı yok. Doğrulama, yeni uyarı çıkmadığını gösteriyor.

**Doğrulama** (dosya bazlı, değişiklik öncesi → sonrası)
```text
python -m py_compile cps/web.py                          -> OK
python -m pylint cps/web.py                              -> 392 -> 392 mesaj (3.06/10; satır numaraları hariç birebir aynı)
python -m flake8 --isolated --select=E,W cps/web.py      -> 398 -> 398 ihlal (yeni satır 74 karakter)
python -m bandit cps/web.py                              -> 1 -> 1 (B107, ilgisiz; değişmedi)
```

### FIND-080 (+FIND-109): `validate_mime_type` içinde çıplak `except` (kod kalitesi, Pylint W0702 / flake8 E722)

**PR:** #16 · **Dal:** `fix/find-080` · **Dosya:** `cps/file_helper.py` · **Gözden geçiren:** Emre Bulut

**Önceki kod**
```python
        try:
            with zipfile.ZipFile(BytesIO(file_buffer.read()), 'r') as epub:
                file_buffer.seek(0)
                if "mimetype" in epub.namelist():
                    return True
        except:
            file_buffer.seek(0)
```

**Yeni kod**
```python
        try:
            with zipfile.ZipFile(BytesIO(file_buffer.read()), 'r') as epub:
                file_buffer.seek(0)
                if "mimetype" in epub.namelist():
                    return True
        except (zipfile.BadZipFile, OSError, ValueError, NotImplementedError):
            file_buffer.seek(0)
```

**Gerekçe.**
- `try` bloğu yalnızca `file_buffer.read()`, `zipfile.ZipFile(...)` ve `namelist()` çağırıyor. Beklenen istisnalar: `BadZipFile` (zip olmayan, boş veya kesik veri), `NotImplementedError` (desteklenmeyen sürüm alanı), `ValueError` (kapalı akış; `UnicodeDecodeError` da bunun alt sınıfı), `OSError` (akış okuma hatası).
- Liste yalıtılmış deneme ile doğrulandı (K9; uygulama çalıştırılmadı, yalnızca standart kütüphane `zipfile`): geçerli EPUB/ZIP örnekleri bayt değiştirme, kesme, araya bayt ekleme ve merkezi dizin alanlarını bozma yoluyla 60.000 kez bozuldu. Sonuç: 31.980 başarılı, 26.248 `BadZipFile`, 1.086 `UnicodeDecodeError`, 686 `NotImplementedError`; **liste dışı istisna 0**. Gözden geçiren de 20.000 örnekle bağımsız olarak denedi, liste dışı istisna çıkmadı.
- Bu istisnalarda davranış değişmedi: `seek(0)` çalışır, ardından "Mimetype not found" logu ve `return False`.
- `except Exception` bilinçli olarak kullanılmadı, çünkü yeni bir W0718 uyarısı doğururdu. Çıplak `except` ayrıca `KeyboardInterrupt` ve `SystemExit`'i de yutuyordu.

**Doğrulama** (dosya bazlı, değişiklik öncesi → sonrası)
```text
python -m py_compile cps/file_helper.py                          -> OK
python -m pylint cps/file_helper.py                              -> 19 -> 18 mesaj (W0702 kapandı, yeni mesaj yok; 5.74 -> 5.93)
python -m flake8 --isolated --select=E,W cps/file_helper.py      -> 6 -> 5 ihlal (E722 kapandı; kalan 5 E501 önceden de vardı)
python -m bandit cps/file_helper.py                              -> 0 -> 0
```
W0702 ve E722 aynı satırın iki aracın gözünden görünümü; tek değişiklikle kapandılar. Karşılaştırmada ayrı uyarı olarak sayılırlar ama ayrı düzeltme sayılmazlar.

### Seçilip uygulanmayan düzeltme: FIND-057 (+FIND-082), `helper.py` `except` sırası

`save_cover_from_url()` içinde wand kurulu değilse `MissingDelegateError = BaseException` oluyor (`helper.py:80`). Bu yüzden SSRF engel istisnası (`UnacceptableAddressException`) yanlış blokta yakalanıyor ve kullanıcı "Cover Format Error" görüyor; engelleme yine de çalışıyor. Önerilen düzeltme iki bloğun yerini değiştirmekti.
- Deneme sırasında **salt sıra değişikliğinin Pylint uyarısını kapatmadığı** görüldü. E0701 ayna biçimde geri geliyor ("BaseException, MissingDelegateError'ın atası"), W0705 sürüyor. Nedeni: advocate import edilemezse `UnacceptableAddressException` da `BaseException` oluyor (`helper.py:53`); Pylint iki yönde de ata-torun ilişkisi görüyor.
- Uyarıları kapatan bir varyant da denendi: sıra değişikliği ve `helper.py:53`'te docstring'li bir yedek sınıf. E0701, W0705 ve W0718 kapandı, yeni uyarı çıkmadı. Ama planın dışında bir davranış farkı (advocate yokken `BaseException` catch-all'ının kalkması) taşıdığı için ekip kararı beklendi.
- K10 kararıyla kapsam dışı kaldı; kod değiştirilmedi. FIND-057 ve FIND-082 kayıtta "Kabul edildi (düzeltilmeyecek)", gerekçelerinde K10 notu var. Bu örnek, bir Pylint uyarısını "kapatmak" ile asıl sorunu düzeltmenin her zaman aynı değişiklik olmadığını gösteriyor.

---

## Gözden geçirme katkısı

- **PR #11 (Emre Bulut, `review-auth.md`):** Kararlar onaylandı. Notlar: A2'ye FIND-150/151 çapraz referansı eklenmeli; FIND-126 için 3/dakika sınırının yanında 40/gün sınırı da var.
- **PR #21 (Dilara Yıldırım, B113 + FIND-116 + FIND-085):** Onaylandı. Bağımsız olarak kontrol edilenler:
  - 5 dosyada 7 çağrıya yalnızca `timeout=(5, 30)` eklenmiş; `py_compile` temiz.
  - Dosya bazında Bandit'te 5 B113 kapandı, Pylint'te 5 W3101 kapandı (8.26 → 8.36), flake8 96 → 96; yeni uyarı yok.
  - Zaman aşımı istisnası her yolda yakalanıyor: `except Exception` blokları, goodreads'te `get_author_info` (`goodreads_support.py:141-143`).
  - Plan madde 5 (FIND-013, paralel istekler): `None` sonuçları `search_metadata.py:69-70`'te eleniyor.
  - Plan madde 6 (FIND-014): yazar sayfasındaki tüm goodreads istekleri `get_author_info`'nun `try` bloğunda.
  - İncelemeden iki sonuç çıktı: Pylint kapsam boşluğu (aşağıda, 10. bölüm notları) ve `douban.py`'deki aynı türden üç istek. İkincisi FIND-160 olarak kayda eklendi. FIND-085 ve FIND-116'nın `gozden_geciren` alanı Hasan Kurt olarak dolduruldu.

---

## 10. bölüm için sınırlılık notları

- **Pylint taraması `cps/metadata_provider/` dizinini kapsamıyor.** Dizinde `__init__.py` olmadığı için `python -m pylint cps.py cps` komutu bu 6 dosyaya girmiyor; baseline `pylint.txt`'de bu dizine ait 0 mesaj var (Bandit ve flake8 ise taramış). Bu yüzden B113 düzeltmesinde dosya bazında 5 W3101 kapansa da, aynı parametrelerle yapılan resmi önce-sonra karşılaştırmasında yalnızca 1 W3101 (FIND-085, `goodreads_support.py`) kapanmış görünür.
- **`douban.py`'deki zaman aşımsız istekler sonradan bulundu (FIND-160).** `cps/metadata_provider/douban.py:105, 127, 154`'te `requests.Session` üzerinden zaman aşımsız üç istek var (FIND-116 ile aynı tür; Bandit B113 görmüyor). PR #21 incelemesi sırasında bulundular; dosya incelemesindeki E4 bağlam notunda gözden kaçmışlardı. K10 nedeniyle düzeltilmedi; kayıtta "Kabul edildi (düzeltilmeyecek)".
- **Düzeltilmeyen bulgular tek durumda toplandı.** Bu alanda düzeltilmeyen bulguların hepsi (FIND-151…160) ile seçilip uygulanmayan FIND-057 ve ikizi FIND-082 kayıtta "Kabul edildi (düzeltilmeyecek)" olarak işaretlendi; gerekçelerinde K10 notu var.
- **Doğrulama ortamı farklı.** Bu bölümdeki doğrulama çıktıları Linux'ta (Python 3.12.3), ekibin sabit araç sürümleriyle (bandit 1.9.4, pylint 4.1.3, astroid 4.3.4, flake8 7.4.1) alındı. Gözden geçiren (Emre Bulut) PR #16 ve #17'deki araç sonuçlarını bağımsız olarak doğruladı.
