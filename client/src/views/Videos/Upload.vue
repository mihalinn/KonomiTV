<template>
    <!-- [改造] ビデオ追加ページ (動画ファイルのアップロード取り込み) -->
    <div class="route-container">
        <HeaderBar />
        <main>
            <Navigation />
            <div class="upload-container-wrapper">
                <SPHeaderBar />
                <div class="upload-container">
                    <Breadcrumbs :crumbs="breadcrumbs" />
                    <h2 class="upload-container__title">ビデオ追加</h2>
                    <div class="upload-container__notice" v-if="userStore.user !== null && !userStore.user.is_admin">
                        このページは管理者アカウントでのみ使えます。
                    </div>
        <v-card class="upload-card" elevation="0">
            <v-card-text class="pt-4 pb-0">
                <div class="text-body-2 text-text-darken-1 mb-3">
                    MP4 や WebM などの動画を、録画番組として追加します。KonomiTV で再生できない形式 (VP9 / AV1 / Opus など) は、サーバーで自動的に H.264 + AAC の MP4 に変換されます。
                    追加先フォルダは下で決められます。(空のままなら、ファイル名から自動で決まります)
                    アップロード中はこのページを開いたままにしてください。(変換が始まったら閉じても大丈夫です)
                </div>

                <datalist id="import-folder-list">
                    <option v-for="name in existingFolders" :key="name" :value="name"></option>
                </datalist>
                <v-text-field class="mb-4" v-model="defaultFolder" label="追加先フォルダ (空なら自動・なければ新規作成)" list="import-folder-list"
                    variant="outlined" density="comfortable" hide-details="auto" clearable :counter="60"
                    :error-messages="defaultFolderError"
                    hint="ファイルを選ぶ前に決めておくと、選んだファイルすべてに入ります。ファイルごとに直すこともできます。" persistent-hint />

                <input ref="fileInput" type="file" multiple hidden
                    accept=".mp4,.m4v,.mkv,.webm,.ts,.m2ts,.m2t,.mts,.mov,.avi,.flv,.wmv,.mpg,.mpeg,video/*"
                    @change="onFilesSelected($event, false)">
                <input ref="fileInputAny" type="file" multiple hidden
                    @change="onFilesSelected($event, true)">
                <template v-if="isMobile">
                    <div class="d-flex flex-wrap" style="gap: 8px;">
                        <v-btn variant="tonal" color="primary" @click="fileInputAny?.click()">
                            <Icon icon="fluent:folder-open-20-regular" width="18px" height="18px" />
                            <span class="ml-1">ファイルアプリから選ぶ</span>
                        </v-btn>
                        <v-btn variant="tonal" color="primary" @click="fileInput?.click()">
                            <Icon icon="fluent:image-multiple-20-regular" width="18px" height="18px" />
                            <span class="ml-1">アルバムから選ぶ</span>
                        </v-btn>
                    </div>
                    <div v-if="isIOS" class="text-caption text-text-darken-1 mt-2">
                        iPhone / iPad では、表示されたメニューの「ファイルを選択」を押すとファイルアプリが開きます。
                    </div>
                </template>
                <v-btn v-else variant="tonal" color="primary" @click="fileInput?.click()">
                    <Icon icon="fluent:document-add-20-regular" width="18px" height="18px" />
                    <span class="ml-1">ファイルを選ぶ</span>
                </v-btn>

                <template v-if="items.length > 0">
                    <v-select class="mt-5" v-model="quality" label="変換方式 (変換が必要なファイルのみ)" variant="outlined" density="comfortable"
                        hint="画質はどちらも同じです。違いは変換にかかる時間だけです。" persistent-hint
                        :items="qualityItems" item-title="title" item-value="value" />
                    <div class="import-items mt-5">
                        <div class="import-items__label">
                            追加するファイル ({{items.length}}件) ・ 追加先フォルダ・タイトル・放送日は直せます
                            <button type="button" class="import-items__unify" v-if="items.length > 1" @click="unifyFolders">
                                全部を先頭のファイルと同じフォルダにする
                            </button>
                        </div>
                        <div class="import-item" v-for="item in items" :key="item.key">
                            <div class="import-item__file">
                                {{item.file.name}} ({{formatSize(item.file.size)}})
                                <button type="button" class="import-item__remove" @click="removeItem(item.key)" aria-label="一覧から外す">
                                    <Icon icon="fluent:dismiss-20-regular" width="16px" height="16px" />
                                </button>
                            </div>
                            <div class="import-item__fields">
                                <v-text-field class="import-item__title" v-model="item.title" label="タイトル" variant="outlined" density="compact"
                                    hide-details="auto" :error-messages="titleError(item)" />
                                <v-text-field class="import-item__date" v-model="item.date" label="放送日" type="date" variant="outlined"
                                    density="compact" hide-details />
                                <v-text-field class="import-item__folder" v-model="item.folder" label="追加先フォルダ (なければ新規作成)" list="import-folder-list"
                                    variant="outlined" density="compact" hide-details="auto" clearable :counter="60"
                                    :error-messages="folderError(item)" :hint="folderHint(item)" persistent-hint />
                            </div>
                            <div class="import-item__error" v-if="item.error">{{item.error}}</div>
                        </div>
                    </div>
                </template>

                <div class="import-jobs mt-6" v-if="jobs.length > 0">
                    <div class="import-items__label">取り込み状況</div>
                    <div class="import-job" v-for="job in jobs" :key="job.id">
                        <div class="import-job__head">
                            <div class="import-job__title">{{job.title}}</div>
                            <div class="import-job__folder">{{job.folder}}</div>
                            <button type="button" class="import-item__remove" @click="removeJob(job)"
                                :aria-label="job.status === 'done' || job.status === 'failed' ? '一覧から消す' : '取り消す'">
                                <Icon icon="fluent:dismiss-20-regular" width="16px" height="16px" />
                            </button>
                        </div>
                        <div class="import-job__status" :class="{'import-job__status--error': job.status === 'failed'}">
                            {{jobStatusText(job)}}
                        </div>
                        <v-progress-linear v-if="job.status === 'uploading' || job.status === 'converting'" class="mt-1"
                            :model-value="jobPercent(job)" color="primary" height="6" rounded />
                    </div>
                </div>
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn class="px-3" color="primary" variant="flat" :disabled="!canStart || !isAdmin" @click="startUpload">
                    <Icon icon="fluent:arrow-upload-20-regular" width="18px" height="18px" />
                    <span class="ml-1">{{items.length}}件をアップロードして追加</span>
                </v-btn>
            </v-card-actions>
        </v-card>
                </div>
            </div>
        </main>
    </div>
