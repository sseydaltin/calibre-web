# Calibre-Web Üzerinde Güvenlik İçin Statik Kod Analizi

Bu depo, Calibre-Web'in (upstream `janeczku/calibre-web`, commit `6e840acb`) `cps/` paketi ile `cps.py` giriş noktasının, uygulama çalıştırılmadan Bandit, Pylint ve flake8 ile analizini içerir. Araç bulguları elle doğrulandı ve gerçek sorun, düşük öncelikli uyarı ya da yanlış pozitif olarak sınıflandırıldı. Seçilen sorunlar küçük ve davranışı koruyan değişikliklerle düzeltildi. Araçlar başlangıçtaki sürüm ve parametrelerle yeniden çalıştırılıp sonuçlar karşılaştırıldı. Taranan son kod commit `830d3a80`'dir; ayrıntılı rapor [docs/final-report.md](docs/final-report.md) dosyasındadır.

## Sonuçlar

| Araç | Ölçü | Başlangıç | Son |
| --- | --- | --- | --- |
| Bandit 1.9.4 | Toplam bulgu (`cps/` + `cps.py`) | 43 (42 + 1) | 38 (37 + 1) |
| | HIGH / MEDIUM / LOW önem | 0 / 14 / 29 | 0 / 9 / 29 |
| Pylint 4.1.3 | Puan | 6.42/10 | 6.44/10 |
| | Mesaj sayısı (`R0401` hariç) | 3956 | 3936 |
| flake8 7.4.1 | PEP 8 ihlali (`E`, `W`) | 3409 | 3393 |

- Üç araçta da yeni çıkan uyarı yok. Uyarıları susturan yorum (`# nosec`, `# noqa`, `# pylint: disable`) eklenmedi; bütün kapanışlar kod düzeltmesidir.
- Bulgu kaydı ([docs/findings-register.csv](docs/findings-register.csv)) 137 satırdır: 17 düzeltildi, 77 kabul edildi (düzeltilmeyecek), 43 yanlış pozitif.
- Ayrıntılı karşılaştırmalar [docs/5-karsilastirma/](docs/5-karsilastirma/) klasöründedir.

## Düzeltmeler

| Bulgu | Konu | PR | Düzelten | Gözden geçiren |
| --- | --- | --- | --- | --- |
| FIND-010–014, 116, 085 | Dış isteklere zaman aşımı (B113, W3101) | #21 | Dilara Yıldırım | Hasan Kurt |
| FIND-150 | E-okuyucuya göndermede içerik kısıtlaması | #17 | Hasan Kurt | Emre Bulut |
| FIND-126 | Parola sıfırlamada kullanıcı adı tahmini | #18 | Emre Bulut | Şeyda Altın |
| FIND-080, 109 | Çıplak `except` (W0702, E722) | #16 | Hasan Kurt | Emre Bulut |
| FIND-049 | Hata işleyicisinde `e.orig` (E1101) | #20 | Emre Bulut | Dilara Yıldırım |
| FIND-078 | Biçimlenmeyen hata mesajı (W0715) | #22 | Şeyda Altın | Dilara Yıldırım |
| FIND-081 | Ters `isinstance` (W1116) | #23 | Şeyda Altın | Dilara Yıldırım |
| FIND-056 | Eksik yer tutucu (E1305) | #24 | Şeyda Altın | Dilara Yıldırım |
| FIND-069 | Kodlaması belirtilmemiş `open()` (W1514) | #25 | Şeyda Altın | Dilara Yıldırım |
| FIND-117 | `jinjia.py` PEP 8 temizliği | #26 | Şeyda Altın | Dilara Yıldırım |

## Ekip ve roller

| Üye | Katkı |
| --- | --- |
| Şeyda Altın | Kapsam, mimari, Pylint/PEP 8 analizi ve kalite düzeltmeleri, son taramalar ve karşılaştırmalar |
| Dilara Yıldırım | Bandit taramaları ve risk sınıflandırması, bulgu kaydının yönetimi, zaman aşımı düzeltmesi, kalite düzeltmelerinin gözden geçirilmesi |
| Emre Bulut | Bandit bulgularının kod üzerinden değerlendirilmesi, kimlik doğrulama/yetki incelemesi ve düzeltmeleri, son taramanın bağımsız tekrarı |
| Hasan Kurt | Dosya işleme, süreç ve ağ incelemesi ve düzeltmeleri, araçların göremediği isteklerin tespiti, zaman aşımı düzeltmesinin gözden geçirilmesi |

## Klasör haritası

| Yol | İçerik |
| --- | --- |
| `docs/final-report.md` | Final rapor |
| `docs/findings-register.csv` | Bulgu kaydı (UTF-8 BOM, CRLF; Excel'de açıp kaydetmeyin) |
| `docs/1-kapsam/` | Kapsam, mimari, analiz edilen commit |
| `docs/2-baslangic/` | Başlangıç tarama özetleri (Pylint, flake8, Bandit) |
| `docs/3-inceleme/` | Bandit, kimlik doğrulama/yetki ve dosya işleme incelemeleri; rapor payları |
| `docs/4-duzeltme/` | Düzeltme adayları ve seçim gerekçesi |
| `docs/5-karsilastirma/` | Önce-sonra karşılaştırmaları |
| `docs/surec/` | Ortam notları ve tarama kayıtları, ekip çalışma kuralları, rol rehberleri |
| `reports/baseline/`, `reports/final/` | Ham tarama çıktıları (değiştirilmez) |
| `evidence/` | Yanlış Bandit sürümüyle (1.8.6) üretilip geçersiz sayılan ilk raporlar |
| `scripts/` | Özet ve karşılaştırma betikleri |

## Taramaları tekrarlama

Gereken: Python 3.12 ve Windows/PowerShell (başka işletim sistemlerinde raporlardaki yol ayıracı `/` olur).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m bandit --version    # 1.9.4
python -m pylint --version    # 4.1.3
python -m flake8 --version    # 7.4.1
git checkout 830d3a80
python -m bandit -r cps -f json -o reports\final\bandit-cps.json
python -m bandit cps.py -f json -o reports\final\bandit-entrypoint.json
python -m pylint cps.py cps --output=reports\final\pylint.txt
python -m flake8 --isolated --select=E,W --statistics --count --output-file=reports\final\pep8.txt cps.py cps
```

Karşılaştırma dokümanlarını yeniden üretmek için (güncel `project-analysis` dalında):

```powershell
python scripts/compare_reports.py --final-commit 830d3a80 --file-scores
```

- Araçlar bulgu bulduğunda sıfırdan farklı çıkış kodu döner; bu bir hata değildir.
- Pylint'in `R0401` (cyclic-import) mesaj sayısı aynı kod üzerinde çalıştırmadan çalıştırmaya değişir; karşılaştırmada bu yüzden ayrı tutulur.
- `python-ldap` ve `Flask-SimpleLDAP` Windows'ta derlenemediği için kilit dosyasında yoktur; LDAP kodu yine de taranır.
- Tarama kayıtları (tarih, çıkış kodu, sürümler): [docs/surec/environment-notes.md](docs/surec/environment-notes.md).

Calibre-Web'in kendi kurulum ve kullanım belgeleri için [README.md](README.md) dosyasına bakın.
