<template>
    <div class="route-container">
        <HeaderBar />
        <main>
            <Navigation />
            <div class="genre-list-wrapper">
                <SPHeaderBar />
                <div class="genre-list">
                    <Breadcrumbs :crumbs="[
                        { name: 'ホーム', path: '/' },
                        { name: '番組表', path: '/timetable/' },
                        { name: 'ジャンル別一覧', path: '/timetable/genre', disabled: true },
                    ]" />

                    <!-- ジャンル選択 -->
                    <div class="genre-list__genres">
                        <button v-for="genre in GENRES" :key="genre" type="button" class="genre-chip"
                            :class="{'genre-chip--active': genre === selectedGenre}"
                            :style="{'--genre-color': genreColor(genre)}"
                            @click="selectGenre(genre)">
                            <span class="genre-chip__dot"></span>
                            <span>{{genre}}</span>
                        </button>
                    </div>

                    <!-- 絞り込み -->
                    <div class="genre-list__filters">
                        <v-select class="genre-list__select" variant="outlined" density="compact" hide-details
                            :items="RANGE_ITEMS" v-model="selectedRange" />
                        <v-select class="genre-list__select" variant="outlined" density="compact" hide-details
                            :items="TYPE_ITEMS" v-model="selectedType" />
                        <div class="genre-list__count" v-if="!is_loading">{{filteredPrograms.length}}件</div>
                    </div>

                    <div class="genre-list__message" v-if="is_loading">読み込み中…</div>
                    <div class="genre-list__message" v-else-if="filteredPrograms.length === 0">
                        この条件に合う番組はありません。
                    </div>

                    <!-- 日付ごとの一覧 -->
                    <section class="genre-day" v-for="day in days" :key="day.key">
                        <h3 class="genre-day__title">{{day.label}}</h3>
                        <div class="genre-row" v-for="program in day.programs" :key="program.id" v-ripple
                            :style="{'--genre-color': programColor(program)}"
                            @click="openDrawer(program)">
                            <div class="genre-row__time">
                                <span class="genre-row__start">{{formatTime(program.start_time)}}</span>
                                <span class="genre-row__duration">{{Math.round(program.duration / 60)}}分</span>
                            </div>
                            <div class="genre-row__body">
                                <div class="genre-row__title">
                                    <span class="genre-row__now" v-if="isOnAir(program)">放送中</span>{{program.title}}
                                </div>
                                <div class="genre-row__channel">{{channelName(program)}}</div>
                            </div>
                            <Icon v-if="reservationMap.has(program.id)" class="genre-row__reserved"
                                icon="fluent:record-16-filled" width="16px" />
                        </div>
                    </section>
                </div>
            </div>
        </main>
        <ReservationDetailDrawer
            v-model="isDrawerOpen"
            :reservation="drawerReservation"
            :isPastProgram="false"
            @added="updateReservations"
            @updated="updateReservations"
            @deleted="updateReservations" />
    </div>
</template>
<script lang="ts" setup>

