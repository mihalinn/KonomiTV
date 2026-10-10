<template>
    <div class="route-container">
        <HeaderBar />
        <main>
            <Navigation />
            <div class="conditions-container-wrapper">
                <SPHeaderBar />
                <div class="conditions-container">
                    <Breadcrumbs :crumbs="[
                        { name: 'ホーム', path: '/' },
                        { name: '録画予約', path: '/reservations/' },
                        { name: '毎週録画 (キーワード自動予約)', path: '/reservations/conditions', disabled: true },
                    ]" />
                    <div class="conditions__header">
                        <h2 class="conditions__title">
                            <div v-ripple class="conditions__title-back" @click="$router.back()">
                                <Icon icon="fluent:chevron-left-12-filled" width="27px" />
                            </div>
                            <span class="conditions__title-text">毎週録画 (キーワード自動予約)</span>
                            <span class="conditions__title-count">
                                <Icon v-if="isLoading" icon="line-md:loading-twotone-loop" width="20px" height="20px" />
                                <template v-else>{{ conditions.length }}件</template>
                            </span>
                        </h2>
                    </div>
                    <div class="conditions__description">
                        番組表の番組詳細にある「毎週録画」から登録した条件の一覧です。条件に合う番組が放送されると、自動で録画予約が追加されます。
                    </div>

                    <div class="conditions__list">
                        <div v-if="!isLoading && conditions.length === 0" class="conditions__empty">
                            <Icon icon="fluent:calendar-repeat-16-regular" width="48px" height="48px" />
                            <div class="mt-2">毎週録画の条件はまだありません。</div>
                            <div class="text-caption mt-1">番組表で番組をクリックし、「毎週録画」から追加できます。</div>
                        </div>

                        <div v-for="condition in conditions" :key="condition.id" class="condition"
                            :class="{ 'condition--disabled': !condition.program_search_condition.is_enabled }">
                            <div class="condition__main">
                                <div class="condition__keyword">{{ condition.program_search_condition.keyword || '(キーワードなし)' }}</div>
                                <div class="condition__meta">
                                    <span class="condition__meta-item">
                                        <Icon icon="fluent:calendar-clock-16-regular" width="16px" height="16px" />
                                        {{ formatDateRanges(condition) }}
                                    </span>
                                    <span class="condition__meta-item">
                                        <Icon icon="fluent:tv-16-regular" width="16px" height="16px" />
                                        {{ formatChannels(condition) }}
                                    </span>
                                    <span class="condition__meta-item">
                                        <Icon icon="fluent:timer-16-regular" width="16px" height="16px" />
                                        予約中 {{ condition.reservation_count }}件
                                    </span>
                                </div>
                                <div v-if="condition.program_search_condition.note" class="condition__note">
                                    メモ: {{ condition.program_search_condition.note }}
                                </div>
                            </div>
                            <div class="condition__actions">
                                <v-switch :model-value="condition.program_search_condition.is_enabled" color="primary"
                                    density="compact" hide-details inset
                                    :loading="busyIds.has(condition.id)" :disabled="busyIds.has(condition.id)"
                                    :label="condition.program_search_condition.is_enabled ? '有効' : '無効'"
                                    @update:model-value="toggleEnabled(condition, $event === true)" />
                                <v-btn variant="text" color="primary" class="px-2" :disabled="busyIds.has(condition.id)"
                                    @click="openEdit(condition)">
                                    <Icon icon="fluent:edit-16-regular" width="20px" height="20px" />
                                    <span class="ml-1">編集</span>
                                </v-btn>
                                <v-btn variant="text" color="error" class="px-2" :disabled="busyIds.has(condition.id)"
                                    @click="deleteTarget = condition">
                                    <Icon icon="fluent:delete-16-regular" width="20px" height="20px" />
                                    <span class="ml-1">削除</span>
                                </v-btn>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>

        <!-- 簡易編集ダイアログ -->
        <v-dialog :model-value="editTarget !== null" max-width="600" @update:model-value="editTarget = null">
            <v-card v-if="editTarget">
                <v-card-title class="d-flex justify-center pt-6 font-weight-bold">
                    毎週録画の編集
                </v-card-title>
                <v-card-text class="pt-2 pb-0">
                    <v-text-field v-model="form.keyword" label="番組名キーワード" variant="outlined"
                        density="comfortable" hide-details="auto" />
                    <v-text-field v-model="form.excludeKeyword" class="mt-4" label="除外キーワード (任意)" variant="outlined"
                        density="comfortable" hide-details="auto" />

                    <!-- チャンネル -->
                    <v-select v-if="form.channelEditable" v-model="form.channelKey" class="mt-4" label="チャンネル"
                        :items="channelItems" item-title="title" item-value="value" variant="outlined"
                        density="comfortable" hide-details="auto" />
                    <div v-else class="text-body-2 text-text-darken-1 mt-4">
                        チャンネル: {{ formatChannels(editTarget) }} (複数指定のため、ここでは変更できません)
                    </div>

                    <!-- 曜日・時間帯 -->
                    <template v-if="form.timeEditable">
                        <v-switch v-model="form.anyTime" class="mt-2" color="primary" hide-details density="comfortable"
                            label="曜日・時間帯を指定しない (毎日・全時間帯)" />
                        <div v-if="!form.anyTime" class="condition-edit__time-row">
                            <v-select v-model="form.dayOfWeek" label="曜日" :items="dayItems" item-title="title"
                                item-value="value" variant="outlined" density="comfortable" hide-details />
                            <v-text-field v-model="form.startTime" type="time" label="この時刻から" variant="outlined"
                                density="comfortable" hide-details />
                            <v-text-field v-model="form.endTime" type="time" label="この時刻まで" variant="outlined"
                                density="comfortable" hide-details />
                        </div>
                        <div v-if="!form.anyTime" class="text-caption text-text-darken-1 mt-1">
                            番組の「放送開始時刻」がこの範囲に入るものが対象です。終了が開始より早い場合は翌日の時刻として扱います。
                        </div>
                    </template>
                    <div v-else class="text-body-2 text-text-darken-1 mt-2">
                        時間帯: {{ formatDateRanges(editTarget) }} (複雑な指定のため、ここでは変更できません)
                    </div>

                    <v-select v-model="form.duplicateScope" class="mt-4" label="録画済みの同名番組" :items="duplicateItems"
                        item-title="title" item-value="value" variant="outlined" density="comfortable"
                        hide-details="auto" />

                    <!-- 保存先フォルダ -->
                    <v-text-field v-if="form.folderEditable" v-model="form.folderPath" class="mt-4"
                        label="録画フォルダ (空欄でデフォルト)" variant="outlined" density="comfortable" hide-details="auto"
                        placeholder="例: D:\TV-Record\番組名" />
                    <div v-else class="text-body-2 text-text-darken-1 mt-4">
                        録画フォルダが複数指定されているため、ここでは変更できません。
                    </div>
                    <v-text-field v-model="form.note" class="mt-4" label="メモ (任意)" variant="outlined"
                        density="comfortable" hide-details="auto" />
                </v-card-text>
                <v-card-actions class="pt-4 px-6 pb-6">
                    <v-spacer></v-spacer>
                    <v-btn color="text" variant="text" @click="editTarget = null">キャンセル</v-btn>
                    <v-btn class="px-3" color="secondary" variant="flat" :loading="isSaving"
                        :disabled="form.keyword.trim() === ''" @click="saveEdit">
                        <Icon icon="fluent:save-16-regular" width="18px" height="18px" />
                        <span class="ml-1">保存</span>
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <v-dialog :model-value="deleteTarget !== null" max-width="520" @update:model-value="deleteTarget = null">
            <v-card v-if="deleteTarget">
                <v-card-title class="d-flex justify-center pt-6 font-weight-bold">
                    毎週録画の条件を削除しますか？
                </v-card-title>
                <v-card-text class="pt-2 pb-0">
                    <div class="text-h6 text-text mb-2">{{ deleteTarget.program_search_condition.keyword }}</div>
                    <div class="text-body-2 text-text-darken-1">
                        {{ formatDateRanges(deleteTarget) }} / {{ formatChannels(deleteTarget) }}
                    </div>
                    <div class="text-body-2 mt-3">
                        今後は自動で予約されなくなります。すでに追加済みの録画予約は削除されないため、
                        不要な場合は「録画予約」画面から個別に削除してください。
                    </div>
                </v-card-text>
                <v-card-actions class="pt-4 px-6 pb-6">
                    <v-spacer></v-spacer>
                    <v-btn color="text" variant="text" @click="deleteTarget = null">キャンセル</v-btn>
                    <v-btn class="px-3" color="error" variant="flat" :loading="isDeleting" @click="confirmDelete">
                        <Icon icon="fluent:delete-20-regular" width="18px" height="18px" />
                        <span class="ml-1">条件を削除</span>
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>
<script lang="ts" setup>

