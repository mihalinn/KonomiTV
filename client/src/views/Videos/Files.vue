<template>
    <!-- [改造] ビデオ整理ページ (エクスプローラー風のフォルダ・ファイル管理) -->
    <div class="route-container">
        <HeaderBar />
        <main>
            <Navigation />
            <div class="files-wrapper">
                <SPHeaderBar />
                <div class="files">
                    <div class="files__head">
                        <h2 class="files__title">ビデオ整理</h2>
                        <span class="files__count" v-if="!is_loading">{{folders.length}}フォルダ / {{programs.length}}件</span>
                    </div>
                    <div class="files__notice" v-if="userStore.user !== null && !isAdmin">
                        このページの操作 (移動・フォルダ作成・削除など) は管理者アカウントでのみ使えます。
                    </div>

                    <!-- ツールバー -->
                    <div class="toolbar" v-if="isAdmin">
                        <v-btn class="toolbar__tree-button" variant="tonal" size="small" @click="showTree = !showTree">
                            <Icon icon="fluent:folder-20-regular" width="18px" height="18px" />
                            <span class="ml-1">フォルダ</span>
                        </v-btn>
                        <v-btn variant="tonal" color="primary" size="small" @click="openCreateDialog">
                            <Icon icon="fluent:folder-add-20-regular" width="18px" height="18px" />
                            <span class="ml-1">新規フォルダ</span>
                        </v-btn>
                        <v-btn variant="tonal" size="small" :disabled="currentKey === ROOT_KEY" @click="openRenameDialog">
                            <Icon icon="fluent:rename-20-regular" width="18px" height="18px" />
                            <span class="ml-1">名前を変更</span>
                        </v-btn>
                        <v-btn variant="tonal" size="small" :disabled="currentKey === ROOT_KEY || files.length > 0" @click="openDeleteFolderDialog">
                            <Icon icon="fluent:folder-prohibited-20-regular" width="18px" height="18px" />
                            <span class="ml-1">空のフォルダを削除</span>
                        </v-btn>
                        <v-btn variant="tonal" size="small" :disabled="busy" @click="reload">
                            <Icon icon="fluent:arrow-sync-20-regular" width="18px" height="18px" />
                            <span class="ml-1">更新</span>
                        </v-btn>
                        <v-btn variant="tonal" color="primary" size="small" :to="addPageLink">
                            <Icon icon="fluent:arrow-upload-20-regular" width="18px" height="18px" />
                            <span class="ml-1">ビデオ追加へ</span>
                        </v-btn>
                    </div>

                    <div class="explorer">
                        <!-- 左: フォルダ一覧 -->
                        <nav class="tree" :class="{'tree--open': showTree}" aria-label="フォルダ一覧">
                            <button type="button" class="tree__node" :class="{'tree__node--on': currentKey === ROOT_KEY, 'tree__node--drop': dropTarget === ROOT_KEY}"
                                @click="openFolder(ROOT_KEY)"
                                @dragover="onDragOver($event, ROOT_KEY)" @dragleave="onDragLeave(ROOT_KEY)" @drop="onDrop($event, ROOT_KEY)">
                                <Icon icon="fluent:folder-open-20-filled" width="20px" height="20px" />
                                <span class="tree__name">録画フォルダ (未分類)</span>
                                <span class="tree__count">{{rootPrograms.length}}</span>
                            </button>
                            <button type="button" v-for="folder in folders" :key="folder.key" class="tree__node tree__node--child"
                                :class="{'tree__node--on': currentKey === folder.key, 'tree__node--drop': dropTarget === folder.key}"
                                @click="openFolder(folder.key)"
                                @dragover="onDragOver($event, folder.key)" @dragleave="onDragLeave(folder.key)" @drop="onDrop($event, folder.key)">
                                <Icon :icon="currentKey === folder.key ? 'fluent:folder-open-20-regular' : 'fluent:folder-20-regular'" width="20px" height="20px" />
                                <span class="tree__name">{{folder.name}}</span>
                                <span class="tree__count">{{folder.programs.length}}</span>
                            </button>
                        </nav>

                        <!-- 右: 中身 -->
                        <section class="pane">
                            <div class="pane__path">
                                <button type="button" class="pane__crumb" :class="{'pane__crumb--drop': dropTarget === ROOT_KEY}" @click="openFolder(ROOT_KEY)"
                                    @dragover="onDragOver($event, ROOT_KEY)" @dragleave="onDragLeave(ROOT_KEY)" @drop="onDrop($event, ROOT_KEY)">録画フォルダ</button>
                                <template v-if="currentKey !== ROOT_KEY">
                                    <Icon icon="fluent:chevron-right-20-regular" width="16px" height="16px" />
                                    <span class="pane__crumb pane__crumb--current">{{currentName}}</span>
                                </template>
                                <span class="pane__summary">{{files.length}}件 ・ {{formatSize(filesTotalSize)}}</span>
                            </div>

                            <div class="pane__tools">
                                <v-text-field class="pane__search" v-model="searchText" placeholder="タイトル・ファイル名で絞り込み" variant="outlined"
                                    density="compact" hide-details clearable prepend-inner-icon="mdi-magnify" />
                                <v-select class="pane__sort" v-model="sortKey" :items="sortItems" item-title="title" item-value="value"
                                    variant="outlined" density="compact" hide-details />
                                <v-btn variant="text" size="small" class="pane__sort-order" @click="sortDesc = !sortDesc"
                                    :aria-label="sortDesc ? '降順' : '昇順'">
                                    <Icon :icon="sortDesc ? 'fluent:arrow-sort-down-20-regular' : 'fluent:arrow-sort-up-20-regular'" width="20px" height="20px" />
                                    <span class="ml-1">{{sortDesc ? '降順' : '昇順'}}</span>
                                </v-btn>
                            </div>

                            <div class="actions" v-if="isAdmin && files.length > 0">
                                <v-btn variant="text" size="small" @click="selectAll">すべて選択</v-btn>
                                <v-btn variant="text" size="small" :disabled="selectedIds.length === 0" @click="selectedIds = []">選択解除</v-btn>
                                <span class="actions__selected" v-if="selectedIds.length > 0">{{selectedIds.length}}件 選択中</span>
                                <v-btn class="ml-auto" variant="flat" color="primary" size="small" :disabled="selectedIds.length === 0 || busy" @click="openMoveDialog">
                                    <Icon icon="fluent:folder-arrow-right-20-regular" width="18px" height="18px" />
                                    <span class="ml-1">フォルダへ移動</span>
                                </v-btn>
                                <v-btn variant="tonal" color="error" size="small" :disabled="selectedIds.length === 0 || busy" @click="openDeleteDialog">
                                    <Icon icon="fluent:delete-20-regular" width="18px" height="18px" />
                                    <span class="ml-1">削除</span>
                                </v-btn>
                            </div>
                            <div class="hint" v-if="isAdmin && files.length > 0">
                                ヒント: ファイルをドラッグして、左のフォルダに落とすと移動できます。(スマホは、選択して「フォルダへ移動」)
                            </div>

                            <div class="pane__empty" v-if="is_loading">読み込み中…</div>
                            <template v-else>
                                <!-- 中のフォルダ (録画フォルダを開いているとき) -->
                                <div class="rows" v-if="currentKey === ROOT_KEY && visibleFolders.length > 0">
                                    <div class="row row--folder" v-for="folder in visibleFolders" :key="folder.key"
                                        :class="{'row--drop': dropTarget === folder.key}"
                                        @click="openFolder(folder.key)"
                                        @dragover="onDragOver($event, folder.key)" @dragleave="onDragLeave(folder.key)" @drop="onDrop($event, folder.key)">
                                        <span class="row__icon"><Icon icon="fluent:folder-20-filled" width="28px" height="28px" /></span>
                                        <div class="row__body">
                                            <div class="row__title">{{folder.name}}</div>
                                            <div class="row__meta">{{folder.programs.length}}件 ・ {{formatSize(folder.size)}}</div>
                                        </div>
                                    </div>
                                </div>

                                <!-- ファイル -->
                                <div class="rows">
                                    <div class="row" v-for="program in visibleFiles" :key="program.id"
                                        :class="{'row--selected': isSelected(program.id), 'row--dragging': dragIds.includes(program.id)}"
                                        :draggable="isAdmin" @dragstart="onDragStart($event, program)" @dragend="onDragEnd"
                                        @click="toggleSelect(program.id)" @dblclick="openVideo(program.id)">
                                        <input class="row__check" type="checkbox" v-if="isAdmin" :checked="isSelected(program.id)" @click.stop @change="toggleSelect(program.id)">
                                        <img class="row__thumb" loading="lazy" decoding="async" draggable="false"
                                            :src="`${Utils.api_base_url}/videos/${program.id}/thumbnail`">
                                        <div class="row__body">
                                            <div class="row__title">{{program.title}}</div>
                                            <div class="row__meta">{{baseFileName(program)}}</div>
                                            <div class="row__meta row__meta--sp">{{formatDateTime(program.start_time)}} ・ {{formatDuration(program.recorded_video.duration)}} ・ {{formatSize(program.recorded_video.file_size)}}</div>
                                        </div>
                                        <div class="row__col row__col--date">{{formatDateTime(program.start_time)}}</div>
                                        <div class="row__col row__col--duration">{{formatDuration(program.recorded_video.duration)}}</div>
                                        <div class="row__col row__col--size">{{formatSize(program.recorded_video.file_size)}}</div>
                                        <button type="button" class="row__play" aria-label="再生" @click.stop="openVideo(program.id)">
                                            <Icon icon="fluent:play-20-filled" width="20px" height="20px" />
                                        </button>
                                    </div>
                                </div>
                                <div class="pane__empty" v-if="visibleFiles.length === 0 && (currentKey !== ROOT_KEY || visibleFolders.length === 0)">
                                    {{searchText ? '該当するファイルがありません。' : (currentKey === ROOT_KEY ? '録画フォルダ直下にファイルはありません。' : 'このフォルダは空です。')}}
                                </div>
                            </template>
                        </section>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- 移動先を選ぶダイアログ -->
    <v-dialog v-model="showMoveDialog" max-width="560" :persistent="busy">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">{{selectedIds.length}}件をフォルダへ移動</v-card-title>
            <v-card-text class="pt-2 pb-0">
                <v-text-field v-model="moveInput" label="フォルダ名 (入力で絞り込み・なければ新規作成)" variant="outlined" density="comfortable"
                    hide-details="auto" :counter="60" :disabled="busy" clearable :error-messages="moveNameError" />
                <div class="text-body-2 mt-3" v-if="moveTarget !== null">
                    移動先: <b>{{moveTarget === '' ? '録画フォルダ直下 (未分類)' : moveTarget}}</b>
                    <span class="text-text-darken-1">{{moveTarget === '' ? '' : (moveIsNew ? '(新規作成)' : '(既存のフォルダ)')}}</span>
                </div>
                <div class="candidates mt-3">
                    <div class="candidates__label">既存のフォルダ ({{moveCandidates.length}}件)</div>
                    <div class="candidates__list">
                        <button type="button" class="candidates__item" :class="{'candidates__item--on': moveTarget === ''}" :disabled="busy"
                            @click="moveInput = ''; moveToRoot = true">
                            <Icon icon="fluent:folder-open-20-regular" width="18px" height="18px" />
                            <span>録画フォルダ直下 (未分類)</span>
                        </button>
                        <button type="button" v-for="name in moveCandidates" :key="name" class="candidates__item"
                            :class="{'candidates__item--on': moveTarget === name}" :disabled="busy"
                            @click="moveInput = name; moveToRoot = false">
                            <Icon icon="fluent:folder-20-regular" width="18px" height="18px" />
                            <span>{{name}}</span>
                        </button>
                    </div>
                </div>
                <div class="progress mt-3" v-if="busy || failures.length > 0">
                    <div v-if="busy">処理中… {{doneCount}} / {{totalCount}}</div>
                    <div v-for="failure in failures" :key="failure.id" class="progress__error">{{failure.title}}: {{failure.message}}</div>
                </div>
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" :disabled="busy" @click="showMoveDialog = false">閉じる</v-btn>
                <v-btn class="px-3" color="primary" variant="flat" :disabled="busy || moveTarget === null || moveNameError !== ''" @click="executeMoveFromDialog">
                    <Icon icon="fluent:folder-arrow-right-20-regular" width="18px" height="18px" />
                    <span class="ml-1">移動する</span>
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- 新規フォルダ -->
    <v-dialog v-model="showCreateDialog" max-width="480" :persistent="busy">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">新規フォルダ</v-card-title>
            <v-card-text class="pt-2 pb-0">
                <v-text-field v-model="folderInput" label="フォルダ名" variant="outlined" density="comfortable" hide-details="auto"
                    :counter="60" :disabled="busy" autofocus :error-messages="folderInputError" @keydown.enter="executeCreate" />
                <div class="text-caption text-text-darken-1 mt-2">録画フォルダの直下に作成されます。</div>
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" :disabled="busy" @click="showCreateDialog = false">閉じる</v-btn>
                <v-btn class="px-3" color="primary" variant="flat" :disabled="busy || folderInput.trim() === '' || folderInputError !== ''" @click="executeCreate">作成</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- フォルダ名の変更 -->
    <v-dialog v-model="showRenameDialog" max-width="480" :persistent="busy">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">フォルダ名を変更</v-card-title>
            <v-card-text class="pt-2 pb-0">
                <div class="text-body-2 text-text-darken-1 mb-3">
                    「{{currentName}}」の名前を変えます。中の録画 ({{files.length}}件) の情報・サムネイルはそのまま引き継がれます。
                </div>
                <v-text-field v-model="folderInput" label="新しいフォルダ名" variant="outlined" density="comfortable" hide-details="auto"
                    :counter="60" :disabled="busy" autofocus :error-messages="folderInputError" @keydown.enter="executeRename" />
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" :disabled="busy" @click="showRenameDialog = false">閉じる</v-btn>
                <v-btn class="px-3" color="primary" variant="flat"
                    :disabled="busy || folderInput.trim() === '' || folderInput.trim() === currentName || folderInputError !== ''" @click="executeRename">変更する</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- 空のフォルダの削除 -->
    <v-dialog v-model="showDeleteFolderDialog" max-width="480" :persistent="busy">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">空のフォルダを削除</v-card-title>
            <v-card-text class="pt-2 pb-0">
                空のフォルダ「{{currentName}}」を削除します。中に何かあるフォルダは削除されません。
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" :disabled="busy" @click="showDeleteFolderDialog = false">閉じる</v-btn>
                <v-btn class="px-3" color="error" variant="flat" :disabled="busy" @click="executeDeleteFolder">削除する</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- 録画ファイルの削除 -->
    <v-dialog v-model="showDeleteDialog" max-width="560" :persistent="busy">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">{{selectedIds.length}}件の録画を削除</v-card-title>
            <v-card-text class="pt-2 pb-0">
                <div class="text-body-2 mb-3" style="color: rgb(var(--v-theme-error));">
                    NAS 上のファイルも削除されます。元に戻せません。
                </div>
                <div class="delete-list">
                    <div v-for="program in selectedPrograms.slice(0, 8)" :key="program.id" class="delete-list__item">{{program.title}}</div>
                    <div v-if="selectedPrograms.length > 8" class="delete-list__item">ほか {{selectedPrograms.length - 8}}件</div>
                </div>
                <div class="progress mt-3" v-if="busy || failures.length > 0">
                    <div v-if="busy">処理中… {{doneCount}} / {{totalCount}}</div>
                    <div v-for="failure in failures" :key="failure.id" class="progress__error">{{failure.title}}: {{failure.message}}</div>
                </div>
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" :disabled="busy" @click="showDeleteDialog = false">閉じる</v-btn>
                <v-btn class="px-3" color="error" variant="flat" :disabled="busy" @click="executeDelete">削除する</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>
