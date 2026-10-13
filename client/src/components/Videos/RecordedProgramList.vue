<template>
    <div class="recorded-program-list" :class="{'recorded-program-list--show-sort': !hideSort}">
        <div class="recorded-program-list__header" v-if="!hideHeader">
            <h2 class="recorded-program-list__title">
                <div v-if="showBackButton" v-ripple class="recorded-program-list__title-back" @click="$router.back()">
                    <Icon icon="fluent:chevron-left-12-filled" width="27px" />
                </div>
                <span class="recorded-program-list__title-text">{{title}}</span>
                <div class="recorded-program-list__title-count" v-if="!showMoreButton">
                    <template v-if="isSearching">
                        <Icon icon="line-md:loading-twotone-loop" class="mr-1 spin" width="20px" height="20px" />
                        <span>検索中...</span>
                    </template>
                    <template v-else>{{displayTotal}}件</template>
                </div>
            </h2>
            <div class="recorded-program-list__actions" :class="{'recorded-program-list__actions--mylist': forMylist}">
                <v-btn v-if="canSelect"
                    variant="text"
                    class="recorded-program-list__select-toggle"
                    :class="{'recorded-program-list__select-toggle--active': select_mode}"
                    v-ftooltip="'複数の録画番組を選んで、まとめて CM 解析できます'"
                    @click="toggleSelectMode">
                    <Icon :icon="select_mode ? 'fluent:dismiss-16-regular' : 'fluent:checkmark-circle-16-regular'" width="18px" />
                    <span class="ml-1">{{select_mode ? '選択をやめる' : '選択'}}</span>
                </v-btn>
                <v-select v-if="!hideSort"
                    v-model="sort_order"
                    :items="forMylist ? [
                        { title: '追加が新しい順', value: 'mylist_added_desc' },
                        { title: '追加が古い順', value: 'mylist_added_asc' },
                        { title: '録画が新しい順', value: 'recorded_desc' },
                        { title: '録画が古い順', value: 'recorded_asc' },
                    ] : [
                        { title: '新しい順', value: 'desc' },
                        { title: '古い順', value: 'asc' },
                    ]"
                    item-title="title"
                    item-value="value"
                    class="recorded-program-list__sort"
                    color="primary"
                    bg-color="background-lighten-1"
                    variant="solo"
                    density="comfortable"
                    hide-details
                    @update:model-value="$emit('update:sortOrder', $event)">
                </v-select>
                <v-btn v-if="showMoreButton"
                    variant="text"
                    class="recorded-program-list__more"
                    @click="$emit('more')">
                    <span class="text-primary">もっと見る</span>
                    <Icon icon="fluent:chevron-right-12-regular" width="18px" class="ml-1 text-text-darken-1" style="margin: 0px -4px;" />
                </v-btn>
            </div>
        </div>
        <div class="recorded-program-list__selection" v-if="select_mode">
            <span class="recorded-program-list__selection-count">{{selected_video_ids.size}}件を選択中</span>
            <v-btn variant="text" size="small" @click="selectAllInPage">このページをすべて選択</v-btn>
            <v-btn variant="text" size="small" :disabled="selected_video_ids.size === 0" @click="selected_video_ids.clear()">選択を解除</v-btn>
            <v-btn variant="flat" size="small" color="primary" class="recorded-program-list__selection-analyze"
                :disabled="selected_video_ids.size === 0" @click="analyzeSelected">
                <Icon icon="fluent:fast-forward-20-regular" width="18px" />
                <span class="ml-1">CM 解析する</span>
            </v-btn>
        </div>
        <div class="recorded-program-list__grid"
            :class="{
                'recorded-program-list__grid--loading': isLoading || isSearching,
                'recorded-program-list__grid--empty': displayTotal === 0 && showEmptyMessage,
                'recorded-program-list__grid--searching': isSearching,
            }">
            <div class="recorded-program-list__empty"
                :class="{
                    'recorded-program-list__empty--show': displayTotal === 0 && showEmptyMessage && !isSearching,
                }">
                <div class="recorded-program-list__empty-content">
                    <Icon class="recorded-program-list__empty-icon" :icon="emptyIcon" width="54px" height="54px" />
                    <h2 v-html="emptyMessage"></h2>
                    <div class="recorded-program-list__empty-submessage"
                        v-if="emptySubMessage" v-html="emptySubMessage"></div>
                </div>
            </div>
            <div class="recorded-program-list__grid-content">
                <RecordedProgram v-for="program in displayPrograms" :key="program.id" :program="program"
                    :forMylist="forMylist" :forWatchedHistory="forWatchedHistory"
                    :selectable="select_mode" :selected="selected_video_ids.has(program.recorded_video.id)"
                    @toggleSelect="toggleSelect(program)" @deleted="handleProgramDeleted" />
            </div>
        </div>
        <div class="recorded-program-list__pagination" v-if="!hidePagination && displayTotal > 0">
            <v-pagination
                v-model="current_page"
                active-color="primary"
                density="comfortable"
                :length="Math.ceil(displayTotal / 30)"
                :total-visible="Utils.isSmartphoneVertical() ? 5 : 7"
                @update:model-value="$emit('update:page', $event)">
            </v-pagination>
        </div>
    </div>
