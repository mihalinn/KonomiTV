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

import { onMounted, ref } from 'vue';

import Breadcrumbs from '@/components/Breadcrumbs.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import Message from '@/message';
import Channels from '@/services/Channels';
import ReservationConditions, { type IReservationCondition } from '@/services/ReservationConditions';

const DAY_OF_WEEK_LABELS = ['日', '月', '火', '水', '木', '金', '土'];

const conditions = ref<IReservationCondition[]>([]);
const isLoading = ref(true);
const busyIds = ref<Set<number>>(new Set());
const deleteTarget = ref<IReservationCondition | null>(null);
const isDeleting = ref(false);

// "network_id:service_id" -> チャンネル名
const channelNames = ref<Map<string, string>>(new Map());

const fetchAll = async () => {
    const [result, channels] = await Promise.all([
        ReservationConditions.fetchReservationConditions(),
        Channels.fetchAllChannels(),
    ]);
    if (channels) {
        const map = new Map<string, string>();
        for (const list of Object.values(channels)) {
            for (const channel of list) {
                map.set(`${channel.network_id}:${channel.service_id}`, channel.name);
            }
        }
        channelNames.value = map;
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

</style>
