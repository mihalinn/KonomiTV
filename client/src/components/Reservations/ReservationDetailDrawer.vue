<template>
    <!-- 背景スクリム -->
    <div class="reservation-detail-drawer__scrim"
        :class="{ 'reservation-detail-drawer__scrim--visible': isVisible }"
        @click="handleClose"></div>

    <!-- ドロワー本体 -->
    <div class="reservation-detail-drawer" :class="{ 'reservation-detail-drawer--visible': isVisible }">
        <!-- ヘッダー -->
        <div class="reservation-detail-drawer__header">
            <div class="reservation-detail-drawer__tabs" :class="{ 'reservation-detail-drawer__tabs--single': !showSettingsTab }">
                <div v-ripple class="reservation-detail-drawer__tab"
                    :class="{ 'reservation-detail-drawer__tab--active': activeTab === 'info' }"
                    @click="activeTab = 'info'">
                    <Icon icon="fluent:info-12-regular" width="20px" height="20px" />
                    <span class="reservation-detail-drawer__tab-text">番組情報 {{ !showSettingsTab ? '（終了済み）' : '' }}</span>
                </div>
                <div v-if="showSettingsTab" v-ripple class="reservation-detail-drawer__tab"
                    :class="{ 'reservation-detail-drawer__tab--active': activeTab === 'settings' }"
                    @click="activeTab = 'settings'">
                    <Icon icon="material-symbols:settings-video-camera-outline-rounded" width="20px" height="20px" />
                    <span class="reservation-detail-drawer__tab-text">録画設定</span>
                </div>
            </div>
            <div v-ripple class="reservation-detail-drawer__close" @click="handleClose">
                <Icon icon="fluent:dismiss-16-filled" width="22px" height="22px" />
            </div>
        </div>

        <!-- コンテンツ -->
        <div class="reservation-detail-drawer__content">
            <!-- 番組情報タブ -->
            <div v-if="activeTab === 'info'" class="reservation-detail-drawer__info">
                <!-- チューナー不足警告バナー（一部のみ録画） -->
                <div v-if="isPartialRecording" class="status-banner status-banner--warning mb-4">
                    <Icon icon="fluent:warning-16-filled" class="status-banner__icon" />
                    <span class="status-banner__text">
                        チューナー不足のため、この番組は一部のみ録画されます。<br>
                        優先度を上げるか、重複する録画予約を調整してください。
                    </span>
                </div>
                <!-- チューナー不足エラーバナー（録画不可） -->
                <div v-if="isUnavailableRecording" class="status-banner status-banner--error mb-4">
                    <Icon icon="fluent:error-circle-16-filled" class="status-banner__icon" />
                    <span class="status-banner__text">
                        チューナー不足のため、この番組は録画できません。<br>
                        優先度を上げるか、重複する録画予約を削除してください。
                    </span>
                </div>
                <!-- Mirakurun バックエンド時の通知 -->
                <div v-if="!isEDCBBackend && !isPastProgram && !hasRealReservation" class="status-banner status-banner--info mb-4">
                    <Icon icon="fluent:info-16-regular" class="status-banner__icon" />
                    <span class="status-banner__text">
                        録画予約機能は EDCB バックエンド選択時のみ利用できます。
                    </span>
                </div>
                <!-- 番組情報 -->
                <ReservationProgramInfo
                    :reservation="reservation"
                    :program="program"
                    :channel="channel" />
            </div>

            <!-- 録画設定タブ -->
            <div v-if="activeTab === 'settings' && reservation" class="reservation-detail-drawer__settings">
                <ReservationRecordingSettings
                    :reservation="reservation"
                    :presets="presets"
                    :has-changes="hasChanges"
                    @update-settings="handleUpdateSettings"
                    @changes-detected="hasChanges = $event" />
            </div>
        </div>

        <!-- フッター -->
        <div class="reservation-detail-drawer__footer" v-if="!isPastProgram">
            <div class="reservation-detail-drawer__actions">
                <!-- 実際の予約がある場合: 削除ボタン -->
                <v-btn v-if="hasRealReservation" class="px-3" variant="text" @click="handleDelete">
                    <Icon icon="fluent:delete-16-regular" width="20px" height="20px" />
                    <span class="ml-1">予約を削除</span>
                </v-btn>
                <!-- 実際の予約がある場合かつ録画設定タブ: 保存ボタン -->
                <v-btn v-if="hasRealReservation && activeTab === 'settings'" class="px-3" color="secondary" variant="flat"
                    :disabled="!hasChanges" :loading="isSaving" @click="handleSave">
                    <Icon icon="fluent:save-16-regular" width="20px" height="20px" />
                    <span class="ml-1">変更を保存</span>
                </v-btn>
                <!-- mock の予約 (予約なし) の場合: 予約追加ボタン -->
                <v-btn v-if="showAddButton" class="px-3" color="secondary" variant="flat"
                    :disabled="!isEDCBBackend" :loading="isAdding" @click="handleAddReservation">
                    <Icon icon="fluent:timer-16-regular" width="20px" height="20px" />
                    <span class="ml-1">予約を追加</span>
                </v-btn>
                <!-- [改造] 毎週録画ボタン: 番組名・チャンネル・曜日/時刻からキーワード自動予約条件を作る -->
                <v-btn v-if="showWeeklyButton" class="px-3" color="primary" variant="tonal"
                    :disabled="!isEDCBBackend" @click="openWeeklyDialog">
                    <Icon icon="fluent:calendar-repeat-16-regular" width="20px" height="20px" />
                    <span class="ml-1">毎週録画</span>
                </v-btn>
            </div>
        </div>
        <!-- 過去番組の場合は閉じるボタンのみ表示 -->
        <div class="reservation-detail-drawer__footer" v-else>
            <div class="reservation-detail-drawer__actions">
                <v-btn class="px-3" variant="text" @click="handleClose">
                    <Icon icon="fluent:dismiss-16-regular" width="20px" height="20px" />
                    <span class="ml-1">閉じる</span>
                </v-btn>
            </div>
        </div>
    </div>

    <!-- 削除確認ダイアログ -->
    <v-dialog v-model="showDeleteDialog" max-width="715">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">
                録画予約を削除しますか？
            </v-card-title>
            <v-card-text class="pt-2 pb-0">
                <div v-if="reservation" class="mb-4">
                    <div class="text-h6 text-text mb-2"
                        v-html="ProgramUtils.decorateProgramInfo(reservation.program, 'title')"></div>
                    <div class="text-body-2 text-text-darken-1">
                        {{ ProgramUtils.getProgramTime(reservation.program) }}
                    </div>
                </div>
                <div v-if="isRecordingInProgress && reservation" class="warning-banner warning-banner--recording">
                    <Icon icon="fluent:warning-16-filled" class="warning-banner__icon" />
                    <span class="warning-banner__text">
                        この番組は現在録画中です。<br>
                        予約を削除すると、現在までの録画ファイルは残りますが、残りの期間の録画は中断されます。
                    </span>
                </div>
                <div v-else-if="reservation" class="warning-banner warning-banner--normal">
                    <Icon icon="fluent:info-16-regular" class="warning-banner__icon" />
                    <span class="warning-banner__text">
                        録画予約を削除すると、番組開始時刻までに再度予約を追加しない限り、この番組は録画されません。
                    </span>
                </div>
                <div v-if="isKeywordAutoReservation && reservation" class="warning-banner warning-banner--keyword mt-3">
                    <Icon icon="fluent:warning-16-filled" class="warning-banner__icon" />
                    <span class="warning-banner__text">
                        この予約はキーワード自動予約で追加されました。削除してもすぐに再追加される可能性があります。<br>
                        録画が不要な場合は削除ではなく「無効」にすることをおすすめします。
                    </span>
                </div>
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" @click="showDeleteDialog = false">
                    <Icon icon="fluent:dismiss-20-regular" width="18px" height="18px" />
                    <span class="ml-1">キャンセル</span>
                </v-btn>
                <v-btn class="px-3" color="error" variant="flat" @click="confirmDelete">
                    <Icon icon="fluent:delete-20-regular" width="18px" height="18px" />
                    <span class="ml-1">予約を削除</span>
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- 閉じる確認ダイアログ -->
    <v-dialog v-model="showCloseConfirmDialog" max-width="500">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">
                変更を破棄しますか？
            </v-card-title>
            <v-card-text class="pt-2 pb-0">
                <div class="warning-banner warning-banner--normal">
                    <Icon icon="fluent:info-16-regular" class="warning-banner__icon" />
                    <span class="warning-banner__text">
                        録画設定の変更がまだ保存されていません。<br>
                        このまま閉じると、変更内容は破棄されます。
                    </span>
                </div>
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" @click="showCloseConfirmDialog = false">
                    <Icon icon="fluent:arrow-left-20-regular" width="18px" height="18px" />
                    <span class="ml-1">編集に戻る</span>
                </v-btn>
                <v-btn class="px-3" color="secondary" variant="flat" @click="confirmClose">
                    <Icon icon="fluent:dismiss-20-regular" width="18px" height="18px" />
                    <span class="ml-1">変更を破棄</span>
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- [改造] 毎週録画ダイアログ -->
    <v-dialog v-model="showWeeklyDialog" max-width="560">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">
                毎週録画を登録
            </v-card-title>
            <v-card-text class="pt-2 pb-0">
                <div class="text-body-2 text-text-darken-1 mb-4">
                    {{ weeklyScheduleLabel }} に放送される、下のキーワードを含む番組を毎週自動で録画予約します。
                </div>
                <v-text-field v-model="weeklyKeyword" label="番組名キーワード" variant="outlined"
                    density="comfortable" hide-details="auto" />
                <v-text-field v-model.number="weeklyTimeToleranceMinutes" class="mt-4" type="number" min="0" max="180"
                    label="放送時刻の許容幅 (前後の分)" variant="outlined" density="comfortable" hide-details="auto" />
                <v-switch v-model="weeklyAnyChannel" class="mt-2" color="primary" hide-details density="comfortable"
                    :label="`チャンネルを限定しない (オフ: ${weeklyChannelName} のみ)`" />
                <v-switch v-model="weeklySkipAlreadyRecorded" color="primary" hide-details density="comfortable"
                    label="すでに録画済みの同名番組は録画しない (再放送対策)" />
                <v-switch v-model="weeklySeriesFolder" color="primary" hide-details density="comfortable"
                    label="番組名のフォルダを作って、そこに録画する (シリーズ別に自動で整理)" />
                <v-text-field v-if="weeklySeriesFolder" v-model="weeklyBaseFolder" class="mt-2"
                    label="録画先の親フォルダ" variant="outlined" density="comfortable" hide-details="auto"
                    :hint="`保存先: ${weeklyFolderPreview}`" persistent-hint />
                <div class="text-caption text-text-darken-1 mt-3">
                    登録した条件は「毎週録画の管理」ページで編集・削除できます。
                </div>
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" @click="showWeeklyDialog = false">
                    <Icon icon="fluent:dismiss-20-regular" width="18px" height="18px" />
                    <span class="ml-1">キャンセル</span>
                </v-btn>
                <v-btn class="px-3" color="secondary" variant="flat" :loading="isAddingWeekly"
                    :disabled="weeklyKeyword.trim() === ''" @click="confirmWeekly">
                    <Icon icon="fluent:calendar-repeat-16-regular" width="18px" height="18px" />
                    <span class="ml-1">毎週録画を登録</span>
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>
<script lang="ts" setup>