</template>
<script lang="ts" setup>

import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import RecordedProgram from '@/components/Videos/RecordedProgram.vue';
import CMAnalysis from '@/services/CMAnalysis';
import { IRecordedProgram, MylistSortOrder, SortOrder } from '@/services/Videos';
import useUserStore from '@/stores/UserStore';
import Utils from '@/utils';

const router = useRouter();

// Props
const props = withDefaults(defineProps<{
    title: string;
    programs: IRecordedProgram[];
    total: number;
    page?: number;
    sortOrder?: SortOrder | MylistSortOrder;
    hideHeader?: boolean;
    hideSort?: boolean;
    hidePagination?: boolean;
    showMoreButton?: boolean;
    showBackButton?: boolean;
    showEmptyMessage?: boolean;
    emptyIcon?: string;
    emptyMessage?: string;
    emptySubMessage?: string;
    isLoading?: boolean;
    isSearching?: boolean;
    forMylist?: boolean;
    forWatchedHistory?: boolean;
}>(), {
    page: 1,
    sortOrder: 'desc',
    hideHeader: false,
    hideSort: false,
    hidePagination: false,
    showMoreButton: false,
    showBackButton: false,
    showEmptyMessage: true,
    emptyIcon: 'fluent:search-20-regular',
    emptyMessage: '録画番組が見つかりませんでした。',
    emptySubMessage: 'サーバー設定で録画フォルダのパスを<br class="d-sm-none">正しく設定できているか確認してください。',
    isLoading: false,
    isSearching: false,
    forMylist: false,
    forWatchedHistory: false,
});

// Emits
defineEmits<{
    (e: 'update:page', page: number): void;
    (e: 'update:sortOrder', order: SortOrder | MylistSortOrder): void;
    (e: 'more'): void;
}>();

// 現在のページ番号
const current_page = ref(props.page);

// 並び順
const sort_order = ref<SortOrder | MylistSortOrder>(props.sortOrder);

// 内部で管理するプログラムリスト
const displayPrograms = ref<IRecordedProgram[]>([...props.programs]);
// 内部で管理する合計数
const displayTotal = ref<number>(props.total);

// props の page が変更されたら current_page を更新
watch(() => props.page, (newPage) => {
    current_page.value = newPage;
});

// props の sortOrder が変更されたら sort_order を更新
watch(() => props.sortOrder, (newOrder) => {
    sort_order.value = newOrder;
});

// props の programs が変更されたら displayPrograms を更新
watch(() => props.programs, (newPrograms) => {
    displayPrograms.value = [...newPrograms];
});

