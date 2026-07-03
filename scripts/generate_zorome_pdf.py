"""
マルハンM2000蒲田7 ゾロ目日（11日・22日）分析PDF生成
"""
import sys, warnings
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

def find_jp_font():
    for path in ["C:/Windows/Fonts/meiryo.ttc", "C:/Windows/Fonts/msgothic.ttc",
                 "C:/Windows/Fonts/YuGothM.ttc", "C:/Windows/Fonts/msmincho.ttc"]:
        try:
            fm.FontProperties(fname=path)
            return path
        except Exception:
            pass
    return None

font_path = find_jp_font()
if font_path:
    fm.fontManager.addfont(font_path)
    prop = fm.FontProperties(fname=font_path)
    matplotlib.rcParams["font.family"] = prop.get_name()
else:
    prop = fm.FontProperties()
matplotlib.rcParams["axes.unicode_minus"] = False

CSV_PATH      = "minrepo_maruhan_kamata7_browser.csv"
STORE_NAME    = "マルハンM2000蒲田7"
RED           = "#FFCCCC"
GREEN_HI      = "#00AA44"
GREEN_MID     = "#66CC88"
GREEN_LO      = "#AADDBB"
WHITE         = "#FFFFFF"
GRAY          = "#F2F2F2"
NAVY          = "#1A3A5C"
DOW_JP        = ["月","火","水","木","金","土","日"]
ROWS_PER_PAGE = 35

print("データ読み込み中...")
df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
df["date"]           = pd.to_datetime(df["date"])
df["total_diff"]     = pd.to_numeric(df["total_diff"], errors="coerce")
df["machine_number"] = pd.to_numeric(df["machine_number"], errors="coerce")
df = df.dropna(subset=["total_diff", "machine_number"])
df["machine_number"] = df["machine_number"].astype(int)
print(f"  {len(df):,}行 読み込み完了\n")

def fmt_diff(val):
    if pd.isna(val): return "-"
    return f"{int(val):,}"

def win_color_zentai(rate):
    if rate >= 0.80: return GREEN_HI
    if rate >= 0.70: return GREEN_MID
    if rate >= 0.60: return GREEN_LO
    return WHITE

def win_color_kishu(rate):
    if rate >= 0.90: return GREEN_HI
    if rate >= 0.80: return "#44AA66"
    if rate >= 0.60: return GREEN_LO
    return WHITE

def diff_bg(val):
    if pd.isna(val): return GRAY
    return RED if val < 0 else WHITE

def make_col_labels(event_dates):
    return [f"{pd.Timestamp(d).month}/{pd.Timestamp(d).day}({DOW_JP[pd.Timestamp(d).dayofweek]})"
            for d in event_dates]

def draw_table_page(ax, header, rows_data, cell_colors, col_widths_rel,
                    title, legend_items, page_idx, total_pages):
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.01, 0.955), 0.98, 0.035,
        boxstyle="round,pad=0.002", fc=NAVY, ec="none", transform=ax.transAxes))
    ax.text(0.5, 0.972, title, ha="center", va="center", color="white",
            fontsize=13, fontweight="bold", fontproperties=prop, transform=ax.transAxes)
    lx = 0.01
    for color, label in legend_items:
        ax.add_patch(FancyBboxPatch((lx, 0.925), 0.012, 0.016,
            boxstyle="round,pad=0.001", fc=color, ec="#888888", lw=0.5, transform=ax.transAxes))
        ax.text(lx+0.015, 0.933, label, va="center", fontsize=7.5,
                fontproperties=prop, transform=ax.transAxes)
        lx += 0.11
    total_w = sum(col_widths_rel)
    col_w = [w / total_w * 0.98 for w in col_widths_rel]
    table_top, table_bot = 0.91, 0.02
    row_h = (table_top - table_bot) / (ROWS_PER_PAGE + 1)
    all_data   = [header] + rows_data
    all_colors = [[NAVY] * len(header)] + cell_colors
    for ri, (row_vals, row_cols) in enumerate(zip(all_data, all_colors)):
        y = table_top - ri * row_h
        x = 0.01
        for ci, (val, bg) in enumerate(zip(row_vals, row_cols)):
            w = col_w[ci]
            ax.add_patch(FancyBboxPatch((x, y - row_h), w - 0.001, row_h,
                boxstyle="square,pad=0", fc=bg,
                ec="#CCCCCC" if ri == 0 else "#DDDDDD",
                lw=0.3 if ri == 0 else 0.2, transform=ax.transAxes))
            fs = (6.5 if ci == 0 else 7) if ri == 0 else (5.5 if ci == 0 else 6)
            ax.text(x + w / 2, y - row_h / 2, str(val),
                    ha="center", va="center",
                    color="white" if ri == 0 else "black",
                    fontsize=fs,
                    fontweight="bold" if ri == 0 else "normal",
                    fontproperties=prop, transform=ax.transAxes)
            x += w
    ax.text(0.99, 0.01, f"p.{page_idx+1}/{total_pages}", ha="right", va="bottom",
            fontsize=7, color="#666666", fontproperties=prop, transform=ax.transAxes)

