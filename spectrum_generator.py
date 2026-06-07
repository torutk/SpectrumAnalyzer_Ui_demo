"""衛星通信ダウンリンクスペクトラムを擬似的に生成する

コーディング生成AIで生成

ver. 0.1.0
"""

import numpy as np
from bokeh.io import output_file, save
from bokeh.models import (
    SingleIntervalTicker, Arrow, VeeHead, BoxAnnotation, Label, Legend, LegendItem
)
from bokeh.plotting import figure

np.random.seed(2025)

# 擬似スペクトラム生成の条件

F_START = 7250.0
F_STOP = 7750.0
N_PTS = 80_000
RBW = 0.0063

freqs = np.linspace(F_START, F_STOP, N_PTS)
delta_f = freqs[1] - freqs[0]

# ノイズフロアの生成

NOISE_FLOOR_DBM = -98.0
NOISE_SIGMA_DB = 1.5

noise_dbm = NOISE_FLOOR_DBM + NOISE_SIGMA_DB * np.random.randn(N_PTS)
spec_mw = 10.0 ** (noise_dbm / 10.0)

# 各種信号の生成

def qpsk_signal(freqs, fc, sym_rate, p_dbm, alpha=0.35):
    fn = np.abs(freqs - fc) / (sym_rate / 2.0)
    shape = np.where(
        fn <= (1.0 - alpha),
        1.0,
        np.where(
            fn <= (1.0 + alpha),
            0.5 * (1.0 + np.cos(np.pi / (2.0 * alpha) * (fn - (1.0 - alpha)))),
            0.0
        )
    )
    ripple = np.exp((np.log(10.0) / 10.0) * 1.0 * np.random.randn(len(freqs)))
    mask = shape > 1e-4
    shape = shape.copy()
    shape[mask] *= ripple[mask]
    bw_hz = sym_rate * (1.0 + alpha)
    psd_mw = 10.0 ** (p_dbm / 10.0) / bw_hz
    sig = psd_mw * RBW * shape
    leak_mw = 10.0 ** ((p_dbm - 25.0) / 10.0)
    sig += leak_mw * np.exp(-0.5 * ((freqs - fc) / (delta_f * 1.5)) ** 2)
    return sig

#
def dsss_signal(freqs, fc, chip_rate, p_dbm):
    x = (freqs - fc) / chip_rate
    shape = np.sinc(x) ** 2

    ripple = np.exp((np.log(10.0) / 10.0) * 1.2 * np.random.randn(len(freqs)))
    mask = shape > 1e-4
    shape[mask] *= ripple[mask]

    psd_mw = 10.0 ** (p_dbm / 10.0) / chip_rate
    return psd_mw * RBW * shape


def cw_signal(freqs, fc, p_dbm):
    sigma = delta_f * 2.5
    return 10.0 ** (p_dbm / 10.0) * np.exp(-0.5 * ((freqs - fc) / sigma) ** 2)

# 各信号の諸元設定

QPSK_PARAMS = [
    (7310, 6, -55, 0.35, "QPSK-A\n6 Mbps a=0.35"),
    (7500, 8, -52, 0.25, "QPSK-B\n8 Mbps b=0.25"),
    (7680, 2, -58, 0.40, "QPSK-C\n2 Mbps c=0.40"),
]

DSSS_PARAMS = [
    (7395, 80, -55, "DSSS-A\n80 Mcps"),
    (7610, 56, -62, "DSSS-B\n56 Mcps"),
]

CW_PARAMS = [
    (7268, -58, "CW-1"),
    (7460, -71, "CW-2"),
    (7736, -61, "CW-3"),
]

# 信号の生成

for fc, rs, pw, a, _ in QPSK_PARAMS:
    spec_mw = spec_mw + qpsk_signal(freqs, fc, rs, pw, a)

for fc, cr, pw, _ in DSSS_PARAMS:
    spec_mw = spec_mw + dsss_signal(freqs, fc, cr, pw)

for fc, pw, _ in CW_PARAMS:
    spec_mw = spec_mw + cw_signal(freqs, fc, pw)

spec_dbm = 10.0 * np.log10(np.maximum(spec_mw, 1e-20))

# プロット

DARK_BG = "#0c0c18"
CYAN = "#00e5ff"
LABEL_C = "#c0c0e0"
QPSK_C = "#ffe566"
DSSS_C = "#ff7843"
CW_C = "#66ffaa"

html_path = "spectrum_7250_7750mhz.html"
output_file(html_path)

