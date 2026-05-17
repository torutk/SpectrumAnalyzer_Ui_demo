"""スペクトラムアナライザ風のグラフ表示"""

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models.callbacks import CustomJS
from bokeh.plotting import figure
from bokeh.models import CheckboxGroup, ColumnDataSource, HoverTool
import numpy as np
import spectrum

t = 0.0

def main():
    # X軸（周波数）のデータ生成
    freq = np.linspace(7250e6, 7750e6, 5_000)
    # データソースの定義
    ## スペクトラム現在値
    source = ColumnDataSource(data=dict(
        x=freq / 1e6,
        y=np.zeros_like(freq),
    ))
    ## スペクトラムのMin Hold
    min_source = ColumnDataSource(data=dict(x=freq / 1e6, y=np.full(freq.size, np.inf)))
    ## スペクトラムのMax Hold
    max_source = ColumnDataSource(data=dict(x=freq / 1e6, y=np.full(freq.size, -np.inf)))
    ## Peak Marker用
    peak_source = ColumnDataSource(data=dict(x=[0.0], y=[0.0]))
    # プロット領域
    p = figure(
        width=1000, height=400,
        title="Spectrum",
        x_axis_label="Frequency [MHz]", y_axis_label="Power [dBm]",
        toolbar_location="above",
    )
    # Y軸の表示範囲を固定
    p.y_range.start = -120
    p.y_range.end = -40
    # 現在値のプロット
    current_line = p.line("x", "y", source=source, legend_label="current", color="royalblue")
    # Min Holdのプロット
    p.line("x", "y", source=min_source, legend_label="min hold", color="lightgreen")
    # Max Holdのプロット
    p.line("x", "y", source=max_source, legend_label="max hold", color="orange")
    # ピークマーカーのプロット（デフォルトは非表示）
    peak_scatter = p.scatter("x", "y", source=peak_source, color="darkred", marker="diamond", size=12, visible=False)
    # マウスカーソルに直近のデータをホバー表示
    p.add_tools(HoverTool(tooltips=[("Frequency[MHz]", "@x{0,0.000}"), ("Power[dBm]", "@y{0,0.000}")]))
    #p.add_tools(HoverTool(tooltips=[("Frequency[MHz]", "@x{0,0.000}"), ("Power[dBm]", "@y{0,0.000}")], renderers=[current_line]))

    # 凡例のラインをクリックしてプロットの表示・非表示操作を可能に
    p.legend.click_policy = "hide" # needs call after legend properties are set
    legend = p.legend[0]
    p.add_layout(legend, "right")

    def update():
        global t
        current = spectrum.generate(freq, t)
        source.data = dict(x=freq / 1e6, y=current)
        min_hold = min_source.data["y"]
        min_source.data = dict(x=freq / 1e6, y=np.minimum(min_hold, current))
        max_hold = max_source.data["y"]
        max_source.data = dict(x=freq / 1e6, y=np.maximum(max_hold, current))
        peak_idx = np.argmax(current)
        peak_source.data = dict(x=[freq[peak_idx] / 1e6], y=[current[peak_idx]])
        t += 1

    peak_checkbox = CheckboxGroup(labels=["Peak Marker"], active=[], align="center")
    peak_callback = CustomJS(args=dict(scatter=peak_scatter), code="""
        console.log("peak_scatter is visible?", scatter.visible)
        scatter.visible = cb_obj.active.includes(0);
    """)
    peak_checkbox.js_on_change("active", peak_callback)

    layout = column(
        row(
            p,
            column(
                peak_checkbox,
            )
        )
    )
    curdoc().add_periodic_callback(update, 1000)
    curdoc().add_root(layout)

main()