import { onMounted, ref, toRaw } from 'vue';

import Breadcrumbs from '@/components/Breadcrumbs.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import Message from '@/message';
import Channels from '@/services/Channels';
import { type IProgramSearchCondition } from '@/services/Programs';
import ReservationConditions, { type IReservationCondition } from '@/services/ReservationConditions';

const DAY_OF_WEEK_LABELS = ['日', '月', '火', '水', '木', '金', '土'];

const conditions = ref<IReservationCondition[]>([]);
const isLoading = ref(true);
const busyIds = ref<Set<number>>(new Set());
const deleteTarget = ref<IReservationCondition | null>(null);
const isDeleting = ref(false);

// "network_id:service_id" -> チャンネル名
const channelNames = ref<Map<string, string>>(new Map());
const baseChannelItems = ref<{ title: string; value: string }[]>([]);

const fetchAll = async () => {
    const [result, channels] = await Promise.all([
        ReservationConditions.fetchReservationConditions(),
        Channels.fetchAllChannels(),
    ]);
    if (channels) {
        const map = new Map<string, string>();
        const items: { title: string; value: string }[] = [];
        for (const list of Object.values(channels)) {
            for (const channel of list) {
                map.set(`${channel.network_id}:${channel.service_id}`, channel.name);
                if (channel.transport_stream_id !== null) {
                    items.push({
                        title: channel.name,
                        value: `${channel.network_id}:${channel.transport_stream_id}:${channel.service_id}`,
                    });
                }
            }
        }
        channelNames.value = map;
        baseChannelItems.value = items;
    }
    if (result) {
        conditions.value = result.reservation_conditions;
    }
    isLoading.value = false;
};

