<template>
    <div class="route-container">
        <HeaderBar />
        <main>
            <Navigation />
            <div class="series-container-wrapper">
                <SPHeaderBar />
                <div class="series-container">
                    <Breadcrumbs :crumbs="breadcrumbs" />
                    <template v-if="selectedFolder === null">
                        <h2 class="series-container__title">
                            <span>シリーズ別</span>
                            <span class="series-container__count" v-if="!is_loading">{{folders.length}}シリーズ / {{programs.length}}件</span>
                        </h2>
                        <div class="series-container__loading" v-if="is_loading">読み込み中…</div>
                        <div class="series-container__empty" v-else-if="folders.length === 0">録画番組がありません。</div>
                        <template v-else>
                            <section class="series-section" v-for="section in sections" :key="section.label">
                                <h3 class="series-section__label" v-if="pinnedFolders.length > 0">
                                    <Icon v-if="section.pinned" icon="fluent:pin-20-filled" width="16px" height="16px" />
                                    <span>{{section.label}}</span>
                                    <span class="series-section__count">{{section.folders.length}}</span>
                                </h3>
                                <div class="series-grid">
                                    <div v-for="folder in section.folders" :key="folder.key"
                                        class="series-item" :class="{'series-item--pinned': isPinned(folder.key)}">
                                        <router-link v-ripple class="series-item__link"
                                            :to="{path: '/videos/series', query: {folder: folder.key}}">
                                            <div class="series-item__thumbnail">
                                                <img loading="lazy" decoding="async"
                                                    :src="`${Utils.api_base_url}/videos/${folder.latest.id}/thumbnail`">
                                                <div class="series-item__badge">{{folder.programs.length}}話</div>
                                            </div>
                                            <div class="series-item__body">
                                                <div class="series-item__name">{{folder.name}}</div>
                                                <div class="series-item__meta">{{folder.programs.length}}話 ・ 最新 {{formatDate(folder.latest.start_time)}}</div>
                                            </div>
                                        </router-link>
                                        <button type="button" class="series-item__pin"
                                            :class="{'series-item__pin--on': isPinned(folder.key)}"
                                            :aria-label="isPinned(folder.key) ? '固定を外す' : '上に固定する'"
                                            @click.prevent.stop="togglePin(folder.key)">
                                            <Icon :icon="isPinned(folder.key) ? 'fluent:pin-20-filled' : 'fluent:pin-20-regular'" width="22px" height="22px" />
                                        </button>
                                    </div>
                                </div>
                            </section>
                        </template>
                    </template>
                    <RecordedProgramList v-else
                        :title="selectedName"
                        :programs="selectedPrograms"
                        :total="selectedPrograms.length"
                        :hideSort="true"
                        :hidePagination="true"
                        :showBackButton="true"
                        :showEmptyMessage="!is_loading"
                        :isLoading="is_loading" />
                </div>
            </div>
        </main>
    </div>
</template>
<script lang="ts" setup>

import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import Breadcrumbs from '@/components/Breadcrumbs.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import RecordedProgramList from '@/components/Videos/RecordedProgramList.vue';
import { IRecordedProgram } from '@/services/Videos';
import Videos from '@/services/Videos';
import useUserStore from '@/stores/UserStore';
import Utils from '@/utils';

interface IFolder {
    key: string;
    name: string;
    programs: IRecordedProgram[];
    latest: IRecordedProgram;
}

const UNSORTED_KEY = '';
const UNSORTED_NAME = '未分類 (フォルダ分けなし)';

const route = useRoute();

const programs = ref<IRecordedProgram[]>([]);
const is_loading = ref(true);

// ファイルの置き場所 (フォルダのフルパス)
const dirOf = (program: IRecordedProgram): string => {
    const path = program.recorded_video.file_path;
    const index = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    return index >= 0 ? path.slice(0, index) : '';
};

const baseName = (dir: string): string => {
    const index = Math.max(dir.lastIndexOf('/'), dir.lastIndexOf('\\'));
    return index >= 0 ? dir.slice(index + 1) : dir;
};

