
import APIClient from  '@/services/APIClient';
import { IChannel } from '@/services/Channels';
import Utils, { CommentUtils } from '@/utils';

/** [改造] 動画ファイルの取り込みジョブを表すインターフェース */
export interface IVideoImportJob {
    id: string;
    filename: string;
    size: number;
    received: number;
    folder: string;
    title: string;
    start_date: string | null;
    quality: 'quality' | 'fast';
    status: 'uploading' | 'queued' | 'converting' | 'done' | 'failed';
    progress: number;
    message: string;
    plan: 'copy' | 'audio' | 'transcode' | null;
    dest_path: string | null;
    created_at: number;
    updated_at: number;
}

/** ソート順序を表す型 */
export type SortOrder = 'desc' | 'asc';

/** マイリストのソート順序を表す型 */
export type MylistSortOrder = 'mylist_added_desc' | 'mylist_added_asc' | 'recorded_desc' | 'recorded_asc';

/** 録画ファイル情報を表すインターフェース */
export interface IRecordedVideo {
    id: number;
    status: 'Recording' | 'Recorded' | 'AnalysisFailed' | 'Missing';
    file_path: string;
    file_hash: string;
    file_size: number;
    file_created_at: string;
    file_modified_at: string;
    recording_start_time: string | null;
    recording_end_time: string | null;
    duration: number;
    container_format: 'MPEG-TS' | 'MPEG-4';
    video_codec: 'MPEG-2' | 'H.264' | 'H.265';
    video_codec_profile: 'High' | 'High 10' | 'Main' | 'Main 10' | 'Baseline' | 'Constrained Baseline';
    video_scan_type: 'Interlaced' | 'Progressive';
    video_frame_rate: number;
    video_resolution_width: number;
    video_resolution_height: number;
    has_video_stream_changes: boolean;
    primary_audio_codec: 'AAC-LC' | 'HE-AAC';
    primary_audio_channel: 'Monaural' | 'Stereo' | '5.1ch';
    primary_audio_sampling_rate: number;
    secondary_audio_codec: 'AAC-LC' | 'HE-AAC' | null;
    secondary_audio_channel: 'Monaural' | 'Stereo' | '5.1ch' | null;
    secondary_audio_sampling_rate: number | null;
    cm_sections: { start_time: number; end_time: number; }[] | null;
    cm_analysis_version: string | null;
    thumbnail_info: IThumbnailInfo | null;
    created_at: string;
    updated_at: string;
}

/** サムネイル情報を表すインターフェース */
export interface IThumbnailInfo {
    version: number;
    representative: IThumbnailImageInfo;
    tile: IThumbnailTileInfo;
}

/** 代表サムネイル情報を表すインターフェース */
export interface IThumbnailImageInfo {
    format: 'WebP';
    width: number;
    height: number;
    revision: number;
}

/** サムネイルタイル情報を表すインターフェース */
export interface IThumbnailTileInfo {
    format: 'WebP';
    image_width: number;
    image_height: number;
    tile_width: number;
    tile_height: number;
    total_tiles: number;
    column_count: number;
    row_count: number;
    interval_sec: number;
}

/** 録画ファイル情報を表すインターフェースのデフォルト値 */
export const IRecordedVideoDefault: IRecordedVideo = {
    id: -1,
    status: 'Recorded',
    file_path: '',
    file_hash: '',
    file_size: 0,
    file_created_at: '2000-01-01T00:00:00+09:00',
    file_modified_at: '2000-01-01T00:00:00+09:00',
    recording_start_time: null,
    recording_end_time: null,
    duration: 0,
    container_format: 'MPEG-TS',
    video_codec: 'MPEG-2',
    video_codec_profile: 'High',
    video_scan_type: 'Interlaced',
    video_frame_rate: 29.97,
    video_resolution_width: 1440,
    video_resolution_height: 1080,
    has_video_stream_changes: false,
    primary_audio_codec: 'AAC-LC',
    primary_audio_channel: 'Stereo',
    primary_audio_sampling_rate: 48000,
    secondary_audio_codec: null,
    secondary_audio_channel: null,
    secondary_audio_sampling_rate: null,
    cm_sections: null,
    cm_analysis_version: null,
    thumbnail_info: null,
    created_at: '2000-01-01T00:00:00+09:00',
    updated_at: '2000-01-01T00:00:00+09:00',
};