</template>
<script lang="ts" setup>

import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { onBeforeRouteLeave, useRoute } from 'vue-router';

import Breadcrumbs from '@/components/Breadcrumbs.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import Message from '@/message';
import { makeSeriesTitle } from '@/services/SeriesTitle';
import Videos, { IVideoImportJob } from '@/services/Videos';
import useUserStore from '@/stores/UserStore';

const route = useRoute();
const userStore = useUserStore();
const isAdmin = computed(() => userStore.user?.is_admin === true);

const breadcrumbs = [
    { name: 'ホーム', path: '/' },
    { name: 'ビデオ追加', path: '/videos/upload', disabled: true },
];

// 取り込みが完了したとき (このページでは一覧の再読み込みは不要)
const emit = (_event: 'imported'): void => {};

interface IImportItem {
    key: number;
    file: File;
    title: string;
    date: string;
    folder: string;
    error: string;
}

const CHUNK_SIZE = 8 * 1024 * 1024;
const MAX_TITLE_BYTES = 200;

const fileInput = ref<HTMLInputElement | null>(null);
const fileInputAny = ref<HTMLInputElement | null>(null);
const userAgent = navigator.userAgent;
const isIOS = /iPhone|iPad|iPod/.test(userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
const isMobile = isIOS || /Android/.test(userAgent) || window.matchMedia('(pointer: coarse)').matches;
const VIDEO_EXTENSIONS = ['mp4', 'm4v', 'mkv', 'webm', 'ts', 'm2ts', 'm2t', 'mts', 'mov', 'avi', 'flv', 'wmv', 'mpg', 'mpeg'];
const items = ref<IImportItem[]>([]);
const jobs = ref<IVideoImportJob[]>([]);
const existingFolders = ref<string[]>([]);
const defaultFolder = ref<string | null>('');
const quality = ref<'quality' | 'fast'>('quality');
const uploading = ref(false);
let nextKey = 1;
// このページがアップロードを続けているジョブの ID
const activeUploads = new Set<string>();

const qualityItems = [
    { title: '標準 (CPU・約7分)', value: 'quality' },
    { title: '高速 (GPU・約2分)', value: 'fast' },
];

// ---- ファイル名 → タイトルの整形 ----

const FULLWIDTH_REPLACEMENTS: Record<string, string> = {
    '\\': '＼', '/': '／', ':': '：', '*': '＊', '?': '？', '"': '”', '<': '＜', '>': '＞', '|': '｜',
};
const INVALID_CHARS = '\\/:*?"<>|';
const isInvalidChar = (c: string): boolean => INVALID_CHARS.includes(c) || c.charCodeAt(0) < 32 || c.charCodeAt(0) === 127;

const makeTitle = (filename: string): string => {
    let t = filename.replace(/\.[^.]+$/, '').normalize('NFC');
    // YouTube の「チャンネル名 ⧸ - 」のような前置きを外す
    if (t.includes('⧸')) t = t.replace(/^[^⧸]*⧸\s*-?\s*/, '');
    t = t.replace(/【公式】/g, '').replace(/\s*(期間限定)?(本編)?配信\s*$/, '');
    // 先頭の「作品名」の鉤括弧を外す
    t = t.replace(/^\s*「([^」]+)」\s*/, '$1 ');
    return sanitizeName(t);
};

// ファイル名・フォルダ名に使えない文字を置き換え、前後の空白とドットを取り除く
const sanitizeName = (name: string): string => {
    let t = Array.from(name).map(c => FULLWIDTH_REPLACEMENTS[c] ?? (isInvalidChar(c) ? ' ' : c)).join('');
    t = t.replace(/\s+/g, ' ').trim().replace(/\.+$/, '').trim();
    return t;
};

// ファイル名から追加先フォルダ名を決める (先頭の「作品名」→ なければ自動フォルダ分けと同じ規則)
const guessFolder = (filename: string, title: string): string => {
    let t = filename.replace(/\.[^.]+$/, '').normalize('NFC');
    if (t.includes('⧸')) t = t.replace(/^[^⧸]*⧸\s*-?\s*/, '');
    t = t.replace(/【公式】/g, '').replace(/^\s*第\d+話\s*[～~〜]\s*第\d+話\s*/, '').trim();
    const quoted = /^\s*「([^」]+)」/.exec(t);
    const name = sanitizeName(quoted ? quoted[1] : makeSeriesTitle(title));
    return name.slice(0, 60).trim();
};

// 近い名前の既存フォルダがあればそれを使う (完全一致、または一方が他方の先頭と一致)
const matchExistingFolder = (name: string): string => {
    const q = normalizeForSearch(name);
    if (q === '') return name;
    let best: string | null = null;
    let bestRank = 99;
    for (const folder of existingFolders.value) {
        const n = normalizeForSearch(folder);
        if (n === '') continue;
        let rank = 99;
        if (n === q) rank = 0;
        else if (n.length >= 4 && q.length >= 4 && (n.startsWith(q) || q.startsWith(n))) rank = 1;
        if (rank < bestRank) {
            best = folder;
            bestRank = rank;
        }
    }
    return best ?? name;
};

const pad2 = (n: number): string => String(n).padStart(2, '0');
const toDateInput = (time: number): string => {
    const d = new Date(time);
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
};

const formatSize = (size: number): string => size >= 1024 * 1024 * 1024
    ? `${(size / 1024 / 1024 / 1024).toFixed(2)}GB` : `${Math.round(size / 1024 / 1024)}MB`;

const onFilesSelected = (event: Event, checkExtension: boolean) => {
    const input = event.target as HTMLInputElement;
    let files = Array.from(input.files ?? []);
    input.value = '';
    if (checkExtension) {
        const accepted = files.filter(file => {
            const ext = file.name.includes('.') ? file.name.split('.').pop()!.toLowerCase() : '';
            return VIDEO_EXTENSIONS.includes(ext) || file.type.startsWith('video/');
        });
        if (accepted.length < files.length) {
            Message.warning(`対応していない形式のファイルは追加しませんでした。(${files.length - accepted.length}件)`);
        }
        files = accepted;
    }
    files.sort((a, b) => a.name.localeCompare(b.name, 'ja', { numeric: true }));
    for (const file of files) {
        const title = makeTitle(file.name);
        const preset = (defaultFolder.value ?? '').trim();
        const folder = preset !== '' ? preset : matchExistingFolder(guessFolder(file.name, title));
        items.value.push({ key: nextKey++, file, title, date: toDateInput(file.lastModified), folder, error: '' });
    }
};

const removeItem = (key: number) => {
    items.value = items.value.filter(item => item.key !== key);
};

// ---- 追加先フォルダ ----

const folderError = (item: IImportItem): string => {
    const name = item.folder.trim();
    if (name === '') return '追加先フォルダを入力してください。';
    if (name.length > 60) return '60文字までです。';
    if (Array.from(name).some(isInvalidChar)) return '使えない文字が含まれています。(\\ / : * ? " < > |)';
    if (name === '.' || name === '..' || name.endsWith('.')) return '末尾にドットは使えません。';
    return '';
};

const folderHint = (item: IImportItem): string => {
    const name = item.folder.trim();
    if (name === '' || folderError(item) !== '') return '';
    return existingFolders.value.includes(name) ? '既存のフォルダに追加します' : '新規作成します';
};

const unifyFolders = () => {
    if (items.value.length === 0) return;
    const folder = items.value[0].folder;
    for (const item of items.value) item.folder = folder;
};
const normalizeForSearch = (s: string): string => Array.from(s.normalize('NFKC').toLowerCase())
    .map(c => {
        const code = c.charCodeAt(0);
        return code >= 0x30a1 && code <= 0x30f6 ? String.fromCharCode(code - 0x60) : c;
    })
    .join('')
    .replace(/[\s・!?~〜]/g, '');

// ---- タイトルの検証 ----

const titleError = (item: IImportItem): string => {
    const title = item.title;
    if (title.trim() === '') return 'タイトルを入力してください。';
    if (title !== title.trim()) return '前後の空白は使えません。';
    if (Array.from(title).some(isInvalidChar)) return '使えない文字が含まれています。(\\ / : * ? " < > |)';
    if (title.endsWith('.')) return '末尾にドットは使えません。';
    if (new TextEncoder().encode(title).length > MAX_TITLE_BYTES) return 'タイトルが長すぎます。';
    if (items.value.some(other => other.key !== item.key && other.title === title)) return '同じタイトルが他にもあります。';
    return '';
};

const canStart = computed(() => !uploading.value && items.value.length > 0
    && items.value.every(item => folderError(item) === '' && titleError(item) === '' && item.date !== ''));

// ---- アップロード ----

const sleep = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));

