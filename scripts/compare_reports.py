#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Başlangıç (reports/baseline/) ve son (reports/final/) tarama raporlarını
karşılaştırır ve üç Türkçe karşılaştırma dokümanı üretir.

Girdi (değiştirilmez, ham raporlar):
    reports/{baseline,final}/pylint.txt
    reports/{baseline,final}/pep8.txt
    reports/{baseline,final}/bandit-cps.json, bandit-entrypoint.json
    docs/findings-register.csv   (FIND-ID / PR eşleştirmesi için, salt okunur)

Çıktı:
    docs/pylint-comparison.md
    docs/pep8-comparison.md
    docs/bandit-comparison.md

Eşleştirme yöntemi (CLAUDE.md → "Önce-sonra karşılaştırması"):
    Satır numaraları kayar, bu yüzden her uyarı şu anahtarla eşleştirilir:
        normalize yol ('\\' -> '/') + kural kodu + kod parçası
    Kod parçası, uyarının işaret ettiği kaynak satırın boşlukları kırpılmış
    metnidir; ilgili commit'teki dosyadan `git show <commit>:<yol>` ile okunur
    (başlangıç: docs/baseline-commit.txt, son: --final-commit).
    Aynı anahtar birden çok kez geçebilir; eşleştirme çoklu küme (multiset)
    farkıyla yapılır.
    İkinci geçiş: kapanan ve yeni çıkan listelerinde aynı yol + kod + mesaj
    (sayılar çıkarılmış) taşıyan çiftler "devam eden (satırı değişti)" sayılır;
    yalnızca satırı yeniden biçimlendirilen bir uyarı böylece hem "kapandı"
    hem "yeni" görünmez.

İsteğe bağlı: --file-scores, düzeltilen dosyalarda dosya bazlı Pylint puanını
başlangıç commit'i (geçici git worktree) ve son commit için ayrı ayrı
`python -m pylint <dosya>` ile hesaplar. Bu resmi tarama değildir; yalnızca
dosya düzeyindeki etkiyi göstermek içindir.

Kullanım:
    python scripts/compare_reports.py --final-commit 830d3a80 [--file-scores]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "reports" / "baseline"
FINAL = ROOT / "reports" / "final"
DOCS = ROOT / "docs"
REGISTER = DOCS / "findings-register.csv"

CATEGORY_NAMES = {"C": "convention", "R": "refactor", "W": "warning",
                  "E": "error", "F": "fatal", "I": "information"}

# Dosya bazlı puan tablosu için düzeltme PR'larının dokunduğu dosyalar.
FIXED_FILES = [
    ("cps/admin.py", "FIND-049, 069, 078 (PR #20, #25, #22)"),
    ("cps/shelf.py", "FIND-049 (PR #20)"),
    ("cps/helper.py", "FIND-081, 056 (PR #23, #24)"),
    ("cps/file_helper.py", "FIND-080/109 (PR #16)"),
    ("cps/web.py", "FIND-150, 126 (PR #17, #18)"),
    ("cps/dep_check.py", "FIND-069 (PR #25)"),
    ("cps/kobo.py", "FIND-069 (PR #25)"),
    ("cps/updater.py", "FIND-069 (PR #25)"),
    ("cps/jinjia.py", "FIND-117 (PR #26)"),
    ("cps/services/goodreads_support.py", "FIND-014, 085 (PR #21)"),
    ("cps/metadata_provider/comicvine.py", "FIND-010 (PR #21)"),
    ("cps/metadata_provider/google.py", "FIND-011 (PR #21)"),
    ("cps/metadata_provider/lubimyczytac.py", "FIND-012, 013 (PR #21)"),
    ("cps/metadata_provider/amazon.py", "FIND-116 (PR #21)"),
]


# --------------------------------------------------------------------------
# Yardımcılar
# --------------------------------------------------------------------------

def norm(path: str) -> str:
    return path.replace("\\", "/")


class Source:
    """Bir commit'teki dosya satırlarını git'ten okur (önbellekli)."""

    def __init__(self, commit: str):
        self.commit = commit
        self.cache: dict[str, list[str]] = {}

    def line(self, path: str, lineno: int) -> str:
        if path not in self.cache:
            res = subprocess.run(["git", "show", f"{self.commit}:{path}"],
                                 cwd=ROOT, capture_output=True, check=False)
            text = res.stdout.decode("utf-8", errors="replace")
            self.cache[path] = text.splitlines() if res.returncode == 0 else []
        lines = self.cache[path]
        if 1 <= lineno <= len(lines):
            return lines[lineno - 1].strip()
        return ""


def msg_class(msg: str) -> str:
    """Eşleştirme için mesajdaki sayıları çıkarır."""
    return re.sub(r"\d+", "#", msg)


class Item:
    __slots__ = ("path", "code", "line", "msg", "snippet", "extra")

    def __init__(self, path, code, line, msg, snippet, extra=None):
        self.path, self.code, self.line = path, code, line
        self.msg, self.snippet, self.extra = msg, snippet, extra or {}

    @property
    def key(self):
        return (self.path, self.code, self.snippet)


MOVE_WINDOW = 10  # ikinci geçişte kabul edilen en büyük satır uzaklığı