/** 録画番組情報を表すインターフェース */
export interface IRecordedProgram {
    id: number;
    recorded_video: IRecordedVideo;
    recording_start_margin: number;
    recording_end_margin: number;
    is_partially_recorded: boolean;
    channel: IChannel | null;
    network_id: number | null;
    service_id: number | null;
    event_id: number | null;
    series_id: number | null;
    series_broadcast_period_id: number | null;
    title: string;
    series_title: string | null;
    episode_number: string | null;
    subtitle: string | null;
    description: string;
    detail: { [key: string]: string };
    start_time: string;
    end_time: string;
    duration: number;
    is_free: boolean;
    genres: { major: string; middle: string; }[];
    primary_audio_type: string;
    primary_audio_language: string;
    secondary_audio_type: string | null;
    secondary_audio_language: string | null;
    created_at: string;
    updated_at: string;
}

/** 録画番組情報を表すインターフェースのデフォルト値 */
export const IRecordedProgramDefault: IRecordedProgram = {
    id: -1,
    recorded_video: IRecordedVideoDefault,
    recording_start_margin: 0,
    recording_end_margin: 0,
    is_partially_recorded: false,
    channel: null,
    network_id: null,
    service_id: null,
    event_id: null,
    series_id: null,
    series_broadcast_period_id: null,
    title: '取得中…',
    series_title: null,
    episode_number: null,
    subtitle: null,
    description: '取得中…',
    detail: {},
    start_time: '2000-01-01T00:00:00+09:00',
    end_time: '2000-01-01T00:00:00+09:00',
    duration: 0,
    is_free: true,
    genres: [],
    primary_audio_type: '2/0モード(ステレオ)',
    primary_audio_language: '日本語',
    secondary_audio_type: null,
    secondary_audio_language: null,
    created_at: '2000-01-01T00:00:00+09:00',
    updated_at: '2000-01-01T00:00:00+09:00',
};

/** 録画番組情報リストを表すインターフェース */
export interface IRecordedPrograms {
    total: number;
    recorded_programs: IRecordedProgram[];
}

/** 過去ログコメントを表すインターフェース */
export interface IJikkyoComment {
    time: number;
    type: 'top' | 'right' | 'bottom';
    size: 'big' | 'medium' | 'small';
    color: string;
    author: string;
    text: string;
}

/** 過去ログコメントのリストを表すインターフェース */
export interface IJikkyoComments {
    is_success: boolean;
    comments: IJikkyoComment[];
    detail: string;
}


class Videos {

    /**
     * 録画番組一覧を取得する
     * @param order ソート順序 ('desc' or 'asc' or 'ids')
     * @param page ページ番号
     * @param ids 録画番組の ID のリスト
     * @returns 録画番組一覧情報 or 録画番組一覧情報の取得に失敗した場合は null
     */
    static async fetchVideos(order: 'desc' | 'asc' | 'ids' = 'desc', page: number = 1, ids: number[] | null = null): Promise<IRecordedPrograms | null> {

        // API リクエストを実行
        const response = await APIClient.get<IRecordedPrograms>('/videos', {
            params: {
                order,
                page,
                ids,
            },
            // 録画番組の ID のリストを FastAPI が受け付ける &ids=1&ids=2&ids=3&... の形式にエンコードする
            // ref: https://github.com/axios/axios/issues/5058#issuecomment-1272107602
            paramsSerializer: {
                indexes: null,
            },
        });

        // エラー処理
        if (response.type === 'error') {
            APIClient.showGenericError(response, '録画番組一覧を取得できませんでした。');
            return null;
        }

        return response.data;
    }