// 他のフォルダの親になっているフォルダは録画フォルダ本体 (= 直下に置かれたファイル) とみなす
const rootDirs = computed(() => {
    const dirs = [...new Set(programs.value.map(dirOf))];
    return new Set(dirs.filter(d => dirs.some(o => o !== d && (o.startsWith(d + '/') || o.startsWith(d + '\\')))));
});

const folders = computed<IFolder[]>(() => {
    const map = new Map<string, IRecordedProgram[]>();
    for (const program of programs.value) {
        const dir = dirOf(program);
        const key = rootDirs.value.has(dir) ? UNSORTED_KEY : dir;
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(program);
    }
    const result: IFolder[] = [];
    for (const [key, list] of map) {
        // 話数順に並べたいので放送日時の古い順
        list.sort((a, b) => a.start_time.localeCompare(b.start_time));
        result.push({
            key,
            name: key === UNSORTED_KEY ? UNSORTED_NAME : baseName(key),
            programs: list,
            latest: list[list.length - 1],
        });
    }
    // シリーズ名順。未分類は最後
    result.sort((a, b) => {
        if (a.key === UNSORTED_KEY) return 1;
        if (b.key === UNSORTED_KEY) return -1;
        return a.name.localeCompare(b.name, 'ja');
    });
    return result;
});

// 上に固定しているシリーズ (この端末のブラウザに保存)
const PINNED_STORAGE_KEY = 'konomitv.series.pinned';
const loadPinned = (): string[] => {
    try {
        const parsed = JSON.parse(localStorage.getItem(PINNED_STORAGE_KEY) ?? '[]');
        return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : [];
    } catch {
        return [];
    }
};
const pinnedKeys = ref<string[]>(loadPinned());

const isPinned = (key: string): boolean => pinnedKeys.value.includes(key);

const togglePin = (key: string) => {
    pinnedKeys.value = isPinned(key) ? pinnedKeys.value.filter(k => k !== key) : [...pinnedKeys.value, key];
    try {
        localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(pinnedKeys.value));
    } catch {
        // 保存できなくても画面上の固定は有効
    }
};

// 固定中のシリーズ (固定した順)。存在しなくなったフォルダは無視する
const pinnedFolders = computed(() => pinnedKeys.value
    .map(key => folders.value.find(f => f.key === key))
    .filter((f): f is IFolder => f !== undefined));

const sections = computed(() => {
    if (pinnedFolders.value.length === 0) {
        return [{ label: 'すべてのシリーズ', pinned: false, folders: folders.value }];
    }
    const rest = folders.value.filter(f => !isPinned(f.key));
    const result = [{ label: '固定中', pinned: true, folders: pinnedFolders.value }];
    if (rest.length > 0) result.push({ label: 'すべてのシリーズ', pinned: false, folders: rest });
    return result;
});

const formatDate = (iso: string): string => {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? '' : `${d.getMonth() + 1}/${d.getDate()}`;
};

// 選択中のフォルダ (null = 一覧表示)
const selectedFolder = computed<string | null>(() => {
    const q = route.query.folder;
    if (q === undefined) return null;
    return typeof q === 'string' ? q : null;
});
const selectedFolderData = computed(() => folders.value.find(f => f.key === selectedFolder.value) ?? null);
const selectedName = computed(() => selectedFolderData.value?.name ?? (selectedFolder.value === UNSORTED_KEY ? UNSORTED_NAME : baseName(selectedFolder.value ?? '')));
const selectedPrograms = computed(() => selectedFolderData.value?.programs ?? []);

const breadcrumbs = computed(() => {
    const crumbs: { name: string; path: string; disabled?: boolean }[] = [
        { name: 'ホーム', path: '/' },
        { name: 'ビデオをみる', path: '/videos/' },
    ];
    if (selectedFolder.value === null) {
        crumbs.push({ name: 'シリーズ別', path: '/videos/series', disabled: true });
    } else {
        crumbs.push({ name: 'シリーズ別', path: '/videos/series' });
        crumbs.push({ name: selectedName.value, path: `/videos/series?folder=${encodeURIComponent(selectedFolder.value)}`, disabled: true });
    }
    return crumbs;
});

