#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final rapordaki şekilleri ham raporlardan üretir (matplotlib, 300 dpi).

Girdi (salt okunur):
    reports/{baseline,final}/bandit-cps.json, bandit-entrypoint.json
    reports/{baseline,final}/pylint.txt
    docs/findings-register.csv
    docs/5-karsilastirma/pylint-comparison.md  (dosya bazlı puan tablosu;
        bu puanlar resmi taramada yok, compare_reports.py --file-scores ile
        üretilmiştir)

Çıktı:
    docs/figures/sekil-1-surec.png
    docs/figures/sekil-3-bandit-onem.png
    docs/figures/sekil-4-pylint-kategori.png
    docs/figures/sekil-5-dosya-puan.png
    docs/figures/sekil-2-dogrulama.png

Şekiller gri tonlarında da okunabilsin diye desen (hatch) ve değer
etiketleri kullanır. Font: Times New Roman.

Kullanım:
    python scripts/make_figures.py [--root DEPO_KOKU] [--out CIKTI_DIZINI]
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

DPI = 300
WIDTH_IN = 5.04  # Belgedeki yerleşim genişliği (metin genişliğinin %80'i, 12,8 cm);
                 # şekiller ölçeklenmeden yerleştirildiği için yazılar gerçek boyutundadır.

plt.rcParams.update({
    "font.family": "Times New Roman",
    "font.size": 9,
    "axes.titlesize": 9,
    "axes.labelsize": 9,
    "legend.fontsize": 8.5,
    "hatch.linewidth": 0.6,
})

BASE_STYLE = dict(color="#d9d9d9", edgecolor="black", hatch="///")
FINAL_STYLE = dict(color="#595959", edgecolor="black")


def label_bars(ax, bars, fmt="{:g}", log=False):
    for bar in bars:
        h = bar.get_height()
        y = h * 1.08 if log else h
        ax.annotate(fmt.format(h), (bar.get_x() + bar.get_width() / 2, y),
                    xytext=(0, 2), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.5)


def bandit_results(root, phase):
    results = []
    for name in ("bandit-cps.json", "bandit-entrypoint.json"):
        path = root / "reports" / phase / name
        results += json.loads(path.read_text(encoding="utf-8"))["results"]
    return results


PYLINT_RE = re.compile(r"^[^ ]+:\d+:\d+: ([CRWEIF])\d{4}: ")


def pylint_categories(root, phase):
    text = (root / "reports" / phase / "pylint.txt").read_text(encoding="utf-8")
    return collections.Counter(m.group(1) for line in text.splitlines()
                               if (m := PYLINT_RE.match(line)))