<script lang="ts" setup>

import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import Message from '@/message';
import Videos, { IRecordedProgram } from '@/services/Videos';
import useUserStore from '@/stores/UserStore';
import Utils from '@/utils';

interface IFolderNode {
    key: string;
    name: string;
    programs: IRecordedProgram[];
    size: number;
}

// 録画フォルダ直下 (フォルダ分けなし) を表すキー
const ROOT_KEY = '';

const router = useRouter();
const userStore = useUserStore();
const isAdmin = computed(() => userStore.user?.is_admin === true);

const programs = ref<IRecordedProgram[]>([]);
const apiFolders = ref<{ name: string; path: string }[]>([]);
const is_loading = ref(true);
const currentKey = ref<string>(ROOT_KEY);
const selectedIds = ref<number[]>([]);
const searchText = ref<string | null>('');
const sortKey = ref<'start_time' | 'title' | 'file_size' | 'duration'>('start_time');
const sortDesc = ref(false);
const showTree = ref(false);

const sortItems = [
    { title: '放送日', value: 'start_time' },
    { title: 'タイトル', value: 'title' },
    { title: 'サイズ', value: 'file_size' },
    { title: '長さ', value: 'duration' },
];

// ---- フォルダ構造 ----

const dirOf = (program: IRecordedProgram): string => {
    const path = program.recorded_video.file_path;
    const index = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    return index >= 0 ? path.slice(0, index) : '';
};