import { ref, computed, watch, onMounted } from 'vue';

import ReservationProgramInfo from '@/components/Reservations/ReservationProgramInfo.vue';
import ReservationRecordingSettings from '@/components/Reservations/ReservationRecordingSettings.vue';
import Message from '@/message';
import { type IChannel } from '@/services/Channels';
import { type IProgram, type IProgramSearchCondition } from '@/services/Programs';
import ReservationConditions from '@/services/ReservationConditions';
import Reservations, { type IReservation, type IRecordSettings, type IRecordSettingsPresets } from '@/services/Reservations';
import useServerSettingsStore from '@/stores/ServerSettingsStore';
import { ProgramUtils } from '@/utils';

// Props
const props = defineProps<{
    // 予約情報（予約がある場合に使用）
    reservation: IReservation | null;
    // 番組情報（予約がない場合に使用、番組表からの呼び出し用）
    program?: IProgram | null;
    // チャンネル情報（予約がない場合に使用、番組表からの呼び出し用）
    channel?: IChannel | null;
    // 過去番組かどうか（true の場合、予約関連 UI は非表示）
    isPastProgram?: boolean;
    // ドロワーの表示状態
    modelValue: boolean;
}>();

// Emits
const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void;
    (e: 'updated', reservation: IReservation): void;
    (e: 'deleted', reservationId: number): void;
    (e: 'added'): void;
}>();