def _nearest_pairs(left, right, max_dist=None):
    """İki listeyi satır numarası en yakın olan çiftlerden başlayarak eşler.
    Dönüş: (çiftler, eşleşmeyen sol, eşleşmeyen sağ)."""
    cands = sorted(((abs(l.line - r.line), i, j)
                    for i, l in enumerate(left) for j, r in enumerate(right)
                    if max_dist is None or abs(l.line - r.line) <= max_dist))
    used_l, used_r, pairs = set(), set(), []
    for _, i, j in cands:
        if i not in used_l and j not in used_r:
            used_l.add(i)
            used_r.add(j)
            pairs.append((left[i], right[j]))
    rest_l = [x for i, x in enumerate(left) if i not in used_l]
    rest_r = [x for j, x in enumerate(right) if j not in used_r]
    return pairs, rest_l, rest_r


def compare(before: list[Item], after: list[Item]):
    """Kapanan / devam eden / yeni çıkan + satırı değişen eşleşmeler.

    1. geçiş: aynı yol + kod + kod parçası; aynı anahtar birden çok kez
       geçiyorsa örnekler en yakın satır numarasıyla eşlenir (böylece
       değişmeyen satırlar değişen satırların yerine "kapanmış" sayılmaz).
    2. geçiş: kalan kapanan / yeni çıkanlar arasında aynı yol + kod + mesaj
       sınıfı ve en fazla MOVE_WINDOW satır uzaklık → "satırı değişti".
    """
    bk, ak = defaultdict(list), defaultdict(list)
    for it in before:
        bk[it.key].append(it)
    for it in after:
        ak[it.key].append(it)
    closed, new, persisting = [], [], []
    for k in set(bk) | set(ak):
        pairs, rest_b, rest_a = _nearest_pairs(bk.get(k, []), ak.get(k, []))
        persisting += [a for _, a in pairs]
        closed += rest_b
        new += rest_a
    gb, ga = defaultdict(list), defaultdict(list)
    for it in closed:
        gb[(it.path, it.code, msg_class(it.msg))].append(it)
    for it in new:
        ga[(it.path, it.code, msg_class(it.msg))].append(it)
    moved, really_closed, really_new = [], [], []
    for k in set(gb) | set(ga):
        pairs, rest_b, rest_a = _nearest_pairs(gb.get(k, []), ga.get(k, []),
                                               MOVE_WINDOW)
        moved += pairs
        really_closed += rest_b
        really_new += rest_a
    srt = lambda lst: sorted(lst, key=lambda x: (x.path, x.line, x.code))
    moved.sort(key=lambda p: (p[0].path, p[0].line))
    return srt(really_closed), srt(persisting), moved, srt(really_new)


def load_register():
    raw = REGISTER.read_bytes().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(raw, newline="")))


def find_ids(register, path: str, code: str, line: int | None = None):
    """Düzeltildi durumundaki kayıt satırlarından FIND-ID ve PR bul."""
    hits = []
    for r in register:
        if r["durum"] != "Düzeltildi":
            continue
        codes = [c.strip() for c in r["kural_kodu"].split(",")]
        if code not in codes:
            continue
        files = [f.strip() for f in r["dosya"].split(";")]
        if path in files or any(f.startswith("cps/ (") for f in files):
            hits.append(r)
    if line is not None and len(hits) > 1:
        def dist(r):
            nums = [int(x) for x in re.findall(r"\d+", r["satir"])]
            return min((abs(n - line) for n in nums), default=10 ** 6)
        hits.sort(key=dist)
        hits = hits[:1]
    return ", ".join(f'{r["id"]} ({r["commit_pr"]})' for r in hits) or "-"


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |",
           "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def delta(b, a):
    d = a - b
    return f"{d:+d}" if d else "0"


# --------------------------------------------------------------------------
# Ayrıştırıcılar
# --------------------------------------------------------------------------

PYLINT_RE = re.compile(r"^(cps[^:]*\.py):(\d+):(\d+): ([CRWEFI]\d{4}): (.*)$")
PEP8_RE = re.compile(r"^(cps[^:]*\.py):(\d+):(\d+): ([EW]\d{3}) (.*)$")
SCORE_RE = re.compile(r"rated at (-?[\d.]+)/10")


def parse_pylint(path: Path, src: Source):
    items, score = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PYLINT_RE.match(line)
        if m:
            p, ln = norm(m.group(1)), int(m.group(2))
            items.append(Item(p, m.group(4), ln, m.group(5), src.line(p, ln)))
        s = SCORE_RE.search(line)
        if s:
            score = float(s.group(1))
    return items, score


def parse_pep8(path: Path, src: Source):
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PEP8_RE.match(line)
        if m:
            p, ln = norm(m.group(1)), int(m.group(2))
            items.append(Item(p, m.group(4), ln, m.group(5), src.line(p, ln)))
    return items


def parse_bandit(folder: Path, src: Source):
    items, totals = [], {}
    for name in ("bandit-cps.json", "bandit-entrypoint.json"):
        data = json.loads((folder / name).read_text(encoding="utf-8"))
        totals[name] = data["metrics"]["_totals"]
        for r in data["results"]:
            p, ln = norm(r["filename"]), r["line_number"]
            items.append(Item(p, r["test_id"], ln, r["issue_text"],
                              src.line(p, ln),
                              {"sev": r["issue_severity"],
                               "conf": r["issue_confidence"],
                               "name": r["test_name"], "report": name}))
    return items, totals


# --------------------------------------------------------------------------
# Dosya bazlı Pylint puanları (isteğe bağlı)
# --------------------------------------------------------------------------