import { computed, onMounted, ref, toRaw, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import Breadcrumbs from '@/components/Breadcrumbs.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import ReservationDetailDrawer from '@/components/Reservations/ReservationDetailDrawer.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import { IChannel } from '@/services/Channels';
import Programs, { IProgram, IProgramSearchCondition } from '@/services/Programs';
import Reservations, { IRecordSettings, IRecordSettingsDefault, IReservation } from '@/services/Reservations';
import useChannelsStore from '@/stores/ChannelsStore';
import useSettingsStore from '@/stores/SettingsStore';
import useUserStore from '@/stores/UserStore';
import { dayjs } from '@/utils';
import { TimeTableUtils } from '@/utils/TimeTableUtils';

// ジャンル一覧 (番組表設定のジャンル色と同じ名前・順序)
const GENRES = [
    'ニュース・報道', '情報・ワイドショー', 'ドキュメンタリー・教養', 'スポーツ', 'ドラマ', 'アニメ・特撮',
    'バラエティ', '音楽', '映画', '劇場・公演', '趣味・教育', '福祉', 'その他',
];
const DEFAULT_GENRE = 'アニメ・特撮';

const RANGE_ITEMS = [
    { title: '今日', value: 'today' },
    { title: '3日間', value: '3days' },
    { title: '1週間', value: 'week' },
    { title: 'すべて', value: 'all' },
];
const TYPE_ITEMS = [
    { title: 'すべての放送', value: 'all' },
    { title: '地デジ', value: 'GR' },
    { title: 'BS', value: 'BS' },
    { title: 'CS', value: 'CS' },
];
const WEEKDAYS = ['日', '月', '火', '水', '木', '金', '土'];

const route = useRoute();
const router = useRouter();
const channelsStore = useChannelsStore();
const settingsStore = useSettingsStore();

const selectedGenre = ref<string>(DEFAULT_GENRE);
const selectedRange = ref('week');
const selectedType = ref('all');

const programs = ref<IProgram[]>([]);
const is_loading = ref(true);
const reservationMap = ref<Map<string, IReservation>>(new Map());
const defaultRecordSettings = ref<IRecordSettings | null>(null);

const isDrawerOpen = ref(false);
const drawerReservation = ref<IReservation | null>(null);

const channelMap = computed(() => {
    const channels = Object.values(channelsStore.channels_list).flat();
    return new Map(channels.map((channel) => [channel.id, channel]));
});

const genreColor = (genre: string | undefined): string => {
    return TimeTableUtils.getGenreColors(genre, settingsStore.settings.timetable_genre_colors).highlight;
};
const programColor = (program: IProgram): string => genreColor(program.genres?.[0]?.major);

const channelName = (program: IProgram): string => channelMap.value.get(program.channel_id)?.name ?? program.channel_id;
const formatTime = (time: string): string => dayjs(time).format('HH:mm');
const isOnAir = (program: IProgram): boolean => {
    const now = dayjs();
    return !dayjs(program.start_time).isAfter(now) && dayjs(program.end_time).isAfter(now);
};

// 放送日 (4時区切り) ごとの見出し
const dayKey = (time: string): string => dayjs(time).subtract(4, 'hour').format('YYYY-MM-DD');
const dayLabel = (key: string): string => {
    const d = dayjs(key);
    const diff = d.startOf('day').diff(dayjs().subtract(4, 'hour').startOf('day'), 'day');
    const suffix = diff === 0 ? ' (今日)' : diff === 1 ? ' (明日)' : '';
    return `${d.month() + 1}/${d.date()}(${WEEKDAYS[d.day()]})${suffix}`;
};

const filteredPrograms = computed<IProgram[]>(() => {
    const now = dayjs();
    let limit: ReturnType<typeof dayjs> | null = null;
    // 「今日」は放送日の区切り (翌4時) まで
    if (selectedRange.value === 'today') {
        const boundary = now.hour() < 4 ? now.startOf('day').add(4, 'hour') : now.startOf('day').add(1, 'day').add(4, 'hour');
        limit = boundary;
    } else if (selectedRange.value === '3days') {
        limit = now.add(3, 'day');
    } else if (selectedRange.value === 'week') {
        limit = now.add(7, 'day');
    }
    return programs.value
        .filter((program) => dayjs(program.end_time).isAfter(now))
        .filter((program) => limit === null || dayjs(program.start_time).isBefore(limit))
        .filter((program) => selectedType.value === 'all' || channelMap.value.get(program.channel_id)?.type === selectedType.value)
        .sort((a, b) => dayjs(a.start_time).valueOf() - dayjs(b.start_time).valueOf());
});

const days = computed(() => {
    const result: { key: string; label: string; programs: IProgram[] }[] = [];
    for (const program of filteredPrograms.value) {
        const key = dayKey(program.start_time);
        const last = result[result.length - 1];
        if (last !== undefined && last.key === key) {
            last.programs.push(program);
        } else {
            result.push({ key, label: dayLabel(key), programs: [program] });
        }
    }
    return result;
});

const createSearchCondition = (genre: string): IProgramSearchCondition => ({
    is_enabled: true,
    keyword: '',
    exclude_keyword: '',
    note: '',
    is_title_only: false,
    is_case_sensitive: false,
    is_fuzzy_search_enabled: false,
    is_regex_search_enabled: false,
    service_ranges: null,
    genre_ranges: [{ major: genre, middle: 'すべて' }],
    is_exclude_genre_ranges: false,
    date_ranges: null,
    is_exclude_date_ranges: false,
    duration_range_min: null,
    duration_range_max: null,
    broadcast_type: 'All',
    duplicate_title_check_scope: 'None',
    duplicate_title_check_period_days: 6,
});

const fetchPrograms = async () => {
    is_loading.value = true;
    const result = await Programs.searchPrograms(createSearchCondition(selectedGenre.value));
    programs.value = result?.programs ?? [];
    is_loading.value = false;
};

const selectGenre = async (genre: string) => {
    if (genre === selectedGenre.value) return;
    await router.replace({ query: { ...route.query, genre } });
};

const updateReservations = async () => {
    const result = await Reservations.fetchReservations();
    if (result !== null) {
        reservationMap.value = new Map(result.reservations.map((reservation) => [reservation.program.id, reservation]));
    }
};

const createFallbackChannel = (program: IProgram): IChannel => ({
    id: program.channel_id,
    display_channel_id: program.channel_id,
    network_id: program.network_id,
    service_id: program.service_id,
    transport_stream_id: null,
    remocon_id: 0,
    channel_number: '---',
    type: 'GR',
    name: program.channel_id,
    terrestrial_regions: null,
    jikkyo_force: null,
    is_subchannel: false,
    is_radiochannel: false,
    is_watchable: true,
});

const openDrawer = (program: IProgram) => {
    const reservation = reservationMap.value.get(program.id);
    if (reservation !== undefined) {
        drawerReservation.value = reservation;
    } else {
        const recordSettings = defaultRecordSettings.value !== null
            ? structuredClone(toRaw(defaultRecordSettings.value))
            : structuredClone(toRaw(IRecordSettingsDefault));
        drawerReservation.value = {
            id: -1,
            channel: channelMap.value.get(program.channel_id) ?? createFallbackChannel(program),
            program,
            is_recording_in_progress: false,
            recording_availability: 'Full',
            comment: '',
            scheduled_recording_file_name: '',
            estimated_recording_file_size: 0,
            record_settings: recordSettings,
        };
    }
    isDrawerOpen.value = true;
};

// URL (?genre=...) と選択状態を同期
const syncFromRoute = () => {
    const g = route.query.genre;
    selectedGenre.value = typeof g === 'string' && GENRES.includes(g) ? g : DEFAULT_GENRE;
};

watch(() => route.query.genre, async () => {
    syncFromRoute();
    await fetchPrograms();
});

onMounted(async () => {
    syncFromRoute();
    const userStore = useUserStore();
    await Promise.all([
        userStore.fetchUser(),
        channelsStore.update(),
        updateReservations(),
        Reservations.fetchDefaultRecordSettings().then((settings) => {
            defaultRecordSettings.value = settings;
        }),
    ]);
    await fetchPrograms();
});

</script>
<style lang="scss" scoped>

.genre-list-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
}