// ドロワーの表示状態
const isVisible = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

// サーバー設定（バックエンド種別の判定用）
const serverSettingsStore = useServerSettingsStore();
const serverSettings = computed(() => serverSettingsStore.server_settings);

// アクティブなタブ
const activeTab = ref<'info' | 'settings'>('info');

// 変更の検知
const hasChanges = ref(false);

// 保存中フラグ
const isSaving = ref(false);

// 予約追加中フラグ
const isAdding = ref(false);

// 現在の録画設定
const currentSettings = ref<IRecordSettings | null>(null);

// 削除確認ダイアログの表示状態
const showDeleteDialog = ref(false);

// 閉じる確認ダイアログの表示状態
const showCloseConfirmDialog = ref(false);

// 録画設定プリセット一覧 (EDCB バックエンド時のみ取得される)
const presets = ref<IRecordSettingsPresets | null>(null);

// 予約があるかどうか (null でなければ予約がある)
// ただし id === -1 の場合は mock の予約なので、実際には予約がない状態
const hasReservation = computed(() => props.reservation !== null);

// mock の予約かどうか (id === -1 の場合は予約がない番組用の mock)
// TimeTable.vue から渡される mock の IReservation を判定するために使用
const isMockReservation = computed(() => props.reservation !== null && props.reservation.id === -1);

