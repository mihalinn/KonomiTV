<template>
    <!-- ベース画面の中にそれぞれの設定画面で異なる部分を記述する -->
    <SettingsBase>
        <h2 class="settings__heading">
            <a v-ripple class="settings__back-button" @click="$router.back()">
                <Icon icon="fluent:chevron-left-12-filled" width="27px" />
            </a>
            <Icon icon="fluent:fast-forward-20-filled" width="22px" />
            <span class="ml-2">CM 解析設定</span>
        </h2>
        <div class="settings__description">
            録画番組の CM 区間を AI で検出し、再生中に CM を自動でスキップできるようにする機能の設定です。<br>
            CM 検出は CPU (または GPU) に負荷がかかる重い処理です。使わない場合は、CM 検出機能をオフのままにしておいてください。<br>
        </div>
        <div class="settings__description mt-1">
            CM 検出の設定を変更するには、管理者アカウントでログインしている必要があります。<br>
            [CM 検出設定を更新] ボタンを押さずにこのページから離れると、変更内容は破棄されます。サーバーの再起動は不要です。<br>
        </div>
        <div class="settings__content" :class="{'settings__content--disabled': is_disabled || status === null}">
            <div class="settings__content-heading">
                <Icon icon="fluent:server-surface-16-filled" width="22px" />
                <span class="ml-2">CM 検出 (サーバー全体)</span>
            </div>
            <div class="settings__item settings__item--switch">
                <label class="settings__item-heading" for="cm_detection_enabled">CM 検出機能を有効にする</label>
                <label class="settings__item-label" for="cm_detection_enabled">
                    オフにすると、CM 検出に関わるすべての処理 (新しい録画の自動解析・手動での CM 解析) が行われなくなります。<br>
                    すでに検出済みの CM 区間は削除されず、再生中のスキップにはそのまま使えます。<br>
                </label>
                <v-switch class="settings__item-switch" color="primary" id="cm_detection_enabled" hide-details
                    v-model="cm_settings.enabled">
                </v-switch>
            </div>
            <div class="settings__item settings__item--switch">
                <label class="settings__item-heading" for="cm_detection_analyze_new">新しく録画された番組を自動で CM 解析する</label>
                <label class="settings__item-label" for="cm_detection_analyze_new">
                    オンにすると、録画が終わった番組が自動的に CM 解析の順番待ちに入ります。デフォルトはオフです。<br>
                    すでに録画されている番組は自動では解析されません。録画番組の一覧で番組を選び、[CM 解析する] を押したときだけ解析されます。<br>
                </label>
                <v-switch class="settings__item-switch" color="primary" id="cm_detection_analyze_new" hide-details
                    :disabled="!cm_settings.enabled"
                    v-model="cm_settings.analyze_new_recordings">
                </v-switch>
            </div>
            <div class="settings__item">
                <div class="settings__item-heading">CM 解析に使うデバイス</div>
                <div class="settings__item-label">
                    CPU はどの PC でも使えますが、解析に時間がかかります (30 分番組で数分程度)。<br>
                    GPU は NVIDIA GPU など対応環境でのみ選べます。ライブ視聴や録画再生のエンコードと GPU を共有するため、同時に使うと動作が重くなることがあります。<br>
                </div>
                <div class="settings__item-label mt-1" v-if="status !== null">
                    利用可能な推論エンジン: {{status.providers.join(' / ')}}<br>
                    <span v-if="!status.gpu_available">この環境では GPU を使った CM 解析は利用できません (CPU で解析されます)。<br></span>
                </div>
                <v-select class="settings__item-form" color="primary" variant="outlined" hide-details
                    :density="is_form_dense ? 'compact' : 'default'"
                    :disabled="!cm_settings.enabled"
                    :items="[
                        {title: 'CPU', value: 'CPU'},
                        {title: 'GPU', value: 'GPU', props: {disabled: status !== null && !status.gpu_available}},
                    ]"
                    v-model="cm_settings.device">
                </v-select>
            </div>
            <div class="settings__item">
                <div class="settings__item-heading">CM 解析に使うスレッド数: {{cm_settings.threads}}</div>
                <div class="settings__item-label">
                    CM 解析中に使う CPU スレッド数の目安です。デフォルトは 2 です。<br>
                    大きくすると解析は速くなりますが、解析中に他の処理 (視聴・録画) に影響が出やすくなります。<br>
                </div>
                <v-slider class="settings__item-form" color="primary" show-ticks="always" thumb-label hide-details
                    :min="1" :max="16" :step="1"
                    :disabled="!cm_settings.enabled"
                    :density="is_form_dense ? 'compact' : 'default'"
                    v-model="cm_settings.threads">
                </v-slider>
            </div>
            <div class="settings__item" v-if="status !== null">
                <div class="settings__item-heading">CM 検出 AI のモデル</div>
                <div class="settings__item-label">
                    <template v-if="status.model_ready">
                        モデルファイルは準備できています。<br>
                    </template>
                    <template v-else>
                        <span class="text-error-lighten-1">モデルファイルが見つかりません。</span>
                        CM 解析を行うには、モデルファイルを KonomiTV の data/cm-detection-models/ フォルダに配置してください。<br>
                    </template>
                    <template v-if="status.model_download.state === 'Downloading'">
                        ダウンロード中... {{Math.round(status.model_download.progress * 100)}}%<br>
                    </template>
                    <template v-else-if="status.model_download.state === 'Failed'">
                        <span class="text-error-lighten-1">ダウンロードに失敗しました: {{status.model_download.message}}</span><br>
                    </template>
                </div>
                <v-btn class="settings__save-button mt-3" variant="flat" color="secondary"
                    v-if="!status.model_ready && status.model_downloadable"
                    :disabled="status.model_download.state === 'Downloading'"
                    @click="downloadModel()">
                    <Icon icon="fluent:arrow-download-24-regular" height="20px" />
                    <span class="ml-2">モデルをダウンロード</span>
                </v-btn>
            </div>
            <v-btn class="settings__save-button mt-5" color="secondary" variant="flat"
                @click="updateCMSettings()">
                <Icon icon="fluent:save-16-filled" height="20px" />
                <span class="ml-2">CM 検出設定を更新</span>
            </v-btn>
        </div>
        <div class="settings__content mt-6">
            <div class="settings__content-heading">
                <Icon icon="fluent:task-list-ltr-24-regular" width="22px" />
                <span class="ml-2">CM 解析の進行状況</span>
            </div>
            <div class="settings__description mt-1">
                録画番組の一覧で番組を選び、[CM 解析する] を押すとここに表示されます。解析は 1 本ずつ順番に行われます。<br>
            </div>
            <div class="cm-jobs" v-if="jobs.length > 0">
                <div class="cm-jobs__item" v-for="job in jobs" :key="job.video_id">
                    <div class="cm-jobs__title">{{job.title}}</div>
                    <div class="cm-jobs__state">
                        <template v-if="job.state === 'Running'">解析中 ({{job.stage}}) {{Math.round(job.progress * 100)}}%</template>
                        <template v-else-if="job.state === 'Pending'">順番待ち</template>
                        <template v-else-if="job.state === 'Completed'">完了 (CM {{job.cm_section_count}} か所)</template>
                        <template v-else-if="job.state === 'Cancelled'">取り消し</template>
                        <template v-else><span class="text-error-lighten-1">失敗: {{job.message}}</span></template>
                    </div>
                    <v-progress-linear class="mt-1" color="primary" rounded height="6"
                        v-if="job.state === 'Running'" :model-value="job.progress * 100">
                    </v-progress-linear>
                </div>
            </div>
            <div class="settings__item-label mt-3" v-else>
                実行中・順番待ちの CM 解析はありません。<br>
            </div>
            <div class="d-flex mt-4" style="gap: 12px; flex-wrap: wrap;" v-if="jobs.length > 0 && !is_disabled">
                <v-btn variant="flat" color="secondary" @click="cancelAllJobs()">
                    <Icon icon="fluent:dismiss-circle-20-regular" height="20px" />
                    <span class="ml-2">実行中・順番待ちをすべて取り消す</span>
                </v-btn>
                <v-btn variant="flat" color="background-lighten-2" @click="clearFinishedJobs()">
                    <span>終了済みを一覧から消す</span>
                </v-btn>
            </div>
        </div>
        <div class="settings__content mt-6">
            <div class="settings__content-heading">
                <Icon icon="fluent:fast-forward-20-filled" width="22px" />
                <span class="ml-2">CM 自動スキップ (この端末の設定)</span>
            </div>
            <div class="settings__description mt-1">
                録画番組の再生中の動作です。この設定は、この端末のブラウザにだけ保存されます。<br>
                CM 区間が検出済みの録画番組だけが対象です。自動スキップを使わない場合でも、CM 中にプレイヤーに表示される [CM をスキップ] ボタンで手動でスキップできます。<br>
            </div>
            <div class="settings__item settings__item--switch">
                <label class="settings__item-heading" for="cm_auto_skip">再生中に CM を自動でスキップする</label>
                <label class="settings__item-label" for="cm_auto_skip">
                    オンにすると、CM 区間に入ったときに CM の終わりまで自動で飛ばします。デフォルトはオフです。<br>
                </label>
                <v-switch class="settings__item-switch" color="primary" id="cm_auto_skip" hide-details
                    v-model="settingsStore.settings.cm_auto_skip">
                </v-switch>
            </div>
            <div class="settings__item">
                <div class="settings__item-heading">スキップ開始の余白: {{settingsStore.settings.cm_skip_start_margin.toFixed(1)}} 秒</div>
                <div class="settings__item-label">
                    CM の開始位置からこの秒数が経ってからスキップします。デフォルトは 0.5 秒です。<br>
                    本編の最後が切れてしまう場合は大きく、CM の頭が少し見えてしまう場合は小さくしてください。<br>
                </div>
                <v-slider class="settings__item-form" color="primary" show-ticks="always" thumb-label hide-details
                    :min="0" :max="5" :step="0.1"
                    :density="is_form_dense ? 'compact' : 'default'"
                    v-model="settingsStore.settings.cm_skip_start_margin">
                </v-slider>
            </div>
            <div class="settings__item">
                <div class="settings__item-heading">スキップ終了の余白: {{settingsStore.settings.cm_skip_end_margin.toFixed(1)}} 秒</div>
                <div class="settings__item-label">
                    CM の終了位置からさらにこの秒数だけ先に進めます。デフォルトは 0 秒です。<br>
                    CM の最後が少し見えてしまう場合は大きく、本編の頭が切れてしまう場合はマイナスにしてください (最大 -3 秒)。<br>
                </div>
                <v-slider class="settings__item-form" color="primary" show-ticks="always" thumb-label hide-details
                    :min="-3" :max="5" :step="0.1"
                    :density="is_form_dense ? 'compact' : 'default'"
                    v-model="settingsStore.settings.cm_skip_end_margin">
                </v-slider>
            </div>
        </div>
        <div class="settings__content mt-6">
            <div class="settings__content-heading">
                <Icon icon="fluent:document-text-20-filled" width="22px" />
                <span class="ml-2">ライセンス (CM 検出 AI)</span>
            </div>
            <div class="settings__description mt-1">
                CM 検出 AI のモデルと、その元になっているソフトウェアのライセンスです。<br>
                モデルを配布・再配布する場合は、下記の著作権表示と許諾文を必ず添付してください。<br>
            </div>
            <div class="settings__item">
                <div class="settings__item-heading">CM 判定モデル (cm_seq.onnx)</div>
                <div class="settings__item-label">
                    このプロジェクトで独自に学習した CM 判定モデル (GRU のアンサンブル) です。MIT License で提供します。<br>
                    Copyright (c) 2026 KonomiTV CM 検出モデルの作者<br>
                    学習には、作者自身が録画した番組から計算した特徴量だけを使っています。録画映像そのものはモデルに含まれていません。<br>
                </div>
            </div>
            <div class="settings__item">
                <div class="settings__item-heading">画像特徴抽出モデル (clip_image.onnx)</div>
                <div class="settings__item-label">
                    OpenAI の CLIP (ViT-B/32) の画像エンコーダを ONNX 形式に変換したものです。MIT License です。<br>
                    Copyright (c) 2021 OpenAI (https://github.com/openai/CLIP)<br>
                    変換には OpenCLIP (MIT License, https://github.com/mlfoundations/open_clip) を使用しました。<br>
                    CLIP のモデルカードには、研究用途を主に想定しており、商用利用は推奨しない旨の注意書きがあります。<br>
                </div>
            </div>
            <div class="settings__item">
                <div class="settings__item-heading">推論エンジン (ONNX Runtime)</div>
                <div class="settings__item-label">
                    ONNX Runtime (MIT License, Copyright (c) Microsoft Corporation) を使用しています。<br>
                    GPU で解析する場合に必要な NVIDIA CUDA / cuDNN は、NVIDIA のライセンスに従って各自でインストールするものです。KonomiTV には同梱されません。<br>
                </div>
            </div>
            <div class="settings__item">
                <div class="settings__item-heading">MIT License</div>
                <pre class="cm-license">Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.</pre>
            </div>
        </div>
    </SettingsBase>
</template>
<script lang="ts" setup>

import { onBeforeUnmount, ref } from 'vue';

import Message from '@/message';
import CMAnalysis, { ICMAnalysisJob, ICMAnalysisSettings, ICMAnalysisStatus } from '@/services/CMAnalysis';
import useSettingsStore from '@/stores/SettingsStore';
import useUserStore from '@/stores/UserStore';
import Utils from '@/utils';
import SettingsBase from '@/views/Settings/Base.vue';

// フォームを小さくするかどうか
const is_form_dense = Utils.isSmartphoneHorizontal();

const settingsStore = useSettingsStore();

// ユーザー情報を取得し、もし管理者権限であれば無効化を解除
const is_disabled = ref(true);
const user_store = useUserStore();
user_store.fetchUser().then((user) => {
    if (user && user.is_admin) {
        is_disabled.value = false;
    }
});

// CM 解析機能の状態 (取得できるまでは null)
const status = ref<ICMAnalysisStatus | null>(null);
// フォームで編集中の CM 検出設定
const cm_settings = ref<ICMAnalysisSettings>({
    enabled: false,
    analyze_new_recordings: false,
    device: 'CPU',
    threads: 2,
});
// CM 解析ジョブの一覧
const jobs = ref<ICMAnalysisJob[]>([]);

// 状態を取得し、フォームの初期値に反映する
CMAnalysis.fetchStatus().then((result) => {
    if (result) {
        status.value = result;
        cm_settings.value = {
            enabled: result.enabled,
            analyze_new_recordings: result.analyze_new_recordings,
            device: result.device,
            threads: result.threads,
        };
    }
});

// CM 解析設定を更新する関数
async function updateCMSettings() {
    const result = await CMAnalysis.updateSettings(cm_settings.value);
    if (result) {
        status.value = result;
        Message.success('CM 検出設定を更新しました。');
    }
}

// CM 検出モデルのダウンロードを開始する関数
async function downloadModel() {
    if (await CMAnalysis.downloadModel()) {
        Message.show('CM 検出モデルのダウンロードを開始しました。');
    }
}

// 待機中のジョブを取り消す関数
async function cancelAllJobs() {
    if (await CMAnalysis.cancel()) {
        await refresh();
    }
}

// 終了済みのジョブを一覧から消す関数
async function clearFinishedJobs() {
    if (await CMAnalysis.cancel(undefined, true)) {
        await refresh();
    }
}

// ジョブ一覧とモデルのダウンロード状況を更新する関数
async function refresh() {
    const result = await CMAnalysis.fetchJobs(true);
    if (result) {
        jobs.value = result;
    }
    // モデルのダウンロード状況・キューの件数だけ最新にする (編集中のフォームは上書きしない)
    const latest_status = await CMAnalysis.fetchStatus(true);
    if (latest_status && status.value) {
        status.value = latest_status;
    }
}

// 2 秒ごとに進行状況を更新する
refresh();
const refresh_timer = window.setInterval(refresh, 2000);
onBeforeUnmount(() => window.clearInterval(refresh_timer));

</script>
<style lang="scss" scoped>

.cm-license {
    margin-top: 8px;
    padding: 10px 14px;
    border-radius: 8px;
    background: rgb(var(--v-theme-background-lighten-1));
    font-family: inherit;
    font-size: 12px;
    line-height: 1.5;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    color: rgb(var(--v-theme-text-darken-1));
}

.cm-jobs {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 14px;

    &__item {
        padding: 10px 14px;
        border-radius: 8px;
        background: rgb(var(--v-theme-background-lighten-1));
    }

    &__title {
        font-size: 14.5px;
        font-weight: 700;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    &__state {
        margin-top: 2px;
        font-size: 13px;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

</style>