const baseName = (dir: string): string => {
    const index = Math.max(dir.lastIndexOf('/'), dir.lastIndexOf('\\'));
    return index >= 0 ? dir.slice(index + 1) : dir;
};

const baseFileName = (program: IRecordedProgram): string => baseName(program.recorded_video.file_path);

// 他のフォルダの親になっているフォルダは録画フォルダ本体 (= 直下に置かれたファイル) とみなす
const rootDirs = computed(() => {
    const dirs = [...new Set(programs.value.map(dirOf))];
    const roots = new Set(dirs.filter(d => dirs.some(o => o !== d && (o.startsWith(d + '/') || o.startsWith(d + '\\')))));
    // フォルダ一覧 API が返すフォルダの親も、録画フォルダ本体
    for (const folder of apiFolders.value) {
        const index = Math.max(folder.path.lastIndexOf('/'), folder.path.lastIndexOf('\\'));
        if (index > 0) roots.add(folder.path.slice(0, index));
    }
    return roots;
});

const keyOf = (program: IRecordedProgram): string => {
    const dir = dirOf(program);
    return rootDirs.value.has(dir) ? ROOT_KEY : dir;
};

const folders = computed<IFolderNode[]>(() => {
    const map = new Map<string, IRecordedProgram[]>();
    for (const folder of apiFolders.value) map.set(folder.path, []);
    for (const program of programs.value) {
        const key = keyOf(program);
        if (key === ROOT_KEY) continue;
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(program);
    }
    const result: IFolderNode[] = [];
    for (const [key, list] of map) {
        result.push({
            key,
            name: baseName(key),
            programs: list,
            size: list.reduce((sum, p) => sum + p.recorded_video.file_size, 0),
        });
    }
    result.sort((a, b) => a.name.localeCompare(b.name, 'ja'));
    return result;
});