    /**
     * 録画番組を検索する
     * @param query 検索キーワード
     * @param order ソート順序 ('desc' or 'asc')
     * @param page ページ番号
     * @returns 検索結果の録画番組一覧情報 or 検索に失敗した場合は null
     */
    static async searchVideos(query: string, order: 'desc' | 'asc' = 'desc', page: number = 1): Promise<IRecordedPrograms | null> {

        // API リクエストを実行
        const response = await APIClient.get<IRecordedPrograms>('/videos/search', {
            params: {
                query,
                order,
                page,
            },
        });

        // エラー処理
        if (response.type === 'error') {
            APIClient.showGenericError(response, '録画番組の検索に失敗しました。');
            return null;
        }

        return response.data;
    }


    /**
     * 録画番組情報を取得する
     * @param video_id 録画番組の ID
     * @returns 録画番組情報 or 録画番組情報の取得に失敗した場合は null
     */
    static async fetchVideo(video_id: number): Promise<IRecordedProgram | null> {

        // API リクエストを実行
        const response = await APIClient.get<IRecordedProgram>(`/videos/${video_id}`);

        // エラー処理
        if (response.type === 'error') {
            APIClient.showGenericError(response, '録画番組情報を取得できませんでした。');
            return null;
        }

        return response.data;
    }


    /**
     * 録画番組の放送中に投稿されたニコニコ実況の過去ログコメントを取得する
     * @param video_id 録画番組の ID
     * @returns 過去ログコメントのリスト
     */
    static async fetchVideoJikkyoComments(video_id: number): Promise<IJikkyoComments> {

        // API リクエストを実行
        const response = await APIClient.get<IJikkyoComments>(`/videos/${video_id}/jikkyo`);

        // エラー処理
        if (response.type === 'error') {
            APIClient.showGenericError(response, '過去ログコメントを取得できませんでした。');
            return {
                is_success: false,
                comments: [],
                detail: '過去ログコメントを取得できませんでした。',
            };
        }

        // ミュート対象のコメントを除外して返す
        response.data.comments = response.data.comments.filter((comment) => {
            return CommentUtils.isMutedComment(comment.text, comment.author, comment.color, comment.type, comment.size) === false;
        });
        return response.data;
    }


    /**
     * 録画番組のメタデータを再解析する
     * @param video_id 録画番組の ID
     * @returns メタデータ再解析に成功した場合は true
     */
    static async reanalyzeVideo(video_id: number): Promise<boolean> {

        // API リクエストを実行
        const response = await APIClient.post(`/videos/${video_id}/reanalyze`, undefined, {
            // 数分以上かかるのでタイムアウトを 10 分に設定
            timeout: 10 * 60 * 1000,
        });

        // エラー処理
        if (response.type === 'error') {
            switch (response.data.detail) {
                default:
                    APIClient.showGenericError(response, 'メタデータの再解析に失敗しました。');
                    break;
            }
            return false;
        }

        return true;
    }


    /**
     * 録画番組の代表サムネイルの URL を返す
     * 代表サムネイルは30日間キャッシュされるので、サムネイルを作り直すたびに単調増加する revision の値を URL に付加する
     * @param program 録画番組
     * @returns 代表サムネイルの URL
     */
    static getThumbnailURL(program: IRecordedProgram): string {
        const revision = program.recorded_video.thumbnail_info?.representative.revision;
        const query = revision !== undefined ? `?revision=${revision}` : '';
        return `${Utils.api_base_url}/videos/${program.id}/thumbnail${query}`;
    }


    /**
     * キャプチャの画像を、録画番組の代表サムネイルにする
     * @param video_id 録画番組の ID
     * @param capture_id 代表サムネイルにするキャプチャの ID (その録画番組と同じ番組で撮ったもの)
     * @returns 設定に成功した場合は true
     */
    static async updateThumbnailFromCapture(video_id: number, capture_id: number): Promise<boolean> {

        // API リクエストを実行
        const response = await APIClient.put(`/videos/${video_id}/thumbnail`, { capture_id });

        // エラー処理
        if (response.type === 'error') {
            APIClient.showGenericError(response, '録画番組のサムネイルを変更できませんでした。');
            return false;
        }

        return true;
    }