// 実際に予約が存在するかどうか (mock でない場合)
const hasRealReservation = computed(() => hasReservation.value && !isMockReservation.value);

// 表示用の番組情報（予約があればそちらを優先）
const displayProgram = computed(() => props.reservation?.program ?? props.program ?? null);

// EDCB バックエンドかどうか
// サーバー設定がまだ取得されていない場合は EDCB と判定しない
// (デフォルト値が 'EDCB' のため、未取得状態で誤って true を返すと Mirakurun バックエンドでも予約操作が有効化されてしまう)
const isEDCBBackend = computed(() => serverSettingsStore.is_loaded === true && serverSettings.value.general.backend === 'EDCB');

// 録画設定タブを表示するかどうか
// - 実際の予約がある場合: 表示 (既存予約の設定編集)
// - mock の予約がある場合 (予約なし): 表示 (新規予約前の設定カスタマイズ)
// - 過去番組の場合: 非表示
const showSettingsTab = computed(() => hasReservation.value && !props.isPastProgram);

// 予約追加ボタンを表示するかどうか
// mock の予約がある場合 (実際には予約なし) かつ過去番組でない場合に表示
const showAddButton = computed(() => isMockReservation.value && !props.isPastProgram);

// [改造] 毎週録画ボタンを表示するかどうか
// 未予約の番組、または手動予約のみの番組で表示する (キーワード自動予約・過去番組では非表示)
const showWeeklyButton = computed(() => {
    if (props.isPastProgram) return false;
    if (displayProgram.value === null) return false;
    if (isMockReservation.value) return true;
    if (hasRealReservation.value && !(props.reservation?.comment.includes('EPG自動予約') ?? false)) return true;
    return false;
});

// キーワード自動予約かどうか
const isKeywordAutoReservation = computed(() => {
    return props.reservation?.comment.includes('EPG自動予約') ?? false;
});

// 録画中かどうか
const isRecordingInProgress = computed(() => {
    return props.reservation?.is_recording_in_progress ?? false;
});

// 録画可能性（チューナー不足判定）
const recordingAvailability = computed(() => {
    return props.reservation?.recording_availability ?? 'Full';
});

// チューナー不足（一部のみ録画）
const isPartialRecording = computed(() => recordingAvailability.value === 'Partial');

// チューナー不足（録画不可）
const isUnavailableRecording = computed(() => recordingAvailability.value === 'Unavailable');

// サーバー設定を取得し、EDCB バックエンドの場合は録画設定プリセットも取得する
onMounted(async () => {
    await serverSettingsStore.fetchServerSettingsOnce();
    // EDCB バックエンドの場合のみプリセットを取得
    if (isEDCBBackend.value) {
        presets.value = await Reservations.fetchRecordingPresets();
    }
});

// ドロワーが開かれた時の処理
watch(isVisible, (newValue) => {
    if (newValue) {
        // 開かれた時は番組情報タブを表示
        activeTab.value = 'info';
        hasChanges.value = false;
        // ページ全体のスクロールを無効にする
        document.documentElement.classList.add('v-overlay-scroll-blocked');
    } else {
        // ページ全体のスクロールを有効に戻す
        document.documentElement.classList.remove('v-overlay-scroll-blocked');
    }
});

// 閉じる処理
const handleClose = () => {
    if (hasChanges.value) {
        // 変更がある場合は確認ダイアログを表示
        showCloseConfirmDialog.value = true;
        return;
    }
    isVisible.value = false;
};

