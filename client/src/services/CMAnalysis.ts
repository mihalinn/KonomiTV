
import Message from '@/message';
import APIClient from '@/services/APIClient';


/** CM 解析機能の状態を表すインターフェース */
export interface ICMAnalysisStatus {
    enabled: boolean;
    analyze_new_recordings: boolean;
    device: 'CPU' | 'GPU';
    threads: number;
    gpu_available: boolean;
    providers: string[];
    model_ready: boolean;
    model_downloadable: boolean;
    model_version: string;
    model_installed_version: string | null;
    model_update_available: boolean;
    model_download: {
        state: 'Idle' | 'Downloading' | 'Completed' | 'Failed';
        progress: number;
        message: string;
    };
    pending_count: number;
    running_count: number;
}

/** CM 解析設定を表すインターフェース */
export interface ICMAnalysisSettings {
    enabled: boolean;
    analyze_new_recordings: boolean;
    device: 'CPU' | 'GPU';
    threads: number;
}

/** CM 解析ジョブを表すインターフェース */
export interface ICMAnalysisJob {
    video_id: number;
    title: string;
    state: 'Pending' | 'Running' | 'Completed' | 'Failed' | 'Cancelled';
    stage: string;
    progress: number;
    message: string;
    cm_section_count: number | null;
}


class CMAnalysis {

    /**
     * CM 解析機能の状態を取得する
     * @param silent エラー時にエラーメッセージを表示しない (定期的な更新用)
     * @returns CM 解析機能の状態 or 取得に失敗した場合は null
     */
    static async fetchStatus(silent: boolean = false): Promise<ICMAnalysisStatus | null> {

        const response = await APIClient.get<ICMAnalysisStatus>('/cm-analysis/status');
        if (response.type === 'error') {
            if (!silent) {
                APIClient.showGenericError(response, 'CM 解析の状態を取得できませんでした。');
            }
            return null;
        }
        return response.data;
    }


    /**
     * CM 解析設定を更新する (サーバーの再起動なしですぐに反映される)
     * @param settings 更新する CM 解析設定
     * @returns 更新後の CM 解析機能の状態 or 更新に失敗した場合は null
     */
    static async updateSettings(settings: ICMAnalysisSettings): Promise<ICMAnalysisStatus | null> {

        const response = await APIClient.put<ICMAnalysisStatus>('/cm-analysis/settings', settings);
        if (response.type === 'error') {
            APIClient.showGenericError(response, 'CM 解析設定を更新できませんでした。');
            return null;
        }
        return response.data;
    }


    /**
     * CM 検出モデルのダウンロードを開始する
     * @returns ダウンロードの開始に成功したかどうか
     */
    static async downloadModel(): Promise<boolean> {

        const response = await APIClient.post('/cm-analysis/model/download');
        if (response.type === 'error') {
            APIClient.showGenericError(response, 'CM 検出モデルのダウンロードを開始できませんでした。');
            return false;
        }
        return true;
    }


    /**
     * CM 解析ジョブの一覧を取得する
     * @param silent エラー時にエラーメッセージを表示しない (定期的な更新用)
     * @returns CM 解析ジョブの一覧 or 取得に失敗した場合は null
     */
    static async fetchJobs(silent: boolean = false): Promise<ICMAnalysisJob[] | null> {

        const response = await APIClient.get<{jobs: ICMAnalysisJob[]}>('/cm-analysis/jobs');
        if (response.type === 'error') {
            if (!silent) {
                APIClient.showGenericError(response, 'CM 解析ジョブの一覧を取得できませんでした。');
            }
            return null;
        }
        return response.data.jobs;
    }


    /**
     * 録画ファイルを CM 解析キューに追加する
     * すでに CM 区間が解析済みでも、再度解析し直す
     * @param video_ids CM 解析する録画ファイル (RecordedVideo) の ID のリスト
     * @returns 新たにキューに追加された件数 or 追加に失敗した場合は null
     */
    static async enqueue(video_ids: number[]): Promise<number | null> {

        const response = await APIClient.post<number>('/cm-analysis/jobs', {video_ids});
        if (response.type === 'error') {
            // 機能が無効・モデル未配置の場合はサーバーが 400 を返す
            if (response.status === 400) {
                APIClient.showGenericError(response, 'CM 解析を開始できませんでした。設定の「CM 解析設定」で機能を有効にし、モデルを準備してください。');
            } else if (response.status === 403) {
                APIClient.showGenericError(response, 'CM 解析の実行には管理者権限が必要です。');
            } else {
                APIClient.showGenericError(response, 'CM 解析を開始できませんでした。');
            }
            return null;
        }
        return response.data;
    }



    /**
     * 指定した解析バージョンのうち、現在の AI と同じバージョンで解析済みのものの件数を返す
     * @param analysis_versions 録画ファイルごとの CM 解析バージョン
     * @returns 同じバージョンで解析済みの件数と、現在の AI のバージョン表記
     */
    static async countAnalyzedWithCurrentVersion(analysis_versions: (string | null)[]): Promise<{count: number; label: string}> {

        const status = await CMAnalysis.fetchStatus(true);
        if (status === null) {
            return {count: 0, label: ''};
        }
        const label = `AI ${status.model_version}`;
        return {count: analysis_versions.filter((version) => version === label).length, label};
    }


    /**
     * 録画ファイルを CM 解析キューに追加し、結果をメッセージで通知する (録画番組一覧の「CM 解析する」用)
     * @param video_ids CM 解析する録画ファイル (RecordedVideo) の ID のリスト
     */
    static async requestAnalysis(video_ids: number[]): Promise<void> {

        const added = await CMAnalysis.enqueue(video_ids);
        if (added === null) {
            return;
        }
        if (added === 0) {
            Message.show('選択した録画番組は、すでに CM 解析の順番待ち (または解析中) です。');
        } else {
            Message.success(
                `${added} 件の録画番組を CM 解析の順番待ちに追加しました。\n` +
                '進行状況は、設定の「CM 解析設定」で確認できます。'
            );
        }
    }


    /**
     * 待機中の CM 解析ジョブを取り消し、実行中のジョブには中断を要求する
     * @param video_id 取り消す録画ファイルの ID (省略するとすべて取り消す)
     * @param clear_finished 終了済みのジョブも一覧から消すか
     * @returns 成功したかどうか
     */
    static async cancel(video_id?: number, clear_finished: boolean = false): Promise<boolean> {

        const response = await APIClient.delete('/cm-analysis/jobs', {
            params: {
                video_id,
                clear_finished,
            },
        });
        if (response.type === 'error') {
            APIClient.showGenericError(response, 'CM 解析ジョブを取り消せませんでした。');
            return false;
        }
        return true;
    }
}

export default CMAnalysis;