const uploadItem = async (item: IImportItem, index: number): Promise<boolean> => {
    // 同じ日付でも並び順が保たれるよう、選んだ順に分単位でずらす
    const minutes = index;
    const start_date = `${item.date}T${pad2(Math.floor(minutes / 60))}:${pad2(minutes % 60)}`;
    const created = await Videos.createImport({
        filename: item.file.name,
        size: item.file.size,
        folder: item.folder.trim(),
        title: item.title,
        start_date,
        quality: quality.value,
    });
    if (created.job === null) {
        item.error = created.error ?? '取り込みを開始できませんでした。';
        return false;
    }
    const job = created.job;
    activeUploads.add(job.id);
    // 作成できたファイルは「追加するファイル」から「取り込み状況」に移る
    items.value = items.value.filter(other => other.key !== item.key);
    await refreshJobs();

    try {
        let offset = 0;
        let failures = 0;
        while (offset < item.file.size) {
            const end = Math.min(offset + CHUNK_SIZE, item.file.size);
            const result = await Videos.uploadImportChunk(job.id, offset, item.file.slice(offset, end));
            if (result.job !== null) {
                offset = end;
                failures = 0;
                const local = jobs.value.find(j => j.id === job.id);
                if (local) local.received = result.job.received;
                continue;
            }
            if (result.status === 404) return false;
            if (result.status === 409) {
                // サーバーが受け取った位置とずれた場合は、サーバー側の受信済み位置から再開する
                const latest = (await Videos.fetchImports())?.find(j => j.id === job.id);
                if (!latest || latest.status !== 'uploading') return false;
                offset = latest.received;
                continue;
            }
            failures++;
            if (failures >= 5) {
                Message.error(`「${job.title}」のアップロードに失敗しました。(${result.error})`);
                return false;
            }
            await sleep(2000 * failures);
        }
        const error = await Videos.completeImport(job.id);
        if (error !== null) {
            Message.error(`「${job.title}」: ${error}`);
            return false;
        }
        return true;
    } finally {
        activeUploads.delete(job.id);
        await refreshJobs();
    }
};

