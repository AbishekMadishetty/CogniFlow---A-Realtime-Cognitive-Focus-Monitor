"""
CogniFlow — Session Dashboard (Tokyo Night Theme)
Opens automatically when main.py runs.
Reads cogniflow_log.csv from the same folder.
"""

import tkinter as tk
import csv
import os
import time
from datetime import datetime
from collections import Counter

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import numpy as np

CSV_FILE = "cogniflow_log.csv"

# ── Tokyo Night Palette ───────────────────────────────────────────────────────
BG         = "#1A1B26"
BG_CARD    = "#24283B"
BG_CARD2   = "#292E42"
BORDER     = "#414868"
BORDER2    = "#565F89"
TEXT       = "#C0CAF5"
TEXT_MUTED = "#9AA5CE"
TEXT_DIM   = "#565F89"
GREEN      = "#9ECE6A" 
AMBER      = "#E0AF68" 
RED        = "#F7768E" 
BLUE       = "#7AA2F7" 
CYAN       = "#7DCFFF" 
PURPLE     = "#BB9AF7" 
PINK       = "#FF9E64" 

# Typography
FONT_MAIN = "Segoe UI"
FONT_MONO = "Consolas"

matplotlib.rcParams.update({
    "figure.facecolor":  BG,
    "axes.facecolor":    BG_CARD,
    "axes.edgecolor":    BORDER,
    "axes.labelcolor":   TEXT_MUTED,
    "axes.titlecolor":   TEXT,
    "xtick.color":       TEXT_MUTED,
    "ytick.color":       TEXT_MUTED,
    "text.color":        TEXT,
    "grid.color":        BORDER,
    "grid.linewidth":    0.5,
    "grid.linestyle":    "--",
    "font.family":       "sans-serif",
    "font.sans-serif":   [FONT_MAIN, "Helvetica"],
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_csv():
    if not os.path.exists(CSV_FILE):
        return []
    rows = []
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                row_type = row.get("Type", "DATA")
                rows.append({
                    "time":       row["Time"],
                    "score":      int(row["Score"])      if row.get("Score")      else 0,
                    "label":      row.get("Label",       ""),
                    "state":      row.get("State",       "thinking"),
                    "ear":        float(row["EAR"])      if row.get("EAR")        else 0,
                    "variance":   float(row["Variance"]) if row.get("Variance")   else 0,
                    "yawns":      int(row["Yawns"])      if row.get("Yawns")      else 0,
                    "eye_closes": int(row["EyeCloses"])  if row.get("EyeCloses")  else 0,
                    "activity":   row.get("Activity",    ""),
                    "ml_label":   row.get("ML_Label",    "N/A"),
                    "dt":         datetime.strptime(row["Time"], "%Y-%m-%d %H:%M:%S"),
                    "type":       row_type,
                })
            except Exception:
                continue
    return rows


def split_sessions(rows, gap_min=10):
    if not rows:
        return []
    sessions, cur = [], []
    for r in rows:
        if r["type"] == "SESSION_START":
            if cur:
                sessions.append(cur)
            cur = []
            continue
        if cur and (r["dt"] - cur[-1]["dt"]).seconds / 60 > gap_min:
            sessions.append(cur)
            cur = []
        cur.append(r)
    if cur:
        sessions.append(cur)
    return [s for s in sessions if s]


def score_color(s):
    if s >= 75: return GREEN
    if s >= 55: return AMBER
    if s >= 35: return PINK
    return RED


# ── Dashboard ─────────────────────────────────────────────────────────────────

class Dashboard(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("CogniFlow  ·  Session Dashboard")
        self.configure(bg=BG)
        self.geometry("1350x850")
        self.minsize(1100, 700)
        self.resizable(True, True)

        self._rows     = []
        self._sessions = []
        self._sel      = 0

        self._build()
        self._refresh()
        self._tick()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="◈ CogniFlow",
                 bg=BG, fg=BLUE,
                 font=(FONT_MAIN, 18, "bold")
                 ).pack(side="left", padx=24, pady=12)

        tk.Label(hdr, text="ANALYTICS ENGINE",
                 bg=BG, fg=TEXT_DIM,
                 font=(FONT_MAIN, 10, "bold")
                 ).pack(side="left", padx=4, pady=16)

        self._clock_var = tk.StringVar()
        tk.Label(hdr, textvariable=self._clock_var,
                 bg=BG, fg=TEXT_DIM,
                 font=(FONT_MAIN, 10)
                 ).pack(side="right", padx=24)

        tk.Button(hdr, text="↺ Refresh Data",
                  bg=BG_CARD, fg=TEXT,
                  font=(FONT_MAIN, 9, "bold"),
                  activebackground=BORDER, activeforeground=TEXT,
                  relief="flat", bd=0, padx=14, pady=6,
                  cursor="hand2",
                  command=self._refresh
                  ).pack(side="right", padx=10, pady=14)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Body
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = tk.Frame(body, bg=BG_CARD, width=240)
        self._sidebar.pack(fill="y", side="left")
        self._sidebar.pack_propagate(False)

        tk.Label(self._sidebar, text="SESSION LOGS",
                 bg=BG_CARD, fg=TEXT_MUTED,
                 font=(FONT_MAIN, 9, "bold")
                 ).pack(anchor="w", padx=20, pady=(20, 10))

        self._sess_list = tk.Frame(self._sidebar, bg=BG_CARD)
        self._sess_list.pack(fill="both", expand=True)

        tk.Frame(body, bg=BORDER, width=1).pack(fill="y", side="left")

        # Content
        self._content = tk.Frame(body, bg=BG)
        self._content.pack(fill="both", expand=True)

        self._cards = tk.Frame(self._content, bg=BG)
        self._cards.pack(fill="x", padx=20, pady=(20, 0))

        self._chart_area = tk.Frame(self._content, bg=BG)
        self._chart_area.pack(fill="both", expand=True, padx=20, pady=10)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _refresh(self):
        self._rows     = load_csv()
        self._sessions = split_sessions(self._rows)
        if self._sel >= len(self._sessions):
            self._sel = max(0, len(self._sessions) - 1)
        self._clock_var.set(f"Last sync: {time.strftime('%H:%M:%S')}")
        self._build_sidebar()
        self._render()

    def _tick(self):
        try:
            self._refresh()
        except Exception:
            pass
        self.after(8000, self._tick)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        for w in self._sess_list.winfo_children():
            w.destroy()

        if not self._sessions:
            tk.Label(self._sess_list,
                     text="\n\nNo records found.\n\nStart the engine\nto track focus.",
                     bg=BG_CARD, fg=TEXT_DIM,
                     font=(FONT_MAIN, 10), justify="center"
                     ).pack(pady=30)
            return

        for i, sess in enumerate(reversed(self._sessions)):
            real_idx = len(self._sessions) - 1 - i
            scores   = [r["score"] for r in sess]
            avg      = int(sum(scores) / len(scores))
            start    = sess[0]["dt"].strftime("%b %d  ·  %H:%M")
            dur      = max(1, int((sess[-1]["dt"] - sess[0]["dt"]).seconds / 60))
            selected = real_idx == self._sel

            bg  = BG_CARD2 if selected else BG_CARD
            fg  = CYAN     if selected else TEXT

            row = tk.Frame(self._sess_list, bg=bg, cursor="hand2")
            row.pack(fill="x", padx=10, pady=4)

            if selected:
                tk.Frame(row, bg=CYAN, width=4).pack(fill="y", side="left")

            inner = tk.Frame(row, bg=bg)
            inner.pack(fill="x", padx=12, pady=10)

            tk.Label(inner, text=f"Session {len(self._sessions) - i}",
                     bg=bg, fg=fg, font=(FONT_MAIN, 11, "bold")
                     ).pack(anchor="w")

            tk.Label(inner, text=start,
                     bg=bg, fg=TEXT_MUTED, font=(FONT_MAIN, 9)
                     ).pack(anchor="w", pady=(2, 6))

            bot = tk.Frame(inner, bg=bg)
            bot.pack(fill="x")

            tk.Label(bot, text=f"{dur} min",
                     bg=bg, fg=TEXT_DIM, font=(FONT_MAIN, 9)
                     ).pack(side="left")

            tk.Label(bot, text=f"Avg {avg}",
                     bg=bg, fg=score_color(avg), font=(FONT_MAIN, 9, "bold")
                     ).pack(side="right")

            def _bind(widget, idx=real_idx):
                widget.bind("<Button-1>", lambda e: self._select(idx))

            for widget in [row, inner, bot]:
                _bind(widget)
                for child in widget.winfo_children():
                    _bind(child)

    def _select(self, idx):
        self._sel = idx
        self._build_sidebar()
        self._render()

    # ── Stat cards ────────────────────────────────────────────────────────────

    def _build_cards(self, sess):
        for w in self._cards.winfo_children():
            w.destroy()

        scores    = [r["score"] for r in sess]
        avg       = int(sum(scores) / len(scores))
        peak      = max(scores)
        low       = min(scores)
        dur       = max(1, int((sess[-1]["dt"] - sess[0]["dt"]).seconds / 60))
        yawns     = sess[-1]["yawns"]
        closes    = sess[-1]["eye_closes"]
        focused_p = int(len([s for s in scores if s >= 70]) / len(scores) * 100)
        start_t   = sess[0]["dt"].strftime("%H:%M")
        end_t     = sess[-1]["dt"].strftime("%H:%M")
        
        # Calculate dominant ML label
        ml_labels = [r["ml_label"] for r in sess if r.get("ml_label", "N/A") not in ("N/A", "Error")]
        ml_dominant = Counter(ml_labels).most_common(1)[0][0] if ml_labels else "N/A"

        data = [
            ("AVG SCORE",  str(avg),          score_color(avg),                    "Out of 100"),
            ("PEAK",       str(peak),         GREEN,                               "Highest point"),
            ("LOWEST",     str(low),          score_color(low),                    "Deepest dip"),
            ("DURATION",   f"{dur}m",         BLUE,                                f"{start_t} – {end_t}"),
            ("ML PRED",    ml_dominant[:9],   PURPLE,                              "Validation"),
            ("FOCUSED",    f"{focused_p}%",   GREEN if focused_p >= 50 else AMBER, "Time ≥ 70"),
            ("YAWNS",      str(yawns),        PINK if yawns > 0 else TEXT_MUTED,   "Detected"),
            ("CLOSES",     str(closes),       RED if closes > 0 else TEXT_MUTED,   "Detected"),
        ]

        for label, val, col, sub in data:
            c = tk.Frame(self._cards, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
            c.pack(side="left", fill="both", expand=True, padx=4)

            tk.Frame(c, bg=col, height=3).pack(fill="x")

            tk.Label(c, text=label, bg=BG_CARD, fg=TEXT_MUTED, font=(FONT_MAIN, 9, "bold")
                     ).pack(anchor="w", padx=14, pady=(12, 0))
            
            tk.Label(c, text=val, bg=BG_CARD, fg=col, font=(FONT_MAIN, 26, "bold")
                     ).pack(anchor="w", padx=12)
            
            tk.Label(c, text=sub, bg=BG_CARD, fg=TEXT_DIM, font=(FONT_MAIN, 9)
                     ).pack(anchor="w", padx=14, pady=(0, 12))

    # ── Charts ────────────────────────────────────────────────────────────────

    def _render(self):
        for w in self._chart_area.winfo_children():
            w.destroy()

        if not self._sessions:
            return

        sess = self._sessions[self._sel]
        self._build_cards(sess)

        fig = Figure(figsize=(12, 6.5), facecolor=BG)
        gs  = gridspec.GridSpec(2, 3, figure=fig,
                                hspace=0.45, wspace=0.35,
                                left=0.05, right=0.98,
                                top=0.92, bottom=0.08)

        self._draw_timeline(fig.add_subplot(gs[0, :]), sess)
        self._draw_state_pie(fig.add_subplot(gs[1, 0]), sess)
        self._draw_activity(fig.add_subplot(gs[1, 1]), sess)
        self._draw_comparison(fig.add_subplot(gs[1, 2]))

        canvas = FigureCanvasTkAgg(fig, master=self._chart_area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _draw_timeline(self, ax, sess):
        scores = [r["score"] for r in sess]
        xs     = list(range(len(scores)))

        # Thicker, smoother line
        ax.plot(xs, scores, color=BLUE, linewidth=3, solid_capstyle="round", zorder=3)
        
        # Elegant gradient fill equivalent
        ax.fill_between(xs, scores, alpha=0.15, color=BLUE)

        for y, lbl, col in [(70, "FOCUSED", GREEN), (40, "DRIFTING", AMBER)]:
            ax.axhline(y, color=col, linewidth=1.5, linestyle=":", alpha=0.6)
            ax.text(len(xs) - 0.5, y + 2, lbl, color=col, fontsize=8, alpha=0.8, ha="right", fontweight="bold")

        pi = int(np.argmax(scores))
        li = int(np.argmin(scores))
        ax.scatter([xs[pi]], [scores[pi]], color=GREEN, s=80, zorder=5, edgecolors=BG, linewidths=2)
        ax.scatter([xs[li]], [scores[li]], color=RED,   s=80, zorder=5, edgecolors=BG, linewidths=2)
        
        ax.annotate(f"{scores[pi]}", (xs[pi], scores[pi]), xytext=(0, 10), textcoords="offset points",
                    color=GREEN, fontsize=9, ha="center", fontweight="bold")
        ax.annotate(f"{scores[li]}", (xs[li], scores[li]), xytext=(0, -18), textcoords="offset points",
                    color=RED, fontsize=9, ha="center", fontweight="bold")

        step  = max(1, len(sess) // 8)
        ticks = xs[::step]
        ax.set_xticks(ticks)
        ax.set_xticklabels([sess[i]["dt"].strftime("%H:%M") for i in ticks], fontsize=9)
        ax.set_xlim(0, max(1, len(xs) - 1))
        ax.set_ylim(0, 108)
        ax.set_ylabel("Score", fontsize=10, labelpad=10)
        ax.set_title("FOCUS TIMELINE", fontsize=11, fontweight="bold", pad=12, loc="left")

    def _draw_state_pie(self, ax, sess):
        counts = Counter(r["state"] for r in sess)
        states = list(counts.keys())
        sizes  = [counts[s] for s in states]
        cols   = {"typing": GREEN, "reading": BLUE, "thinking": PURPLE}
        colors = [cols.get(s, CYAN) for s in states]

        wedges, _, pcts = ax.pie(
            sizes, colors=colors, autopct="%1.0f%%",
            startangle=90, pctdistance=0.75,
            wedgeprops={"linewidth": 3, "edgecolor": BG_CARD}
        )
        for p in pcts:
            p.set_fontsize(9)
            p.set_color(BG)
            p.set_fontweight("bold")

        ax.legend(wedges, [s.title() for s in states],
                  loc="lower center", bbox_to_anchor=(0.5, -0.25),
                  ncol=3, fontsize=9, framealpha=0, labelcolor=TEXT)
        ax.set_title("STATE BREAKDOWN", fontsize=11, fontweight="bold", pad=10, loc="center")

    def _draw_activity(self, ax, sess):
        counts = Counter(r["activity"] for r in sess)
        top    = counts.most_common(5)

        if not top:
            return

        apps  = [t[0].split("→")[0].strip()[:14] for t in top]
        vals  = [t[1] for t in top]
        pal   = [BLUE, CYAN, GREEN, AMBER, PURPLE]

        bars = ax.barh(apps, vals, color=pal[:len(apps)], height=0.6)

        for bar, v in zip(bars, vals):
            ax.text(v + 0.3, bar.get_y() + bar.get_height() / 2,
                    str(v), va="center", fontsize=9, color=TEXT_MUTED)

        ax.invert_yaxis()
        ax.set_title("TOP ACTIVITIES", fontsize=11, fontweight="bold", pad=10, loc="left")
        ax.tick_params(axis="y", labelsize=9)
        ax.spines["left"].set_visible(False)

    def _draw_comparison(self, ax):
        show   = self._sessions[-6:]
        offset = len(self._sessions) - len(show)
        labels = [f"S{offset + i + 1}" for i in range(len(show))]
        avgs   = [int(sum(r["score"] for r in s) / len(s)) for s in show]

        x = np.arange(len(labels))
        
        bars = ax.bar(x, avgs, width=0.5, color=BORDER2, edgecolor=BG_CARD, linewidth=1.5)

        rel = self._sel - offset
        if 0 <= rel < len(show):
            bars[rel].set_color(CYAN)

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                    f'{int(height)}', ha='center', va='bottom', fontsize=8, color=TEXT)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylim(0, 115)
        ax.set_title("SESSION AVERAGES", fontsize=11, fontweight="bold", pad=10, loc="center")
        ax.spines["left"].set_visible(False)
        ax.set_yticks([])


if __name__ == "__main__":
    Dashboard().mainloop()