def file_scores(baseline_commit: str, final_commit: str):
    py = sys.executable
    tmp = Path(tempfile.mkdtemp(prefix="cw-compare-"))
    trees = {"baseline": tmp / "baseline", "final": tmp / "final"}
    result = {}
    try:
        for label, commit in (("baseline", baseline_commit),
                              ("final", final_commit)):
            subprocess.run(["git", "worktree", "add", "-q", "--detach",
                            str(trees[label]), commit], cwd=ROOT, check=True)
        for f, _ in FIXED_FILES:
            result[f] = {}
            for label, tree in trees.items():
                out = subprocess.run([py, "-m", "pylint", f], cwd=tree,
                                     capture_output=True, text=True,
                                     encoding="utf-8", errors="replace")
                s = SCORE_RE.search(out.stdout)
                n = sum(1 for ln in out.stdout.splitlines()
                        if PYLINT_RE.match(ln))
                result[f][label] = (float(s.group(1)) if s else None, n)
    finally:
        for tree in trees.values():
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)],
                           cwd=ROOT, check=False, capture_output=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, check=False)
        shutil.rmtree(tmp, ignore_errors=True)
    return result


# --------------------------------------------------------------------------
# Doküman üreticileri
# --------------------------------------------------------------------------

def header_block(title, baseline_commit, final_commit, extra=""):
    return (f"# {title}\n\n"
            "Bu dosya `scripts/compare_reports.py` ile ham raporlardan üretilir; "
            "elle düzenlenmez. Ham raporlar değiştirilmez.\n\n"
            f"- Başlangıç: `reports/baseline/` · commit `{baseline_commit[:8]}` "
            "(upstream `master`, `docs/baseline-commit.txt`)\n"
            f"- Son: `reports/final/` · commit `{final_commit[:8]}` "
            "(`project-analysis`, 24 Kasım 2026, K10)\n"
            "- Aynı araç sürümü, aynı kapsam (`cps/` + `cps.py`), aynı "
            "parametreler (CLAUDE.md → \"Tarama komutları\"; "
            "`docs/environment-notes.md` → \"Tarama kayıtları\").\n"
            "- Eşleştirme: normalize yol + kural kodu + kod parçası (kaynak "
            "satırın metni). Satırı yeniden biçimlenip aynı mesajla süren "
            "uyarılar \"devam eden (satırı değişti)\" sayılır.\n"
            "- Susturma: bu dönemde `# nosec`, `# noqa` veya "
            "`# pylint: disable` eklenmedi (K6); aşağıdaki tüm kapanışlar "
            "kod düzeltmesidir.\n"
            f"{extra}\n")


# Kayıtta kendi satırı olmayan, ama bir düzeltme PR'ının dokunduğu satırda
# kapanan uyarılar: (yol, başlangıç satır aralığı) -> açıklama.
SIDE_EFFECTS = [
    ("cps/jinjia.py", 1, 200, "FIND-117 (PR #26) yan etkisi"),
    ("cps/web.py", 1428, 1440, "FIND-126 (PR #18) yan etkisi"),
    ("cps/updater.py", 150, 160, "FIND-069 (PR #25) yan etkisi"),
    ("cps/updater.py", 405, 415, "FIND-069 (PR #25) yan etkisi"),
]


def finding_label(register, it):
    fid = find_ids(register, it.path, it.code, it.line)
    if fid != "-":
        return fid
    for path, lo, hi, label in SIDE_EFFECTS:
        if it.path == path and lo <= it.line <= hi:
            return label
    return "-"


def item_rows(items, register, with_find=True, snippet=True):
    rows = []
    for it in items:
        row = [f"`{it.path}:{it.line}`", f"`{it.code}`", it.msg.replace("|", "\\|")]
        if snippet:
            row.append(f"`{it.snippet[:70].replace('|', '¦')}`" if it.snippet else "-")
        if with_find:
            row.append(finding_label(register, it))
        rows.append(row)
    return rows


NEW_EXPLAIN = {
    # (yol, kod) -> açıklama; yeni çıkan uyarılar için
}


# Pylint'in cyclic-import (R0401) raporu deterministik değil: aynı commit'te
# iki ayrı çalıştırma farklı sayıda ve farklı zincirlerle R0401 verdi
# (başlangıç commit'i 43 / 48, son commit 49 / 44; puan ve diğer tüm
# mesajlar aynı). Bu yüzden R0401 eşleştirmeye katılmaz, ayrı raporlanır.
NONDETERMINISTIC = {"R0401"}
R0401_RERUNS = {"baseline": (43, 48), "final": (49, 44)}


