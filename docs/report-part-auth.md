# Final rapor payı — 3. kişi (Emre Bulut): yetki incelemesi ve düzeltmeler

Bu dosya `docs/final-report.md` içine aktarılmak üzere hazırlandı. 5. bölümün yetki kısmını ve 8. bölümdeki FIND-126 ile FIND-049 düzeltmelerini içerir. Ayrıntılı kanıtlar: `docs/review-auth.md`, `docs/findings-register.csv`.

---

## 5. Önemli güvenlik bulgularının kod incelemesi — kimlik doğrulama ve yetki

**Kapsam ve yöntem.** Kimlik doğrulama, oturum, parola, yetki dekoratörleri, CSRF ve diğer giriş yolları kod okumayla incelendi; uygulama çalıştırılmadı (K2). `cps/*.py` içindeki route'lar AST ile çıkarıldı (190 route fonksiyonu), dekoratörleri ve iç yetki kontrolleri tek tek izlendi. 20 kontrol noktasının sonucu: **2 gerçek sorun, 7 düşük öncelikli uyarı, 11 sorun yok**.

**Sağlam bulunan noktalar:**
- Yönetici route'larının 49'unun 46'sı `@user_login_required` + `@admin_required` ile korunuyor. Kalan üçü ya varsayılan olarak kapalı (`/reconnect`, FIND-125) ya da yalnızca kullanıcının kendi verisine dokunuyor.
- Rol dekoratörleri (`upload/edit/download/viewer_required`) ve iç kontroller (`role_delete_books`, raf sahipliği, Kobo token'ında `user_id` kontrolü) doğru uygulanıyor. Başka kullanıcının kaynağına erişim (IDOR) bulunmadı.
- Parolalar Werkzeug `scrypt` ile saklanıyor. `SECRET_KEY` rastgele üretiliyor. Çıkışta oturum sunucu tarafında da siliniyor. Oturum koruması varsayılan olarak `strong`.
- `next` parametresiyle açık yönlendirme yok: hedef, uygulamanın route haritasıyla eşleşmezse varsayılan sayfaya dönülüyor.
- OAuth eşleme değişmez sağlayıcı kimliğiyle yapılıyor. Uzaktan giriş token'ı 128 bit, 10 dakika geçerli ve tek kullanımlık.

**Gerçek sorunlar:**

| FIND | Konum | Sorun | Sonuç |
| --- | --- | --- | --- |
| FIND-044 | `cps/constants.py:140`, `cps/ub.py:677-689` | İlk kurulumda tam yetkili `admin` / `admin123` hesabı açılıyor ve ilk girişte parola değişikliği zorlanmıyor. Upstream'de `# nosec` ile susturulduğu için Bandit raporunda görünmüyor. Sunucu varsayılan olarak tüm arayüzleri dinlediği için (FIND-009) parolası değiştirilmemiş bir kurulum ağdan ele geçirilebilir. | Düzeltme büyük (yeni akış, veri modeli, şablon); risk ve kurulum önerisi olarak raporlanıyor. |
| FIND-126 | `cps/web.py:1428-1439` (`login_post`) | "Parolamı unuttum" girişsiz ve yalnızca kullanıcı adıyla çalışıyor; parolayı onay bağlantısı olmadan hemen değiştiriyor. Var olan ve olmayan kullanıcı adına farklı mesaj dönüyor, bu da kullanıcı adlarının tahmin edilmesine izin veriyor. | Kullanıcı adı tahmini düzeltildi (bölüm 8). Onaysız sıfırlama öneri olarak kalıyor. |

**Düşük öncelikli uyarılar:**
- **FIND-125:** `/reconnect` kimlik doğrulamasız, ama varsayılan olarak kapalı.
- **FIND-127:** Giriş denemesi sınırı yalnızca kullanıcı adına bağlı; OPDS'de günlük sınır yok.
- **FIND-128:** Bazı uçlar GET ile durum değiştirdiği için CSRF korumasının dışında kalıyor: OAuth bağlantısını kaldırma, Kobo token oluşturma, çıkış.
- **FIND-129:** Profilde parola ve e-posta, mevcut parola sorulmadan değiştirilebiliyor.
- **FIND-130:** Çerezlerde `Secure` bayrağı yok; "beni hatırla" çerezi 365 gün geçerli.
- **FIND-131:** Kobo token'ı süresiz ve URL'de taşınıyor.
- **FIND-132:** Raf görüntüleme kontrolü istisnada erişime izin veriyor (fail-open).
- **FIND-133:** Başarısız girişte parola forma geri yazılıyor.

**Statik analiz araçlarıyla ilişki.**
- Bandit'in bu alandaki tüm uyarıları (B105/B107 ×9) kodla incelendi ve **yanlış pozitif** çıktı. Yedisi boş `''` parola değeri, ikisi adında "password"/"token" geçen herkese açık Kobo URL'leri. Boş değerler bir giriş yolu açmıyor, çünkü Werkzeug `check_password_hash('', x)` her zaman `False` döner.
- Buna karşılık bu alandaki iki gerçek sorunun hiçbiri araç uyarısı olarak görünmedi:
  - FIND-044 upstream'de `# nosec` ile susturulmuş.
  - FIND-126 bir mantık hatası; Bandit'in örüntü tabanlı yaklaşımı bunu yakalayamaz.

  Bu durum, statik analiz çıktısının manuel incelemeyle tamamlanması gerektiğini gösteriyor.

---

## 8. Düzeltmeler — FIND-126 ve FIND-049

### FIND-126: Parola sıfırlamada kullanıcı adı tahmini (güvenlik)

**Dal:** `fix/find-126` · **Dosya:** `cps/web.py` (`login_post`)

**Önceki kod**
```python
if user is not None and user.name != "Guest":
    ret, __ = reset_password(user.id)
    if ret == 1:
        flash(_(u"New Password was sent to your email address"), category="info")
        log.info('Password reset for user "%s" IP-address: %s', username, ip_address)
    else:
        log.error(u"An unknown error occurred. Please try again later")
        flash(_(u"An unknown error occurred. Please try again later."), category="error")
else:
    flash(_(u"Please enter valid username to reset password"), category="error")
    log.warning('Username missing for password reset IP-address: %s', ip_address)
```

**Yeni kod**
```python
if user is not None and user.name != "Guest":
    ret, __ = reset_password(user.id)
    if ret == 1:
        log.info('Password reset for user "%s" IP-address: %s', username, ip_address)
    else:
        log.error(u"An unknown error occurred. Please try again later")
else:
    log.warning('Username missing for password reset IP-address: %s', ip_address)
# one message for all cases (no username enumeration)
flash(_(u"New Password was sent to your email address"), category="info")
```

**Gerekçe.**
- Bütün durumlarda (başarı, kullanıcı yok, e-posta ayarsız, hata) aynı mesaj gösteriliyor. Böylece yanıt, kullanıcı adının var olup olmadığını ele vermiyor.
- Yeni çeviri metni eklenmedi; başarı dalındaki mevcut metin kullanıldı.
- Meşru kullanıcının gördüğü mesaj değişmedi. HTTP durum kodu her durumda zaten 401.
- E-posta ayarsızken ya da hata durumunda parola değişmiyor (`reset_password` dokunmadan dönüyor ya da `rollback` yapıyor); yani mesaj kimseyi hesabından etmiyor.
- Ayrı log satırları korunduğu için yönetici gerçek durumu görmeye devam ediyor.
- **Sınırlılık:** Onaysız sıfırlama ve zamanlama farkı sürüyor.

**Doğrulama** (dosya bazlı, değişiklik öncesi → sonrası)
```text
python -m py_compile cps\web.py                          -> OK
python -m pylint cps\web.py                              -> 392 -> 389 mesaj (C0301 ×1 ve W1406 ×2 kapandı, yeni mesaj yok)
python -m flake8 --isolated --select=E,W cps\web.py      -> 398 -> 396 ihlal (E501 ×2 kapandı; taşınan flash satırı 93 -> 85 karakter)
python -m bandit cps\web.py                              -> 1 -> 1 (değişmedi)
```

### FIND-049: Hata işleyicisinde `e.orig` (kod kalitesi, Pylint E1101)

**Dal:** `fix/find-049` · **Dosyalar:** `cps/admin.py` (`update_mailsettings`), `cps/shelf.py` (`delete_shelf`)

**Önceki kod**
```python
except Exception as e:                       # admin.py:1376 (shelf.py:284: except InvalidRequestError as e)
    flash(_("Oops! Database Error: %(error)s.", error=e.orig), category="error")
```

**Yeni kod**
```python
except Exception as e:
    flash(_("Oops! Database Error: %(error)s.", error=getattr(e, 'orig', e)), category="error")
```
(Aynı değişiklik `admin.py:1374`'te de, `OperationalError` ile birlikte yakalanan `InvalidRequestError` için.)

**Gerekçe.**
- `orig` özniteliği yalnızca `StatementError`/`DBAPIError` sınıflarında bulunuyor.
- Düz `Exception` ya da `InvalidRequestError` yakalandığında `e.orig` kendisi `AttributeError` fırlatıyor, kullanıcı hata mesajı yerine 500 alıyordu. Bu, kurulu SQLAlchemy 2.0.55 ile yalıtılmış denemeyle doğrulandı (K9).
- `getattr(e, 'orig', e)` ile `orig` varsa mesaj öncekiyle birebir aynı; yoksa istisnanın kendisi gösteriliyor.

**Doğrulama**
```text
python -m py_compile cps\admin.py cps\shelf.py                       -> OK
python -m pylint cps\admin.py cps\shelf.py                           -> 526 -> 524 mesaj (E1101 admin.py:1377 ve shelf.py:287 kapandı, yeni mesaj yok)
python -m flake8 --isolated --select=E,W cps\admin.py cps\shelf.py   -> 435 -> 435 (değişen 3 satır önceden de E501 idi)
python -m bandit cps\admin.py cps\shelf.py                           -> 2 -> 2 (değişmedi)
```

---

## Gözden geçirme katkısı

4. kişinin düzeltme PR'ları gözden geçirildi ve doğrulandı:
- **PR #16 (FIND-080/109):** 20.000 bozuk ZIP örneğiyle istisna listesi bağımsız olarak denendi; liste dışı istisna çıkmadı.
- **PR #17 (FIND-150):** İndirme yoluyla aynı filtre çağrısı kullanılıyor; araç çıktıları değişmiyor.
- **PR #12 (FIND-159):** MD5 karşılaştırmasının dosya yerine yol metnini özetlediği kodda doğrulandı.
