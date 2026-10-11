<template>
    <div class="series-container" ref="container">
        <div class="series-header" v-if="state === 'ready'">
            <h2 class="series-header__name">{{series_name}}</h2>
            <div class="series-header__count">全 {{programs.length}} 件 ・ {{current_index + 1}} 件目を再生中</div>
        </div>
        <div class="series-message" v-if="state === 'loading'">
            <Icon icon="line-md:loading-twotone-loop" width="22px" height="22px" class="mr-2" />
            <span>読み込み中…</span>
        </div>
        <div class="series-message" v-else-if="state === 'error'">
            <div>同じシリーズの録画を取得できませんでした。</div>
            <v-btn class="mt-3" variant="outlined" color="primary" @click="load(true)">再試行</v-btn>
        </div>
        <div class="series-list" v-else-if="state === 'ready'">
            <component v-for="program in programs" :key="program.id"
                :is="program.recorded_video.status === 'Recorded' && program.id !== current_id ? 'router-link' : 'div'"
                v-bind="program.recorded_video.status === 'Recorded' && program.id !== current_id ? {to: `/videos/watch/${program.id}`} : {}"
                v-ripple class="series-item" :class="{'series-item--current': program.id === current_id}">
                <div class="series-item__thumbnail">
                    <img class="series-item__thumbnail-image" loading="lazy" decoding="async"
                        :src="`${Utils.api_base_url}/videos/${program.id}/thumbnail`">
                    <div class="series-item__duration">{{ProgramUtils.getProgramDuration(program)}}</div>
                </div>
                <div class="series-item__body">
                    <div class="series-item__title">
                        <span class="series-item__now" v-if="program.id === current_id">再生中</span>
                        <span class="series-item__recording" v-else-if="program.recorded_video.status === 'Recording'">録画中</span>
                        {{program.subtitle || program.title}}
                    </div>
                    <div class="series-item__meta">{{formatDateTime(program.start_time)}}</div>
                </div>
            </component>
        </div>
    </div>
</template>
<script lang="ts" setup>

import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { fetchAllPrograms, getSeriesOf } from '@/services/SeriesFolder';
import { IRecordedProgram } from '@/services/Videos';
import usePlayerStore from '@/stores/PlayerStore';
import Utils, { ProgramUtils } from '@/utils';

const player_store = usePlayerStore();
const container = ref<HTMLElement | null>(null);

const state = ref<'idle' | 'loading' | 'ready' | 'error'>('idle');
const all_programs = ref<IRecordedProgram[]>([]);

const current_id = computed(() => player_store.recorded_program.id);
const series = computed(() => {
    if (current_id.value < 0) return null;
    const current = all_programs.value.find(p => p.id === current_id.value);
    return current ? getSeriesOf(all_programs.value, current) : null;
});
const programs = computed(() => series.value?.programs ?? []);
const series_name = computed(() => series.value?.name ?? '');
const current_index = computed(() => programs.value.findIndex(p => p.id === current_id.value));

const WEEKDAYS = ['日', '月', '火', '水', '木', '金', '土'];
const formatDateTime = (iso: string): string => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} (${WEEKDAYS[d.getDay()]}) ${hh}:${mm}`;
};

// 再生中の回が見える位置までスクロールする
const scrollToCurrent = async () => {
    await nextTick();
    const el = container.value;
    const item = el?.querySelector<HTMLElement>('.series-item--current');
    if (!el || !item) return;
    el.scrollTop = Math.max(0, item.offsetTop - (el.clientHeight - item.offsetHeight) / 2);
};

const load = async (force: boolean = false) => {
    if (current_id.value < 0) return;
    state.value = 'loading';
    try {
        all_programs.value = await fetchAllPrograms(force);
        // 録画直後などで一覧のキャッシュにまだ無い場合は取り直す
        if (!all_programs.value.some(p => p.id === current_id.value) && force === false) {
            all_programs.value = await fetchAllPrograms(true);
        }
        state.value = series.value === null ? 'error' : 'ready';
    } catch (error) {
        console.error(error);
        state.value = 'error';
        return;
    }
    await scrollToCurrent();
};

// タブが開かれたとき・再生する録画が切り替わったときに読み込む (最初のタブ表示までは取得しない)
const is_active = () => player_store.video_panel_active_tab === 'Series';
watch(() => player_store.video_panel_active_tab, async () => {
    if (!is_active()) return;
    if (state.value === 'idle' || state.value === 'error') await load();
    else await scrollToCurrent();
});
watch(current_id, async () => {
    if (!is_active() && state.value === 'idle') return;
    await load();
});
onMounted(() => {
    if (is_active()) load();
});

</script>
<style lang="scss" scoped>

.series-container {
    padding-bottom: 16px;
    overflow-y: auto;
    @include tablet-vertical {
        padding-top: 20px;
    }
    @include smartphone-horizontal {
        padding-top: 12px;
    }
    @include smartphone-vertical {
        padding-top: 14px;
    }
}

.series-header {
    padding: 0 16px 10px;
    @include tablet-vertical {
        padding: 0 24px 10px;
    }

    &__name {
        font-size: 17px;
        font-weight: bold;
        line-height: 1.4;
        word-break: break-word;
    }

    &__count {
        margin-top: 2px;
        font-size: 12.5px;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

.series-message {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 16px;
    color: rgb(var(--v-theme-text-darken-1));
    text-align: center;
}

.series-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 0 8px;
    @include tablet-vertical {
        padding: 0 16px;
    }
}

.series-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px;
    border-radius: 8px;
    color: rgb(var(--v-theme-text));
    text-decoration: none;
    cursor: pointer;
    transition: background-color 0.15s;

    &:hover {
        background: rgb(var(--v-theme-background-lighten-1));
    }

    &--current {
        background: rgb(var(--v-theme-background-lighten-1));
        box-shadow: inset 3px 0 0 rgb(var(--v-theme-primary));
        cursor: default;
    }

    &__thumbnail {
        position: relative;
        flex: none;
        width: 116px;
        aspect-ratio: 16 / 9;
        border-radius: 6px;
        overflow: hidden;
        background: rgb(var(--v-theme-background-lighten-2));
    }

    &__thumbnail-image {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    &__duration {
        position: absolute;
        right: 4px;
        bottom: 4px;
        padding: 1px 5px;
        border-radius: 3px;
        background: rgba(0, 0, 0, 0.75);
        color: #fff;
        font-size: 11px;
        line-height: 1.4;
    }

    &__body {
        flex: 1;
        min-width: 0;
    }

    &__title {
        font-size: 14px;
        font-weight: 500;
        line-height: 1.4;
        word-break: break-word;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    &__meta {
        margin-top: 3px;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__now, &__recording {
        display: inline-block;
        margin-right: 6px;
        padding: 0 6px;
        border-radius: 3px;
        font-size: 11px;
        font-weight: bold;
        line-height: 1.6;
        vertical-align: 1px;
    }
    &__now {
        background: rgb(var(--v-theme-primary));
        color: #fff;
    }
    &__recording {
        background: rgb(var(--v-theme-secondary));
        color: #fff;
    }
}

</style>
