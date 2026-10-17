
# [改造: 動画ファイルのアップロード取り込み]
# ブラウザからアップロードされた動画 (MP4 / WebM / MKV など) を、KonomiTV が再生できる形式 (H.264/H.265/MPEG-2 + AAC の MP4/TS) に
# 必要に応じて変換した上で、録画フォルダ直下のシリーズフォルダへ置く。置いた直後に、ファイル監視を待たず録画番組として DB へ登録する
# (新しく作ったフォルダの中の変更はファイル監視が拾えないことがあるため)。

import asyncio
import json
import os
import shutil
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import anyio

from app import logging
from app.constants import DATA_DIR, JST, LIBRARY_PATH
from app.metadata.RecordedScanTask import RecordedScanTask, RecordedVideoMoveError


class VideoImportError(Exception):
    """ 取り込み処理のエラー (kind: NotFound / Invalid / Conflict / Failed) """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


class VideoImporter:
    """ アップロードされた動画の受け取り・変換・配置を行うシングルトン """

    STAGING_DIR = DATA_DIR / 'import-staging'

    # アップロードを受け付ける拡張子 (中身は ffprobe で検証する)
    ALLOWED_EXTENSIONS = ('.mp4', '.m4v', '.mkv', '.webm', '.ts', '.m2ts', '.m2t', '.mts', '.mov', '.avi', '.flv', '.wmv', '.mpg', '.mpeg')
    # KonomiTV がそのまま扱える映像コーデック (ffprobe の codec_name)
    SUPPORTED_VIDEO_CODECS = ('h264', 'hevc', 'mpeg2video')
    SUPPORTED_PIX_FMTS = ('yuv420p', 'yuvj420p')
    # 1 回のチャンク送信の最大サイズ
    MAX_CHUNK_SIZE = 64 * 1024 * 1024
    # 受け付けるファイルサイズの上限
    MAX_FILE_SIZE = 20 * 1024 * 1024 * 1024
    # 空き容量として常に残しておく余裕
    FREE_SPACE_MARGIN = 2 * 1024 * 1024 * 1024
    # タイトル (ファイル名) の最大バイト数 (拡張子や .part を除く)
    MAX_TITLE_BYTES = 200
    # 完了・失敗したジョブを保持する日数
    JOB_RETENTION_DAYS = 3

    _instance: 'VideoImporter | None' = None

    def __new__(cls) -> 'VideoImporter':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.jobs: dict[str, dict[str, Any]] = {}
        self._loaded = False
        self._worker: asyncio.Task[None] | None = None
        self._wake = asyncio.Event()
        self._upload_locks: dict[str, asyncio.Lock] = {}
        self._current_process: asyncio.subprocess.Process | None = None
        self._current_job_id: str | None = None
        self._cancel_requested: set[str] = set()


    # ---- ジョブの保存・読み込み ----

    def __jobFile(self, job_id: str) -> Path:
        return self.STAGING_DIR / f'{job_id}.json'

    def __sourceFile(self, job_id: str) -> Path:
        return self.STAGING_DIR / f'{job_id}.src'

    def __saveJob(self, job: dict[str, Any]) -> None:
        tmp = self.__jobFile(job['id']).with_suffix('.json.tmp')
        tmp.write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
        os.replace(tmp, self.__jobFile(job['id']))

    def __ensureLoaded(self) -> None:
        """ 初回アクセス時にステージングフォルダからジョブを読み込み、ワーカーを起動する """

        if not self._loaded:
            self._loaded = True
            self.STAGING_DIR.mkdir(parents=True, exist_ok=True)
            now = time.time()
            for job_file in sorted(self.STAGING_DIR.glob('*.json')):
                try:
                    job = json.loads(job_file.read_text(encoding='utf-8'))
                    job_id = job['id']
                except Exception as ex:
                    logging.warning(f'[VideoImporter] Failed to load job file: {job_file}', exc_info=ex)
                    continue
                # 完了・失敗から一定日数経ったジョブは掃除する
                if job['status'] in ('done', 'failed', 'uploading') and now - job.get('updated_at', now) > self.JOB_RETENTION_DAYS * 86400:
                    self.__removeJobFiles(job_id)
                    continue
                # サーバー再起動で中断された変換は、最初からやり直す
                if job['status'] == 'converting':
                    job['status'] = 'queued'
                    job['progress'] = 0
                    job['message'] = 'サーバー再起動のため変換をやり直します。'
                self.jobs[job_id] = job
            logging.info(f'[VideoImporter] Loaded {len(self.jobs)} import job(s).')

        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self.__workerLoop())
            self._wake.set()

    def __removeJobFiles(self, job_id: str) -> None:
        for path in (self.__jobFile(job_id), self.__sourceFile(job_id)):
            try:
                path.unlink(missing_ok=True)
            except Exception as ex:
                logging.warning(f'[VideoImporter] Failed to remove: {path}', exc_info=ex)

    def __touch(self, job: dict[str, Any], **changes: Any) -> None:
        job.update(changes)
        job['updated_at'] = time.time()
        try:
            self.__saveJob(job)
        except Exception as ex:
            logging.warning(f'[VideoImporter] Failed to save job: {job["id"]}', exc_info=ex)


    # ---- 検証 ----

    @classmethod
    def validateTitle(cls, title: str) -> str:
        """ タイトル (= 保存時のファイル名の拡張子を除いた部分) を検証する """

        if title.strip() == '' or title != title.strip():
            raise VideoImportError('Invalid', 'タイトルが空か、前後に空白があります。')
        if title.endswith('.') or title in ('.', '..'):
            raise VideoImportError('Invalid', 'タイトルの末尾にドットは使えません。')
        if len(title.encode('utf-8')) > cls.MAX_TITLE_BYTES:
            raise VideoImportError('Invalid', 'タイトルが長すぎます。')
        for char in title:
            if char in RecordedScanTask.MOVE_FOLDER_FORBIDDEN_CHARS or ord(char) < 32 or ord(char) == 127:
                raise VideoImportError('Invalid', 'タイトルに使えない文字が含まれています。(\\ / : * ? " < > | と制御文字)')
        if title.split('.')[0].upper() in RecordedScanTask.MOVE_FOLDER_RESERVED_NAMES:
            raise VideoImportError('Invalid', 'このタイトルは使えません。(システム予約名)')
        return title

    def __recordedRoot(self) -> Path:
        folders = RecordedScanTask().recorded_folders
        if len(folders) == 0:
            raise VideoImportError('Failed', '録画フォルダが設定されていません。')
        return Path(str(folders[0]))

    def __destinationExists(self, folder: str, title: str) -> bool:
        directory = self.__recordedRoot() / folder
        return any((directory / f'{title}{ext}').exists() for ext in ('.mp4', '.ts', '.m2ts', '.m2t', '.mts'))


    # ---- ジョブ操作 ----

    def listJobs(self) -> list[dict[str, Any]]:
        self.__ensureLoaded()
        return sorted(self.jobs.values(), key=lambda job: job['created_at'])

    def getJob(self, job_id: str) -> dict[str, Any]:
        self.__ensureLoaded()
        job = self.jobs.get(job_id)
        if job is None:
            raise VideoImportError('NotFound', '取り込みジョブが見つかりません。')
        return job

    def createJob(
        self,
        filename: str,
        size: int,
        folder: str,
        title: str,
        start_date: str | None,
        quality: str,
    ) -> dict[str, Any]:
        """ アップロード用のジョブを作成する """

        self.__ensureLoaded()
        try:
            folder = RecordedScanTask.validateMoveFolderName(folder)
        except RecordedVideoMoveError as ex:
            raise VideoImportError('Invalid', ex.message)
        title = self.validateTitle(title)
        extension = os.path.splitext(filename)[1].lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise VideoImportError('Invalid', f'この拡張子のファイルは取り込めません。({extension or "拡張子なし"})')
        if size <= 0 or size > self.MAX_FILE_SIZE:
            raise VideoImportError('Invalid', 'ファイルサイズが不正です。(空、または大きすぎます)')
        if quality not in ('quality', 'fast'):
            raise VideoImportError('Invalid', '変換方式が不正です。')

        recorded_root = self.__recordedRoot()
        if (recorded_root / folder).is_symlink():
            raise VideoImportError('Invalid', '追加先フォルダがシンボリックリンクのため使えません。')
        if (recorded_root / folder).exists() and not (recorded_root / folder).is_dir():
            raise VideoImportError('Invalid', '同名のファイルがあるため、このフォルダ名は使えません。')
        if self.__destinationExists(folder, title):
            raise VideoImportError('Conflict', f'追加先に同名の番組があります。({title})')
        # 同じ追加先・タイトルのジョブが既にある場合も重複扱いにする
        for other in self.jobs.values():
            if other['status'] != 'failed' and other['folder'] == folder and other['title'] == title:
                raise VideoImportError('Conflict', f'同じ追加先・タイトルの取り込みが既にあります。({title})')

        parsed_start: str | None = None
        if start_date:
            try:
                parsed = datetime.fromisoformat(start_date)
            except ValueError:
                raise VideoImportError('Invalid', '放送日の形式が不正です。')
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=JST)
            parsed_start = parsed.isoformat()

        # 空き容量の確認 (ステージングは受信分、配置先は変換後ぶんとして元サイズ程度を見込む)
        if shutil.disk_usage(self.STAGING_DIR).free < size + self.FREE_SPACE_MARGIN:
            raise VideoImportError('Invalid', 'サーバーの一時保存領域の空き容量が足りません。')
        recorded_root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(recorded_root).free < size * 2 + self.FREE_SPACE_MARGIN:
            raise VideoImportError('Invalid', '録画フォルダの空き容量が足りません。')

        job_id = uuid.uuid4().hex
        job = {
            'id': job_id,
            'filename': filename,
            'size': size,
            'received': 0,
            'folder': folder,
            'title': title,
            'start_date': parsed_start,
            'quality': quality,
            'status': 'uploading',
            'progress': 0,
            'message': '',
            'plan': None,
            'dest_path': None,
            'created_at': time.time(),
            'updated_at': time.time(),
        }
        self.jobs[job_id] = job
        self.__sourceFile(job_id).touch()
        self.__touch(job)
        return job

    async def writeChunk(self, job_id: str, offset: int, stream: Any) -> dict[str, Any]:
        """ チャンクを受信してステージングファイルの末尾に追記する。offset が受信済みバイト数と一致しない場合は Conflict """

        job = self.getJob(job_id)
        lock = self._upload_locks.setdefault(job_id, asyncio.Lock())
        async with lock:
            if job['status'] != 'uploading':
                raise VideoImportError('Conflict', 'このジョブはアップロード中ではありません。')
            if offset != job['received']:
                raise VideoImportError('Conflict', f'受信済みの位置と一致しません。(received={job["received"]})')
            written = 0
            try:
                with open(self.__sourceFile(job_id), 'r+b') as file:
                    file.seek(offset)
                    file.truncate()
                    async for data in stream:
                        written += len(data)
                        if written > self.MAX_CHUNK_SIZE or offset + written > job['size']:
                            raise VideoImportError('Invalid', 'チャンクが大きすぎます。')
                        await asyncio.to_thread(file.write, data)
            except VideoImportError:
                self.__rewind(job_id, offset)
                raise
            except Exception as ex:
                self.__rewind(job_id, offset)
                logging.error(f'[VideoImporter] Failed to receive chunk: {job_id}', exc_info=ex)
                raise VideoImportError('Failed', f'データの受信に失敗しました。({ex!s})')
            job['received'] = offset + written
            self.__touch(job)
            return job

    def __rewind(self, job_id: str, offset: int) -> None:
        try:
            with open(self.__sourceFile(job_id), 'r+b') as file:
                file.truncate(offset)
        except Exception as ex:
            logging.warning(f'[VideoImporter] Failed to truncate: {job_id}', exc_info=ex)

    def completeUpload(self, job_id: str) -> dict[str, Any]:
        job = self.getJob(job_id)
        if job['status'] != 'uploading':
            raise VideoImportError('Conflict', 'このジョブはアップロード中ではありません。')
        if job['received'] != job['size'] or self.__sourceFile(job_id).stat().st_size != job['size']:
            raise VideoImportError('Invalid', 'アップロードが完了していません。')
        self.__touch(job, status='queued', progress=0, message='')
        self._wake.set()
        return job

    def deleteJob(self, job_id: str) -> None:
        """ ジョブを取り消す・一覧から消す (変換中なら変換を中止する) """

        job = self.getJob(job_id)
        if job['status'] == 'converting' and self._current_job_id == job_id:
            self._cancel_requested.add(job_id)
            if self._current_process is not None:
                try:
                    self._current_process.kill()
                except ProcessLookupError:
                    pass
            return
        self.jobs.pop(job_id, None)
        self._upload_locks.pop(job_id, None)
        self.__removeJobFiles(job_id)


    # ---- 変換ワーカー ----

    async def __workerLoop(self) -> None:
        while True:
            await self._wake.wait()
            self._wake.clear()
            while True:
                queued = sorted((job for job in self.jobs.values() if job['status'] == 'queued'), key=lambda job: job['created_at'])
                if len(queued) == 0:
                    break
                job = queued[0]
                try:
                    await self.__process(job)
                except asyncio.CancelledError:
                    raise
                except Exception as ex:
                    logging.error(f'[VideoImporter] Unexpected error: {job["id"]}', exc_info=ex)
                    self.__touch(job, status='failed', message=f'予期しないエラー: {ex!s}')

    def __ffmpegEnv(self) -> dict[str, str]:
        env = dict(os.environ)
        library_dir = str(Path(LIBRARY_PATH['FFmpeg']).parent)
        env['LD_LIBRARY_PATH'] = library_dir + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
        return env

    async def __runCommand(self, args: list[str], job: dict[str, Any] | None = None, duration: float = 0.0) -> tuple[int, str, str]:
        """ ffmpeg / ffprobe を低優先度で実行する (job を渡すと -progress の出力から進捗を更新する) """

        if sys.platform == 'linux' and shutil.which('nice') is not None:
            args = ['nice', '-n', '19', *args]
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.__ffmpegEnv(),
        )
        if job is not None:
            self._current_process = process

        stdout_lines: list[str] = []

        async def read_stdout() -> None:
            assert process.stdout is not None
            last_saved = 0.0
            while True:
                raw = await process.stdout.readline()
                if not raw:
                    break
                line = raw.decode('utf-8', errors='replace').strip()
                if job is None:
                    stdout_lines.append(line)
                    continue
                if line.startswith('out_time_us=') and duration > 0:
                    try:
                        seconds = int(line.split('=', 1)[1]) / 1_000_000
                    except ValueError:
                        continue
                    progress = max(0, min(99, int(seconds / duration * 100)))
                    if progress != job['progress'] and time.time() - last_saved > 1.0:
                        last_saved = time.time()
                        self.__touch(job, progress=progress)

        async def read_stderr() -> str:
            assert process.stderr is not None
            return (await process.stderr.read()).decode('utf-8', errors='replace')

        try:
            _, stderr_text = await asyncio.gather(read_stdout(), read_stderr())
            return_code = await process.wait()
        except asyncio.CancelledError:
            process.kill()
            raise
        finally:
            if job is not None:
                self._current_process = None
        return return_code, '\n'.join(stdout_lines), stderr_text

    async def __probe(self, path: Path) -> dict[str, Any]:
        ffprobe = LIBRARY_PATH['FFprobe']
        return_code, stdout_text, stderr_text = await self.__runCommand([
            ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path),
        ])
        if return_code != 0:
            raise VideoImportError('Failed', f'動画ファイルを解析できませんでした。({stderr_text.strip()[-200:]})')
        try:
            return json.loads(stdout_text)
        except json.JSONDecodeError:
            raise VideoImportError('Failed', '動画ファイルの解析結果を読み取れませんでした。')

    async def __process(self, job: dict[str, Any]) -> None:
        job_id = job['id']
        source = self.__sourceFile(job_id)
        self._current_job_id = job_id
        self.__touch(job, status='converting', progress=0, message='解析中')
        created_dir: Path | None = None
        part_path: Path | None = None
        try:
            probe = await self.__probe(source)
            streams = probe.get('streams', [])
            video = next((s for s in streams if s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic')), None)
            audio = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            if video is None:
                raise VideoImportError('Failed', '映像ストリームが見つかりません。')
            if audio is None:
                raise VideoImportError('Failed', '音声ストリームが見つかりません。(音声なしの動画は取り込めません)')
            try:
                duration = float(probe.get('format', {}).get('duration') or video.get('duration') or 0)
            except ValueError:
                duration = 0.0
            if duration <= 0:
                raise VideoImportError('Failed', '動画の長さを取得できませんでした。')

            format_name = probe.get('format', {}).get('format_name', '')
            container_ok = 'mpegts' in format_name or 'mp4' in format_name
            video_ok = video.get('codec_name') in self.SUPPORTED_VIDEO_CODECS and video.get('pix_fmt') in self.SUPPORTED_PIX_FMTS
            audio_ok = audio.get('codec_name') == 'aac' and audio.get('profile', 'LC') == 'LC' and int(audio.get('channels', 2)) <= 2

            if container_ok and video_ok and audio_ok:
                plan = 'copy'
                extension = '.ts' if 'mpegts' in format_name else '.mp4'
            elif video_ok:
                plan = 'audio'
                extension = '.mp4'
            else:
                plan = 'transcode'
                extension = '.mp4'
            self.__touch(job, plan=plan)

            # 配置先 (なければフォルダを作成)
            recorded_root = self.__recordedRoot()
            folder_path = recorded_root / job['folder']
            if not folder_path.exists():
                folder_path.mkdir()
                created_dir = folder_path
            dest_path = folder_path / f'{job["title"]}{extension}'
            if self.__destinationExists(job['folder'], job['title']):
                raise VideoImportError('Conflict', f'追加先に同名の番組が既にあります。({job["title"]})')
            part_path = folder_path / f'{job["title"]}{extension}.part'
            if part_path.exists():
                raise VideoImportError('Conflict', '追加先に同名の作業ファイルがあります。')

            if plan == 'copy':
                self.__touch(job, message='コピー中')
                await asyncio.to_thread(shutil.copyfile, source, part_path)
            else:
                self.__touch(job, message='変換中 (音声のみ)' if plan == 'audio' else '変換中')
                ffmpeg = LIBRARY_PATH['FFmpeg']
                args = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', str(source),
                        '-map', f'0:{video["index"]}', '-map', f'0:{audio["index"]}', '-sn', '-dn', '-map_metadata', '-1']
                if plan == 'audio':
                    args += ['-c:v', 'copy']
                elif job['quality'] == 'fast':
                    args += ['-c:v', 'h264_nvenc', '-preset', 'p5', '-rc', 'vbr', '-cq', '28', '-b:v', '0',
                             '-profile:v', 'high', '-pix_fmt', 'yuv420p']
                else:
                    args += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-profile:v', 'high', '-pix_fmt', 'yuv420p']
                args += ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
                         '-movflags', '+faststart', '-f', 'mp4', '-progress', 'pipe:1', '-nostats', str(part_path)]
                return_code, _, stderr_text = await self.__runCommand(args, job=job, duration=duration)
                if job_id in self._cancel_requested:
                    raise VideoImportError('Failed', '取り消されました。')
                if return_code != 0:
                    raise VideoImportError('Failed', f'変換に失敗しました。({stderr_text.strip()[-300:]})')

            if not part_path.exists() or part_path.stat().st_size == 0:
                raise VideoImportError('Failed', '変換後のファイルが作成されませんでした。')

            # 番組の開始時刻は「ファイルの更新日時 - 動画の長さ」で決まるため、指定された放送日から逆算して更新日時を設定する
            if job['start_date']:
                modified = datetime.fromisoformat(job['start_date']) + timedelta(seconds=duration)
                timestamp = modified.timestamp()
                os.utime(part_path, (timestamp, timestamp))

            if dest_path.exists():
                raise VideoImportError('Conflict', f'追加先に同名の番組が既にあります。({job["title"]})')
            os.replace(part_path, dest_path)
            part_path = None
            created_dir = None
            source.unlink(missing_ok=True)
            self.__touch(job, status='done', progress=100, message='', dest_path=str(dest_path))
            logging.info(f'[VideoImporter] Imported: {dest_path} (plan={plan})')
            # 新しく作ったフォルダの中の変更はファイル監視が拾えないことがあるため、ここで明示的に録画番組として登録する
            # (ファイル監視側でも同じファイルが検知された場合は、既に登録済みとして何も行われない)
            try:
                await RecordedScanTask().processRecordedFile(anyio.Path(dest_path))
            except Exception as ex:
                logging.warning(f'[VideoImporter] Failed to register the imported file: {dest_path}', exc_info=ex)

        except VideoImportError as ex:
            self.__touch(job, status='failed', message=ex.message)
            logging.warning(f'[VideoImporter] Import failed: {job_id}: {ex.message}')
        except Exception as ex:
            self.__touch(job, status='failed', message=f'エラー: {ex!s}')
            logging.error(f'[VideoImporter] Import failed: {job_id}', exc_info=ex)
        finally:
            self._current_job_id = None
            cancelled = job_id in self._cancel_requested
            self._cancel_requested.discard(job_id)
            if part_path is not None:
                try:
                    part_path.unlink(missing_ok=True)
                except Exception as ex:
                    logging.warning(f'[VideoImporter] Failed to remove the work file: {part_path}', exc_info=ex)
            if created_dir is not None:
                try:
                    created_dir.rmdir()
                except OSError:
                    pass
            if cancelled:
                self.jobs.pop(job_id, None)
                self.__removeJobFiles(job_id)