const startUpload = async () => {
    if (!canStart.value) return;
    uploading.value = true;
    window.addEventListener('beforeunload', onBeforeUnload);
    const targets = [...items.value];
    let failed = 0;
    for (let i = 0; i < targets.length; i++) {
        const ok = await uploadItem(targets[i], i);
        if (!ok) failed++;
    }
    window.removeEventListener('beforeunload', onBeforeUnload);
    uploading.value = false;
    if (failed === 0) {
        Message.success('アップロードが完了しました。変換が終わると番組一覧に追加されます。');
    } else {
        Message.warning(`${failed}件はアップロードできませんでした。`);
    }
};

const onBeforeUnload = (event: BeforeUnloadEvent) => {
    event.preventDefault();
    event.returnValue = '';
};

// ---- 取り込み状況 ----

const jobPercent = (job: IVideoImportJob): number => {
    if (job.status === 'uploading') return job.size > 0 ? Math.floor(job.received / job.size * 100) : 0;
    return job.progress;
};

const jobStatusText = (job: IVideoImportJob): string => {
    switch (job.status) {
        case 'uploading':
            return activeUploads.has(job.id)
                ? `アップロード中 ${jobPercent(job)}% (${formatSize(job.received)} / ${formatSize(job.size)})`
                : `アップロード中断 (${jobPercent(job)}%) ・ この画面からは再開できません。取り消してやり直してください。`;
        case 'queued':
            return '変換待ち';
        case 'converting':
            return `${job.message || '変換中'} ${job.progress}%`;
        case 'done':
            return job.plan === 'copy' ? '追加しました (変換なし)' : '追加しました (変換済み)・一覧への反映に少し時間がかかることがあります';
        case 'failed':
            return `失敗: ${job.message}`;
    }
};

