
from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray


class CMFeatureExtractor:
    """
    CM 区間検出 AI に入力する特徴量を、録画ファイルから ffmpeg + numpy だけで抽出するクラス
    全体を 1 秒刻みの時系列として扱い、画像 (CLIP)・ロゴ・音声・無音/黒/場面転換から 18 + 512 次元の特徴を作る
    ここの処理を変えると学習済みモデルの精度が変わってしまうため、学習時と同じ処理を厳密に保つこと
    """

    # CLIP (ViT-B/32) の入力サイズと正規化パラメータ
    CLIP_SIZE = 224
    CLIP_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32).reshape(1, 3, 1, 1)
    CLIP_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32).reshape(1, 3, 1, 1)

    # ロゴ検出 (フレームの四隅を切り出して固定ロゴの有無を調べる)
    LOGO_FPS = 2
    LOGO_W, LOGO_H = 480, 270
    LOGO_CW, LOGO_CH = 120, 68

    # 音声特徴 (0.5 秒刻み)
    AUDIO_SR = 16000
    AUDIO_HOP = AUDIO_SR // 2

    def __init__(
        self,
        ffmpeg_path: str,
        threads: int = 2,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        """
        特徴量抽出クラスを初期化する

        Args:
            ffmpeg_path (str): ffmpeg 実行ファイルのパス
            threads (int): ffmpeg と numpy 演算に使うスレッド数の目安
            should_stop (Callable[[], bool] | None): True を返すと処理を中断する (InterruptedError を送出する)
        """

        self.ffmpeg_path = ffmpeg_path
        self.threads = threads
        self.should_stop = should_stop


    @staticmethod
    def __popenArgs() -> dict[str, Any]:
        """ ffmpeg を低優先度で起動するための Popen 引数 (録画やライブ視聴を邪魔しないため) """

        if sys.platform == 'win32':
            return {'creationflags': subprocess.BELOW_NORMAL_PRIORITY_CLASS}
        return {'preexec_fn': lambda: os.nice(10)}


    @staticmethod
    def __readExact(stream: Any, size: int) -> bytes:
        """ パイプからちょうど size バイトを読む (足りなければ末尾まで) """

        chunks: list[bytes] = []
        remain = size
        while remain > 0:
            data = stream.read(remain)
            if not data:
                break
            chunks.append(data)
            remain -= len(data)
        return b''.join(chunks)


    def __iterRawFrames(self, file_path: str, video_filter: str, frame_bytes: int) -> Iterator[bytes]:
        """ ffmpeg でデコード・縮小した生フレームを 1 枚ずつ返す """

        command = [
            self.ffmpeg_path, '-v', 'error', '-threads', str(self.threads), '-i', file_path,
            '-map', '0:v:0', '-an', '-vf', video_filter, '-f', 'rawvideo', '-',
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **self.__popenArgs())
        try:
            assert process.stdout is not None
            while True:
                if self.should_stop is not None and self.should_stop():
                    raise InterruptedError('cancelled')
                frame = self.__readExact(process.stdout, frame_bytes)
                if len(frame) < frame_bytes:
                    break
                yield frame
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()


    def __runAndCapture(self, command: list[str]) -> tuple[bytes, bytes]:
        """ ffmpeg を実行して標準出力と標準エラーを取得する (中断要求があれば kill する) """

        process = cast('subprocess.Popen[bytes]', subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **self.__popenArgs()))
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    return stdout, stderr
                except subprocess.TimeoutExpired:
                    if self.should_stop is not None and self.should_stop():
                        raise InterruptedError('cancelled') from None
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


    def extractClip(
        self,
        file_path: str,
        encode: Callable[[NDArray[np.float32]], NDArray[np.float32]],
        duration: float,
        on_progress: Callable[[float], None] | None = None,
        batch_size: int = 64,
    ) -> NDArray[np.float32]:
        """
        1fps で全体を 224x224 に縮小したフレームを CLIP 画像エンコーダに通し、正規化済み埋め込み (T, 512) を返す

        Args:
            file_path (str): 録画ファイルのパス
            encode (Callable): (N, 3, 224, 224) の正規化済み画像を (N, 512) の埋め込みに変換する関数
            duration (float): 録画ファイルの長さ (秒) (進捗率の計算にだけ使う)
            on_progress (Callable[[float], None] | None): 進捗率 (0.0 ~ 1.0) の通知先
            batch_size (int): 一度にエンコードするフレーム数

        Returns:
            NDArray[np.float32]: 1 秒ごとの埋め込み (T, 512)
        """

        video_filter = f'fps=1,scale={self.CLIP_SIZE}:{self.CLIP_SIZE}:flags=area,format=rgb24'
        frame_bytes = self.CLIP_SIZE * self.CLIP_SIZE * 3
        outputs: list[NDArray[np.float32]] = []
        buffer: list[NDArray[np.uint8]] = []
        done = 0

        def flush() -> None:
            nonlocal done
            images = np.stack(buffer).transpose(0, 3, 1, 2).astype(np.float32) / 255.0
            images = (images - self.CLIP_MEAN) / self.CLIP_STD
            outputs.append(encode(images.astype(np.float32)))
            done += len(buffer)
            buffer.clear()
            if on_progress is not None:
                on_progress(min(done / max(duration, 1.0), 1.0))

        for frame in self.__iterRawFrames(file_path, video_filter, frame_bytes):
            buffer.append(np.frombuffer(frame, dtype=np.uint8).reshape(self.CLIP_SIZE, self.CLIP_SIZE, 3))
            if len(buffer) == batch_size:
                flush()
        if buffer:
            flush()
        if not outputs:
            raise RuntimeError('映像フレームを取得できませんでした')
        return np.concatenate(outputs)


    @staticmethod
    def __box(a: NDArray[np.float64], r: int) -> NDArray[np.float64]:
        """ 積分画像による r×r の平均フィルタ """

        c = np.cumsum(np.cumsum(a, axis=-2), axis=-1)
        c = np.pad(c, [(0, 0)] * (a.ndim - 2) + [(1, 0), (1, 0)])
        return (c[..., r:, r:] - c[..., :-r, r:] - c[..., r:, :-r] + c[..., :-r, :-r]) / (r * r)


    @classmethod
    def __highpass(cls, a: NDArray[np.float32], r: int = 5) -> NDArray[np.float32]:
        """ 平均フィルタとの差分によるハイパスフィルタ (ロゴの輪郭だけを残す) """

        b = cls.__box(a.astype(np.float64), r)
        o = r // 2
        return (a[..., o:o + b.shape[-2], o:o + b.shape[-1]] - b).astype(np.float32)


    @staticmethod
    def __smoothMedian(x: NDArray[np.float64], k: int) -> NDArray[np.float64]:
        """ 幅 k の移動中央値 """

        pad = k // 2
        xp = np.pad(x, pad, mode='edge')
        return np.median(np.lib.stride_tricks.sliding_window_view(xp, k), axis=1)


    def extractLogo(
        self,
        file_path: str,
        on_progress: Callable[[float], None] | None = None,
        duration: float = 0.0,
    ) -> NDArray[np.float64]:
        """
        2fps のグレースケール映像の四隅から、固定ロゴの有無を示すスコア (0.5 秒刻み) を返す
        時間方向の中央値でロゴのテンプレートを作り、各フレームがどれだけテンプレートに近いかを測る

        Args:
            file_path (str): 録画ファイルのパス
            on_progress (Callable[[float], None] | None): 進捗率 (0.0 ~ 1.0) の通知先
            duration (float): 録画ファイルの長さ (秒) (進捗率の計算にだけ使う)

        Returns:
            NDArray[np.float64]: 0.5 秒ごとのロゴスコア
        """

        video_filter = f'fps={self.LOGO_FPS},scale={self.LOGO_W}:{self.LOGO_H}:flags=area,format=gray'
        frame_bytes = self.LOGO_W * self.LOGO_H
        corners = {
            'TL': (slice(0, self.LOGO_CH), slice(0, self.LOGO_CW)),
            'TR': (slice(0, self.LOGO_CH), slice(self.LOGO_W - self.LOGO_CW, self.LOGO_W)),
            'BL': (slice(self.LOGO_H - self.LOGO_CH, self.LOGO_H), slice(0, self.LOGO_CW)),
            'BR': (slice(self.LOGO_H - self.LOGO_CH, self.LOGO_H), slice(self.LOGO_W - self.LOGO_CW, self.LOGO_W)),
        }
        raw: dict[str, list[NDArray[np.uint8]]] = {k: [] for k in corners}
        total_frames = max(duration * self.LOGO_FPS, 1.0)
        count = 0
        for frame in self.__iterRawFrames(file_path, video_filter, frame_bytes):
            image = np.frombuffer(frame, dtype=np.uint8).reshape(self.LOGO_H, self.LOGO_W)
            for key, (ys, xs) in corners.items():
                raw[key].append(image[ys, xs].copy())
            count += 1
            if on_progress is not None and count % 120 == 0:
                on_progress(min(count / total_frames, 1.0) * 0.7)
        n = len(raw['TL'])
        if n < 20:
            raise RuntimeError('ロゴ検出に必要なフレームが足りません')

        # 四隅それぞれについてスコアを求め、テンプレートの強さ (ノルム) が最大の隅を採用する
        best: tuple[float, NDArray[np.float64]] | None = None
        for key_index, key in enumerate(corners):
            arr = np.stack(raw[key])
            # テンプレート: 時間方向の中央値 (動く背景は相殺され、固定ロゴが残る)。メモリ節約のため 64 フレームおきのブロックで求める
            template_samples = np.concatenate([self.__highpass(arr[i:i + 64].astype(np.float32)) for i in range(0, n, 128)])
            template = np.median(template_samples, axis=0)
            template_centered = template - template.mean()
            template_norm = float(np.linalg.norm(template_centered)) + 1e-6
            amplitude = np.empty(n, dtype=np.float64)
            template_flat = template_centered.reshape(-1).astype(np.float64)
            for i in range(0, n, 64):
                block = self.__highpass(arr[i:i + 64].astype(np.float32)).reshape(min(64, n - i), -1).astype(np.float64)
                block -= block.mean(axis=1, keepdims=True)
                amplitude[i:i + 64] = (block @ template_flat) / (template_norm * template_norm + 1e-6)
            smoothed = self.__smoothMedian(amplitude, 5)
            if best is None or template_norm > best[0]:
                best = (template_norm, smoothed)
            if on_progress is not None:
                on_progress(0.7 + 0.3 * (key_index + 1) / len(corners))
        assert best is not None
        return best[1]


    def extractAudio(self, file_path: str) -> tuple[list[list[float]], NDArray[np.float32]]:
        """
        無音区間 (silencedetect) と 0.5 秒刻みの音声特徴 (n, 4) を 1 回のデコードで取得する
        音声特徴は mid の音量 (dB)・side の音量 (dB)・side/mid の差 (dB)・4kHz 以上の成分比

        Args:
            file_path (str): 録画ファイルのパス

        Returns:
            tuple[list[list[float]], NDArray[np.float32]]: 無音区間 [[開始秒, 終了秒], ...] と音声特徴
        """

        command = [
            self.ffmpeg_path, '-hide_banner', '-nostats', '-v', 'info', '-threads', str(self.threads), '-i', file_path,
            '-map', '0:a:0', '-af', 'silencedetect=n=-45dB:d=0.08', '-ac', '2', '-ar', str(self.AUDIO_SR),
            '-f', 's16le', '-',
        ]
        stdout, stderr = self.__runAndCapture(command)
        silences: list[list[float]] = []
        silence_start: float | None = None
        for line in stderr.decode(errors='replace').splitlines():
            match = re.search(r'silence_start: (-?[\d.]+)', line)
            if match:
                silence_start = float(match.group(1))
            match = re.search(r'silence_end: (-?[\d.]+)', line)
            if match and silence_start is not None:
                silences.append([max(0.0, silence_start), float(match.group(1))])
                silence_start = None

        samples = np.frombuffer(stdout, dtype=np.int16)
        samples = samples[:len(samples) // 2 * 2].astype(np.float32).reshape(-1, 2) / 32768.0
        n = len(samples) // self.AUDIO_HOP
        if n < 4:
            raise RuntimeError('音声を取得できませんでした')
        samples = samples[:n * self.AUDIO_HOP].reshape(n, self.AUDIO_HOP, 2)
        mid = (samples[..., 0] + samples[..., 1]) / 2
        side = (samples[..., 0] - samples[..., 1]) / 2
        rms_mid = np.sqrt((mid ** 2).mean(axis=1) + 1e-10)
        rms_side = np.sqrt((side ** 2).mean(axis=1) + 1e-10)
        spectrum = np.abs(np.fft.rfft(mid * np.hanning(self.AUDIO_HOP), axis=1)) ** 2
        k = int(4000 / (self.AUDIO_SR / self.AUDIO_HOP))
        high_ratio = spectrum[:, k:].sum(axis=1) / (spectrum.sum(axis=1) + 1e-10)
        features = np.stack([
            20 * np.log10(rms_mid), 20 * np.log10(rms_side), 20 * np.log10(rms_side / rms_mid), high_ratio,
        ], axis=1).astype(np.float32)
        return silences, features


    def extractBlackAndScene(self, file_path: str) -> tuple[list[list[float]], list[float]]:
        """
        黒フレーム区間と場面転換の時刻を取得する

        Args:
            file_path (str): 録画ファイルのパス

        Returns:
            tuple[list[list[float]], list[float]]: 黒フレーム区間 [[開始秒, 終了秒], ...] と場面転換の時刻 (秒) のリスト
        """

        command = [
            self.ffmpeg_path, '-hide_banner', '-nostats', '-v', 'info', '-threads', str(self.threads), '-i', file_path,
            '-map', '0:v:0',
            '-vf', "scale=320:180,blackdetect=d=0.03:pic_th=0.92:pix_th=0.12,select='gt(scene,0.35)',showinfo",
            '-an', '-f', 'null', '-',
        ]
        _, stderr = self.__runAndCapture(command)
        text = stderr.decode(errors='replace')
        blacks = [
            [float(m.group(1)), float(m.group(2))]
            for m in re.finditer(r'black_start:([\d.]+) black_end:([\d.]+)', text)
        ]
        scenes = [float(x) for x in re.findall(r'pts_time:([\d.]+)', text)]
        return blacks, scenes


    @staticmethod
    def __perSecond(arr_2hz: NDArray[Any], length: int) -> NDArray[Any]:
        """ 0.5 秒刻みの配列を 1 秒刻みに平均化し、length に揃える """

        n = len(arr_2hz) // 2 * 2
        a = arr_2hz[:n].reshape(-1, 2, *arr_2hz.shape[1:]).mean(axis=1)
        if len(a) < length:
            a = np.concatenate([a, np.repeat(a[-1:], length - len(a), axis=0)])
        return a[:length]


    @staticmethod
    def __rangeFlag(events: list[list[float]], length: int) -> NDArray[np.float32]:
        """ 区間のリストを 1 秒刻みの 0/1 フラグに変換する """

        flags = np.zeros(length, np.float32)
        for start, end in events:
            a, b = int(start), min(int(end) + 1, length)
            if 0 <= a < length:
                flags[a:max(b, a + 1)] = 1
        return flags


    @staticmethod
    def __bodyCentroid(clip: NDArray[np.float32], logo_1s: NDArray[np.float32], length: int) -> NDArray[np.float32]:
        """
        本編の代表画像を求める
        ロゴが出ている長い連続区間 (100 秒以上、4 秒未満の途切れは連結) の埋め込みの平均を、本編の重心とする
        """

        q = np.quantile(logo_1s, 0.7) or 1.0
        logo_on = (logo_1s / max(q, 0.05)) > 0.5
        padded = np.pad(logo_on.astype(np.float32), 2, mode='edge')
        logo_on = np.median(np.lib.stride_tricks.sliding_window_view(padded, 5), axis=1) > 0.5
        runs: list[list[int]] = []
        i = 0
        while i < length:
            if logo_on[i]:
                j = i
                while j < length and logo_on[j]:
                    j += 1
                runs.append([i, j])
                i = j
            else:
                i += 1
        merged: list[list[int]] = []
        for run in runs:
            if merged and run[0] - merged[-1][1] < 4:
                merged[-1][1] = run[1]
            else:
                merged.append(run)
        frames = [clip[a:b] for a, b in merged if b - a >= 100]
        if not frames:
            frames = [clip[logo_on]] if logo_on.sum() > 30 else [clip]
        centroid = np.concatenate(frames).mean(axis=0)
        return (centroid / (np.linalg.norm(centroid) + 1e-9)).astype(np.float32)


    @classmethod
    def buildFeatures(
        cls,
        duration: float,
        clip: NDArray[np.float32],
        audio: NDArray[np.float32],
        logo: NDArray[np.float64],
        silences: list[list[float]],
        blacks: list[list[float]],
        scenes: list[float],
    ) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
        """
        各抽出結果から、モデルに入力する基本特徴 (T, 18) と、T に揃えた CLIP 埋め込み (T, 512) を組み立てる
        基本特徴の列順: 本編との類似度, 同 - 中央値, 音声4次元, 音声4次元 - 中央値, ロゴ, ロゴ/70%点, 場面転換数,
        無音フラグ, 黒フラグ, 位置 t/dur, log1p(残り)/8, log1p(経過)/8

        Returns:
            tuple[NDArray[np.float32], NDArray[np.float32]]: (基本特徴, CLIP 埋め込み)
        """

        length = int(duration)
        if len(clip) < length:
            clip = np.concatenate([clip, np.repeat(clip[-1:], length - len(clip), axis=0)])
        clip = clip[:length]
        audio_1s = cls.__perSecond(audio.astype(np.float32), length)
        audio_1s_centered = audio_1s - np.median(audio_1s, axis=0, keepdims=True)
        logo_1s = cls.__perSecond(logo.astype(np.float32), length)
        centroid = cls.__bodyCentroid(clip, logo_1s, length)
        similarity = clip @ centroid
        similarity_median = np.median(similarity)
        q = np.quantile(logo_1s, 0.7) or 1.0
        logo_normalized = logo_1s / max(q, 0.05)
        scene_count = np.zeros(length, np.float32)
        for t in scenes:
            if 0 <= int(t) < length:
                scene_count[int(t)] += 1
        silence_flag = cls.__rangeFlag(silences, length)
        black_flag = cls.__rangeFlag(blacks, length)
        t = np.arange(length)
        columns = [
            similarity[:, None], (similarity - similarity_median)[:, None], audio_1s, audio_1s_centered,
            logo_1s[:, None], logo_normalized[:, None], scene_count[:, None], silence_flag[:, None],
            black_flag[:, None], (t / duration)[:, None], np.log1p(duration - t)[:, None] / 8,
            np.log1p(t)[:, None] / 8,
        ]
        return np.concatenate(columns, axis=1).astype(np.float32), clip.astype(np.float32)