// props の total が変更されたら displayTotal を更新
watch(() => props.total, (newTotal) => {
    displayTotal.value = newTotal;
});

// 選択モード (複数の録画番組を選んでまとめて CM 解析するための UI)
const user_store = useUserStore();
const select_mode = ref(false);
// 選択中の録画ファイル (RecordedVideo) の ID (ページをまたいでも保持する)
const selected_video_ids = ref<Set<number>>(new Set());
// CM 解析は管理者のみ実行できる。ヘッダーを表示しない一覧・視聴履歴・「もっと見る」付きの一覧では選択モードを出さない
const canSelect = computed(() => {
    return user_store.user?.is_admin === true && !props.hideHeader && !props.forWatchedHistory && !props.showMoreButton;
});

const toggleSelectMode = () => {
    select_mode.value = !select_mode.value;
    selected_video_ids.value.clear();
};

const toggleSelect = (program: IRecordedProgram) => {
    const video_id = program.recorded_video.id;
    if (selected_video_ids.value.has(video_id)) {
        selected_video_ids.value.delete(video_id);
    } else {
        selected_video_ids.value.add(video_id);
    }
};

// 表示中のページの、録画が完了している番組をすべて選択する
const selectAllInPage = () => {
    for (const program of displayPrograms.value) {
        if (program.recorded_video.status === 'Recorded') {
            selected_video_ids.value.add(program.recorded_video.id);
        }
    }
};

const analyzeSelected = async () => {
    await CMAnalysis.requestAnalysis([...selected_video_ids.value]);
    select_mode.value = false;
    selected_video_ids.value.clear();
};

// 録画ファイルが削除された時の処理
const handleProgramDeleted = (id: number) => {
    // 内部のプログラムリストから削除されたプログラムを除外
    displayPrograms.value = displayPrograms.value.filter(program => program.id !== id);
    // 合計数を1減らす
    displayTotal.value--;
};

</script>
<style lang="scss" scoped>