    /**
     * 録画番組のサムネイルを再生成する
     * @param video_id 録画番組の ID
     * @returns サムネイルの再生成に成功した場合は true
     */
    static async regenerateThumbnail(video_id: number): Promise<boolean> {

        // API リクエストを実行
        const response = await APIClient.post(`/videos/${video_id}/thumbnail/regenerate`, undefined, {
            // 数分以上かかるのでタイムアウトを 30 分に設定
            timeout: 30 * 60 * 1000,
        });

        // エラー処理
        if (response.type === 'error') {
            switch (response.data.detail) {
                default:
                    APIClient.showGenericError(response, 'サムネイルの再生成に失敗しました。');
                    break;
            }
            return false;
        }

        return true;
    }

    /**
     * 録画番組を削除する
     * @param video_id 録画番組の ID
     * @returns 削除に成功した場合は true
     */
    static async deleteVideo(video_id: number): Promise<boolean> {

        // API リクエストを実行
        const response = await APIClient.delete(`/videos/${video_id}`);

        // エラー処理
        if (response.type === 'error') {
            switch (response.data.detail) {
                default:
                    APIClient.showGenericError(response, '録画ファイルの削除に失敗しました。');
                    break;
            }
            return false;
        }

        return true;
    }

    /**
     * [改造] 録画フォルダ直下のサブフォルダ一覧を取得する (空のフォルダも含む・管理者のみ)
     * @returns フォルダ名の一覧。失敗した場合は null
     */
    static async fetchFolders(): Promise<{ name: string; path: string }[] | null> {

        const response = await APIClient.get<{ folders: { name: string; path: string }[] }>('/videos/folders');

        if (response.type === 'error') {
            APIClient.showGenericError(response, 'フォルダ一覧の取得に失敗しました。');
            return null;
        }

        return response.data.folders;
    }


    /**
     * [改造] 録画ファイルを録画フォルダ直下の指定フォルダへ移動する (なければ作成・管理者のみ)
     * 録画番組の ID・メタデータ・サムネイルはそのまま引き継がれる
     * @param video_id 録画番組の ID
     * @param folder 移動先フォルダ名 (1 階層のみ)
     * @returns 移動に成功した場合は null 、失敗した場合はエラーメッセージ
     */
    static async moveVideo(video_id: number, folder: string): Promise<string | null> {

        const response = await APIClient.post(`/videos/${video_id}/move`, { folder });

        if (response.type === 'error') {
            const detail = response.data.detail;
            return typeof detail === 'string' && detail !== '' ? detail : '移動に失敗しました。';
        }

        return null;
    }