// 全ページ分の録画番組を取得
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
    is_loading.value = false;
};

onMounted(async () => {
    const userStore = useUserStore();
    await userStore.fetchUser();
    await fetchAll();
});

</script>
<style lang="scss" scoped>

.series-container-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
}

.series-container {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    padding: 20px;
    margin: 0 auto;
    min-width: 0;
    max-width: 1000px;
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
        display: flex;
        align-items: baseline;
        gap: 12px;
        font-size: 24px;
        font-weight: 700;
        padding-top: 8px;
        padding-bottom: 20px;
        @include smartphone-vertical {
            font-size: 22px;
            padding: 0px 8px 16px;
        }
    }

    &__count {
        font-size: 14px;
        font-weight: 400;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__loading, &__empty {
        padding: 40px 0;
        text-align: center;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

.series-section {
    margin-bottom: 20px;
    &__label {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 10px;
        font-size: 14px;
        font-weight: 700;
        color: rgb(var(--v-theme-text-darken-1));
        @include smartphone-vertical {
            padding: 0 8px;
        }
    }
    &__count {
        font-size: 12px;
        font-weight: 400;
    }
}

.series-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
    // スマホ縦向きは 1 列のリスト表示
    @include smartphone-vertical {
        grid-template-columns: minmax(0, 1fr);
        gap: 6px;
    }
}

.series-item {
    position: relative;
    min-width: 0;
    border-radius: 11px;
    overflow: hidden;
    background: rgb(var(--v-theme-background-lighten-1));
    transition: background-color 0.15s;
    &:hover {
        background: rgb(var(--v-theme-background-lighten-2));
    }
    &--pinned {
        box-shadow: inset 3px 0 0 rgb(var(--v-theme-primary));
    }

    &__link {
        display: flex;
        flex-direction: column;
        min-width: 0;
        color: rgb(var(--v-theme-text));
        text-decoration: none;
        cursor: pointer;
        @include smartphone-vertical {
            flex-direction: row;
            align-items: center;
            gap: 12px;
            padding: 8px 52px 8px 8px;
        }
    }

    &__thumbnail {
        position: relative;
        aspect-ratio: 16 / 9;
        background: rgb(var(--v-theme-background-lighten-2));
        img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        @include smartphone-vertical {
            flex: none;
            width: 112px;
            border-radius: 6px;
            overflow: hidden;
        }
    }

    &__badge {
        position: absolute;
        right: 6px;
        bottom: 6px;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 700;
        color: #fff;
        background: rgba(0, 0, 0, 0.75);
        // リスト表示では話数を文字側に出すので隠す
        @include smartphone-vertical {
            display: none;
        }
    }

    &__body {
        min-width: 0;
        padding: 10px 12px 12px;
        @include smartphone-vertical {
            flex: 1;
            padding: 0;
        }
    }

    &__name {
        font-size: 14px;
        font-weight: 700;
        line-height: 1.4;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        word-break: break-all;
    }

    &__meta {
        display: none;
        margin-top: 4px;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
        @include smartphone-vertical {
            display: block;
        }
    }

    &__pin {
        position: absolute;
        top: 6px;
        right: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        border: none;
        cursor: pointer;
        color: #fff;
        background: rgba(0, 0, 0, 0.55);
        transition: background-color 0.15s, color 0.15s;
        &:hover {
            background: rgba(0, 0, 0, 0.8);
        }
        &--on {
            color: rgb(var(--v-theme-primary));
            background: rgba(0, 0, 0, 0.8);
        }
        @include smartphone-vertical {
            top: 50%;
            right: 4px;
            width: 44px;
            height: 44px;
            transform: translateY(-50%);
            color: rgb(var(--v-theme-text-darken-1));
            background: transparent;
            &:hover {
                background: transparent;
            }
            &--on {
                color: rgb(var(--v-theme-primary));
                background: transparent;
            }
        }
    }
}

</style>