def fig_process(out):
    steps = [
        ("Proje seçimi\nve kapsam", "Calibre-Web,\ncps/ ve cps.py"),
        ("Başlangıç\ntaramaları", "Bandit, Pylint,\nflake8"),
        ("Elle doğrulama ve\nsınıflandırma", "Bulgu kaydı,\nkod incelemesi"),
        ("Düzeltme ve\nçapraz inceleme", "Küçük ve davranışı\nkorumaya yönelik"),
        ("Son tarama", "Aynı sürüm, kapsam\nve parametreler"),
        ("Karşılaştırma", "Kapanan, devam eden,\nyeni uyarılar"),
    ]
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.4))
    ax.set_xlim(-0.03, 3.03)
    ax.set_ylim(0.08, 1.92)
    ax.axis("off")
    w, h = 0.9, 0.74
    pos = [(0.5, 1.5), (1.5, 1.5), (2.5, 1.5), (2.5, 0.5), (1.5, 0.5), (0.5, 0.5)]
    for i, ((title, sub), (x, y)) in enumerate(zip(steps, pos), start=1):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.05",
                                    facecolor="#f2f2f2", edgecolor="black", lw=0.8))
        ax.text(x, y + 0.12, f"{i}. {title}", ha="center", va="center",
                fontsize=8.5, fontweight="bold", linespacing=1.15)
        ax.text(x, y - 0.2, sub, ha="center", va="center", fontsize=8,
                linespacing=1.1)
    arrow = dict(arrowstyle="-|>", color="black", lw=0.8)
    for (x1, y1), (x2, y2) in zip(pos, pos[1:]):
        if y1 == y2:
            dx = w / 2 if x2 > x1 else -w / 2
            ax.annotate("", (x2 - dx, y2), (x1 + dx, y1), arrowprops=arrow)
        else:
            ax.annotate("", (x2, y2 + h / 2), (x1, y1 - h / 2), arrowprops=arrow)
    # Düzeltme dosya bazlı tarama ile doğrulanıp gerekirse yeniden ele alınır.
    ax.annotate("", (2.5 - w / 2 + 0.05, 1.5 - h / 2),
                (2.5 - w / 2 + 0.05, 0.5 + h / 2),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=0.6, ls="--"))
    ax.text(2.5 - w / 2 + 0.01, 1.0, "dosya bazlı\ntekrar tarama", fontsize=7.5,
            va="center", ha="right", style="italic")
    fig.savefig(out / "sekil-1-surec.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def fig_bandit(root, out):
    levels = ["HIGH", "MEDIUM", "LOW"]
    base = collections.Counter(r["issue_severity"] for r in bandit_results(root, "baseline"))
    final = collections.Counter(r["issue_severity"] for r in bandit_results(root, "final"))
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 1.85))
    x = range(len(levels))
    b1 = ax.bar([i - 0.18 for i in x], [base[l] for l in levels], 0.36,
                label="Başlangıç", **BASE_STYLE)
    b2 = ax.bar([i + 0.18 for i in x], [final[l] for l in levels], 0.36,
                label="Son", **FINAL_STYLE)
    label_bars(ax, b1)
    label_bars(ax, b2)
    ax.set_xticks(list(x), levels)
    ax.set_xlabel("Bandit önem düzeyi")
    ax.set_ylabel("Bulgu sayısı")
    ax.set_ylim(0, max(base.values()) * 1.2)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "sekil-3-bandit-onem.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def fig_pylint(root, out):
    cats = [("C", "convention"), ("R", "refactor"), ("W", "warning"),
            ("E", "error"), ("I", "information")]
    base = pylint_categories(root, "baseline")
    final = pylint_categories(root, "final")
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.2))
    x = range(len(cats))
    b1 = ax.bar([i - 0.18 for i in x], [base[c] for c, _ in cats], 0.36,
                label="Başlangıç", **BASE_STYLE)
    b2 = ax.bar([i + 0.18 for i in x], [final[c] for c, _ in cats], 0.36,
                label="Son", **FINAL_STYLE)
    ax.set_yscale("log")
    label_bars(ax, b1, log=True)
    label_bars(ax, b2, log=True)
    ax.set_xticks(list(x), [f"{name}\n({c})" for c, name in cats])
    ax.set_xlabel("Pylint mesaj kategorisi")
    ax.set_ylabel("Mesaj sayısı (logaritmik)")
    ax.set_ylim(10, max(base.values()) * 3)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "sekil-4-pylint-kategori.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def fig_file_scores(root, out):
    text = (root / "docs" / "5-karsilastirma" / "pylint-comparison.md").read_text(encoding="utf-8")
    section = text.split("## 4.", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 8 and cells[0].startswith("`cps/"):
            rows.append((cells[0].strip("`").replace("cps/", ""),
                         float(cells[2]), float(cells[3])))
    rows.reverse()
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 2.6))
    y = range(len(rows))
    b1 = ax.barh([i + 0.18 for i in y], [r[1] for r in rows], 0.36,
                 label="Başlangıç", **BASE_STYLE)
    b2 = ax.barh([i - 0.18 for i in y], [r[2] for r in rows], 0.36,
                 label="Son", **FINAL_STYLE)
    for i, (_, before, after) in enumerate(rows):
        ax.annotate(f"{before:.2f} → {after:.2f}".replace(".", ","),
                    (max(before, after), i), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8)
    ax.set_yticks(list(y), [r[0].split("/")[-1] for r in rows], fontsize=8.5)
    ax.set_xlabel("Dosya bazlı Pylint puanı (10 üzerinden)")
    ax.set_xlim(0, 10)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "sekil-5-dosya-puan.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def fig_validation(root, out):
    path = root / "docs" / "findings-register.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    sources = [("Bandit", "Bandit"), ("Pylint", "Pylint"),
               ("PEP8", "flake8 (PEP 8)"), ("Manuel", "Manuel inceleme")]
    results = [("Gerçek sorun", "Gerçek sorun", dict(color="#404040", edgecolor="black")),
               ("Düşük öncelikli uyarı", "Düşük öncelikli uyarı",
                dict(color="#bfbfbf", edgecolor="black", hatch="...")),
               ("Yanlış pozitif", "Yanlış pozitif",
                dict(color="white", edgecolor="black", hatch="///"))]
    count = collections.Counter((r["kaynak"], r["dogrulama_sonucu"]) for r in rows)
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 1.9))
    x = range(len(sources))
    bottom = [0] * len(sources)
    for key, label, style in results:
        vals = [count[(s, key)] for s, _ in sources]
        bars = ax.bar(list(x), vals, 0.55, bottom=bottom, label=label, **style)
        for bar, v, b in zip(bars, vals, bottom):
            if v and v < 4:
                ax.annotate(str(v), (bar.get_x() + bar.get_width(), b + v / 2),
                            xytext=(4, 0), textcoords="offset points",
                            va="center", fontsize=8.5)
            elif v:
                ax.text(bar.get_x() + bar.get_width() / 2, b + v / 2, str(v),
                        ha="center", va="center", fontsize=8.5,
                        color="white" if key == "Gerçek sorun" else "black",
                        bbox=None if key == "Gerçek sorun" else
                        dict(facecolor="white", edgecolor="none", pad=0.5))
        bottom = [b + v for b, v in zip(bottom, vals)]
    for i, total in enumerate(bottom):
        ax.text(i, total + 0.8, f"Toplam {total}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(list(x), [label for _, label in sources])
    ax.set_xlabel("Bulgu kaynağı")
    ax.set_ylabel("Bulgu kaydı satırı")
    ax.set_ylim(0, max(bottom) * 1.15)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "sekil-2-dogrulama.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    root_default = Path(__file__).resolve().parent.parent
    parser.add_argument("--root", type=Path, default=root_default)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or args.root / "docs" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    fig_process(out)
    fig_bandit(args.root, out)
    fig_pylint(args.root, out)
    fig_file_scores(args.root, out)
    fig_validation(args.root, out)
    print(f"Şekiller yazıldı: {out}")


if __name__ == "__main__":
    main()