// 閉じる確認
const confirmClose = () => {
    showCloseConfirmDialog.value = false;
    hasChanges.value = false;
    isVisible.value = false;
};

// 設定更新の処理
const handleUpdateSettings = (newSettings: IRecordSettings) => {
    currentSettings.value = newSettings;
};

// 保存処理
const handleSave = async () => {
    if (!hasChanges.value || isSaving.value || !currentSettings.value || !props.reservation) return;

    // バリデーションチェック
    const captionIsDefault = currentSettings.value.caption_recording_mode === 'Default';
    const dataBroadcastingIsDefault = currentSettings.value.data_broadcasting_recording_mode === 'Default';
    if (captionIsDefault !== dataBroadcastingIsDefault) {
        Message.warning('字幕データ録画設定・データ放送録画設定を明示的に設定する際は、両方とも「デフォルト設定を使う」以外に設定してください。');
        return;
    }

    isSaving.value = true;
    try {
        const result = await Reservations.updateReservation(props.reservation.id, currentSettings.value);
        if (result) {
            Message.success('録画設定の変更を保存しました。');
            const updatedReservation = { ...props.reservation, record_settings: currentSettings.value };
            emit('updated', updatedReservation);
            hasChanges.value = false;
        }
    } catch (error) {
        console.error('Failed to save settings:', error);
        Message.error('録画設定の保存に失敗しました。');
    } finally {
        isSaving.value = false;
    }
};

// 削除処理
const handleDelete = () => {
    showDeleteDialog.value = true;
};

// 削除確認
const confirmDelete = async () => {
    showDeleteDialog.value = false;
    if (!props.reservation) return;

    try {
        const success = await Reservations.deleteReservation(props.reservation.id);
        if (success) {
            Message.success('録画予約を削除しました。');
            emit('deleted', props.reservation.id);
            isVisible.value = false;
        }
    } catch (error) {
        console.error('Failed to delete reservation:', error);
    }
};

// ---- [改造] 毎週録画 ----

const DAY_OF_WEEK_LABELS = ['日', '月', '火', '水', '木', '金', '土'];

const showWeeklyDialog = ref(false);
const isAddingWeekly = ref(false);
const weeklyKeyword = ref('');
const weeklyTimeToleranceMinutes = ref(15);
const weeklyAnyChannel = ref(false);
const weeklySkipAlreadyRecorded = ref(false);
const weeklySeriesFolder = ref(true);
const weeklyBaseFolder = ref('');

const WEEKLY_BASE_FOLDER_KEY = 'konomitv-custom-weekly-base-folder';
const WEEKLY_DEFAULT_BASE_FOLDER = 'D:\\TV-Record';

// フォルダ名に使えない文字を全角に置き換える (Windows 互換。シリーズ整理ツールと同じ規則)
const makeFolderName = (name: string): string => {
    const map: Record<string, string> = { '\\': '＼', '/': '／', ':': '：', '*': '＊', '?': '？', '"': '＂', '<': '＜', '>': '＞', '|': '｜' };
    const replaced = Array.from(name).map((c) => map[c] ?? c).join('');
    return replaced.replace(/\s+/g, ' ').trim().replace(/[. ]+$/, '').slice(0, 60).replace(/[. ]+$/, '');
};
const weeklyFolderPath = computed(() => {
    const folder = makeFolderName(weeklyKeyword.value);
    const base = weeklyBaseFolder.value.trim().replace(/[\\/]+$/, '');
    return folder === '' || base === '' ? '' : `${base}\\${folder}`;
});
const weeklyFolderPreview = computed(() => weeklyFolderPath.value || '(未設定)');

// 番組を放送するチャンネル (番組表経由なら props.channel、予約一覧経由なら予約に付属するチャンネル)
const weeklyChannel = computed(() => props.channel ?? props.reservation?.channel ?? null);
const weeklyChannelName = computed(() => weeklyChannel.value?.name ?? '指定チャンネル');

// 番組の放送開始時刻から曜日・時・分を取り出す (ブラウザのタイムゾーンに依存しないよう文字列から直接パースする)
const weeklyStart = computed(() => {
    const m = displayProgram.value?.start_time.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
    if (!m) return null;
    const dayOfWeek = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))).getUTCDay();
    return { dayOfWeek, hour: Number(m[4]), minute: Number(m[5]) };
});