.genre-list {
    display: flex;
    flex-direction: column;
    width: 100%;
    padding: 20px;
    margin: 0 auto;
    min-width: 0;
    max-width: 900px;
    @include smartphone-horizontal {
        padding: 16px 20px !important;
    }
    @include smartphone-vertical {
        padding: 16px 8px !important;
        padding-top: 8px !important;
    }

    &__genres {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 14px;
    }

    &__filters {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 16px;
    }

    &__select {
        flex: 0 1 160px;
        min-width: 130px;
    }

    &__count {
        margin-left: auto;
        font-size: 14px;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__message {
        padding: 40px 0;
        text-align: center;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

.genre-chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 7px 14px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 700;
    color: rgb(var(--v-theme-text));
    background: rgb(var(--v-theme-background-lighten-1));
    border: 2px solid transparent;
    cursor: pointer;
    transition: background-color 0.15s;
    &:hover {
        background: rgb(var(--v-theme-background-lighten-2));
    }

    &__dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--genre-color);
        box-shadow: 0 0 0 1px rgba(128, 128, 128, 0.45);
    }

    &--active {
        border-color: var(--genre-color);
        background: rgb(var(--v-theme-background-lighten-2));
    }
}

.genre-day {
    margin-bottom: 18px;

    &__title {
        position: sticky;
        top: 0;
        z-index: 1;
        padding: 8px 4px;
        font-size: 16px;
        font-weight: 700;
        background: rgb(var(--v-theme-background));
        border-bottom: 1px solid rgb(var(--v-theme-background-lighten-2));
    }
}

.genre-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 10px 12px;
    margin-top: 6px;
    border-left: 5px solid var(--genre-color);
    border-radius: 6px;
    background: rgb(var(--v-theme-background-lighten-1));
    cursor: pointer;
    transition: background-color 0.15s;
    &:hover {
        background: rgb(var(--v-theme-background-lighten-2));
    }

    &__time {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 0 0 auto;
        min-width: 52px;
    }

    &__start {
        font-size: 17px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
    }

    &__duration {
        font-size: 11px;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__body {
        flex: 1 1 auto;
        min-width: 0;
    }

    &__title {
        font-size: 15px;
        font-weight: 700;
        line-height: 1.4;
        word-break: break-all;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    &__now {
        display: inline-block;
        margin-right: 6px;
        padding: 0 6px;
        border-radius: 4px;
        font-size: 11px;
        color: #fff;
        background: rgb(var(--v-theme-primary));
        vertical-align: 1px;
    }

    &__channel {
        margin-top: 2px;
        font-size: 12px;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__reserved {
        flex: 0 0 auto;
        color: #ff4d4f;
    }
}

</style>
