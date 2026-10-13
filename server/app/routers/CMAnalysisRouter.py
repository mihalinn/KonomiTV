
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, status
from fastapi.exceptions import HTTPException

from app import schemas
from app.config import Config, SaveCMDetectionConfig
from app.constants import CM_DETECTION_MODEL_VERSION
from app.metadata.CMAnalysisQueue import CMAnalysisQueue
from app.metadata.CMModelDetector import CMModelDetector
from app.models.User import User
from app.routers.UsersRouter import GetCurrentAdminUser, GetCurrentUser


# ルーター
router = APIRouter(
    tags = ['CMAnalysis'],
    prefix = '/api/cm-analysis',
)


def BuildStatus() -> schemas.CMAnalysisStatus:
    """ 現在の CM 解析機能の状態を組み立てる """

    settings = Config().cm_detection
    jobs = CMAnalysisQueue.getJobs()
    return schemas.CMAnalysisStatus(
        enabled = settings.enabled,
        analyze_new_recordings = settings.analyze_new_recordings,
        device = settings.device,
        threads = settings.threads,
        gpu_available = CMModelDetector.isGPUAvailable(),
        providers = CMModelDetector.getAvailableProviders(),
        model_ready = CMModelDetector.isModelReady(),
        model_downloadable = CMModelDetector.isDownloadable(),
        model_version = CM_DETECTION_MODEL_VERSION,
        model_download = CMModelDetector.download_status,
        pending_count = len([job for job in jobs if job.state == 'Pending']),
        running_count = len([job for job in jobs if job.state == 'Running']),
    )


@router.get(
    '/status',
    summary = 'CM 解析の状態取得 API',
    response_description = 'CM 解析機能の有効/無効、利用可能なデバイス、モデルの配置状況、キューの件数。',
    response_model = schemas.CMAnalysisStatus,
)
async def CMAnalysisStatusAPI(
    current_user: Annotated[User, Depends(GetCurrentUser)],
):
    """
    CM 解析機能の現在の状態を取得する。<br>
    JWT エンコードされたアクセストークンがリクエストの Authorization: Bearer に設定されていないとアクセスできない。
    """

    return BuildStatus()


@router.put(
    '/settings',
    summary = 'CM 解析設定更新 API',
    response_description = '更新後の CM 解析機能の状態。',
    response_model = schemas.CMAnalysisStatus,
)
async def CMAnalysisSettingsUpdateAPI(
    settings: Annotated[schemas.CMAnalysisSettings, Body(description='更新する CM 解析設定。')],
    current_user: Annotated[User, Depends(GetCurrentAdminUser)],
):
    """
    CM 解析設定を更新する。サーバーの再起動なしですぐに反映される。<br>
    CM 検出を無効にすると、待機中の解析は取り消される (実行中の解析は中断を要求する)。<br>
    JWT エンコードされたアクセストークンがリクエストの Authorization: Bearer に設定されていて、かつ管理者アカウントでないとアクセスできない。
    """

    current = Config().cm_detection.model_copy(update=settings.model_dump())
    SaveCMDetectionConfig(current)
    if not settings.enabled:
        CMAnalysisQueue.cancel()
    # デバイスやスレッド数が変わった場合に備え、次回の解析で読み込み直す
    CMModelDetector.unload()
    return BuildStatus()


@router.post(
    '/model/download',
    summary = 'CM 検出モデルのダウンロード API',
    status_code = status.HTTP_202_ACCEPTED,
)
async def CMAnalysisModelDownloadAPI(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(GetCurrentAdminUser)],
):
    """
    CM 検出 AI のモデルファイルのダウンロードを開始する。進捗は CM 解析の状態取得 API の model_download で確認できる。<br>
    JWT エンコードされたアクセストークンがリクエストの Authorization: Bearer に設定されていて、かつ管理者アカウントでないとアクセスできない。
    """

    if not CMModelDetector.isDownloadable():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = 'Model download source is not configured. Please place the model files manually.',
        )
    background_tasks.add_task(CMModelDetector.downloadModels)


@router.get(
    '/jobs',
    summary = 'CM 解析ジョブ一覧 API',
    response_description = '解析中・待機中・終了済みの CM 解析ジョブ。',
    response_model = schemas.CMAnalysisJobs,
)
async def CMAnalysisJobsAPI(
    current_user: Annotated[User, Depends(GetCurrentUser)],
):
    """
    CM 解析ジョブの一覧を取得する。<br>
    JWT エンコードされたアクセストークンがリクエストの Authorization: Bearer に設定されていないとアクセスできない。
    """

    return schemas.CMAnalysisJobs(jobs=CMAnalysisQueue.getJobs())


@router.post(
    '/jobs',
    summary = 'CM 解析ジョブ追加 API',
    response_description = '新たに解析キューに追加した件数。',
    response_model = int,
)
async def CMAnalysisJobsCreateAPI(
    request: Annotated[schemas.CMAnalysisRequest, Body(description='CM 解析する録画ファイルの ID のリスト。')],
    current_user: Annotated[User, Depends(GetCurrentAdminUser)],
):
    """
    指定した録画ファイルを CM 解析キューに追加する。すでに CM 区間が解析済みでも、再度解析し直す。<br>
    解析は 1 本ずつ順番にバックグラウンドで実行される。<br>
    JWT エンコードされたアクセストークンがリクエストの Authorization: Bearer に設定されていて、かつ管理者アカウントでないとアクセスできない。
    """

    if not Config().cm_detection.enabled:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = 'CM detection is disabled in the settings.',
        )
    if not CMModelDetector.isModelReady():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = 'CM detection model is not available.',
        )
    return await CMAnalysisQueue.enqueue(request.video_ids)


@router.delete(
    '/jobs',
    summary = 'CM 解析ジョブ取り消し API',
    status_code = status.HTTP_204_NO_CONTENT,
)
async def CMAnalysisJobsCancelAPI(
    current_user: Annotated[User, Depends(GetCurrentAdminUser)],
    video_id: Annotated[int | None, Query(description='取り消す録画ファイルの ID。省略するとすべて取り消す。')] = None,
    clear_finished: Annotated[bool, Query(description='終了済みのジョブも一覧から消すか。')] = False,
):
    """
    待機中の CM 解析ジョブを取り消し、実行中のジョブには中断を要求する。<br>
    JWT エンコードされたアクセストークンがリクエストの Authorization: Bearer に設定されていて、かつ管理者アカウントでないとアクセスできない。
    """

    CMAnalysisQueue.cancel(video_id)
    if clear_finished:
        CMAnalysisQueue.clearFinished()