def write_pylint(bi_all, bs, fi_all, fs, register, scores, bc, fc):
    bi = [i for i in bi_all if i.code not in NONDETERMINISTIC]
    fi = [i for i in fi_all if i.code not in NONDETERMINISTIC]
    nd_b = len(bi_all) - len(bi)
    nd_f = len(fi_all) - len(fi)
    closed, persisting, moved, new = compare(bi, fi)
    cb = Counter(i.code[0] for i in bi_all)
    ca = Counter(i.code[0] for i in fi_all)
    kb = Counter(i.code for i in bi_all)
    ka = Counter(i.code for i in fi_all)
    symb = {}
    for i in bi_all + fi_all:
        m = re.search(r"\(([a-z0-9-]+)\)$", i.msg)
        if m:
            symb[i.code] = m.group(1)

    out = [header_block("Pylint önce-sonra karşılaştırması", bc, fc)]
    out.append("## 1. Özet\n")
    out.append(md_table(
        ["Ölçü", "Başlangıç", "Son", "Fark"],
        [["Puan (score)", f"{bs:.2f}/10", f"{fs:.2f}/10", f"{fs - bs:+.2f}"],
         ["Toplam mesaj (ham rapor)", len(bi_all), len(fi_all),
          delta(len(bi_all), len(fi_all))],
         ["  içinde `R0401` cyclic-import (bkz. not)", nd_b, nd_f,
          delta(nd_b, nd_f)],
         ["**Toplam mesaj, `R0401` hariç**", len(bi), len(fi),
          delta(len(bi), len(fi))],
         ["Kapanan", "", len(closed), ""],
         ["Devam eden (aynı satır)", "", len(persisting), ""],
         ["Devam eden (satırı değişti)", "", len(moved), ""],
         ["Yeni çıkan", "", len(new), ""]]))
    out.append("\nKontrol (`R0401` hariç): başlangıç = kapanan + devam eden "
               f"→ {len(bi)} = {len(closed)} + {len(persisting)} + "
               f"{len(moved)}; son = devam eden + yeni → {len(fi)} = "
               f"{len(persisting)} + {len(moved)} + {len(new)}.\n")
    rb, rf = R0401_RERUNS["baseline"], R0401_RERUNS["final"]
    out.append(
        "**`R0401` (cyclic-import) notu.** Ham raporlarda `R0401` sayısı "
        f"{nd_b} → {nd_f} görünüyor, ama bu düzeltmelerden kaynaklanmıyor: "
        "başlangıç ile son commit arasında hiçbir `import`/`from` satırı "
        "değişmedi (`git diff` ile kontrol edildi). Pylint'in döngüsel import "
        "raporu çalıştırmadan çalıştırmaya değişiyor: aynı parametrelerle "
        f"yapılan doğrulama çalıştırmalarında başlangıç commit'i {rb[0]} ve "
        f"{rb[1]}, son commit {rf[0]} ve {rf[1]} `R0401` verdi; diğer tüm "
        "mesajlar ve puan iki çalıştırmada da aynıydı. Bu doğrulama "
        "çalıştırmaları yalnızca kontrol içindir, rapor olarak kaydedilmedi "
        "ve baseline'ı değiştirmez (kural 11). Bu yüzden `R0401` "
        "eşleştirmeye katılmadı; tablolarda ham sayısıyla gösterildi.\n")
    out.append("Puan artışının küçük olması beklenen bir sonuç: K5 kararı gereği "
               "toplu biçimlendirme yapılmadı, yalnızca seçilmiş bulgular "
               f"elle düzeltildi. {len(bi)} mesajdan (`R0401` hariç) "
               f"{len(closed)} tanesi "
               "kapandı; puan tüm projenin mesaj yoğunluğuna göre "
               "hesaplanır.\n")

    out.append("## 2. Kategori bazında\n")
    out.append(md_table(
        ["Kategori", "Başlangıç", "Son", "Fark"],
        [[f"{CATEGORY_NAMES[c]} ({c})", cb[c], ca[c], delta(cb[c], ca[c])]
         for c in "CRWEFI" if cb[c] or ca[c]]
        + [["**Toplam**", len(bi_all), len(fi_all),
            delta(len(bi_all), len(fi_all))]]))
    out.append(f"\n`refactor` satırındaki farkın {nd_f - nd_b:+d} mesajlık "
               "kısmı `R0401` oynamasıdır (bkz. not).\n")

    out.append("## 3. Mesaj kodu bazında (yalnızca sayısı değişen kodlar)\n")
    changed = sorted((c for c in set(kb) | set(ka) if kb[c] != ka[c]),
                     key=lambda c: (ka[c] - kb[c], c))
    out.append(md_table(
        ["Kod", "Sembol", "Başlangıç", "Son", "Fark", "İlgili bulgu (PR)"],
        [[f"`{c}`", symb.get(c, ""), kb[c], ka[c], delta(kb[c], ka[c]),
          _find_any(register, c)] for c in changed]))
    out.append(f"\nDiğer {len(set(kb) | set(ka)) - len(changed)} mesaj "
               "kodunun sayısı değişmedi.\n")

    if scores:
        out.append("## 4. Düzeltilen dosyalarda dosya bazlı puan\n")
        out.append("Her dosya için `python -m pylint <dosya>` ayrı ayrı "
                   "çalıştırıldı (başlangıç commit'i ve son commit, geçici "
                   "worktree'lerde). Resmi tarama değildir; dosya düzeyindeki "
                   "etkiyi gösterir. `cps/metadata_provider/` dosyaları resmi "
                   "taramada yer almadığı için (bkz. \"`cps/metadata_provider/` "
                   "kapsam notu\") yalnızca burada görünür.\n")
        rows = []
        for f, why in FIXED_FILES:
            b, a = scores[f]["baseline"], scores[f]["final"]
            bsc = f"{b[0]:.2f}" if b[0] is not None else "-"
            asc = f"{a[0]:.2f}" if a[0] is not None else "-"
            dsc = (f"{a[0] - b[0]:+.2f}" if None not in (a[0], b[0]) else "-")
            rows.append([f"`{f}`", why, bsc, asc, dsc, b[1], a[1],
                         delta(b[1], a[1])])
        out.append(md_table(["Dosya", "Düzeltme", "Puan önce", "Puan sonra",
                             "Fark", "Mesaj önce", "Mesaj sonra", "Fark"], rows))
        out.append("")

    n = 5 if scores else 4
    out.append(f"## {n}. Kapanan mesajlar ({len(closed)})\n")
    out.append(md_table(["Konum (başlangıç)", "Kod", "Mesaj", "Kod parçası",
                         "Bulgu (PR)"], item_rows(closed, register)))
    out.append(f"\n## {n + 1}. Devam eden mesajlar\n")
    out.append(f"- Aynı satırda süren: **{len(persisting)}**.\n"
               f"- Satırı değişen ama aynı mesajla süren: **{len(moved)}**. "
               "Bunlar düzeltilen satırlarda ya da onların hemen yanında; "
               "uyarı kodun yeni halinde de geçerli:\n")
    out.append(md_table(
        ["Başlangıç", "Son", "Kod", "Mesaj (son)"],
        [[f"`{b.path}:{b.line}`", f"`{a.path}:{a.line}`", f"`{a.code}`",
          a.msg.replace("|", "\\|")] for b, a in moved]))
    out.append(f"\n## {n + 2}. Yeni çıkan mesajlar ({len(new)})\n")
    if new:
        out.append(md_table(["Konum (son)", "Kod", "Mesaj", "Kod parçası",
                             "Açıklama"],
                            [r[:-1] + [NEW_EXPLAIN.get((it.path, it.code), "")]
                             for r, it in zip(item_rows(new, register), new)]))
    else:
        out.append("Yeni çıkan mesaj yok: düzeltmeler hiçbir dosyada yeni "
                   "Pylint uyarısı doğurmadı.")
    out.append(PYLINT_TAIL)
    (DOCS / "pylint-comparison.md").write_text("\n".join(out) + "\n",
                                               encoding="utf-8", newline="\n")
    return closed, persisting, moved, new