const pad = (n: number) => String(n).padStart(2, '0');

const formatDateRanges = (condition: IReservationCondition): string => {
    const ranges = condition.program_search_condition.date_ranges;
    if (ranges === null || ranges.length === 0) return '毎日・全時間帯';
    const text = ranges.map((r) => {
        const start = `${DAY_OF_WEEK_LABELS[r.start_day_of_week]} ${pad(r.start_hour)}:${pad(r.start_minute)}`;
        const end = r.end_day_of_week === r.start_day_of_week
            ? `${pad(r.end_hour)}:${pad(r.end_minute)}`
            : `${DAY_OF_WEEK_LABELS[r.end_day_of_week]} ${pad(r.end_hour)}:${pad(r.end_minute)}`;
        return `${start}〜${end}`;
    }).join(' / ');
    return (condition.program_search_condition.is_exclude_date_ranges ? '除外: ' : '毎週 ') + text;
};

const formatChannels = (condition: IReservationCondition): string => {
    const services = condition.program_search_condition.service_ranges;
    if (services === null || services.length === 0) return '全チャンネル';
    const names = services.map((s) => channelNames.value.get(`${s.network_id}:${s.service_id}`) ?? `SID ${s.service_id}`);
    if (names.length <= 3) return names.join('、');
    return `${names.length}チャンネル`;
};

// ---- 簡易編集 ----

const dayItems = DAY_OF_WEEK_LABELS.map((label, value) => ({ title: `${label}曜日`, value }));
const duplicateItems = [
    { title: '気にせず録画する', value: 'None' },
    { title: '同じチャンネルで録画済みならスキップ', value: 'SameChannelOnly' },
    { title: 'どのチャンネルでも録画済みならスキップ', value: 'AllChannels' },
];

const editTarget = ref<IReservationCondition | null>(null);
const isSaving = ref(false);
const channelItems = ref<{ title: string; value: string }[]>([]);

const form = ref({
    keyword: '',
    excludeKeyword: '',
    note: '',
    channelEditable: true,
    channelKey: '',
    timeEditable: true,
    anyTime: false,
    dayOfWeek: 0,
    startTime: '00:00',
    endTime: '00:00',
    duplicateScope: 'None' as 'None' | 'SameChannelOnly' | 'AllChannels',
    folderEditable: true,
    folderPath: '',
});

