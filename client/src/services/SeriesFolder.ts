import Videos, { IRecordedProgram } from '@/services/Videos';


// 録画番組の全件キャッシュ (視聴画面のシリーズタブ用)
const CACHE_TTL_MS = 5 * 60 * 1000;
let cache: { programs: IRecordedProgram[]; fetched_at: number; } | null = null;
let pending: Promise<IRecordedProgram[]> | null = null;

export const UNSORTED_NAME = '未分類 (フォルダ分けなし)';

/** 録画ファイルの置き場所 (フォルダのフルパス) */
export function dirOf(program: IRecordedProgram): string {
    const path = program.recorded_video.file_path;
    const index = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    return index >= 0 ? path.slice(0, index) : '';
}

function baseName(dir: string): string {
    const index = Math.max(dir.lastIndexOf('/'), dir.lastIndexOf('\\'));
    return index >= 0 ? dir.slice(index + 1) : dir;
}

/** 全ページ分の録画番組を取得する (5 分間キャッシュ) */
export async function fetchAllPrograms(force: boolean = false): Promise<IRecordedProgram[]> {
    if (!force && cache !== null && Date.now() - cache.fetched_at < CACHE_TTL_MS) {
        return cache.programs;
    }
    if (pending !== null) return pending;
    pending = (async () => {
        try {
            const all: IRecordedProgram[] = [];
            let page = 1;
            while (true) {
                const result = await Videos.fetchVideos('desc', page);
                if (result === null) throw new Error('fetchVideos failed');
                if (result.recorded_programs.length === 0) break;
                all.push(...result.recorded_programs);
                if (all.length >= result.total) break;
                page++;
            }
            cache = { programs: all, fetched_at: Date.now() };
            return all;
        } finally {
            pending = null;
        }
    })();
    return pending;
}

/** 指定した録画と同じシリーズ (= 同じフォルダ) の録画を放送日時の古い順で返す */
export function getSeriesOf(all: IRecordedProgram[], current: IRecordedProgram): { name: string; programs: IRecordedProgram[]; } {
    const dirs = [...new Set(all.map(dirOf))];
    // 他のフォルダの親になっているフォルダは録画フォルダ本体 (= 直下に置かれたファイル) とみなす
    const roots = new Set(dirs.filter(d => dirs.some(o => o !== d && (o.startsWith(d + '/') || o.startsWith(d + '\\')))));
    const current_dir = dirOf(current);
    const is_unsorted = roots.has(current_dir);
    const programs = all.filter(p => {
        const dir = dirOf(p);
        return is_unsorted ? roots.has(dir) : dir === current_dir;
    });
    programs.sort((a, b) => a.start_time.localeCompare(b.start_time));
    return { name: is_unsorted ? UNSORTED_NAME : baseName(current_dir), programs };
}