def _find_any(register, code):
    ids = [f'{r["id"]} ({r["commit_pr"]})' for r in register
           if r["durum"] == "Düzeltildi"
           and code in [c.strip() for c in r["kural_kodu"].split(",")]]
    return ", ".join(ids) or "-"


PYLINT_TAIL = """
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

Toplam **7 Pylint türü**. Buna ek olarak flake8'de 5 PEP 8 türü (E722, E501, E226, E302, W391) düzeltildi (`docs/pep8-comparison.md`). Hedef karşılanıyor.

Sayım notu: `W0702` (Pylint) ile `E722` (flake8) aynı satırın iki aracın gözünden görünümü; tek değişiklikle kapandılar. Karşılaştırmada ayrı uyarı olarak sayılırlar, ama ayrı düzeltme sayılmazlar. Aynı şekilde `W3101`, B113 düzeltmesinin (PR #21) yan etkisidir.

Bazı mesajlar düzeltmenin dolaylı sonucu olarak da kapandı: silinen veya bölünen satırlardaki `C0301` (line-too-long), `W1406` (redundant-u-string-prefix) ve `jinjia.py`'deki `C0305` (trailing-newlines). Bunlar ayrı düzeltme türü olarak sayılmadı.

## `cps/metadata_provider/` kapsam notu

`cps/metadata_provider/` dizininde `__init__.py` yok. Bu yüzden `python -m pylint cps.py cps` komutu bu dizindeki 6 dosyaya (amazon, comicvine, douban, google, lubimyczytac, scholar) girmiyor: başlangıç ve son `pylint.txt`'de bu dizine ait **0 mesaj** var. Bandit (`-r cps`) ve flake8 ise dizini tarıyor.

Sonuç: B113 düzeltmesi (PR #21) bu dizindeki 4 `missing-timeout` (W3101) uyarısını da kapattı (dosya bazlı çalıştırmada görülüyor, bölüm 4), ama resmi karşılaştırmada yalnızca `cps/services/goodreads_support.py`'deki 1 `W3101` (FIND-085) kapanmış görünüyor. Tarama parametreleri baseline ile aynı kalsın diye kapsam değiştirilmedi; bu bir araç kullanım sınırlılığı olarak final rapora (bölüm 10) yazılır.
"""


