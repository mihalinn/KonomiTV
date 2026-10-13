
from __future__ import annotations

import asyncio
import threading
from collections import deque
from typing import ClassVar

import anyio

from app import logging, schemas
from app.config import Config
from app.metadata.CMModelDetector import CMModelDetector
from app.metadata.CMSectionsDetector import CMSectionsDetector
from app.models.RecordedVideo import RecordedVideo


class CMAnalysisQueue:
    """
    CM 区間の AI 解析を 1 本ずつ順番に実行するジョブキュー
    CM 解析は CPU (または GPU) を長時間使う重い処理のため、同時に実行するのは常に 1 本だけに制限している
    キューの内容はメモリ上にのみ保持され、サーバーを再起動すると消える (未解析の録画は再度解析を依頼すればよい)
    """

    # 完了・失敗・キャンセル済みジョブを何件まで履歴として残すか
    MAX_FINISHED_JOBS = 100

    _jobs: ClassVar[dict[int, schemas.CMAnalysisJob]] = {}
    _pending: ClassVar[deque[int]] = deque()
    _worker_task: ClassVar[asyncio.Task[None] | None] = None
    _cancel_event: ClassVar[threading.Event] = threading.Event()


    @classmethod
    async def enqueue(cls, video_ids: list[int]) -> int:
        """
        指定された録画ファイルを解析キューに追加する
        すでに待機中・解析中の録画ファイルは追加しない (重複防止)

        Args:
            video_ids (list[int]): 解析する RecordedVideo の ID のリスト

        Returns:
            int: 新たにキューに追加された件数
        """

        added = 0
        for video_id in video_ids:
            existing = cls._jobs.get(video_id)
            if existing is not None and existing.state in ('Pending', 'Running'):
                continue
            db_recorded_video = await RecordedVideo.get_or_none(id=video_id, status='Recorded').prefetch_related('recorded_program')
            if db_recorded_video is None:
                continue
            cls._jobs.pop(video_id, None)
            cls._jobs[video_id] = schemas.CMAnalysisJob(
                video_id = video_id,
                title = db_recorded_video.recorded_program.title,
                state = 'Pending',
                stage = '',
                progress = 0.0,
                message = '',
                cm_section_count = None,
            )
            cls._pending.append(video_id)
            added += 1

        cls.__trimFinishedJobs()
        if added > 0 and (cls._worker_task is None or cls._worker_task.done()):
            cls._worker_task = asyncio.create_task(cls.__runWorker())
        return added


    @classmethod
    def getJobs(cls) -> list[schemas.CMAnalysisJob]:
        """ ジョブの一覧を返す (解析中 -> 待機中 -> 終了済みの順) """

        order = {'Running': 0, 'Pending': 1, 'Failed': 2, 'Cancelled': 2, 'Completed': 2}
        return sorted(cls._jobs.values(), key=lambda job: order[job.state])


    @classmethod
    def cancel(cls, video_id: int | None = None) -> None:
        """
        待機中のジョブを取り消し、解析中のジョブがあれば中断を要求する

        Args:
            video_id (int | None): 取り消す録画の ID。None の場合はすべて取り消す
        """

        for job in cls._jobs.values():
            if video_id is not None and job.video_id != video_id:
                continue
            if job.state == 'Pending':
                job.state = 'Cancelled'
                if job.video_id in cls._pending:
                    cls._pending.remove(job.video_id)
            elif job.state == 'Running':
                cls._cancel_event.set()


    @classmethod
    def clearFinished(cls) -> None:
        """ 終了済み (完了・失敗・キャンセル) のジョブを一覧から消す """

        for video_id in [i for i, job in cls._jobs.items() if job.state not in ('Pending', 'Running')]:
            del cls._jobs[video_id]


    @classmethod
    def __trimFinishedJobs(cls) -> None:
        """ 終了済みジョブが増えすぎないよう、古いものから消す """

        finished = [i for i, job in cls._jobs.items() if job.state not in ('Pending', 'Running')]
        for video_id in finished[:max(0, len(finished) - cls.MAX_FINISHED_JOBS)]:
            del cls._jobs[video_id]


    @classmethod
    async def __runWorker(cls) -> None:
        """ キューが空になるまで、ジョブを 1 本ずつ処理する """

        try:
            while cls._pending:
                video_id = cls._pending.popleft()
                job = cls._jobs.get(video_id)
                if job is None or job.state != 'Pending':
                    continue
                await cls.__runJob(job)
        finally:
            # 解析が一通り終わったら、数百 MB あるモデルをメモリから解放する
            CMModelDetector.unload()


    @classmethod
    async def __runJob(cls, job: schemas.CMAnalysisJob) -> None:
        """ 1 本分の解析を実行し、結果をジョブに反映する """

        cls._cancel_event.clear()
        job.state = 'Running'
        loop = asyncio.get_running_loop()

        def OnProgress(stage: str, progress: float) -> None:
            job.stage = stage
            job.progress = progress

        def OnProgressThreadSafe(stage: str, progress: float) -> None:
            loop.call_soon_threadsafe(OnProgress, stage, progress)

        try:
            db_recorded_video = await RecordedVideo.get_or_none(id=job.video_id)
            if db_recorded_video is None:
                raise FileNotFoundError('録画データが見つかりません')
            file_path = anyio.Path(db_recorded_video.file_path)
            if not await file_path.is_file():
                raise FileNotFoundError('録画ファイルが見つかりません')

            settings = Config().cm_detection
            detector = CMSectionsDetector(file_path, db_recorded_video.duration)
            cm_sections = await detector.analyzeAndSave(
                device = settings.device,
                threads = settings.threads,
                should_stop = cls._cancel_event.is_set,
                on_progress = OnProgressThreadSafe,
            )
            job.cm_section_count = len(cm_sections)
            job.progress = 1.0
            job.stage = ''
            job.state = 'Completed'

        except InterruptedError:
            job.state = 'Cancelled'
            job.stage = ''
            logging.info(f'[CMAnalysisQueue] Job cancelled. (video_id: {job.video_id})')

        except Exception as ex:
            job.state = 'Failed'
            job.stage = ''
            job.message = f'{type(ex).__name__}: {ex}'
            logging.error(f'[CMAnalysisQueue] Job failed. (video_id: {job.video_id})', exc_info=ex)