const weeklyScheduleLabel = computed(() => {
    if (!weeklyStart.value) return '';
    const s = weeklyStart.value;
    return `毎週${DAY_OF_WEEK_LABELS[s.dayOfWeek]}曜 ${String(s.hour).padStart(2, '0')}:${String(s.minute).padStart(2, '0')} ごろ`
        + (weeklyAnyChannel.value ? '' : ` (${weeklyChannelName.value})`);
});

// 番組名から [新] [終] [字] などの装飾記号と「第N話」「#N」を取り除き、検索キーワードにする
const makeWeeklyKeyword = (title: string): string => {
    let t = title.normalize('NFKC');
    // [新] [終] [字] [再] [デ] [解] [SS] [S] [二] [無] [生] [初] [前] [後] [多] [吹] [N] など、括弧内が短い装飾
    t = t.replace(/[[【<＜(]\s*(新|終|字|再|デ|解|二|無|生|初|前|後|多|吹|映|声|手|SS|S|N|HV|STEREO)\s*[\]】>＞)]/gi, ' ');
    // 「第N話」「#N」「▽」以降のサブタイトル
    t = t.replace(/第\s*\d+\s*[話回夜章]/g, ' ').replace(/[#＃]\s*\d+/g, ' ');
    t = t.replace(/[▽▼◇◆♯].*$/, ' ');
    return t.replace(/\s+/g, ' ').trim();
};

const openWeeklyDialog = () => {
    if (!displayProgram.value) return;
    weeklyKeyword.value = makeWeeklyKeyword(displayProgram.value.title);
    weeklyTimeToleranceMinutes.value = 15;
    weeklyAnyChannel.value = false;
    weeklySkipAlreadyRecorded.value = false;
    weeklySeriesFolder.value = true;
    // 親フォルダ: 現在の録画設定の保存先 → 前回入力した値 → 既定値 の順に採用する
    let savedBase = '';
    try {
        savedBase = localStorage.getItem(WEEKLY_BASE_FOLDER_KEY) ?? '';
    } catch {
        // localStorage が使えない環境では無視
    }
    const presetFolder = (currentSettings.value ?? props.reservation?.record_settings)?.recording_folders?.[0]?.recording_folder_path;
    weeklyBaseFolder.value = presetFolder || savedBase || WEEKLY_DEFAULT_BASE_FOLDER;
    showWeeklyDialog.value = true;
};

const confirmWeekly = async () => {
    if (isAddingWeekly.value || !displayProgram.value || !weeklyStart.value) return;
    const keyword = weeklyKeyword.value.trim();
    if (keyword === '') return;

    const channel = weeklyChannel.value;
    if (!weeklyAnyChannel.value && (channel === null || channel.transport_stream_id === null)) {
        Message.error('このチャンネルの情報が取得できなかったため、チャンネルを限定できません。');
        return;
    }

    // 放送開始時刻 ± 許容幅 を「週の中の分」で表し、日をまたぐ場合も曜日を正しく進める
    const tolerance = Math.min(Math.max(Math.floor(Number(weeklyTimeToleranceMinutes.value) || 0), 0), 180);
    const WEEK_MINUTES = 7 * 24 * 60;
    const startMinuteOfWeek = weeklyStart.value.dayOfWeek * 1440 + weeklyStart.value.hour * 60 + weeklyStart.value.minute;
    const from = (startMinuteOfWeek - tolerance + WEEK_MINUTES) % WEEK_MINUTES;
    const to = (startMinuteOfWeek + tolerance) % WEEK_MINUTES;
    const decode = (v: number) => ({ dow: Math.floor(v / 1440), hour: Math.floor((v % 1440) / 60), minute: v % 60 });
    const f = decode(from);
    const t = decode(to);

    const condition: IProgramSearchCondition = {
        is_enabled: true,
        keyword: keyword,
        exclude_keyword: '',
        note: '毎週録画',
        is_title_only: true,
        is_case_sensitive: false,
        is_fuzzy_search_enabled: false,
        is_regex_search_enabled: false,
        service_ranges: weeklyAnyChannel.value || channel === null ? null : [{
            network_id: channel.network_id,
            transport_stream_id: channel.transport_stream_id ?? 0,
            service_id: channel.service_id,
        }],
        genre_ranges: null,
        is_exclude_genre_ranges: false,
        date_ranges: [{
            start_day_of_week: f.dow, start_hour: f.hour, start_minute: f.minute,
            end_day_of_week: t.dow, end_hour: t.hour, end_minute: t.minute,
        }],
        is_exclude_date_ranges: false,
        duration_range_min: null,
        duration_range_max: null,
        broadcast_type: 'All',
        duplicate_title_check_scope: weeklySkipAlreadyRecorded.value ? 'AllChannels' : 'None',
        duplicate_title_check_period_days: 6,
    };

    const baseSettings = currentSettings.value ?? props.reservation?.record_settings;
    if (!baseSettings) {
        Message.error('録画設定を取得できなかったため、毎週録画を登録できません。');
        return;
    }
    let recordSettings = baseSettings;
    if (weeklySeriesFolder.value) {
        if (weeklyFolderPath.value === '') {
            Message.error('録画先の親フォルダを入力してください。');
            return;
        }
        try {
            localStorage.setItem(WEEKLY_BASE_FOLDER_KEY, weeklyBaseFolder.value.trim());
        } catch {
            // 保存できなくても登録は続行する
        }
        const firstFolder = baseSettings.recording_folders?.[0];
        recordSettings = {
            ...baseSettings,
            recording_folders: [{
                recording_folder_path: weeklyFolderPath.value,
                recording_file_name_template: firstFolder?.recording_file_name_template ?? null,
                is_oneseg_separate_recording_folder: firstFolder?.is_oneseg_separate_recording_folder ?? false,
            }],
        };
    }

    isAddingWeekly.value = true;
    try {
        const success = await ReservationConditions.addReservationCondition(condition, recordSettings);
        if (success) {
            Message.success(`毎週録画を登録しました。(${weeklyScheduleLabel.value} / ${keyword})`);
            showWeeklyDialog.value = false;
            emit('added');
            isVisible.value = false;
        }
    } catch (error) {
        console.error('Failed to add weekly recording:', error);
        Message.error('毎週録画の登録に失敗しました。');
    } finally {
        isAddingWeekly.value = false;
    }
};

// 予約追加処理
// mock の予約に含まれる record_settings (ユーザーがカスタマイズ可能) を使用して追加
const handleAddReservation = async () => {
    if (isAdding.value || !displayProgram.value || !props.reservation) return;

    // EDCB バックエンドでない場合はエラー
    if (!isEDCBBackend.value) {
        Message.error('録画予約機能は EDCB バックエンド選択時のみ利用できます。');
        return;
    }

    isAdding.value = true;
    try {
        // バリデーションチェック (保存処理と同じ)
        const recordSettings = currentSettings.value ?? props.reservation.record_settings;
        const captionIsDefault = recordSettings.caption_recording_mode === 'Default';
        const dataBroadcastingIsDefault = recordSettings.data_broadcasting_recording_mode === 'Default';
        if (captionIsDefault !== dataBroadcastingIsDefault) {
            Message.warning('字幕データ録画設定・データ放送録画設定を明示的に設定する際は、両方とも「デフォルト設定を使う」以外に設定してください。');
            isAdding.value = false;
            return;
        }

        // mock の予約に含まれる record_settings を使用
        // ユーザーが録画設定タブで設定をカスタマイズしていればその設定が使われる
        const success = await Reservations.addReservation(displayProgram.value.id, recordSettings);
        if (success) {
            Message.success('録画予約を追加しました。');
            emit('added');
            isVisible.value = false;
        }
    } catch (error) {
        console.error('Failed to add reservation:', error);
        Message.error('録画予約の追加に失敗しました。');
    } finally {
        isAdding.value = false;
    }
};

</script>
<style lang="scss" scoped>

// 背景スクリム
.reservation-detail-drawer__scrim {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1009;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.25s ease, visibility 0.25s ease;
    pointer-events: none;

    &--visible {
        opacity: 1;
        visibility: visible;
        pointer-events: auto;
    }
}

// ドロワー本体
.reservation-detail-drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 370px;
    display: flex;
    flex-direction: column;
    background: rgb(var(--v-theme-background));
    border-top-left-radius: 16px;
    border-bottom-left-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.16);
    z-index: 1010;
    transform: translateX(100%);
    transition: transform 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);

    &--visible {
        transform: translateX(0);
    }

    // スマートフォンでは左側に少しスクリムが見えるように調整
    @media (max-width: 480px) {
        width: calc(100vw - 32px);
        border-top-left-radius: 16px;
        border-bottom-left-radius: 16px;
    }

    &__header {
        display: flex;
        position: relative;
        width: 100%;
        height: 48px;
        background: rgb(var(--v-theme-background-lighten-1));
        border-bottom: 1px solid rgb(var(--v-theme-background-lighten-2));
        border-top-left-radius: 16px;
        overflow: hidden;
    }

    &__tabs {
        display: flex;
        flex: 1;
        padding-left: 48px;
    }

    &__tab {
        display: flex;
        flex: 1;
        align-items: center;
        justify-content: center;
        gap: 8px;
        height: 100%;
        color: rgb(var(--v-theme-text));
        cursor: pointer;
        transition: background-color 0.15s;
        position: relative;

        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        // タッチデバイスで hover を無効にする
        @media (hover: none) {
            &:hover {
                background: rgb(var(--v-theme-background-lighten-1));
            }
        }

        &::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: rgb(var(--v-theme-background-lighten-2));
        }

        &--active {
            color: rgb(var(--v-theme-text));

            &::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: rgb(var(--v-theme-secondary));
            }
        }
    }

    &__tab-text {
        font-size: 15.5px;
        font-weight: 700;
        letter-spacing: 0.04em;
    }

    &__close {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        color: rgb(var(--v-theme-text));
        cursor: pointer;
        transition: background-color 0.15s;

        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        // タッチデバイスで hover を無効にする
        @media (hover: none) {
            &:hover {
                background: rgb(var(--v-theme-background-lighten-1));
            }
        }
    }

    &__content {
        display: flex;
        flex-direction: column;
        flex: 1;
        overflow-y: auto;
        background: rgb(var(--v-theme-background));
    }

    &__info,
    &__settings {
        padding: 16px;
    }

    &__footer {
        display: flex;
        position: relative;
        width: 100%;
        height: 52px;
        background: rgb(var(--v-theme-background-lighten-1));
        border-top: 1px solid rgb(var(--v-theme-background-lighten-2));
        border-bottom-left-radius: 16px;
        overflow: hidden;
    }

    &__actions {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-left: auto;
        padding: 8px 16px;
    }
}