def write_pep8(bi, fi, register, bc, fc):
    closed, persisting, moved, new = compare(bi, fi)
    kb, ka = Counter(i.code for i in bi), Counter(i.code for i in fi)
    msgs = {}
    for i in bi + fi:
        msgs.setdefault(i.code, re.sub(r"\(.*\)$", "", i.msg).strip())
    extra = ("- flake8 `--isolated --select=E,W`, satır uzunluğu 79 (K4). "
             "Toplam ihlal, raporun ihlal satırlarından sayıldı (`--statistics` "
             "özetiyle aynı).\n")
    out = [header_block("PEP 8 (flake8) önce-sonra karşılaştırması", bc, fc, extra)]
    out.append("## 1. Özet\n")
    out.append(md_table(
        ["Ölçü", "Başlangıç", "Son", "Fark"],
        [["Toplam ihlal", len(bi), len(fi), delta(len(bi), len(fi))],
         ["İhlal kodu sayısı", len(kb), len(ka), delta(len(kb), len(ka))],
         ["Kapanan", "", len(closed), ""],
         ["Devam eden (aynı satır)", "", len(persisting), ""],
         ["Devam eden (satırı değişti)", "", len(moved), ""],
         ["Yeni çıkan", "", len(new), ""]]))
    out.append(f"\nKontrol: {len(bi)} = {len(closed)} + {len(persisting)} + "
               f"{len(moved)}; {len(fi)} = {len(persisting)} + {len(moved)} + "
               f"{len(new)}.\n")

    out.append("## 2. Kod bazında\n")
    codes = sorted(set(kb) | set(ka))
    out.append(md_table(
        ["Kod", "Açıklama", "Başlangıç", "Son", "Fark"],
        [[f"`{c}`", msgs[c], kb[c], ka[c], delta(kb[c], ka[c])] for c in codes]
        + [["**Toplam**", "", len(bi), len(fi), delta(len(bi), len(fi))]]))

    out.append("\n## 3. Düzeltilen dosyalar\n")
    fb = Counter(i.path for i in bi)
    fa = Counter(i.path for i in fi)
    touched = sorted({i.path for i in closed} | {i.path for i in new}
                     | {b.path for b, _ in moved})
    rows = []
    for p in touched:
        cl = Counter(i.code for i in closed if i.path == p)
        nw = Counter(i.code for i in new if i.path == p)
        rows.append([f"`{p}`", fb[p], fa[p], delta(fb[p], fa[p]),
                     ", ".join(f"{c} ×{n}" for c, n in sorted(cl.items())) or "-",
                     ", ".join(f"{c} ×{n}" for c, n in sorted(nw.items())) or "-"])
    out.append(md_table(["Dosya", "Önce", "Sonra", "Fark", "Kapanan", "Yeni"], rows))
    jb = [i for i in bi if i.path == "cps/jinjia.py"]
    ja = [i for i in fi if i.path == "cps/jinjia.py"]
    out.append(f"\n**`cps/jinjia.py` (FIND-117, PR #26): {len(jb)} → {len(ja)}.** "
               "Dosya elle temizlendi (black/autopep8 kullanılmadı, K5). Kalan "
               f"{len(ja)} ihlalin hepsi `E501` ve GPL lisans/telif başlığında "
               "(satır " + ", ".join(str(i.line) for i in ja) + "). CLAUDE.md "
               "lisans bildirimlerinin değiştirilmesini yasakladığı için bu "
               "satırlara dokunulmadı; susturulmadılar da (K6).\n")

    out.append(f"## 4. Kapanan ihlaller ({len(closed)})\n")
    out.append(md_table(["Konum (başlangıç)", "Kod", "Mesaj", "Kod parçası",
                         "Bulgu (PR)"], item_rows(closed, register)))
    out.append("\n`jinjia.py`'deki ihlaller FIND-117'nin (PR #26) parçası, "
               "`E722` FIND-109'dur (PR #16). \"Yan etki\" satırları, kayıtta "
               "kendi satırı olmayan ama bir düzeltme PR'ının değiştirdiği "
               "(silinen ya da bölünen) satırda kapanan ihlallerdir.\n")
    out.append("## 5. Devam eden ihlaller\n")
    out.append(f"- Aynı satırda süren: **{len(persisting)}**.\n"
               f"- Satırı değişen ama aynı mesajla süren: **{len(moved)}**:\n")
    out.append(md_table(
        ["Başlangıç", "Son", "Kod", "Mesaj (son)"],
        [[f"`{b.path}:{b.line}`", f"`{a.path}:{a.line}`", f"`{a.code}`",
          a.msg.replace("|", "\\|")] for b, a in moved]) if moved else "Yok.")
    out.append(f"\n## 6. Yeni çıkan ihlaller ({len(new)})\n")
    if new:
        out.append(md_table(["Konum (son)", "Kod", "Mesaj", "Kod parçası",
                             "Açıklama"],
                            [r[:-1] + [NEW_EXPLAIN.get((it.path, it.code), "")]
                             for r, it in zip(item_rows(new, register), new)]))
    else:
        out.append("Yok.")
    out.append(PEP8_TAIL.format(w503b=kb["W503"], w503a=ka["W503"],
                                w504b=kb["W504"], w504a=ka["W504"]))
    (DOCS / "pep8-comparison.md").write_text("\n".join(out) + "\n",
                                             encoding="utf-8", newline="\n")
    return closed, persisting, moved, new


PEP8_TAIL = """
## W503 / W504 notu

`W503` (ikili operatörden **önce** satır kırma) ve `W504` (ikili operatörden **sonra** satır kırma) birbirinin tersidir: PEP 8 bugün `W503` biçimini öneriyor ve flake8 varsayılanında ikisi de kapalıdır. Bu projede flake8 `--select=E,W` ile çalıştığı için (K4) ikisi de açık; bu yüzden operatörde bölünen **her** satır bu iki uyarıdan birini mutlaka verir. Başlangıç `W503` {w503b} / `W504` {w504b}, son `W503` {w503a} / `W504` {w504a}.

Bu iki kod düzeltme hedefi olarak seçilmedi: birini düzeltmek diğerini doğurur. Ayrıca PEP 8 tarafından gerçek ihlal sayılmazlar. Bu ihlaller FIND-112 grup satırında "Kabul edildi (düzeltilmeyecek)" olarak duruyor.

## K5 gerekçesi (PEP 8 kısmı)

Bu dönemde düzeltilen flake8 türleri: `E722` (FIND-109, PR #16), `E501`, `E226`, `E302` ve `W391` (FIND-117, PR #26). Toplam **5 PEP 8 türü**; Pylint'teki 7 türle birlikte K5'in "en az 5 kod kalitesi / PEP 8 türü" hedefi karşılanıyor (`docs/pylint-comparison.md`).

Toplam ihlalin yalnızca 16 azalması beklenen bir sonuç: K5 gereği toplu biçimlendirme yapılmadı. Seçilen tek dosya (`jinjia.py`) elle ve lisans başlığı korunarak temizlendi.
"""


