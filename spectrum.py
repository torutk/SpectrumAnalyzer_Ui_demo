"""スペクトラム波形モジュール

generate: 擬似的に生成する関数
"""

import numpy as np
from bokeh.plotting import figure, show

NOISE_FLOOR_DBM = -95.0

def generate(
        freq: np.ndarray, t: float
) -> np.ndarray:

    """
    指定された周波数値列と経過時間からスペクトラム波形を生成する。

    Args:
        freq: スペクトラム波形を生成する周波数値列
        t: 最初の波形生成からの経過時間（秒）

    Returns:
        生成したスペクトラムデータ列
    """
    # ノイズフロアの生成
    # 指定した平均（loc）と標準偏差（scale）に基づくガウス分布に従い、size個数の乱数生成
    # およそ、-90から-100dBm の雑音となる
    powers = NOISE_FLOOR_DBM + np.random.normal(0, 1.5, size=freq.size)

    # ---------------------------------
    # キャリア信号（CW波またはそれに近い信号）（CF, BW, Level)
    # 信号の中心周波数、信号の帯域幅、信号のノイズフロアからのレベル
    # ---------------------------------
    carriers = [
        (7350e6, 1024e3, 30),
        (7580e6, 512e3, 40),
        (7662e6, 256e3, 35),
    ]
    for center, width, level in carriers:
        # 時間変動 ±200KHz内の変動（12.5秒周期で）
        center = center + 200e3 * np.sin(t * 0.5)

        # exp(-N) は、Nの値が小さいほど1に近く、大きいほど0に近いので中心周波数に近いほど
        # peakが大きく、中心周波数のときに level * 1 となる
        peak = level * np.exp(
            -((freq - center) ** 2) / (2 * width**2)
        )
        powers += peak

    # ---------------------------------
    # 広帯域信号
    # ---------------------------------
    band_center = 7500e6
    band_width = 20e6

    band = np.exp(
        -((freq - band_center) ** 8)
        / (2 * (band_width / 2) ** 8)
    )

    powers += band * 18

    # ---------------------------------
    # ランダムスパイク
    # ---------------------------------
    if np.random.rand() < 0.05:
        idx = np.random.randint(0, freq.size)
        powers[idx] += 20

    return powers


def main() -> None:
    freqs = np.linspace(7250e6, 7750e6, 50_000)
    powers = generate(freqs, 0.0)
    fig = figure(title="Spectrum", x_axis_label="Frequency [MHz]", y_axis_label="Power [dBm]")
    fig.y_range.start = -120
    fig.y_range.end = -50
    fig.line(freqs / 1e6, powers, line_width=2)
    show(fig)


if __name__ == "__main__":
    main()
