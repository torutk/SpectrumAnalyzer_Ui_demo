"""衛星通信のスペクトラム波形を模擬する

周波数列を指定して初期化する。生成する波形は次の通り。

* ノイズフロア
* SCPC波（QPSK）
* SS波
* CW
* 時間変動(T.B.

"""
from functools import partial
import numpy as np
from dataclasses import dataclass
from scipy.ndimage import gaussian_filter1d


_rng = np.random.default_rng(42) # 乱数生成器


def dbm_to_mw(dbm: float| int | np.ndarray) -> float | int | np.ndarray:
    """単位dBmの値を単位mWの値に変換する"""
    return 10.0 ** (dbm / 10.0)


def mw_to_dbm(mw: float | int | np.ndarray) -> float | int | np.ndarray:
    """単位mWの値を単位dBmの値に変換する"""
    return 10.0 * np.log10(mw)


def add_dbm(
        dbm1: float | int | np.ndarray,
        dbm2: float | int | np.ndarray
) -> float | int | np.ndarray:
    """2つの値[dBm]をmWに変換し加算した後[dBm]に戻して返却する"""
    return mw_to_dbm(dbm_to_mw(dbm1) + dbm_to_mw(dbm2))


def generate_gaussian_ripple(size, sigma=3):
    """リップルを正規分布乱数にガウシアンフィルターで平滑化して生成する。

    Args:
        size: 生成する信号のデータ点数（周波数列のサイズ）
        sigma: リップルの平滑化度合い（大きいほどより平滑化）
    """
    return gaussian_filter1d(_rng.normal(size=size), sigma=sigma)


def generate_normal_ripple(size, sigma):
    """リップルを正規分布乱数で生成する

    Args:
        size: 生成する信号のデータ点数（周波数列のサイズ）
        sigma: リップルの標準偏差
    """
    return _rng.normal(size=size, scale=sigma)


def generate_signal(
        freqs,
        fc,
        bandwidth,
        level,
        rolloff=0.35,
        gen_ripple=generate_gaussian_ripple
):
    """信号を生成する

    周波数列、中心周波数、帯域幅、信号の最大電力、立ち上がり／立ち下がりの急峻さ、
    リップル生成関数を指定し、信号を生成する。
    各周波数について、中心周波数からの距離を帯域幅で正規化した値列を生成
    （中心周波数から帯域幅内が0-1、帯域幅を超えると1以上となる）
    正規化距離が
    * 1 - rolloff 以内：信号レベル 1.0
    * 1 - rolloff から 1以内：信号レベル　1から0にcosineカーブで減少
    * 1以上：信号レベル 0.0
    リップル生成関数は、引数に周波数列のサイズを取り、1をベースとするリップルを戻り値
    とする。

    Args:
        freqs: 周波数の配列[Hz]
        center: 中心周波数[Hz]
        bandwidth: 帯域幅[Hz]
        level_dbm: 信号レベル[dBm]
        rolloff: ローフオフ率（0.0～1.0, 0は急峻な立ち上／下がり）
        gen_ripple: リップル生成関数

    Returns:
        信号[mW]

    """
    fn = np.abs(freqs - fc) / (bandwidth / 2)  # 中心周波数からの距離（帯域幅内が0-1となる）
    shape = np.where(
        fn <= (1.0 - rolloff),
        1.0,
        np.where(
            fn <= 1.0,
            0.5 * (1.0 + np.cos(np.pi * (fn - (1.0 - rolloff)) / rolloff)),
            0.00,
        )
    )
    mask = shape > 1.0e-4  # shape列のうち信号がある（0より大きい）インデックスリスト
    ripple_mw = dbm_to_mw(gen_ripple(len(freqs)))
    shape[mask] *= ripple_mw[mask]
    shape *= dbm_to_mw(level)
    return shape


def generate_cw_signal(freqs, fc, p_dbm):
    """1つの無変調信号を生成する。

    Args:
        freqs: 周波数の配列[Hz]
        fc: 中心周波数[Hz]
        p_dbm: 信号レベル[dBm]
    """
    delta_f = freqs[1] - freqs[0]
    sigma = delta_f * 2.5
    return dbm_to_mw(p_dbm) * np.exp(-0.5 * ((freqs - fc) / sigma) ** 2)


@dataclass
class QPSKSignal:
    """QPSK信号模擬設定を保持する"""
    center_freq_hz: float | int
    bandwidth_hz: float | int
    peak_level_dbm: float | int
    enabled: bool = True


@dataclass
class DSSSSignal:
    """直接スペクトラム拡散信号を保持する"""
    center_freq_hz: float | int
    bandwidth_hz: float | int
    peak_level_dbm: float | int
    enabled: bool = True


@dataclass
class CWSignal:
    """無変調（搬送波）信号を保持する"""
    center_freq_hz: float | int
    peak_level_dbm: float | int
    enabled: bool = True


