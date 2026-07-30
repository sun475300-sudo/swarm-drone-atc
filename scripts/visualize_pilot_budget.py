"""
90일 파일럿 백서 예산 계획 시각화
docs/track_f/p343_360_pilot_whitepaper.md § 4. 예산 계획
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

# ── 한글 폰트 설정 ──────────────────────────────────────────────
from matplotlib import font_manager
import os

# NanumGothic TTF 직접 등록 (addfont 방식)
_nanum_path = os.path.expanduser("~/.fonts/NanumGothic.ttf")
_nanum_bold_path = os.path.expanduser("~/.fonts/NanumGothicBold.ttf")
for _fp in [_nanum_path, _nanum_bold_path]:
    if os.path.exists(_fp):
        font_manager.fontManager.addfont(_fp)

# 사용 가능한 한글 폰트 탐색
candidates = ["NanumGothic", "NanumBarunGothic", "Malgun Gothic", "AppleGothic", "DejaVu Sans"]
chosen = "DejaVu Sans"
for c in candidates:
    matches = [f for f in font_manager.fontManager.ttflist if f.name == c]
    if matches:
        chosen = c
        break

plt.rcParams["font.family"] = chosen
plt.rcParams["axes.unicode_minus"] = False
print(f"[font] 사용 폰트: {chosen}")

# ── 데이터 ──────────────────────────────────────────────────────
labels = [
    "드론 임차\n(6기×90일)",
    "운영 인력\n(4명×90일)",
    "인프라 구축",
    "비행 허가\n및 보험",
    "데이터 분석\n및 보고서",
]
amounts = [54_000_000, 36_000_000, 20_000_000, 5_000_000, 5_000_000]
total = sum(amounts)

colors = ["#2563EB", "#16A34A", "#D97706", "#DC2626", "#7C3AED"]
light_colors = ["#DBEAFE", "#DCFCE7", "#FEF3C7", "#FEE2E2", "#EDE9FE"]

# 90일 누적 지출 (단순 선형 가정 + 단계별 반영)
days = np.arange(0, 91)

def cumulative(day):
    """단계별 지출 패턴 모델링"""
    # Day 0-14: 준비 단계 — 인프라·허가 비용 집중 (25%)
    # Day 15-30: 시범 운영 — 드론·인력 시작 (35%)
    # Day 31-60: 본 운영 — 전체 비용 (65%)
    # Day 61-90: 마무리 — 데이터·보고서 (100%)
    if day <= 14:
        return total * 0.25 * (day / 14)
    elif day <= 30:
        return total * (0.25 + 0.10 * ((day - 14) / 16))
    elif day <= 60:
        return total * (0.35 + 0.30 * ((day - 30) / 30))
    else:
        return total * (0.65 + 0.35 * ((day - 60) / 30))

cum_values = [cumulative(d) for d in days]

# ── 레이아웃 ────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 11), facecolor="#F8FAFC")
fig.patch.set_facecolor("#F8FAFC")

gs = gridspec.GridSpec(
    2, 3,
    figure=fig,
    left=0.06, right=0.97,
    top=0.88, bottom=0.08,
    hspace=0.42, wspace=0.38,
)

# ── 제목 ────────────────────────────────────────────────────────
fig.text(
    0.5, 0.955,
    "목포 해역·전남 도서 90일 파일럿 — 예산 계획",
    ha="center", va="center",
    fontsize=18, fontweight="bold", color="#1E293B",
)
fig.text(
    0.5, 0.925,
    "Phase 343–360  |  SDACS v1.5.0  |  총 예산: 1억 2,000만원",
    ha="center", va="center",
    fontsize=11, color="#64748B",
)

# ── [1] 파이 차트 ────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax1.set_facecolor("#F8FAFC")

wedges, texts, autotexts = ax1.pie(
    amounts,
    labels=None,
    colors=colors,
    autopct="%1.1f%%",
    startangle=140,
    pctdistance=0.72,
    wedgeprops={"edgecolor": "white", "linewidth": 2.5},
    textprops={"fontsize": 10, "fontweight": "bold"},
)
for at, c in zip(autotexts, colors):
    at.set_color("white")
    at.set_fontsize(9.5)
    at.set_fontweight("bold")

ax1.set_title("항목별 비중", fontsize=12, fontweight="bold", color="#1E293B", pad=10)

legend_labels = [f"{l.replace(chr(10), ' ')}  {a/1e6:.0f}M" for l, a in zip(labels, amounts)]
ax1.legend(
    wedges, legend_labels,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.30),
    ncol=1,
    fontsize=8.5,
    frameon=False,
    labelcolor="#374151",
)

# ── [2] 수평 막대 차트 ───────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1:])
ax2.set_facecolor("#F8FAFC")

bar_labels_short = [l.replace("\n", " ") for l in labels]
y_pos = np.arange(len(labels))
bars = ax2.barh(
    y_pos,
    [a / 1e6 for a in amounts],
    color=colors,
    edgecolor="white",
    linewidth=1.5,
    height=0.55,
)

# 값 레이블
for bar, amt in zip(bars, amounts):
    w = bar.get_width()
    ax2.text(
        w + 0.4, bar.get_y() + bar.get_height() / 2,
        f"{amt/1e6:.0f}M원  ({amt/total*100:.1f}%)",
        va="center", ha="left",
        fontsize=9.5, color="#374151", fontweight="bold",
    )

ax2.set_yticks(y_pos)
ax2.set_yticklabels(bar_labels_short, fontsize=10, color="#374151")
ax2.set_xlabel("금액 (백만원)", fontsize=10, color="#64748B")
ax2.set_title("항목별 예산 (단위: 백만원)", fontsize=12, fontweight="bold", color="#1E293B", pad=10)
ax2.set_xlim(0, 68)
ax2.axvline(x=total / 1e6 / len(amounts), color="#CBD5E1", linestyle="--", linewidth=1, alpha=0.6)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.spines["left"].set_color("#E2E8F0")
ax2.spines["bottom"].set_color("#E2E8F0")
ax2.tick_params(colors="#64748B")
ax2.set_facecolor("#F8FAFC")

# ── [3] 누적 지출 곡선 ──────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, :2])
ax3.set_facecolor("#F8FAFC")

ax3.fill_between(days, [v / 1e6 for v in cum_values], alpha=0.12, color="#2563EB")
ax3.plot(days, [v / 1e6 for v in cum_values], color="#2563EB", linewidth=2.5, zorder=3)

# 단계 구분선 및 레이블
phases = [
    (0,  14,  "#FEF3C7", "준비\n(Day 1–14)"),
    (14, 30,  "#DCFCE7", "시범 운영\n(Day 15–30)"),
    (30, 60,  "#DBEAFE", "본 운영\n(Day 31–60)"),
    (60, 75,  "#EDE9FE", "데이터 수집\n(Day 61–75)"),
    (75, 90,  "#FEE2E2", "평가·보고\n(Day 76–90)"),
]
phase_colors_line = ["#D97706", "#16A34A", "#2563EB", "#7C3AED", "#DC2626"]

for i, (s, e, bg, lbl) in enumerate(phases):
    ax3.axvspan(s, e, alpha=0.18, color=bg, zorder=1)
    mid = (s + e) / 2
    ax3.text(
        mid, 126,
        lbl,
        ha="center", va="top",
        fontsize=7.8, color=phase_colors_line[i],
        fontweight="bold",
    )
    ax3.axvline(x=s, color="#CBD5E1", linestyle=":", linewidth=1, zorder=2)

ax3.axvline(x=90, color="#CBD5E1", linestyle=":", linewidth=1, zorder=2)

# 마일스톤 점
milestones = [(14, "준비 완료"), (30, "시범 완료"), (60, "본 운영 완료"), (90, "파일럿 종료")]
for d, lbl in milestones:
    y_val = cumulative(d) / 1e6
    ax3.scatter(d, y_val, color="#1E293B", s=55, zorder=5)
    ax3.annotate(
        f"{lbl}\n{y_val:.0f}M원",
        xy=(d, y_val),
        xytext=(d + 2, y_val - 8),
        fontsize=8, color="#1E293B",
        arrowprops={"arrowstyle": "-", "color": "#94A3B8", "lw": 1},
    )

ax3.set_xlim(0, 90)
ax3.set_ylim(0, 135)
ax3.set_xlabel("경과 일수 (Day)", fontsize=10, color="#64748B")
ax3.set_ylabel("누적 지출 (백만원)", fontsize=10, color="#64748B")
ax3.set_title("90일 누적 지출 곡선 (단계별 지출 패턴)", fontsize=12, fontweight="bold", color="#1E293B", pad=10)
ax3.spines["top"].set_visible(False)
ax3.spines["right"].set_visible(False)
ax3.spines["left"].set_color("#E2E8F0")
ax3.spines["bottom"].set_color("#E2E8F0")
ax3.tick_params(colors="#64748B")
ax3.set_facecolor("#F8FAFC")

# 총액 수평선
ax3.axhline(y=total / 1e6, color="#DC2626", linestyle="--", linewidth=1.5, alpha=0.7, zorder=2)
ax3.text(1, total / 1e6 + 1.5, f"총 예산 {total/1e6:.0f}M원", fontsize=9, color="#DC2626", fontweight="bold")

# ── [4] 요약 카드 ────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 2])
ax4.set_facecolor("#F8FAFC")
ax4.axis("off")

card_data = [
    ("총 예산", f"{total/1e6:.0f}M원", "#1E293B"),
    ("최대 항목", f"드론 임차 54M원\n(45.0%)", "#2563EB"),
    ("인력 비용", f"운영 인력 36M원\n(30.0%)", "#16A34A"),
    ("인프라·기타", f"30M원 (25.0%)", "#D97706"),
    ("파일럿 기간", "90일 (2027 Q2–Q3)", "#7C3AED"),
    ("드론 운용", "6기 (의료 5 + 감시 1)", "#DC2626"),
]

ax4.set_xlim(0, 1)
ax4.set_ylim(0, 1)

ax4.text(0.5, 0.97, "예산 요약", ha="center", va="top",
         fontsize=12, fontweight="bold", color="#1E293B")

for i, (title, value, color) in enumerate(card_data):
    y = 0.87 - i * 0.145
    rect = mpatches.FancyBboxPatch(
        (0.02, y - 0.04), 0.96, 0.115,
        boxstyle="round,pad=0.01",
        facecolor=color + "15",
        edgecolor=color + "55",
        linewidth=1.2,
    )
    ax4.add_patch(rect)
    ax4.text(0.08, y + 0.025, title, ha="left", va="center",
             fontsize=8.5, color="#64748B")
    ax4.text(0.08, y - 0.015, value, ha="left", va="center",
             fontsize=9, fontweight="bold", color=color)

# ── 저장 ────────────────────────────────────────────────────────
out_path = "/home/ubuntu/swarm-drone-atc/docs/track_f/pilot_budget_visualization.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#F8FAFC")
plt.close()
print(f"저장 완료: {out_path}")