const rootPrograms = computed(() => programs.value.filter(p => keyOf(p) === ROOT_KEY));

const currentFolder = computed(() => folders.value.find(f => f.key === currentKey.value) ?? null);
const currentName = computed(() => currentKey.value === ROOT_KEY ? '録画フォルダ' : (currentFolder.value?.name ?? baseName(currentKey.value)));

const files = computed<IRecordedProgram[]>(() => currentKey.value === ROOT_KEY ? rootPrograms.value : (currentFolder.value?.programs ?? []));
const filesTotalSize = computed(() => files.value.reduce((sum, p) => sum + p.recorded_video.file_size, 0));

// ---- 検索・並べ替え ----

const normalizeForSearch = (s: string): string => Array.from(s.normalize('NFKC').toLowerCase())
    .map(c => {
        const code = c.charCodeAt(0);
        return code >= 0x30a1 && code <= 0x30f6 ? String.fromCharCode(code - 0x60) : c;
    })
    .join('')
    .replace(/[\s・!?~〜]/g, '');

const matchesSearch = (text: string, query: string): boolean => normalizeForSearch(text).includes(query);

const visibleFiles = computed(() => {
    const query = normalizeForSearch(searchText.value ?? '');
    const list = query === '' ? [...files.value] : files.value.filter(p => matchesSearch(`${p.title} ${baseFileName(p)}`, query));
    const dir = sortDesc.value ? -1 : 1;
    list.sort((a, b) => {
        switch (sortKey.value) {
            case 'title': return a.title.localeCompare(b.title, 'ja', { numeric: true }) * dir;
            case 'file_size': return (a.recorded_video.file_size - b.recorded_video.file_size) * dir;
            case 'duration': return (a.recorded_video.duration - b.recorded_video.duration) * dir;
            default: return a.start_time.localeCompare(b.start_time) * dir;
        }
    });
    return list;
});