    /**
     * [改造] moveVideo() と同じ移動を行い、移動先に同名のファイルがあったためファイル名が変わったかどうかも返す
     * @returns error が null なら成功 (renamed が true ならファイル名の末尾に -(1) などが付いた)
     */
    static async moveVideoDetailed(video_id: number, folder: string): Promise<{ error: string | null; renamed: boolean }> {

        const response = await APIClient.post<{ id: number; old_path: string; new_path: string }>(`/videos/${video_id}/move`, { folder });

        if (response.type === 'error') {
            const detail = response.data.detail;
            return { error: typeof detail === 'string' && detail !== '' ? detail : '移動に失敗しました。', renamed: false };
        }

        const baseName = (path: string): string => path.slice(Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\')) + 1);
        return { error: null, renamed: baseName(response.data.old_path) !== baseName(response.data.new_path) };
    }


    /**
     * [改造] 録画フォルダ直下に空のフォルダを作成する (管理者のみ)
     * @param folder 作成するフォルダ名
     * @returns 作成したフォルダのフルパス、またはエラーメッセージ
     */
    static async createFolder(folder: string): Promise<{ path: string | null; error: string | null }> {

        const response = await APIClient.post<{ name: string; path: string }>('/videos/folders', { folder });

        if (response.type === 'error') {
            const detail = response.data.detail;
            return { path: null, error: typeof detail === 'string' && detail !== '' ? detail : 'フォルダを作成できませんでした。' };
        }

        return { path: response.data.path, error: null };
    }


    /**
     * [改造] 録画フォルダ直下のフォルダの名前を変更する (管理者のみ・中の録画の ID は維持される)
     * @param folder 変更前のフォルダ名
     * @param new_folder 変更後のフォルダ名
     * @returns 変更後のフォルダのフルパス、またはエラーメッセージ
     */
    static async renameFolder(folder: string, new_folder: string): Promise<{ path: string | null; error: string | null }> {

        const response = await APIClient.post<{ name: string; path: string }>('/videos/folders/rename', { folder, new_folder });

        if (response.type === 'error') {
            const detail = response.data.detail;
            return { path: null, error: typeof detail === 'string' && detail !== '' ? detail : 'フォルダ名を変更できませんでした。' };
        }

        return { path: response.data.path, error: null };
    }


    /**
     * [改造] 録画フォルダ直下の空のフォルダを削除する (管理者のみ)
     * @param folder 削除するフォルダ名
     * @returns 成功した場合は null 、失敗した場合はエラーメッセージ
     */
    static async deleteFolder(folder: string): Promise<string | null> {

        const response = await APIClient.post('/videos/folders/delete', { folder });

        if (response.type === 'error') {
            const detail = response.data.detail;
            return typeof detail === 'string' && detail !== '' ? detail : 'フォルダを削除できませんでした。';
        }

        return null;
    }


    /**
     * [改造] 動画取り込みジョブの一覧を取得する (管理者のみ)
     * @returns ジョブの一覧。失敗した場合は null
     */
    static async fetchImports(): Promise<IVideoImportJob[] | null> {

        const response = await APIClient.get<{ jobs: IVideoImportJob[] }>('/videos/imports');

        if (response.type === 'error') {
            return null;
        }

        return response.data.jobs;
    }


    /**
     * [改造] 動画の取り込みジョブを作成する (管理者のみ)
     * @returns 作成したジョブ、またはエラーメッセージ
     */
    static async createImport(params: {
        filename: string;
        size: number;
        folder: string;
        title: string;
        start_date: string | null;
        quality: 'quality' | 'fast';
    }): Promise<{ job: IVideoImportJob | null; error: string | null }> {

        const response = await APIClient.post<IVideoImportJob>('/videos/imports', params);

        if (response.type === 'error') {
            const detail = response.data.detail;
            return { job: null, error: typeof detail === 'string' && detail !== '' ? detail : '取り込みを開始できませんでした。' };
        }

        return { job: response.data, error: null };
    }


    /**
     * [改造] 動画データの一部を送信する (管理者のみ)
     * @returns 更新されたジョブ、またはエラー (status が 409 なら位置のずれ・404 ならジョブが消えている)
     */
    static async uploadImportChunk(
        import_id: string, offset: number, chunk: Blob, onProgress?: (loaded: number) => void,
    ): Promise<{ job: IVideoImportJob | null; error: string | null; status: number }> {

        const response = await APIClient.put<IVideoImportJob>(`/videos/imports/${import_id}/chunk?offset=${offset}`, chunk, {
            headers: { 'Content-Type': 'application/octet-stream' },
            timeout: 10 * 60 * 1000,
            onUploadProgress: (event) => onProgress?.(event.loaded),
        });

        if (response.type === 'error') {
            const detail = response.data?.detail;
            return {
                job: null,
                error: typeof detail === 'string' && detail !== '' ? detail : '送信に失敗しました。',
                status: response.status,
            };
        }

        return { job: response.data, error: null, status: response.status };
    }


    /**
     * [改造] 動画データの送信完了を通知する (管理者のみ)
     * @returns 成功した場合は null 、失敗した場合はエラーメッセージ
     */
    static async completeImport(import_id: string): Promise<string | null> {

        const response = await APIClient.post(`/videos/imports/${import_id}/complete`);

        if (response.type === 'error') {
            const detail = response.data.detail;
            return typeof detail === 'string' && detail !== '' ? detail : '完了の通知に失敗しました。';
        }

        return null;
    }


    /**
     * [改造] 動画の取り込みジョブを取り消す・一覧から消す (管理者のみ)
     * @returns 成功した場合は null 、失敗した場合はエラーメッセージ
     */
    static async deleteImport(import_id: string): Promise<string | null> {

        const response = await APIClient.delete(`/videos/imports/${import_id}`);

        if (response.type === 'error') {
            const detail = response.data.detail;
            return typeof detail === 'string' && detail !== '' ? detail : '取り消しに失敗しました。';
        }

        return null;
    }
}

export default Videos;