const refreshJobs = async () => {
    const latest = await Videos.fetchImports();
    if (latest === null) return;
    const previouslyDone = new Set(jobs.value.filter(j => j.status === 'done').map(j => j.id));
    jobs.value = latest;
    if (latest.some(j => j.status === 'done' && !previouslyDone.has(j.id))) {
        emit('imported');
    }
};

const removeJob = async (job: IVideoImportJob) => {
    const error = await Videos.deleteImport(job.id);
    if (error !== null) {
        Message.error(error);
        return;
    }
    activeUploads.delete(job.id);
    await refreshJobs();
};

const hasActiveJobs = computed(() => jobs.value.some(j => j.status !== 'done' && j.status !== 'failed'));

let timer: number | null = null;
const startPolling = () => {
    if (timer !== null) return;
    // このページを開いている間は常に状況を更新する
    timer = window.setInterval(() => {
        refreshJobs();
    }, 3000);
};

// 追加先フォルダ (ファイルを選ぶ前に決めておく値) の検証
const defaultFolderError = computed(() => {
    const name = (defaultFolder.value ?? '').trim();
    if (name === '') return '';
    if (name.length > 60) return '60文字までです。';
    if (Array.from(name).some(isInvalidChar)) return '使えない文字が含まれています。(\\ / : * ? " < > |)';
    if (name === '.' || name === '..' || name.endsWith('.')) return '末尾にドットは使えません。';
    return '';
});