def write_bandit(bi, btot, fi, ftot, register, bc, fc):
    closed, persisting, moved, new = compare(bi, fi)
    sev = ["HIGH", "MEDIUM", "LOW"]

    def matrix(items):
        c = Counter((i.extra["sev"], i.extra["conf"]) for i in items)
        rows = [[f"**{s}**"] + [c[(s, k)] for k in sev]
                + [sum(c[(s, k)] for k in sev)] for s in sev]
        rows.append(["**Toplam**"] + [sum(c[(s, k)] for s in sev) for k in sev]
                    + [len(items)])
        return md_table(["Önem \\ Güven", "HIGH", "MEDIUM", "LOW", "Toplam"], rows)

    out = [header_block("Bandit önce-sonra karşılaştırması", bc, fc,
                        "- Bandit varsayılan ayarlarla, tüm testler (K4). İki "
                        "rapor birlikte değerlendirildi: `bandit-cps.json` "
                        "(`-r cps`) ve `bandit-entrypoint.json` (`cps.py`).\n")]
    out.append("## 1. Özet\n")
    bs = Counter(i.extra["sev"] for i in bi)
    fs = Counter(i.extra["sev"] for i in fi)
    rows = [["Toplam bulgu", len(bi), len(fi), delta(len(bi), len(fi))]]
    for s in sev:
        rows.append([f"{s} önem", bs[s], fs[s], delta(bs[s], fs[s])])
    for name in ("bandit-cps.json", "bandit-entrypoint.json"):
        nb = sum(1 for i in bi if i.extra["report"] == name)
        nf = sum(1 for i in fi if i.extra["report"] == name)
        rows.append([f"`{name}`", nb, nf, delta(nb, nf)])
    for key, label in (("loc", "Taranan satır (LOC)"), ("nosec", "`# nosec` satırı")):
        b = sum(t[key] for t in btot.values())
        a = sum(t[key] for t in ftot.values())
        rows.append([label, b, a, delta(b, a)])
    rows += [["Kapanan", "", len(closed), ""],
             ["Devam eden", "", len(persisting) + len(moved), ""],
             ["Yeni çıkan", "", len(new), ""]]
    out.append(md_table(["Ölçü", "Başlangıç", "Son", "Fark"], rows))
    out.append("\n`# nosec` sayısı değişmedi: bu dönemde susturma yorumu "
               "eklenmedi (K6). LOC artışı, düzeltmelerde satır bölmelerinden "
               "kaynaklanıyor.\n")

    out.append("## 2. Önem × güven matrisi\n")
    out.append("**Başlangıç**\n")
    out.append(matrix(bi))
    out.append("\n**Son**\n")
    out.append(matrix(fi))

    out.append("\n## 3. Test kimliği (test_id) bazında\n")
    tb, ta = Counter(i.code for i in bi), Counter(i.code for i in fi)
    names = {i.code: i.extra["name"] for i in bi + fi}
    sevs = defaultdict(set)
    for i in bi + fi:
        sevs[i.code].add(i.extra["sev"])
    out.append(md_table(
        ["test_id", "Ad", "Önem", "Başlangıç", "Son", "Fark"],
        [[f"`{c}`", names[c], "/".join(sorted(sevs[c])), tb[c], ta[c],
          delta(tb[c], ta[c])] for c in sorted(set(tb) | set(ta))]))

    out.append(f"\n## 4. Kapanan bulgular ({len(closed)})\n")
    rows = []
    for it in closed:
        rows.append([f"`{it.path}:{it.line}`", f"`{it.code}`",
                     f'{it.extra["sev"]}/{it.extra["conf"]}',
                     f"`{it.snippet[:60]}`", find_ids(register, it.path, it.code, it.line)])
    out.append(md_table(["Konum (başlangıç)", "test_id", "Önem/Güven",
                         "Kod parçası", "Bulgu (PR)"], rows))
    out.append("\nHepsi PR #21'de `timeout=(5, 30)` eklenerek kod düzeyinde "
               "kapandı (susturma yok). Aynı PR, Pylint `W3101` (FIND-085) "
               "uyarısını da kapattı.\n")

    out.append("## 5. Devam eden ve yeni çıkan bulgular\n")
    out.append(f"- Devam eden: **{len(persisting) + len(moved)}** "
               f"(aynı satırda {len(persisting)}, satırı değişen {len(moved)}).")
    if moved:
        out.append("\n" + md_table(
            ["Başlangıç", "Son", "test_id", "Kod parçası (son)"],
            [[f"`{b.path}:{b.line}`", f"`{a.path}:{a.line}`", f"`{a.code}`",
              f"`{a.snippet[:60]}`"] for b, a in moved]))
        out.append("\nSatırı değişen bulgular, aynı dosyadaki düzeltmelerin "
                   "satır numaralarını kaydırmasından kaynaklanıyor; bulgunun "
                   "kendisi değişmedi.")
    out.append(f"\n- Yeni çıkan: **{len(new)}**.\n")
    if new:
        out.append(md_table(["Konum (son)", "test_id", "Önem/Güven", "Kod parçası"],
                            [[f"`{i.path}:{i.line}`", f"`{i.code}`",
                              f'{i.extra["sev"]}/{i.extra["conf"]}',
                              f"`{i.snippet[:60]}`"] for i in new]))
    pers = Counter(i.code for i in persisting) + Counter(a.code for _, a in moved)
    out.append("\nDevam eden bulguların test_id dağılımı: "
               + ", ".join(f"`{c}` ×{n}" for c, n in sorted(pers.items()))
               + ". Bu bulguların her biri kayıtta kodla incelendi "
               "(`docs/review-bandit.md`, `docs/findings-register.csv`): "
               "yanlış pozitif ya da düşük öncelikli olarak kabul edildi.\n")
    fp = sum(1 for r in register if r["kaynak"] == "Bandit"
             and r["dogrulama_sonucu"] == "Yanlış pozitif")
    out.append(BANDIT_TAIL.replace("{bandit_fp}", str(fp)))
    (DOCS / "bandit-comparison.md").write_text("\n".join(out) + "\n",
                                               encoding="utf-8", newline="\n")
    return closed, persisting, moved, new