const serviceKey = (nid: number, tsid: number, sid: number) => `${nid}:${tsid}:${sid}`;

const openEdit = (condition: IReservationCondition) => {
    const c = condition.program_search_condition;
    const f = form.value;
    f.keyword = c.keyword;
    f.excludeKeyword = c.exclude_keyword;
    f.note = c.note;
    f.duplicateScope = c.duplicate_title_check_scope;

    // チャンネル: 0件=全チャンネル扱い / 1件=選択可 / 2件以上=変更不可
    const services = c.service_ranges;
    f.channelEditable = services === null || services.length <= 1;
    f.channelKey = services !== null && services.length === 1
        ? serviceKey(services[0].network_id, services[0].transport_stream_id, services[0].service_id)
        : 'ALL';
    // 選択肢に現在のチャンネルが無ければ補う
    const items = [{ title: '全チャンネル', value: 'ALL' }, ...baseChannelItems.value];
    if (services !== null && services.length === 1 && !items.some((i) => i.value === f.channelKey)) {
        items.push({ title: formatChannels(condition), value: f.channelKey });
    }
    channelItems.value = items;

    // 時間帯: 指定なし / 1件(同じ曜日 or 翌日にまたぐ)なら編集可 / それ以外は変更不可
    const ranges = c.date_ranges;
    if (ranges === null || ranges.length === 0) {
        f.timeEditable = true;
        f.anyTime = true;
        f.dayOfWeek = 0;
        f.startTime = '00:00';
        f.endTime = '00:00';
    } else if (ranges.length === 1 && !c.is_exclude_date_ranges
        && (ranges[0].end_day_of_week === ranges[0].start_day_of_week
            || ranges[0].end_day_of_week === (ranges[0].start_day_of_week + 1) % 7)) {
        const r = ranges[0];
        f.timeEditable = true;
        f.anyTime = false;
        f.dayOfWeek = r.start_day_of_week;
        f.startTime = `${pad(r.start_hour)}:${pad(r.start_minute)}`;
        f.endTime = `${pad(r.end_hour)}:${pad(r.end_minute)}`;
    } else {
        f.timeEditable = false;
    }

    // 録画フォルダ: 0件 or 1件なら編集可
    const folders = condition.record_settings.recording_folders;
    f.folderEditable = folders.length <= 1;
    f.folderPath = folders.length === 1 ? folders[0].recording_folder_path : '';

    editTarget.value = condition;
};

const saveEdit = async () => {
    const target = editTarget.value;
    if (!target || isSaving.value) return;
    const f = form.value;
    const keyword = f.keyword.trim();
    if (keyword === '') return;

    const condition: IProgramSearchCondition = {
        ...target.program_search_condition,
        keyword,
        exclude_keyword: f.excludeKeyword.trim(),
        note: f.note.trim(),
        duplicate_title_check_scope: f.duplicateScope,
    };

    if (f.channelEditable) {
        if (f.channelKey === 'ALL') {
            condition.service_ranges = null;
        } else {
            const [nid, tsid, sid] = f.channelKey.split(':').map(Number);
            condition.service_ranges = [{ network_id: nid, transport_stream_id: tsid, service_id: sid }];
        }
    }

    if (f.timeEditable) {
        if (f.anyTime) {
            condition.date_ranges = null;
        } else {
            const [sh, sm] = f.startTime.split(':').map(Number);
            const [eh, em] = f.endTime.split(':').map(Number);
            if ([sh, sm, eh, em].some((n) => Number.isNaN(n))) {
                Message.error('時刻を正しく入力してください。');
                return;
            }
            const crossesMidnight = eh * 60 + em < sh * 60 + sm;
            condition.date_ranges = [{
                start_day_of_week: f.dayOfWeek, start_hour: sh, start_minute: sm,
                end_day_of_week: crossesMidnight ? (f.dayOfWeek + 1) % 7 : f.dayOfWeek, end_hour: eh, end_minute: em,
            }];
            condition.is_exclude_date_ranges = false;
        }
    }

    const recordSettings = JSON.parse(JSON.stringify(toRaw(target.record_settings))) as typeof target.record_settings;
    if (f.folderEditable) {
        const path = f.folderPath.trim();
        if (path === '') {
            recordSettings.recording_folders = [];
        } else if (recordSettings.recording_folders.length === 1) {
            recordSettings.recording_folders[0].recording_folder_path = path;
        } else {
            recordSettings.recording_folders = [{
                recording_folder_path: path,
                recording_file_name_template: null,
                is_oneseg_separate_recording_folder: false,
            }];
        }
    }

    isSaving.value = true;
    try {
        const updated = await ReservationConditions.updateReservationCondition(target.id, condition, recordSettings);
        if (updated) {
            const index = conditions.value.findIndex((x) => x.id === target.id);
            if (index !== -1) conditions.value[index] = updated;
            Message.success('毎週録画の条件を更新しました。');
            editTarget.value = null;
        }
    } finally {
        isSaving.value = false;
    }
};