const visibleFolders = computed(() => {
    const query = normalizeForSearch(searchText.value ?? '');
    return query === '' ? folders.value : folders.value.filter(f => matchesSearch(f.name, query));
});

// ---- 表示用の整形 ----

const pad2 = (n: number): string => String(n).padStart(2, '0');

const formatDateTime = (iso: string): string => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return `${d.getFullYear()}/${pad2(d.getMonth() + 1)}/${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
};

const formatDuration = (seconds: number): string => {
    const total = Math.round(seconds);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    return h > 0 ? `${h}:${pad2(m)}:${pad2(total % 60)}` : `${m}:${pad2(total % 60)}`;
};

const formatSize = (size: number): string => {
    if (size >= 1024 * 1024 * 1024) return `${(size / 1024 / 1024 / 1024).toFixed(2)}GB`;
    return `${Math.round(size / 1024 / 1024)}MB`;
};

// ---- 読み込み ----

const fetchAll = async () => {
    const all: IRecordedProgram[] = [];
    let page = 1;
    while (true) {
        const result = await Videos.fetchVideos('desc', page);
        if (!result || result.recorded_programs.length === 0) break;
        all.push(...result.recorded_programs);
        if (all.length >= result.total) break;
        page++;
    }
    programs.value = all;
};

const reload = async () => {
    if (isAdmin.value) {
        const result = await Videos.fetchFolders();
        if (result !== null) apiFolders.value = result;
    }
    await fetchAll();
    is_loading.value = false;
    // 開いていたフォルダがなくなっていたら、録画フォルダ直下に戻る
    if (currentKey.value !== ROOT_KEY && !folders.value.some(f => f.key === currentKey.value)) {
        currentKey.value = ROOT_KEY;
    }
    selectedIds.value = selectedIds.value.filter(id => programs.value.some(p => p.id === id));
};

const openFolder = (key: string) => {
    currentKey.value = key;
    selectedIds.value = [];
    showTree.value = false;
};

watch(currentKey, () => {
    searchText.value = '';
});

const openVideo = (id: number) => {
    router.push(`/videos/watch/${id}`);
};

const addPageLink = computed(() => currentKey.value === ROOT_KEY
    ? '/videos/upload' : `/videos/upload?folder=${encodeURIComponent(currentName.value)}`);

// ---- 選択 ----

const isSelected = (id: number): boolean => selectedIds.value.includes(id);

const toggleSelect = (id: number) => {
    if (!isAdmin.value) return;
    selectedIds.value = isSelected(id) ? selectedIds.value.filter(v => v !== id) : [...selectedIds.value, id];
};

const selectAll = () => {
    selectedIds.value = visibleFiles.value.map(p => p.id);
};

const selectedPrograms = computed(() => programs.value.filter(p => selectedIds.value.includes(p.id)));

// ---- 移動・削除などの共通処理 ----

const busy = ref(false);
const doneCount = ref(0);
const totalCount = ref(0);
const failures = ref<{ id: number; title: string; message: string }[]>([]);

const INVALID_FOLDER_CHARS = '\\/:*?"<>|';
const hasInvalidFolderChar = (c: string): boolean => INVALID_FOLDER_CHARS.includes(c) || c.charCodeAt(0) < 32 || c.charCodeAt(0) === 127;

const validateFolderName = (raw: string): string => {
    const name = raw.trim();
    if (name === '') return '';
    if (name.length > 60) return '60文字までです。';
    if (Array.from(name).some(hasInvalidFolderChar)) return '使えない文字が含まれています。(\\ / : * ? " < > |)';
    if (name === '.' || name === '..' || name.endsWith('.')) return '末尾にドットは使えません。';
    return '';
};

// 指定した録画を、フォルダ (ROOT_KEY なら録画フォルダ直下) へ移動する。移動に成功した件数を返す
const moveTo = async (ids: number[], folderName: string): Promise<number> => {
    const targets = programs.value.filter(p => ids.includes(p.id));
    busy.value = true;
    doneCount.value = 0;
    totalCount.value = targets.length;
    failures.value = [];
    let succeeded = 0;
    renamedCount.value = 0;
    for (const program of targets) {
        const result = await Videos.moveVideoDetailed(program.id, folderName);
        if (result.error === null) {
            succeeded++;
            if (result.renamed) renamedCount.value++;
        } else {
            failures.value.push({ id: program.id, title: program.title, message: result.error });
        }
        doneCount.value++;
    }
    busy.value = false;
    await reload();
    return succeeded;
};

// 直前の移動で、移動先に同名のファイルがあったためファイル名の末尾に -(1) などを付けた件数
const renamedCount = ref(0);

const reportMove = (succeeded: number, label: string) => {
    const note = renamedCount.value > 0
        ? ` (同じ名前のファイルがあった${renamedCount.value}件は、名前の末尾に -(1) などを付けました)` : '';
    if (failures.value.length === 0) {
        Message.success(`${succeeded}件を「${label}」へ移動しました。${note}`);
    } else if (succeeded > 0) {
        Message.warning(`${succeeded}件を移動しました。${failures.value.length}件は失敗しました。(${failures.value[0].message})`);
    } else {
        Message.error(`移動できませんでした。(${failures.value[0].message})`);
    }
};

// ---- ドラッグ & ドロップ ----

const dragIds = ref<number[]>([]);
const dropTarget = ref<string | null>(null);

const onDragStart = (event: DragEvent, program: IRecordedProgram) => {
    if (!isAdmin.value || busy.value) {
        event.preventDefault();
        return;
    }
    if (!isSelected(program.id)) selectedIds.value = [program.id];
    dragIds.value = [...selectedIds.value];
    if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', dragIds.value.join(','));
    }
};

const onDragEnd = () => {
    dragIds.value = [];
    dropTarget.value = null;
};

const onDragOver = (event: DragEvent, key: string) => {
    if (dragIds.value.length === 0) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    dropTarget.value = key;
};

const onDragLeave = (key: string) => {
    if (dropTarget.value === key) dropTarget.value = null;
};

const onDrop = async (event: DragEvent, key: string) => {
    event.preventDefault();
    const ids = dragIds.value;
    dragIds.value = [];
    dropTarget.value = null;
    if (ids.length === 0 || busy.value) return;
    // すでにそのフォルダにあるものは動かさない
    const moving = programs.value.filter(p => ids.includes(p.id) && keyOf(p) !== key).map(p => p.id);
    if (moving.length === 0) return;
    const label = key === ROOT_KEY ? '録画フォルダ直下' : baseName(key);
    const succeeded = await moveTo(moving, key === ROOT_KEY ? '' : baseName(key));
    selectedIds.value = selectedIds.value.filter(id => !moving.includes(id) || failures.value.some(f => f.id === id));
    reportMove(succeeded, label);
};

// ---- 「フォルダへ移動」ダイアログ ----

const showMoveDialog = ref(false);
const moveInput = ref<string | null>('');
const moveToRoot = ref(false);

const moveNameError = computed(() => moveToRoot.value ? '' : validateFolderName(moveInput.value ?? ''));

// 移動先 (null = 未決定、'' = 録画フォルダ直下)
const moveTarget = computed<string | null>(() => {
    if (moveToRoot.value) return '';
    const name = (moveInput.value ?? '').trim();
    return name === '' ? null : name;
});

const moveIsNew = computed(() => moveTarget.value !== null && moveTarget.value !== '' && !folders.value.some(f => f.name === moveTarget.value));

const moveCandidates = computed(() => {
    const q = moveToRoot.value ? '' : normalizeForSearch(moveInput.value ?? '');
    const names = folders.value.map(f => f.name);
    if (q === '') return names;
    const scored: { name: string; rank: number }[] = [];
    for (const name of names) {
        const n = normalizeForSearch(name);
        let rank = -1;
        if (n === q) rank = 0;
        else if (n.startsWith(q) || q.startsWith(n)) rank = 1;
        else if (n.includes(q) || (n.length >= 2 && q.includes(n))) rank = 2;
        if (rank >= 0) scored.push({ name, rank });
    }
    scored.sort((a, b) => a.rank - b.rank || a.name.localeCompare(b.name, 'ja'));
    return scored.map(s => s.name);
});

watch(moveInput, (value) => {
    // 文字を打ち始めたら「録画フォルダ直下」の選択を外す
    if ((value ?? '') !== '') moveToRoot.value = false;
});

const openMoveDialog = () => {
    failures.value = [];
    moveToRoot.value = false;
    moveInput.value = currentKey.value === ROOT_KEY ? '' : currentName.value;
    showMoveDialog.value = true;
};

const executeMoveFromDialog = async () => {
    const target = moveTarget.value;
    if (target === null || moveNameError.value !== '') return;
    const ids = selectedIds.value;
    const succeeded = await moveTo(ids, target);
    selectedIds.value = selectedIds.value.filter(id => failures.value.some(f => f.id === id));
    if (failures.value.length === 0) showMoveDialog.value = false;
    reportMove(succeeded, target === '' ? '録画フォルダ直下' : target);
};

// ---- フォルダの作成・名前変更・削除 ----

const showCreateDialog = ref(false);
const showRenameDialog = ref(false);
const showDeleteFolderDialog = ref(false);
const folderInput = ref('');
const folderInputError = computed(() => validateFolderName(folderInput.value ?? ''));

const openCreateDialog = () => {
    folderInput.value = '';
    showCreateDialog.value = true;
};

const executeCreate = async () => {
    const name = (folderInput.value ?? '').trim();
    if (name === '' || folderInputError.value !== '' || busy.value) return;
    busy.value = true;
    const result = await Videos.createFolder(name);
    busy.value = false;
    if (result.error !== null) {
        Message.error(result.error);
        return;
    }
    showCreateDialog.value = false;
    await reload();
    if (result.path !== null) openFolder(result.path);
    Message.success(`フォルダ「${name}」を作成しました。`);
};

const openRenameDialog = () => {
    if (currentKey.value === ROOT_KEY) return;
    folderInput.value = currentName.value;
    showRenameDialog.value = true;
};

const executeRename = async () => {
    const name = (folderInput.value ?? '').trim();
    if (name === '' || name === currentName.value || folderInputError.value !== '' || busy.value) return;
    busy.value = true;
    const result = await Videos.renameFolder(currentName.value, name);
    busy.value = false;
    if (result.error !== null) {
        Message.error(result.error);
        return;
    }
    showRenameDialog.value = false;
    // 名前を変えたので、ファイルの場所 (キー) が変わる。新しい場所を開き直す
    const newKey = result.path;
    await reload();
    if (newKey !== null) openFolder(newKey);
    Message.success(`フォルダ名を「${name}」に変更しました。`);
};

const openDeleteFolderDialog = () => {
    if (currentKey.value === ROOT_KEY || files.value.length > 0) return;
    showDeleteFolderDialog.value = true;
};

const executeDeleteFolder = async () => {
    if (busy.value) return;
    const name = currentName.value;
    busy.value = true;
    const error = await Videos.deleteFolder(name);
    busy.value = false;
    if (error !== null) {
        Message.error(error);
        return;
    }
    showDeleteFolderDialog.value = false;
    currentKey.value = ROOT_KEY;
    await reload();
    Message.success(`フォルダ「${name}」を削除しました。`);
};

// ---- 録画ファイルの削除 ----

const showDeleteDialog = ref(false);

const openDeleteDialog = () => {
    failures.value = [];
    showDeleteDialog.value = true;
};

const executeDelete = async () => {
    const targets = selectedPrograms.value;
    busy.value = true;
    doneCount.value = 0;
    totalCount.value = targets.length;
    failures.value = [];
    let succeeded = 0;
    for (const program of targets) {
        const ok = await Videos.deleteVideo(program.id);
        if (ok) {
            succeeded++;
        } else {
            failures.value.push({ id: program.id, title: program.title, message: '削除できませんでした。' });
        }
        doneCount.value++;
    }
    busy.value = false;
    selectedIds.value = selectedIds.value.filter(id => failures.value.some(f => f.id === id));
    await reload();
    if (failures.value.length === 0) {
        showDeleteDialog.value = false;
        Message.success(`${succeeded}件を削除しました。`);
    } else {
        Message.warning(`${succeeded}件を削除しました。${failures.value.length}件は失敗しました。`);
    }
};

onMounted(async () => {
    await userStore.fetchUser();
    await reload();
});

</script>
<style lang="scss" scoped>

.files-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
}

.files {
    display: flex;
    flex-direction: column;
    width: 100%;
    padding: 20px;
    margin: 0 auto;
    min-width: 0;
    max-width: 1280px;
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

    &__head {
        display: flex;
        align-items: baseline;
        gap: 12px;
        padding-top: 8px;
        padding-bottom: 14px;
        @include smartphone-vertical {
            padding: 0 8px 12px;
        }
    }

    &__title {
        font-size: 24px;
        font-weight: 700;
        @include smartphone-vertical {
            font-size: 22px;
        }
    }

    &__count {
        font-size: 14px;
        color: rgb(var(--v-theme-text-darken-1));
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

.toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding-bottom: 12px;
    &__tree-button {
        display: none;
        @include smartphone-vertical {
            display: inline-flex;
        }
    }
}

.explorer {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    min-width: 0;
    @include smartphone-vertical {
        flex-direction: column;
        gap: 8px;
    }
}

.tree {
    flex: none;
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 280px;
    max-height: calc(100vh - 220px);
    overflow-y: auto;
    padding: 8px;
    border-radius: 11px;
    background: rgb(var(--v-theme-background-lighten-1));
    @include smartphone-vertical {
        display: none;
        width: 100%;
        max-height: 50vh;
        &--open {
            display: flex;
        }
    }

    &__node {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        padding: 8px 10px;
        border: none;
        border-radius: 8px;
        text-align: left;
        font-size: 14px;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: transparent;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        &--on {
            font-weight: 700;
            background: rgb(var(--v-theme-background-lighten-2));
            box-shadow: inset 3px 0 0 rgb(var(--v-theme-primary));
        }
        &--child {
            padding-left: 22px;
        }
        &--drop {
            outline: 2px dashed rgb(var(--v-theme-primary));
            outline-offset: -2px;
            background: rgb(var(--v-theme-background-lighten-2));
        }
    }

    &__name {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    &__count {
        flex: none;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

.pane {
    flex: 1;
    min-width: 0;
    width: 100%;

    &__path {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 4px;
        padding: 4px 4px 10px;
        font-size: 14px;
    }

    &__crumb {
        padding: 4px 8px;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: transparent;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        &--current {
            font-weight: 700;
            cursor: default;
            &:hover {
                background: transparent;
            }
        }
        &--drop {
            outline: 2px dashed rgb(var(--v-theme-primary));
        }
    }

    &__summary {
        margin-left: auto;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__tools {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
        padding-bottom: 8px;
    }

    &__search {
        flex: 1 1 220px;
        min-width: 0;
    }

    &__sort {
        flex: 0 0 140px;
    }

    &__empty {
        padding: 40px 0;
        text-align: center;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

.actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
    padding: 4px 0;
    &__selected {
        margin-left: 8px;
        font-size: 13px;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

.hint {
    padding: 0 0 8px;
    font-size: 12px;
    color: rgb(var(--v-theme-text-darken-1));
    @include smartphone-vertical {
        display: none;
    }
}

.rows {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 8px;
}

.row {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
    padding: 6px 12px;
    border-radius: 8px;
    cursor: pointer;
    user-select: none;
    background: rgb(var(--v-theme-background-lighten-1));
    &:hover {
        background: rgb(var(--v-theme-background-lighten-2));
    }
    &--selected {
        box-shadow: inset 3px 0 0 rgb(var(--v-theme-primary));
        background: rgb(var(--v-theme-background-lighten-2));
    }
    &--dragging {
        opacity: 0.5;
    }
    &--drop {
        outline: 2px dashed rgb(var(--v-theme-primary));
        outline-offset: -2px;
    }
    &--folder {
        padding: 10px 12px;
    }

    &__check {
        flex: none;
        width: 20px;
        height: 20px;
        accent-color: rgb(var(--v-theme-primary));
    }

    &__icon {
        flex: none;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        color: rgb(var(--v-theme-primary));
    }

    &__thumb {
        flex: none;
        width: 112px;
        aspect-ratio: 16 / 9;
        object-fit: cover;
        border-radius: 6px;
        background: rgb(var(--v-theme-background-lighten-2));
        @include smartphone-vertical {
            width: 88px;
        }
    }

    &__body {
        flex: 1;
        min-width: 0;
    }

    &__title {
        font-size: 14px;
        font-weight: 700;
        line-height: 1.4;
        word-break: break-all;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    &__meta {
        margin-top: 2px;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
        word-break: break-all;
        &--sp {
            display: none;
            @include smartphone-vertical {
                display: block;
            }
        }
    }

    &__col {
        flex: none;
        font-size: 13px;
        text-align: right;
        color: rgb(var(--v-theme-text-darken-1));
        &--date {
            width: 130px;
        }
        &--duration {
            width: 64px;
        }
        &--size {
            width: 80px;
        }
        @include smartphone-vertical {
            display: none;
        }
    }

    &__play {
        flex: none;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: transparent;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
    }
}

.candidates {
    &__label {
        margin-bottom: 6px;
        font-size: 12px;
        font-weight: 700;
        color: rgb(var(--v-theme-text-darken-1));
    }
    &__list {
        display: flex;
        flex-direction: column;
        gap: 4px;
        max-height: 260px;
        overflow-y: auto;
    }
    &__item {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        padding: 8px 12px;
        border: none;
        border-radius: 8px;
        text-align: left;
        font-size: 14px;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: rgb(var(--v-theme-background-lighten-1));
        word-break: break-all;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        &--on {
            font-weight: 700;
            box-shadow: inset 3px 0 0 rgb(var(--v-theme-primary));
        }
    }
}

.progress {
    font-size: 13px;
    &__error {
        color: rgb(var(--v-theme-error));
        word-break: break-all;
    }
}

.delete-list {
    max-height: 200px;
    overflow-y: auto;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    background: rgb(var(--v-theme-background-lighten-1));
    &__item {
        padding: 2px 0;
        word-break: break-all;
    }
}

</style>