// 警告バナー
.warning-banner {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-radius: 6px;

    &__icon {
        width: 22px;
        height: 22px;
        margin-right: 8px;
        flex-shrink: 0;
    }

    &__text {
        font-size: 13px;
        font-weight: 500;
        line-height: 1.55;
    }

    // キーワード自動予約の警告（警告色）
    &--keyword {
        background-color: rgb(var(--v-theme-warning-darken-3), 0.5);

        .warning-banner__icon {
            color: rgb(var(--v-theme-warning));
        }

        .warning-banner__text {
            color: rgb(var(--v-theme-warning-lighten-1));
        }
    }

    // 録画中の警告（エラー色）
    &--recording {
        background-color: rgb(var(--v-theme-error-darken-3), 0.5);

        .warning-banner__icon {
            color: rgb(var(--v-theme-error));
        }

        .warning-banner__text {
            color: rgb(var(--v-theme-error-lighten-1));
        }
    }

    // 通常の警告（情報色）
    &--normal {
        background-color: rgb(var(--v-theme-info-darken-3), 0.5);

        .warning-banner__icon {
            color: rgb(var(--v-theme-info));
        }

        .warning-banner__text {
            color: rgb(var(--v-theme-info-lighten-1));
        }
    }
}

// ステータスバナー（ドロワー内で使用）
.status-banner {
    display: flex;
    align-items: flex-start;
    padding: 12px 16px;
    border-radius: 8px;

    &__icon {
        width: 20px;
        height: 20px;
        margin-right: 10px;
        margin-top: 1px;
        flex-shrink: 0;
    }

    &__text {
        font-size: 13px;
        font-weight: 500;
        line-height: 1.6;
    }

    // 警告（一部のみ録画）
    &--warning {
        background-color: rgb(var(--v-theme-warning-darken-3), 0.4);

        .status-banner__icon {
            color: rgb(var(--v-theme-warning));
        }

        .status-banner__text {
            color: rgb(var(--v-theme-warning-lighten-1));
        }
    }

    // エラー（録画不可）
    &--error {
        background-color: rgb(var(--v-theme-error-darken-3), 0.4);

        .status-banner__icon {
            color: rgb(var(--v-theme-error));
        }

        .status-banner__text {
            color: rgb(var(--v-theme-error-lighten-1));
        }
    }

    // 情報（Mirakurun バックエンド通知など）
    &--info {
        background-color: rgb(var(--v-theme-info-darken-3), 0.4);

        .status-banner__icon {
            color: rgb(var(--v-theme-info));
        }

        .status-banner__text {
            color: rgb(var(--v-theme-info-lighten-1));
        }
    }
}

</style>