const toggleEnabled = async (condition: IReservationCondition, enabled: boolean) => {
    busyIds.value = new Set(busyIds.value).add(condition.id);
    try {
        const updated = await ReservationConditions.updateReservationCondition(
            condition.id,
            { ...condition.program_search_condition, is_enabled: enabled },
            condition.record_settings,
        );
        if (updated) {
            const index = conditions.value.findIndex((c) => c.id === condition.id);
            if (index !== -1) conditions.value[index] = updated;
            Message.success(enabled ? '毎週録画を有効にしました。' : '毎週録画を無効にしました。');
        }
    } finally {
        const next = new Set(busyIds.value);
        next.delete(condition.id);
        busyIds.value = next;
    }
};

const confirmDelete = async () => {
    if (!deleteTarget.value || isDeleting.value) return;
    isDeleting.value = true;
    try {
        const id = deleteTarget.value.id;
        const ok = await ReservationConditions.deleteReservationCondition(id);
        if (ok) {
            conditions.value = conditions.value.filter((c) => c.id !== id);
            Message.success('毎週録画の条件を削除しました。');
            deleteTarget.value = null;
        }
    } finally {
        isDeleting.value = false;
    }
};

onMounted(fetchAll);

</script>
<style lang="scss" scoped>

.conditions-container-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
}

.conditions-container {
    display: flex;
    flex-direction: column;
    width: 100%;
    padding: 20px;
    margin: 0 auto;
    min-width: 0;
    max-width: 1000px;

    @include smartphone-horizontal {
        padding: 16px 20px !important;
    }
    @include smartphone-horizontal-short {
        padding: 16px !important;
    }
    @include smartphone-vertical {
        padding: 8px 8px 20px !important;
    }
}

.conditions {
    &__title {
        display: flex;
        align-items: center;
        position: relative;
        min-width: 0;
        font-size: 24px;
        font-weight: 700;
        padding-top: 8px;
        padding-bottom: 8px;
        @include smartphone-vertical {
            font-size: 20px;
        }

        &-text {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
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
            & + .conditions__title-text {
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
        }
    }

    &__description {
        margin-bottom: 16px;
        font-size: 13.5px;
        line-height: 1.6;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__list {
        display: flex;
        flex-direction: column;
        gap: 1px;
        background: rgb(var(--v-theme-background-lighten-1));
        border-radius: 8px;
        overflow: hidden;
        min-width: 0;
    }

    &__empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 48px 16px;
        color: rgb(var(--v-theme-text-darken-1));
        text-align: center;
    }
}

.condition {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 18px;
    min-width: 0;
    background: rgb(var(--v-theme-background-lighten-1));

    @include smartphone-vertical {
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        padding: 12px 14px;
    }

    &--disabled &__keyword,
    &--disabled &__meta {
        opacity: 0.5;
    }

    &__main {
        flex-grow: 1;
        min-width: 0;
    }

    &__keyword {
        font-size: 17px;
        font-weight: 700;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    &__meta {
        display: flex;
        flex-wrap: wrap;
        gap: 4px 16px;
        margin-top: 4px;
        font-size: 13px;
        color: rgb(var(--v-theme-text-darken-1));

        &-item {
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
    }

    &__note {
        margin-top: 2px;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__actions {
        display: flex;
        align-items: center;
        flex-shrink: 0;
        gap: 12px;
        @include smartphone-vertical {
            justify-content: space-between;
        }
    }
}

.condition-edit__time-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
    margin-top: 12px;

    @include smartphone-vertical {
        grid-template-columns: 1fr;
    }
}
</style>