BANDIT_TAIL = """## 6. Güvenlik düzeltmeleri ve K5 (en az 3 güvenlik bulgusu)

| Bulgu | Tür | Dosya | PR | Bandit'te görünür mü? | Son tarama |
| --- | --- | --- | --- | --- | --- |
| FIND-010…014 | B113 zaman aşımsız dış istek | `metadata_provider/*`, `services/goodreads_support.py` | #21 | Evet (MEDIUM/LOW) | Kapandı (5) |
| FIND-116 | Zaman aşımsız `requests.Session` isteği | `metadata_provider/amazon.py:61, 121` | #21 | **Hayır** | Kod düzeltildi; araç uyarısı yok |
| FIND-150 | İçerik kısıtlaması e-okuyucuya göndermede aşılıyor | `web.py` (`send_to_ereader`) | #17 | Hayır (yetki mantığı) | Kod düzeltildi; araç uyarısı yok |
| FIND-126 | Parola sıfırlamada kullanıcı adı tahmini | `web.py` (`login_post`) | #18 | Hayır (mantık hatası) | Kısmi: tahmin kapandı, onaysız sıfırlama öneri |

Toplam 8 güvenlik bulgusu düzeltildi (B113 ×5, FIND-116, FIND-150, FIND-126); K5'in "en az 3 güvenlik bulgusu" hedefi karşılanıyor. Buna ek olarak {bandit_fp} Bandit kaydı kodla incelenip **yanlış pozitif** olarak gerekçelendirildi (`docs/findings-register.csv`).

## 7. Araç sınırlılığı: B113 `requests.Session` çağrılarını görmüyor

Bandit B113 (`request_without_timeout`) yalnızca modül düzeyindeki `requests.get/post/...` çağrılarını tanıyor; bir `requests.Session()` nesnesi üzerinden yapılan `session.get(...)` çağrılarını yakalamıyor. Manuel incelemede bu türden iki dosya bulundu:

- **FIND-116** — `cps/metadata_provider/amazon.py:61, 121`: iki `session.get` çağrısı. Baseline Bandit raporunda bu dosya için hiç sonuç yok. PR #21'de aynı `timeout=(5, 30)` değeriyle düzeltildi.
- **FIND-160** — `cps/metadata_provider/douban.py:105, 127, 154`: `douban.py:65`'te oluşturulan `requests.Session` ile üç zaman aşımsız istek. PR #21 incelemesi sırasında bulundu; K10 kod dondurması nedeniyle düzeltilmedi, kayıtta "Kabul edildi (düzeltilmeyecek)", raporda öneri.

Bu yüzden Bandit sayısındaki düşüş (42 → 37), yapılan güvenlik düzeltmelerinin tamamını göstermez: FIND-116, FIND-150 ve FIND-126 araç sayılarında görünmeyen düzeltmelerdir. Tersine, son taramada B113 kalmaması projede zaman aşımsız dış istek kalmadığı anlamına gelmez (FIND-160).

Ayrıca iki gerçek risk upstream'de `# nosec` ile susturulmuş olduğu için Bandit raporunda hiç görünmüyor: FIND-044 (`constants.py:140`, varsayılan `admin/admin123`) ve FIND-159'un iki parçası (`gdrive.py:48` B105, `gdrive.py:143` B324). Bunlar manuel incelemeyle bulundu.
"""


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--final-commit", required=True,
                    help="Son taramanın yapıldığı commit (environment-notes.md)")
    ap.add_argument("--file-scores", action="store_true",
                    help="Düzeltilen dosyalar için dosya bazlı Pylint puanı")
    ap.add_argument("--scores-cache", type=Path,
                    help="Dosya bazlı puanlar için JSON önbellek (varsa okunur, "
                         "yoksa hesaplanıp yazılır)")
    args = ap.parse_args()
    bc = (ROOT / "docs" / "baseline-commit.txt").read_text().strip()
    fc = subprocess.run(["git", "rev-parse", args.final_commit], cwd=ROOT,
                        capture_output=True, text=True, check=True).stdout.strip()
    sb, sf = Source(bc), Source(fc)
    register = load_register()

    scores = None
    if args.file_scores:
        cache = args.scores_cache
        if cache and cache.exists():
            scores = json.loads(cache.read_text(encoding="utf-8"))
        else:
            scores = file_scores(bc, fc)
            if cache:
                cache.write_text(json.dumps(scores, indent=1), encoding="utf-8")

    pb, pbs = parse_pylint(BASE / "pylint.txt", sb)
    pf, pfs = parse_pylint(FINAL / "pylint.txt", sf)
    res_p = write_pylint(pb, pbs, pf, pfs, register, scores, bc, fc)

    eb = parse_pep8(BASE / "pep8.txt", sb)
    ef = parse_pep8(FINAL / "pep8.txt", sf)
    res_e = write_pep8(eb, ef, register, bc, fc)

    bb, bt = parse_bandit(BASE, sb)
    bf, ft = parse_bandit(FINAL, sf)
    res_b = write_bandit(bb, bt, bf, ft, register, bc, fc)

    for name, (b, a), (cl, pe, mv, nw) in (
            ("pylint", (len(pb), len(pf)), res_p),
            ("pep8", (len(eb), len(ef)), res_e),
            ("bandit", (len(bb), len(bf)), res_b)):
        print(f"{name}: {b} -> {a} | kapanan {len(cl)} | devam {len(pe)} "
              f"+ satiri degisen {len(mv)} | yeni {len(nw)}")
        for it in nw:
            print(f"   YENI {it.path}:{it.line} {it.code} {it.msg[:80]}")


if __name__ == "__main__":
    main()
