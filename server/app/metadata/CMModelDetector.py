
from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from typing import Any, ClassVar, Literal

import anyio
import httpx
import numpy as np
from numpy.typing import NDArray

from app import logging, schemas
from app.constants import (
    API_REQUEST_HEADERS,
    CM_DETECTION_MODEL_BASE_URL,
    CM_DETECTION_MODEL_DIR,
    CM_DETECTION_MODEL_FILES,
    LIBRARY_PATH,
)
from app.metadata.CMFeatureExtractor import CMFeatureExtractor


class CMModelDetector:
    """
    学習済みの CM 区間検出 AI (ONNX) を使って、録画ファイルから CM 区間を検出するクラス
    モデルは 2 つの ONNX ファイルで構成される。どちらも KonomiTV のリポジトリには含まれず、初回利用時にダウンロードする
    - clip_image.onnx: 1 秒ごとのフレーム画像を 512 次元の特徴に変換する (CLIP 画像エンコーダ)
    - cm_seq.onnx: 全時刻の特徴から 1 秒ごとの CM 確率を出す (GRU 10 個のアンサンブル)
    検出処理は CPU を長時間使うため、同期関数として実装している (呼び出し側で別スレッドで実行すること)
    """

    # 読み込み済みの ONNX セッションのキャッシュ (キー: (デバイス, スレッド数))
    _sessions: ClassVar[dict[tuple[str, int], tuple[Any, Any]]] = {}
    _sessions_lock: ClassVar[threading.Lock] = threading.Lock()

    # モデルのダウンロード状況
    download_status: ClassVar[schemas.CMModelDownloadStatus] = schemas.CMModelDownloadStatus(
        state = 'Idle',
        progress = 0.0,
        message = '',
    )


    @staticmethod
    def isModelReady() -> bool:
        """ 必要なモデルファイルがすべて配置されているかどうか """

        return all((CM_DETECTION_MODEL_DIR / name).is_file() for name in CM_DETECTION_MODEL_FILES)


    @staticmethod
    def isDownloadable() -> bool:
        """ モデルのダウンロード元が設定されているかどうか """

        return CM_DETECTION_MODEL_BASE_URL != ''


    @staticmethod
    def getAvailableProviders() -> list[str]:
        """ 利用可能な ONNX Runtime の実行プロバイダー (GPU 対応版の onnxruntime が入っていれば CUDA / DirectML も含まれる) """

        try:
            import onnxruntime
            CMModelDetector.preloadGPULibraries(onnxruntime)
            return list(onnxruntime.get_available_providers())
        except ImportError:
            return []


    @staticmethod
    def preloadGPULibraries(onnxruntime: Any) -> None:
        """ pip でインストールした CUDA / cuDNN ライブラリを事前に読み込む (GPU 版 onnxruntime が見つけられるようにする) """

        preload_dlls = getattr(onnxruntime, 'preload_dlls', None)
        if preload_dlls is not None:
            try:
                preload_dlls()
            except Exception:
                pass


    @classmethod
    def isGPUAvailable(cls) -> bool:
        """ GPU で推論できるかどうか """

        providers = cls.getAvailableProviders()
        return 'CUDAExecutionProvider' in providers or 'DmlExecutionProvider' in providers


    @classmethod
    def unload(cls) -> None:
        """ 読み込み済みのモデルを破棄してメモリを解放する (解析が空いたときや設定変更時に呼ぶ) """

        with cls._sessions_lock:
            cls._sessions.clear()


    @classmethod
    def __getSessions(cls, device: Literal['CPU', 'GPU'], threads: int) -> tuple[Any, Any]:
        """ ONNX セッションを取得する (初回のみモデルを読み込む) """

        import onnxruntime

        with cls._sessions_lock:
            key = (device, threads)
            if key not in cls._sessions:
                # 設定が変わった場合は古いセッションを先に捨てる
                cls._sessions.clear()
                options = onnxruntime.SessionOptions()
                options.intra_op_num_threads = threads
                options.log_severity_level = 3
                cls.preloadGPULibraries(onnxruntime)
                available = onnxruntime.get_available_providers()
                providers: list[str] = []
                if device == 'GPU':
                    providers += [p for p in ('CUDAExecutionProvider', 'DmlExecutionProvider') if p in available]
                    if len(providers) == 0:
                        logging.warning('[CMModelDetector] GPU is selected but no GPU execution provider is available. Falling back to CPU.')
                providers.append('CPUExecutionProvider')
                clip_session = onnxruntime.InferenceSession(
                    str(CM_DETECTION_MODEL_DIR / 'clip_image.onnx'), options, providers=providers,
                )
                seq_session = onnxruntime.InferenceSession(
                    str(CM_DETECTION_MODEL_DIR / 'cm_seq.onnx'), options, providers=providers,
                )
                logging.info(f'[CMModelDetector] Models loaded. (providers: {clip_session.get_providers()})')
                cls._sessions[key] = (clip_session, seq_session)
            return cls._sessions[key]


    @staticmethod
    def postprocess(probabilities: NDArray[np.float32], min_length: int = 6) -> list[schemas.CMSection]:
        """
        1 秒ごとの CM 確率を CM 区間に変換する
        確率 0.5 超を CM とし、min_length 秒未満の短い区間は隣の区間に吸収する

        Args:
            probabilities (NDArray[np.float32]): 1 秒ごとの CM 確率
            min_length (int): これより短い区間は隣に吸収する (秒)

        Returns:
            list[schemas.CMSection]: CM 区間のリスト
        """

        mask = probabilities > 0.5
        n = len(mask)
        while True:
            runs: list[tuple[int, int]] = []
            i = 0
            while i < n:
                j = i
                while j < n and mask[j] == mask[i]:
                    j += 1
                runs.append((i, j))
                i = j
            short_run = next(((a, b) for a, b in runs if b - a < min_length and len(runs) > 1), None)
            if short_run is None:
                break
            mask[short_run[0]:short_run[1]] = ~mask[short_run[0]]
        sections: list[schemas.CMSection] = []
        i = 0
        while i < n:
            if mask[i]:
                j = i
                while j < n and mask[j]:
                    j += 1
                sections.append({'start_time': float(i), 'end_time': float(j)})
                i = j
            else:
                i += 1
        return sections


    @classmethod
    def detect(
        cls,
        file_path: str,
        duration: float,
        device: Literal['CPU', 'GPU'] = 'CPU',
        threads: int = 2,
        should_stop: Callable[[], bool] | None = None,
        on_progress: Callable[[str, float], None] | None = None,
    ) -> list[schemas.CMSection]:
        """
        録画ファイルの CM 区間を検出する (同期処理・長時間かかる)

        Args:
            file_path (str): 録画ファイルのパス
            duration (float): 録画ファイルの長さ (秒)
            device (Literal['CPU', 'GPU']): 画像特徴の推論に使うデバイス
            threads (int): ffmpeg と推論に使うスレッド数の目安
            should_stop (Callable[[], bool] | None): True を返すと処理を中断する (InterruptedError が送出される)
            on_progress (Callable[[str, float], None] | None): 進捗通知 (工程名, 全体の進捗率 0.0 ~ 1.0)

        Returns:
            list[schemas.CMSection]: CM 区間のリスト (CM が見つからなければ空)
        """

        if not cls.isModelReady():
            raise RuntimeError('CM 検出モデルが配置されていません')

        clip_session, seq_session = cls.__getSessions(device, threads)
        extractor = CMFeatureExtractor(LIBRARY_PATH['FFmpeg'], threads, should_stop)

        # 各工程の全体に占める割合 (CPU で 30 分番組を解析したときの所要時間の比率に近い値)
        stages = [('画像', 0.40), ('ロゴ', 0.18), ('音声', 0.05), ('黒・場面転換', 0.37)]
        offsets = [sum(w for _, w in stages[:i]) for i in range(len(stages))]

        def Report(stage_index: int, fraction: float) -> None:
            if on_progress is not None:
                on_progress(stages[stage_index][0], min(offsets[stage_index] + stages[stage_index][1] * fraction, 0.97))

        def Encode(images: NDArray[np.float32]) -> NDArray[np.float32]:
            return clip_session.run(None, {'image': images})[0]

        Report(0, 0.0)
        clip = extractor.extractClip(file_path, Encode, duration, lambda f: Report(0, f))
        Report(1, 0.0)
        logo = extractor.extractLogo(file_path, lambda f: Report(1, f), duration)
        Report(2, 0.0)
        silences, audio = extractor.extractAudio(file_path)
        Report(3, 0.0)
        blacks, scenes = extractor.extractBlackAndScene(file_path)

        base, clip_features = CMFeatureExtractor.buildFeatures(duration, clip, audio, logo, silences, blacks, scenes)
        probabilities = seq_session.run(None, {'base': base[None], 'clip': clip_features[None]})[0][0]
        return cls.postprocess(probabilities)


    @classmethod
    async def downloadModels(cls) -> None:
        """
        モデルファイルをダウンロードして配置する
        進捗は download_status で確認できる。一時ファイルにダウンロードし、サイズ確認後に正式な名前へリネームする
        """

        if cls.download_status.state == 'Downloading':
            return
        if not cls.isDownloadable():
            cls.download_status = schemas.CMModelDownloadStatus(
                state = 'Failed', progress = 0.0, message = 'ダウンロード元が設定されていません。モデルファイルを手動で配置してください。',
            )
            return

        cls.download_status = schemas.CMModelDownloadStatus(state='Downloading', progress=0.0, message='')
        try:
            CM_DETECTION_MODEL_DIR.mkdir(parents=True, exist_ok=True)
            names = list(CM_DETECTION_MODEL_FILES.keys())
            async with httpx.AsyncClient(headers=API_REQUEST_HEADERS, follow_redirects=True, timeout=60.0) as client:
                for index, name in enumerate(names):
                    expected_sha256 = CM_DETECTION_MODEL_FILES[name]
                    destination = anyio.Path(CM_DETECTION_MODEL_DIR / name)
                    temp_path = anyio.Path(CM_DETECTION_MODEL_DIR / f'{name}.download')
                    # すでに正しいファイルがあればスキップ
                    if await destination.is_file() and await cls.__sha256(destination) == expected_sha256:
                        continue
                    sha256 = hashlib.sha256()
                    async with client.stream('GET', f'{CM_DETECTION_MODEL_BASE_URL}/{name}') as response:
                        response.raise_for_status()
                        total = int(response.headers.get('content-length', '0'))
                        received = 0
                        async with await temp_path.open('wb') as f:
                            async for chunk in response.aiter_bytes(1024 * 1024):
                                await f.write(chunk)
                                sha256.update(chunk)
                                received += len(chunk)
                                file_fraction = received / total if total > 0 else 0.0
                                cls.download_status = schemas.CMModelDownloadStatus(
                                    state = 'Downloading',
                                    progress = (index + file_fraction) / len(names),
                                    message = f'{name} をダウンロード中...',
                                )
                    if sha256.hexdigest() != expected_sha256:
                        await temp_path.unlink(missing_ok=True)
                        raise RuntimeError(f'{name} のハッシュ値が一致しません')
                    await temp_path.replace(destination)
            cls.unload()
            cls.download_status = schemas.CMModelDownloadStatus(state='Completed', progress=1.0, message='')
            logging.info('[CMModelDetector] CM detection models downloaded.')
        except Exception as ex:
            logging.error('[CMModelDetector] Failed to download CM detection models:', exc_info=ex)
            cls.download_status = schemas.CMModelDownloadStatus(state='Failed', progress=0.0, message=f'{type(ex).__name__}: {ex}')


    @staticmethod
    async def __sha256(path: anyio.Path) -> str:
        """ ファイルの SHA-256 を計算する """

        sha256 = hashlib.sha256()
        async with await path.open('rb') as f:
            while chunk := await f.read(1024 * 1024):
                sha256.update(chunk)
        return sha256.hexdigest()