onMounted(async () => {
    await userStore.fetchUser();
    // /videos/upload?folder=フォルダ名 で開くと、追加先フォルダにその名前が入る
    const q = route.query.folder;
    if (typeof q === 'string') defaultFolder.value = q;
    const folders = await Videos.fetchFolders();
    existingFolders.value = folders ? folders.map(f => f.name) : [];
    await refreshJobs();
    startPolling();
});

// アップロード中に別のページへ移ろうとしたら確認する (アップロードはこのページを開いている間だけ続く)
onBeforeRouteLeave(() => {
    if (uploading.value) {
        return window.confirm('アップロード中です。ページを移動すると、進み具合が見えなくなります。移動しますか？');
    }
    return true;
});

onBeforeUnmount(() => {
    if (timer !== null) window.clearInterval(timer);
    window.removeEventListener('beforeunload', onBeforeUnload);
});

</script>
<style lang="scss" scoped>

.upload-container-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
}

.upload-container {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    padding: 20px;
    margin: 0 auto;
    min-width: 0;
    max-width: 860px;
    @include smartphone-horizontal {
        padding: 16px 20px !important;
    }
    @include smartphone-horizontal-short {
        padding: 16px 16px !important;
    }
    @include smartphone-vertical {
        padding: 16px 8px !important;
        padding-top: 8px !important;
    }

    &__title {
        font-size: 24px;
        font-weight: 700;
        padding-top: 8px;
        padding-bottom: 16px;
        @include smartphone-vertical {
            font-size: 22px;
            padding: 0px 8px 12px;
        }
    }

    &__notice {
        margin-bottom: 12px;
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 14px;
        background: rgb(var(--v-theme-background-lighten-1));
        color: rgb(var(--v-theme-error));
    }
}

.upload-card {
    background: transparent !important;
}

.import-items {
    &__label {
        margin-bottom: 8px;
        font-size: 12px;
        font-weight: 700;
        color: rgb(var(--v-theme-text-darken-1));
    }
    &__unify {
        display: block;
        margin-top: 4px;
        padding: 0;
        border: none;
        background: transparent;
        font-size: 12px;
        font-weight: 700;
        cursor: pointer;
        color: rgb(var(--v-theme-primary));
        &:hover {
            text-decoration: underline;
        }
    }
}

.import-item {
    margin-bottom: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    background: rgb(var(--v-theme-background-lighten-1));
    &__file {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
        word-break: break-all;
    }
    &__remove {
        flex-shrink: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: transparent;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
    }
    &__fields {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    &__title {
        flex: 1 1 280px;
        min-width: 0;
    }
    &__date {
        flex: 0 0 170px;
    }
    &__folder {
        flex: 1 1 100%;
        min-width: 0;
    }
    &__error {
        margin-top: 6px;
        font-size: 12px;
        color: rgb(var(--v-theme-error));
        word-break: break-all;
    }
}

.import-job {
    margin-bottom: 10px;
    padding: 10px 12px;
    border-radius: 8px;
    background: rgb(var(--v-theme-background-lighten-1));
    &__head {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    &__title {
        flex: 1;
        min-width: 0;
        font-size: 14px;
        font-weight: 700;
        word-break: break-all;
    }
    &__folder {
        flex-shrink: 0;
        max-width: 40%;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
        word-break: break-all;
    }
    &__status {
        margin-top: 4px;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
        word-break: break-all;
        &--error {
            color: rgb(var(--v-theme-error));
        }
    }
}

</style>