def make_zentai_pdf(label, df_n, event_dates, col_labels, out_path):
    print(f"  全台PDF: {out_path}")
    pivot = df_n.pivot_table(
        index=["model_name", "machine_number"],
        columns="date", values="total_diff", aggfunc="first"
    )
    pivot.columns = event_dates
    pivot["平均"] = pivot[event_dates].mean(axis=1).round(0)
    pivot["勝率"] = (pivot[event_dates] > 0).sum(axis=1) / pivot[event_dates].notna().sum(axis=1)
    pivot = pivot.reset_index().sort_values(["model_name", "machine_number"])
    n_dates = len(event_dates)
    col_widths = [3.5, 1.0] + [1.3] * n_dates + [1.3, 1.0]
    header = ["機種", "台番"] + col_labels + ["平均", "勝率"]
    title  = f"{STORE_NAME}　{label} 台番号別分析"
    legend = [(GREEN_HI,"勝率80%~"), (GREEN_MID,"勝率70%~80%"), (GREEN_LO,"勝率60%~70%"), (RED,"差枚マイナス")]
    pages = [pivot.iloc[i:i+ROWS_PER_PAGE] for i in range(0, len(pivot), ROWS_PER_PAGE)]
    with PdfPages(out_path) as pdf:
        for page_idx, page_df in enumerate(pages):
            rows_data, cell_colors = [], []
            for _, row in page_df.iterrows():
                win_r = row["勝率"] if not pd.isna(row["勝率"]) else 0
                row_bg = win_color_zentai(win_r)
                diffs = [fmt_diff(row.get(d)) for d in event_dates]
                rows_data.append([row["model_name"][:18], str(row["machine_number"])]
                                 + diffs + [fmt_diff(row["平均"]), f"{win_r*100:.0f}%"])
                c_row = [row_bg, row_bg]
                for d in event_dates:
                    v = row.get(d)
                    c_row.append(diff_bg(v) if not pd.isna(v) else GRAY)
                c_row += [row_bg, row_bg]
                cell_colors.append(c_row)
            fig = plt.figure(figsize=(22, 14))
            ax  = fig.add_axes([0, 0, 1, 1])
            draw_table_page(ax, header, rows_data, cell_colors, col_widths,
                            title, legend, page_idx, len(pages))
            pdf.savefig(fig, bbox_inches="tight", dpi=150)
            plt.close(fig)
    print(f"    → {len(pages)}ページ 完了")

def make_kishu_pdf(label, df_n, event_dates, col_labels, out_path):
    print(f"  機種別PDF: {out_path}")
    grp = df_n.groupby(["model_name", "date"])["total_diff"].mean().reset_index()
    pivot = grp.pivot_table(index="model_name", columns="date", values="total_diff")
    pivot.columns = event_dates
    machine_counts = df.groupby("model_name")["machine_number"].nunique()
    pivot["平均"] = pivot[event_dates].mean(axis=1).round(0)
    pivot["勝率"] = (pivot[event_dates] > 0).sum(axis=1) / pivot[event_dates].notna().sum(axis=1)
    pivot["台数"] = machine_counts
    pivot = pivot.reset_index().sort_values("勝率", ascending=False)
    n_dates = len(event_dates)
    col_widths = [4.0, 0.8] + [1.3] * n_dates + [1.3, 1.0]
    header = ["機種名", "台数"] + col_labels + ["平均", "勝率"]
    title  = f"{STORE_NAME}　{label} 機種別分析"
    legend = [(GREEN_HI,"勝率90%~"), ("#44AA66","勝率80%~90%"), (GREEN_LO,"勝率60%~80%"), (RED,"差枚マイナス")]
    rows_data, cell_colors = [], []
    for _, row in pivot.iterrows():
        win_r = row["勝率"] if not pd.isna(row["勝率"]) else 0
        row_bg = win_color_kishu(win_r)
        diffs  = [fmt_diff(row.get(d)) for d in event_dates]
        rows_data.append([row["model_name"][:22],
                          str(int(row["台数"])) if not pd.isna(row["台数"]) else "-"]
                         + diffs + [fmt_diff(row["平均"]), f"{win_r*100:.0f}%"])
        c_row = [row_bg, row_bg]
        for d in event_dates:
            v = row.get(d)
            c_row.append(diff_bg(v) if not pd.isna(v) else GRAY)
        c_row += [row_bg, row_bg]
        cell_colors.append(c_row)
    pages = [rows_data[i:i+ROWS_PER_PAGE] for i in range(0, len(rows_data), ROWS_PER_PAGE)]
    colors_pages = [cell_colors[i:i+ROWS_PER_PAGE] for i in range(0, len(cell_colors), ROWS_PER_PAGE)]
    with PdfPages(out_path) as pdf:
        for page_idx, (page_rows, page_cols) in enumerate(zip(pages, colors_pages)):
            fig = plt.figure(figsize=(22, 14))
            ax  = fig.add_axes([0, 0, 1, 1])
            draw_table_page(ax, header, page_rows, page_cols, col_widths,
                            title, legend, page_idx, len(pages))
            pdf.savefig(fig, bbox_inches="tight", dpi=150)
            plt.close(fig)
    print(f"    → {len(pages)}ページ 完了")

if __name__ == "__main__":
    # ゾロ目日: 11日 と 22日
    zorome_days = [11, 22]

    for day in zorome_days:
        df_n = df[df["date"].dt.day == day].copy()
        event_dates = sorted(df_n["date"].unique())

        if len(event_dates) == 0:
            print(f"{day}日: データなし スキップ")
            continue

        col_labels = make_col_labels(event_dates)
        label = f"{day}日(ゾロ目)"
        print(f"=== {label} ({len(event_dates)}日分: {col_labels[0]}〜{col_labels[-1]}) ===")

        out_zentai = f"{STORE_NAME}_{day}日_全台.pdf"
        out_kishu  = f"{STORE_NAME}_{day}日_機種別.pdf"

        make_zentai_pdf(label, df_n, event_dates, col_labels, out_zentai)
        make_kishu_pdf(label, df_n, event_dates, col_labels, out_kishu)
        print()

    print("全て完了!")