plot = figure(
    width=1200, height=600, x_range=(F_START, F_STOP),
    y_range=(-112, -40),
    background_fill_color=DARK_BG,
    border_fill_color=DARK_BG,
    outline_line_color="#484868",
    x_axis_label="周波数 [MHz]",
    y_axis_label="電力 [dBm]",
    tools="pan,wheel_zoom,box_zoom,reset,save",
)

for axis in (plot.xaxis, plot.yaxis):
    axis.axis_label_text_color = LABEL_C
    axis.major_label_text_color = LABEL_C
    axis.axis_line_color = "#484868"
    axis.major_tick_line_color = "#484868"
    axis.minor_tick_line_color = "#484868"

plot.xaxis.ticker = SingleIntervalTicker(interval=50, num_minor_ticks=5)
plot.yaxis.ticker = SingleIntervalTicker(interval=10, num_minor_ticks=2)

plot.xgrid.grid_line_color = "#202038"
plot.xgrid.grid_line_width = 0.7
plot.xgrid.minor_grid_line_color = "#151525"
plot.xgrid.minor_grid_line_width = 0.3
plot.ygrid.grid_line_color = "#202038"
plot.ygrid.grid_line_width = 0.7
plot.ygrid.minor_grid_line_color = "#151525"
plot.ygrid.minor_grid_line_width = 0.3

plot.line(freqs, spec_dbm, color=CYAN, line_width=0.4, line_alpha=0.92)

qpsk_r = plot.patch([0, 0], [0, 0], color=QPSK_C, alpha=0.7, line_color=None)
dsss_r = plot.patch([0, 0], [0, 0], color=DSSS_C, alpha=0.7, line_color=None)
cw_r = plot.patch([0, 0], [0, 0], color=CW_C, alpha=0.7, line_color=None)

def _add_arrow_label(x_tip, y_tip, x_text, y_text, lbl, color, align="center"):
    plot.add_layout(Arrow(
        end=VeeHead(size=6, fill_color=color, line_color=color),
        x_start=x_text, y_start=y_text, x_end=x_tip, y_end=y_tip,
        line_color=color, line_width=0.85,
    ))
    plot.add_layout(Label(
        x=x_text, y=y_text,
        text=lbl.replace("\n", "  "),
        text_color=color, text_font_size="8px", text_font_style="bold",
        text_align=align, text_baseline="bottom",
        background_fill_color=DARK_BG, background_fill_alpha=0.88,
        border_line_color=color, border_line_width=0.9,
        y_offset=2,
    ))


for fc, rs, pw, a, lbl in QPSK_PARAMS:
    bw = rs * (1.0 + a)
    lvl = pw - 10.0 * np.log10(bw / RBW)
    plot.add_layout(BoxAnnotation(
        left=fc - bw / 2, right=fc + bw / 2,
        fill_color=QPSK_C, fill_alpha=0.07, line_color=None,
    ))
    _add_arrow_label(fc, lvl + 1, fc, lvl + 10, lbl, QPSK_C)

for fc, cr, pw, lbl in DSSS_PARAMS:
    lvl = pw - 10.0 * np.log10(cr / RBW)
    plot.add_layout(BoxAnnotation(
        left=fc - cr / 2, right=fc + cr / 2,
        fill_color=DSSS_C, fill_alpha=0.06, line_color=None,
    ))

cw_offsets = [(+14, -7), (-16, -7), (+14, -7)]
for (fc, pw, lbl), (dx, dy) in zip(CW_PARAMS, cw_offsets):
    x_text = fc + dx
    y_text = pw + dy
    align = "left" if dx > 0 else "right"
    plot.add_layout(Arrow(
        end=VeeHead(size=6, fill_color=CW_C, line_color=CW_C),
        x_start=x_text, y_start=y_text, x_end=fc, y_end=pw - 0.5,
        line_color=CW_C, line_width=0.85,
    ))
    plot.add_layout(Label(
        x=x_text, y=y_text,
        text=lbl,
        text_color=CW_C, text_font_size="8px", text_font_style="bold",
        text_align=align, text_baseline="top",
        background_fill_color=DARK_BG, background_fill_alpha=0.88,
        border_line_color=CW_C, border_line_width=0.9,
    ))

legend = Legend(
    items=[
        LegendItem(label="QPSK (Raised Cosine)", renderers=[qpsk_r]),
        LegendItem(label="DSSS ()", renderers=[dsss_r]),
        LegendItem(label="CW ()", renderers=[cw_r]),
    ],
    location="top_left",
    background_fill_color="#12122a",
    border_line_color="#444466",
    label_text_color="white",
    label_text_font_size="10px",
)
plot.add_layout(legend)
save(plot)