class SpectrumSimulator:
    """衛星通信スペクトラム波形を擬似的に生成する

    Attributes:
        freqs_hz: 模擬する周波数列 [Hz]
        time: 時間に基づく変動の生成に使用する時刻（経過時間[s]）
        noise_level_dbm: ノイズレベルの基準値 [dBm]
        noise_std: ノイズの標準偏差 [dBm]
        qpsk_signals: QPSK信号設定のリスト
        dsss_signals: DSSS信号設定のリスト
        cw_signals: CW信号設定のリスト
        noise_floor_dbm: ノイズフロア [dBm]
        qpsk_signal_dbm: QPSK信号の合計 [dBm]
        dsss_signal_dbm: DSSS信号の合計 [dBm]
        cw_cignal_dbm: CW信号の合計 [dBm]
        spectrum_dbm: 模擬スペクトラム [dBm]

    """
    def __init__(self, freqs: np.ndarray):
        """周波数列を指定して初期化する"""
        self.freqs_hz = freqs
        self.time = 0.0
        self.noise_level_dbm = -95.0
        self.noise_std = 1.0
        self.qpsk_signals = []
        self.dsss_signals = []
        self.cw_signals = []
        self.noise_floor_dbm = None
        self.qpsk_signal_dbm = None
        self.dsss_signal_dbm = None
        self.cw_signal_dbm = None
        self.spectrum_dbm = None


    def add_qpsk(self, center_freq, bandwidth, level):
        """QPSK信号設定を追加する

        Args:
            center_freq_hz: 中心周波数 [Hz]
            bandwidth_hz: 带域幅 [Hz]
            level_dbm: レベル [dBm]
        """
        self.qpsk_signals.append(
            QPSKSignal(center_freq, bandwidth, level)
        )


    def add_dsss(self, center_freq, bandwidth, level):
        """DSSS信号設定を追加する"""
        self.dsss_signals.append(
            DSSSSignal(center_freq, bandwidth, level)
        )


    def add_cw(self, center_freq, level):
        """CW信号設定を追加する"""
        self.cw_signals.append(
            CWSignal(center_freq, level)
        )


    def noise_floor(self):
        """ノイズフロアを生成する"""
        self.noise_floor_dbm = self.noise_level_dbm + _rng.normal(
            scale=self.noise_std, size=len(self.freqs_hz)
        )


    def qpsk_signal(self):
        """QPSK信号を生成する"""
        gen_ripple = partial(generate_gaussian_ripple, sigma=20)
        signals = None
        for sig in self.qpsk_signals:
            qpsk = generate_signal(
                self.freqs_hz, sig.center_freq_hz, sig.bandwidth_hz,
                sig.peak_level_dbm, 0.35, gen_ripple
            )
            if signals is None:
                signals = qpsk
            else:
                signals += qpsk
        self.qpsk_signal_dbm = mw_to_dbm(signals)


    def dsss_signal(self):
        """DSSS信号を生成する"""
        gen_ripple = partial(generate_normal_ripple, sigma=0.5)
        signals = None
        for sig in self.dsss_signals:
            #dsss = generate_dsss_signal(
            #dsss = generate_cdma_signal(
            dsss = generate_signal(
                self.freqs_hz, sig.center_freq_hz, sig.bandwidth_hz,
                sig.peak_level_dbm, 0.6, gen_ripple
            )
            if signals is None:
                signals = dsss
            else:
                signals += dsss
        self.dsss_signal_dbm = mw_to_dbm(signals)


    def cw_signal(self):
        """CW信号を生成する"""
        signals = None
        for sig in self.cw_signals:
            cw = generate_cw_signal(
                self.freqs_hz, sig.center_freq_hz, sig.peak_level_dbm
            )
            if signals is None:
                signals = cw
            else:
                signals += cw
        self.cw_signal_dbm = mw_to_dbm(signals)


    def get_spectrum(self):
        """ノイズフロア、QPSK信号、DSSS信号、CW信号のスペクトラムを合算する

        Returns:
            模擬スペクトラム [dBm]
        """
        self.noise_floor()
        self.qpsk_signal()
        self.dsss_signal()
        self.cw_signal()
        spectrum_mw = (dbm_to_mw(self.noise_floor_dbm)
                       + dbm_to_mw(self.qpsk_signal_dbm)
                       + dbm_to_mw(self.dsss_signal_dbm)
                       + dbm_to_mw(self.cw_signal_dbm))
        self.spectrum_dbm = mw_to_dbm(spectrum_mw)
        return self.spectrum_dbm


def main():
    """単体で動作確認用"""
    from bokeh.plotting import figure, show
    from bokeh.models import LinearAxis, Range1d
    _FREQ_START = 3400e6
    _FREQ_STOP = 4200e6
    _RBW = 3.052e3
    num_points = int((_FREQ_STOP - _FREQ_START) / _RBW)
    freq = np.linspace(_FREQ_START, _FREQ_STOP, num_points)
    sim = SpectrumSimulator(freq)
    sim.add_qpsk(3.56e9, 10e6, -60)
    sim.add_qpsk(3.62e9, 20e6, -61)
    sim.add_qpsk(3.72e9, 4e6, -62)
    sim.add_qpsk(3.84e9, 5e6, -63)
    sim.add_dsss(4.1e9, 80e6, -75)
    sim.add_cw(3.45e9, -58)
    sim.add_cw(3.5e9, -59)

    p = figure(width=800, height=480, y_range=(-120, 0))
    p.extra_y_ranges = {"ripple": Range1d(start=-15, end=5)}
    extra_y_axis = LinearAxis(axis_label="Ripple", y_range_name="ripple")
    p.add_layout(extra_y_axis, 'right')
    p.x_range.range_padding = 0
    p.line(sim.freqs_hz, sim.get_spectrum(), legend_label="Signal")
    p.line(sim.freqs_hz,
           generate_normal_ripple(len(sim.freqs_hz), sigma=0.1),
           y_range_name="ripple", legend_label="ripple/normal",
           line_color="magenta")
    p.line(sim.freqs_hz,
           generate_gaussian_ripple(len(sim.freqs_hz), sigma=20),
           y_range_name="ripple", legend_label="ripple/gaussian",
           line_color="darkviolet")
    show(p)


if __name__ == "__main__":
    main()