.recorded-program-list {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    min-width: 0;  // 親ページ側が縮んだとき、録画番組リスト自身も横幅を押し広げないようにする
    max-width: 100%;

    &--show-sort {
        .recorded-program-list__grid {
            @include smartphone-vertical {
                margin-top: 3px;
            }
        }
    }

    &__header {
        display: flex;
        align-items: center;
        min-width: 0;  // タイトルと操作ボタンの合計幅が狭い画面で親を押し広げないようにする
        @include smartphone-vertical {
            padding: 0px 8px;
        }
    }

    &__title {
        display: flex;
        align-items: center;
        position: relative;
        min-width: 0;  // 長い検索語や一覧名は省略表示へ倒し、右側の操作ボタンを画面内に残す
        font-size: 24px;
        font-weight: 700;
        padding-top: 8px;
        padding-bottom: 20px;
        @include smartphone-vertical {
            font-size: 22px;
            padding-bottom: 16px;
        }

        &-back {
            display: none;
            position: absolute;
            left: -8px;
            padding: 6px;
            border-radius: 50%;
            color: rgb(var(--v-theme-text));
            cursor: pointer;
            @include smartphone-vertical {
                display: flex;
            }

            & + .recorded-program-list__title-text {
                @include smartphone-vertical {
                    margin-left: 32px;
                }
            }
        }

        &-count {
            display: flex;
            align-items: center;
            flex-shrink: 0;
            padding-top: 8px;
            margin-left: 12px;
            font-size: 14px;
            font-weight: 400;
            color: rgb(var(--v-theme-text-darken-1));

            .spin {
                animation: spin 1.15s linear infinite;
            }

            @keyframes spin {
                from {
                    transform: rotate(0deg);
                }
                to {
                    transform: rotate(360deg);
                }
            }
        }

        &-text {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    }

    &__actions {
        display: flex;
        align-items: center;
        flex-shrink: 0;
        margin-left: auto;
        :deep(.v-field) {
            padding-right: 4px !important;
        }
        :deep(.v-field__input) {
            padding-left: 12px !important;
            padding-right: 0px !important;
        }

        .v-select {
            width: 103px;
            margin-left: 12px;
        }
        &--mylist {
            .v-select {
                width: 143px;
            }
        }
    }

    &__select-toggle {
        flex-shrink: 0;
        margin-left: 12px;
        padding: 0px 10px;
        font-size: 14px;
        letter-spacing: 0.02em;
        &--active {
            color: rgb(var(--v-theme-primary));
        }
    }

    &__selection {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 4px 8px;
        margin-bottom: 8px;
        padding: 6px 12px;
        border-radius: 8px;
        background: rgb(var(--v-theme-background-lighten-1));

        &-count {
            margin-right: auto;
            font-size: 14px;
            font-weight: 700;
        }
    }

    &__sort {
        :deep(.v-field__input) {
            font-size: 14px !important;
            padding-top: 6px !important;
            padding-bottom: 6px !important;
            min-height: unset !important;
        }
    }

    &__more {
        margin-bottom: 12px;
        padding: 0px 10px;
        font-size: 15px;
        letter-spacing: 0.05em;
        @include smartphone-vertical {
            margin-bottom: 6px;
        }
    }

    &__grid {
        display: flex;
        flex-direction: column;
        position: relative;
        width: 100%;
        min-width: 0;  // 仮想スクローラー領域も親幅に追従させ、内部カードの最小幅で膨らまないようにする
        max-width: 100%;
        background: rgb(var(--v-theme-background-lighten-1));
        border-radius: 8px;
        overflow: hidden;

        &--loading {
            .recorded-program-list__grid-content {
                visibility: hidden;
                opacity: 0;
            }
        }
        &--empty {
            height: 100%;
            min-height: 200px;
        }
        &--searching {
            height: 100%;
        }

        .recorded-program-list__grid-content {
            height: 100%;
            transition: visibility 0.2s ease, opacity 0.2s ease;
        }

        :deep(.recorded-program) {
            // 最後の項目以外の下にボーダーを追加
            &:not(:last-child) > .recorded-program__container {
                border-bottom: 1px solid rgb(var(--v-theme-background-lighten-2));
            }
        }
    }

    &__pagination {
        display: flex;
        justify-content: center;
        margin-top: 24px;
        @include smartphone-vertical {
            margin-top: 20px;
        }
    }

    &__empty {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        padding-top: 28px;
        padding-left: 12px;
        padding-right: 12px;
        padding-bottom: 40px;
        flex-grow: 1;
        visibility: hidden;
        opacity: 0;
        transition: visibility 0.2s ease, opacity 0.2s ease;

        &--show {
            visibility: visible;
            opacity: 1;
        }

        &-content {
            text-align: center;

            .recorded-program-list__empty-icon {
                color: rgb(var(--v-theme-text-darken-1));
            }

            h2 {
                font-size: 21px;
                @include tablet-vertical {
                    font-size: 19px !important;
                }
                @include smartphone-horizontal {
                    font-size: 19px !important;
                }
                @include smartphone-horizontal-short {
                    font-size: 19px !important;
                }
                @include smartphone-vertical {
                    font-size: 19px !important;
                    text-align: center;
                }
            }

            .recorded-program-list__empty-submessage {
                margin-top: 8px;
                color: rgb(var(--v-theme-text-darken-1));
                font-size: 15px;
                @include tablet-vertical {
                    font-size: 13px !important;
                    text-align: center;
                }
                @include smartphone-horizontal {
                    font-size: 13px !important;
                    text-align: center;
                }
                @include smartphone-vertical {
                    font-size: 13px !important;
                    text-align: center;
                    margin-top: 7px !important;
                    line-height: 1.65;
                }
            }
        }
    }
}

</style>
