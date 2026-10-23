<template>
    <!-- [改造] ビデオ整理ページ (Windows のエクスプローラー風のフォルダ・ファイル管理) -->
    <div class="route-container">
        <HeaderBar />
        <main>
            <Navigation />
            <div class="fx-wrapper">
                <SPHeaderBar />
                <div class="fx" ref="rootEl" tabindex="0" @keydown="onKeydown" @click="closeContextMenu">
                    <div class="fx__notice" v-if="userStore.user !== null && !isAdmin">
                        このページの操作 (移動・フォルダ作成・削除など) は管理者アカウントでのみ使えます。
                    </div>

                    <!-- コマンドバー -->
                    <div class="cmdbar">
                        <v-btn class="cmdbar__tree" variant="text" size="small" @click.stop="showTree = !showTree">
                            <Icon icon="fluent:folder-20-regular" width="20px" height="20px" />
                            <span class="ml-1">フォルダ</span>
                        </v-btn>
                        <template v-if="isAdmin">
                            <v-btn class="cmdbar__btn" variant="text" size="small" @click.stop="openCreateDialog">
                                <Icon icon="fluent:folder-add-20-regular" width="20px" height="20px" />
                                <span class="cmdbar__label">新規フォルダ</span>
                            </v-btn>
                            <span class="cmdbar__sep"></span>
                            <v-btn class="cmdbar__btn" variant="text" size="small" :disabled="selectedPrograms.length === 0 || busy" @click.stop="openMoveDialog">
                                <Icon icon="fluent:folder-arrow-right-20-regular" width="20px" height="20px" />
                                <span class="cmdbar__label">移動</span>
                            </v-btn>
                            <v-btn class="cmdbar__btn" variant="text" size="small" :disabled="folderTarget === null || busy" @click.stop="openRenameDialog">
                                <Icon icon="fluent:rename-20-regular" width="20px" height="20px" />
                                <span class="cmdbar__label">名前の変更</span>
                            </v-btn>
                            <v-btn class="cmdbar__btn" variant="text" size="small" color="error"
                                :disabled="busy || (selectedPrograms.length === 0 && (folderTarget === null || folderTarget.programs.length > 0))"
                                @click.stop="onDeleteCommand">
                                <Icon icon="fluent:delete-20-regular" width="20px" height="20px" />
                                <span class="cmdbar__label">削除</span>
                            </v-btn>
                            <span class="cmdbar__sep"></span>
                        </template>
                        <v-menu>
                            <template #activator="{ props }">
                                <v-btn class="cmdbar__btn" variant="text" size="small" v-bind="props" @click.stop>
                                    <Icon icon="fluent:arrow-sort-20-regular" width="20px" height="20px" />
                                    <span class="cmdbar__label">並べ替え</span>
                                </v-btn>
                            </template>
                            <v-list density="compact">
                                <v-list-item v-for="item in sortItems" :key="item.value" @click="setSort(item.value)">
                                    <template #prepend>
                                        <Icon :icon="sortKey === item.value ? 'fluent:checkmark-20-regular' : 'fluent:circle-20-regular'" width="18px" height="18px"
                                            :style="{opacity: sortKey === item.value ? 1 : 0}" />
                                    </template>
                                    <v-list-item-title>{{item.title}}</v-list-item-title>
                                </v-list-item>
                                <v-divider></v-divider>
                                <v-list-item @click="sortDesc = false"><v-list-item-title>{{sortDesc ? '　' : '✓ '}}昇順</v-list-item-title></v-list-item>
                                <v-list-item @click="sortDesc = true"><v-list-item-title>{{sortDesc ? '✓ ' : '　'}}降順</v-list-item-title></v-list-item>
                            </v-list>
                        </v-menu>
                        <v-menu>
                            <template #activator="{ props }">
                                <v-btn class="cmdbar__btn" variant="text" size="small" v-bind="props" @click.stop>
                                    <Icon :icon="viewIcon(viewMode)" width="20px" height="20px" />
                                    <span class="cmdbar__label">表示</span>
                                </v-btn>
                            </template>
                            <v-list density="compact">
                                <v-list-item v-for="mode in viewModes" :key="mode.value" @click="viewMode = mode.value">
                                    <template #prepend><Icon :icon="mode.icon" width="18px" height="18px" /></template>
                                    <v-list-item-title>{{viewMode === mode.value ? '✓ ' : '　'}}{{mode.title}}</v-list-item-title>
                                </v-list-item>
                                <v-divider></v-divider>
                                <v-list-item @click="showThumbs = !showThumbs">
                                    <v-list-item-title>{{showThumbs ? '✓ ' : '　'}}サムネイルを表示 (詳細)</v-list-item-title>
                                </v-list-item>
                            </v-list>
                        </v-menu>
                        <v-btn class="cmdbar__btn" variant="text" size="small" :disabled="busy" @click.stop="reload">
                            <Icon icon="fluent:arrow-sync-20-regular" width="20px" height="20px" />
                            <span class="cmdbar__label">更新</span>
                        </v-btn>
                        <span class="cmdbar__spacer"></span>
                        <v-btn class="cmdbar__btn" variant="text" size="small" color="primary" :to="addPageLink" @click.stop>
                            <Icon icon="fluent:arrow-upload-20-regular" width="20px" height="20px" />
                            <span class="cmdbar__label">ビデオ追加</span>
                        </v-btn>
                    </div>

                    <!-- アドレスバーと検索 -->
                    <div class="addr">
                        <button type="button" class="addr__nav" :disabled="!canGoBack" aria-label="戻る" @click.stop="goBack">
                            <Icon icon="fluent:arrow-left-20-regular" width="20px" height="20px" />
                        </button>
                        <button type="button" class="addr__nav" :disabled="!canGoForward" aria-label="進む" @click.stop="goForward">
                            <Icon icon="fluent:arrow-right-20-regular" width="20px" height="20px" />
                        </button>
                        <button type="button" class="addr__nav" :disabled="currentKey === ROOT_KEY" aria-label="上へ" @click.stop="goUp">
                            <Icon icon="fluent:arrow-up-20-regular" width="20px" height="20px" />
                        </button>
                        <button type="button" class="addr__nav" :disabled="busy" aria-label="更新" @click.stop="reload">
                            <Icon icon="fluent:arrow-sync-20-regular" width="18px" height="18px" />
                        </button>
                        <div class="addr__path">
                            <Icon icon="fluent:video-clip-20-regular" width="18px" height="18px" class="addr__path-icon" />
                            <button type="button" class="addr__crumb" :class="{'addr__crumb--drop': dropTarget === ROOT_KEY}" @click.stop="openFolder(ROOT_KEY)"
                                @dragover="onDragOver($event, ROOT_KEY)" @dragleave="onDragLeave(ROOT_KEY)" @drop="onDrop($event, ROOT_KEY)">録画フォルダ</button>
                            <template v-if="currentKey !== ROOT_KEY">
                                <Icon icon="fluent:chevron-right-20-regular" width="14px" height="14px" class="addr__chevron" />
                                <span class="addr__crumb addr__crumb--current">{{currentName}}</span>
                            </template>
                        </div>
                        <div class="addr__search">
                            <Icon icon="fluent:search-20-regular" width="18px" height="18px" class="addr__search-icon" />
                            <input class="addr__search-input" type="text" v-model="searchText" :placeholder="`${currentName}の検索`" @click.stop @keydown.esc.stop="searchText = ''">
                            <button type="button" class="addr__search-clear" v-if="searchText" aria-label="検索をやめる" @click.stop="searchText = ''">
                                <Icon icon="fluent:dismiss-20-regular" width="16px" height="16px" />
                            </button>
                        </div>
                    </div>

                    <div class="body">
                        <!-- 左: ナビゲーション (フォルダ一覧) -->
                        <nav class="nav" :class="{'nav--open': showTree}" :style="{width: `${navWidth}px`}" aria-label="フォルダ一覧">
                            <button type="button" class="nav__node nav__node--root" :class="{'nav__node--on': currentKey === ROOT_KEY, 'nav__node--drop': dropTarget === ROOT_KEY}"
                                @click.stop="openFolder(ROOT_KEY)"
                                @dragover="onDragOver($event, ROOT_KEY)" @dragleave="onDragLeave(ROOT_KEY)" @drop="onDrop($event, ROOT_KEY)">
                                <Icon icon="fluent:chevron-down-20-regular" width="14px" height="14px" class="nav__chevron" />
                                <Icon icon="fluent:video-clip-20-regular" width="20px" height="20px" class="nav__icon" />
                                <span class="nav__name">録画フォルダ</span>
                                <span class="nav__count">{{programs.length}}</span>
                            </button>
                            <button type="button" v-for="folder in folders" :key="folder.key" class="nav__node nav__node--child"
                                :class="{'nav__node--on': currentKey === folder.key, 'nav__node--drop': dropTarget === folder.key}"
                                @click.stop="openFolder(folder.key)" @contextmenu.prevent.stop="onFolderContext($event, folder)"
                                @dragover="onDragOver($event, folder.key)" @dragleave="onDragLeave(folder.key)" @drop="onDrop($event, folder.key)">
                                <Icon :icon="currentKey === folder.key ? 'fluent:folder-open-20-filled' : 'fluent:folder-20-filled'" width="20px" height="20px" class="nav__icon nav__icon--folder" />
                                <span class="nav__name">{{folder.name}}</span>
                                <span class="nav__count">{{folder.programs.length}}</span>
                            </button>
                        </nav>
                        <div class="splitter" @pointerdown.prevent="startResize" role="separator" aria-orientation="vertical"></div>

                        <!-- 右: 中身 -->
                        <section class="content" @click="onBackgroundClick" @contextmenu.prevent="onBackgroundContext">
                            <div class="content__empty" v-if="is_loading">読み込み中…</div>
                            <template v-else>
                                <!-- 詳細 -->
                                <div class="details" v-if="viewMode === 'details'">
                                    <div class="details__head">
                                        <div class="details__cell details__cell--check">
                                            <input type="checkbox" v-if="isAdmin" :checked="allSelected" :indeterminate.prop="someSelected && !allSelected"
                                                aria-label="すべて選択" @click.stop @change="toggleSelectAll">
                                        </div>
                                        <button type="button" class="details__cell details__cell--name details__sort" @click.stop="setSort('title')">
                                            名前<Icon v-if="sortKey === 'title'" :icon="sortDesc ? 'fluent:chevron-down-20-regular' : 'fluent:chevron-up-20-regular'" width="14px" height="14px" />
                                        </button>
                                        <button type="button" class="details__cell details__cell--date details__sort" @click.stop="setSort('start_time')">
                                            放送日<Icon v-if="sortKey === 'start_time'" :icon="sortDesc ? 'fluent:chevron-down-20-regular' : 'fluent:chevron-up-20-regular'" width="14px" height="14px" />
                                        </button>
                                        <button type="button" class="details__cell details__cell--duration details__sort" @click.stop="setSort('duration')">
                                            長さ<Icon v-if="sortKey === 'duration'" :icon="sortDesc ? 'fluent:chevron-down-20-regular' : 'fluent:chevron-up-20-regular'" width="14px" height="14px" />
                                        </button>
                                        <button type="button" class="details__cell details__cell--size details__sort" @click.stop="setSort('file_size')">
                                            サイズ<Icon v-if="sortKey === 'file_size'" :icon="sortDesc ? 'fluent:chevron-down-20-regular' : 'fluent:chevron-up-20-regular'" width="14px" height="14px" />
                                        </button>
                                    </div>
                                    <div class="details__row" v-for="(entry, index) in entries" :key="entry.id" :data-id="entry.id"
                                        :class="rowClass(entry)"
                                        :draggable="isAdmin && entry.kind === 'file'"
                                        @click.stop="onItemClick($event, entry, index)" @dblclick.stop="openEntry(entry)"
                                        @contextmenu.prevent.stop="onItemContext($event, entry, index)"
                                        @dragstart="entry.kind === 'file' && onDragStart($event, entry.program)" @dragend="onDragEnd"
                                        @dragover="entry.kind === 'folder' && onDragOver($event, entry.folder.key)"
                                        @dragleave="entry.kind === 'folder' && onDragLeave(entry.folder.key)"
                                        @drop="entry.kind === 'folder' && onDrop($event, entry.folder.key)">
                                        <div class="details__cell details__cell--check">
                                            <input type="checkbox" v-if="isAdmin" :checked="isSel(entry.id)" aria-label="選択" @click.stop @change="toggleSel(entry.id, index)">
                                        </div>
                                        <div class="details__cell details__cell--name">
                                            <template v-if="entry.kind === 'folder'">
                                                <Icon icon="fluent:folder-20-filled" width="30px" height="30px" class="item__folder-icon" />
                                                <div class="item__text">
                                                    <div class="item__title">{{entry.folder.name}}</div>
                                                    <div class="item__sub item__sub--sp">{{entry.folder.programs.length}}個の項目 ・ {{formatSize(entry.folder.size)}}</div>
                                                </div>
                                            </template>
                                            <template v-else>
                                                <img class="item__thumb" v-if="showThumbs" loading="lazy" decoding="async" draggable="false"
                                                    :src="`${Utils.api_base_url}/videos/${entry.program.id}/thumbnail`">
                                                <Icon v-else icon="fluent:video-20-regular" width="22px" height="22px" class="item__file-icon" />
                                                <div class="item__text">
                                                    <div class="item__title">{{entry.program.title}}</div>
                                                    <div class="item__sub">{{baseFileName(entry.program)}}<span v-if="entry.place"> ・ {{entry.place}}</span></div>
                                                    <div class="item__sub item__sub--sp">{{formatDateTime(entry.program.start_time)}} ・ {{formatDuration(entry.program.recorded_video.duration)}} ・ {{formatSize(entry.program.recorded_video.file_size)}}</div>
                                                </div>
                                            </template>
                                        </div>
                                        <template v-if="entry.kind === 'folder'">
                                            <div class="details__cell details__cell--date">{{entry.folder.latest ? formatDateTime(entry.folder.latest) : ''}}</div>
                                            <div class="details__cell details__cell--duration">{{entry.folder.programs.length}}個</div>
                                            <div class="details__cell details__cell--size">{{formatSize(entry.folder.size)}}</div>
                                        </template>
                                        <template v-else>
                                            <div class="details__cell details__cell--date">{{formatDateTime(entry.program.start_time)}}</div>
                                            <div class="details__cell details__cell--duration">{{formatDuration(entry.program.recorded_video.duration)}}</div>
                                            <div class="details__cell details__cell--size">{{formatSize(entry.program.recorded_video.file_size)}}</div>
                                        </template>
                                    </div>
                                </div>

                                <!-- 一覧 -->
                                <div class="list" v-else-if="viewMode === 'list'">
                                    <div class="list__item" v-for="(entry, index) in entries" :key="entry.id" :data-id="entry.id"
                                        :class="rowClass(entry)"
                                        :draggable="isAdmin && entry.kind === 'file'"
                                        @click.stop="onItemClick($event, entry, index)" @dblclick.stop="openEntry(entry)"
                                        @contextmenu.prevent.stop="onItemContext($event, entry, index)"
                                        @dragstart="entry.kind === 'file' && onDragStart($event, entry.program)" @dragend="onDragEnd"
                                        @dragover="entry.kind === 'folder' && onDragOver($event, entry.folder.key)"
                                        @dragleave="entry.kind === 'folder' && onDragLeave(entry.folder.key)"
                                        @drop="entry.kind === 'folder' && onDrop($event, entry.folder.key)">
                                        <Icon v-if="entry.kind === 'folder'" icon="fluent:folder-20-filled" width="22px" height="22px" class="item__folder-icon" />
                                        <Icon v-else icon="fluent:video-20-regular" width="20px" height="20px" class="item__file-icon" />
                                        <span class="list__name">{{entry.kind === 'folder' ? entry.folder.name : entry.program.title}}</span>
                                    </div>
                                </div>

                                <!-- 大アイコン -->
                                <div class="tiles" v-else>
                                    <div class="tiles__item" v-for="(entry, index) in entries" :key="entry.id" :data-id="entry.id"
                                        :class="rowClass(entry)"
                                        :draggable="isAdmin && entry.kind === 'file'"
                                        @click.stop="onItemClick($event, entry, index)" @dblclick.stop="openEntry(entry)"
                                        @contextmenu.prevent.stop="onItemContext($event, entry, index)"
                                        @dragstart="entry.kind === 'file' && onDragStart($event, entry.program)" @dragend="onDragEnd"
                                        @dragover="entry.kind === 'folder' && onDragOver($event, entry.folder.key)"
                                        @dragleave="entry.kind === 'folder' && onDragLeave(entry.folder.key)"
                                        @drop="entry.kind === 'folder' && onDrop($event, entry.folder.key)">
                                        <div class="tiles__visual">
                                            <Icon v-if="entry.kind === 'folder'" icon="fluent:folder-20-filled" width="72px" height="72px" class="item__folder-icon" />
                                            <img v-else loading="lazy" decoding="async" draggable="false" :src="`${Utils.api_base_url}/videos/${entry.program.id}/thumbnail`">
                                            <input class="tiles__check" type="checkbox" v-if="isAdmin" :checked="isSel(entry.id)" aria-label="選択" @click.stop @change="toggleSel(entry.id, index)">
                                        </div>
                                        <div class="tiles__name">{{entry.kind === 'folder' ? entry.folder.name : entry.program.title}}</div>
                                        <div class="tiles__meta">{{entry.kind === 'folder' ? `${entry.folder.programs.length}個の項目` : `${formatDuration(entry.program.recorded_video.duration)} ・ ${formatSize(entry.program.recorded_video.file_size)}`}}</div>
                                    </div>
                                </div>

                                <div class="content__empty" v-if="entries.length === 0">
                                    {{searchText ? `「${searchText}」に一致する項目はありません。` : (currentKey === ROOT_KEY ? 'このフォルダは空です。' : 'このフォルダは空です。')}}
                                </div>
                            </template>
                        </section>
                    </div>

                    <!-- ステータスバー -->
                    <div class="status">
                        <span>{{entries.length}} 個の項目</span>
                        <span v-if="selection.length > 0" class="status__selected">
                            {{selection.length}} 個の項目を選択<span v-if="selectedPrograms.length > 0"> ({{formatSize(selectedSize)}})</span>
                        </span>
                        <span class="status__spacer"></span>
                        <button type="button" class="status__view" v-for="mode in viewModes" :key="mode.value"
                            :class="{'status__view--on': viewMode === mode.value}" :aria-label="mode.title" :title="mode.title" @click.stop="viewMode = mode.value">
                            <Icon :icon="mode.icon" width="18px" height="18px" />
                        </button>
                    </div>

                    <!-- 右クリックメニュー -->
                    <div class="ctx" v-if="contextMenu !== null" :style="{left: `${contextMenu.x}px`, top: `${contextMenu.y}px`}" @click.stop @contextmenu.prevent.stop>
                        <button type="button" class="ctx__item" v-for="item in contextMenu.items" :key="item.label" :disabled="item.disabled"
                            :class="{'ctx__item--danger': item.danger}" @click="runContext(item)">
                            <Icon :icon="item.icon" width="18px" height="18px" />
                            <span>{{item.label}}</span>
                        </button>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- 移動先を選ぶダイアログ -->
    <v-dialog v-model="showMoveDialog" max-width="560" :persistent="busy">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">{{selectedPrograms.length}}件をフォルダへ移動</v-card-title>
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
                            <Icon icon="fluent:folder-link-20-regular" width="18px" height="18px" />
                            <span>録画フォルダ直下 (未分類)</span>
                        </button>
                        <button type="button" v-for="name in moveCandidates" :key="name" class="candidates__item"
                            :class="{'candidates__item--on': moveTarget === name}" :disabled="busy"
                            @click="moveInput = name; moveToRoot = false">
                            <Icon icon="fluent:folder-20-filled" width="18px" height="18px" />
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
                    「{{folderTarget?.name}}」の名前を変えます。中の録画 ({{folderTarget?.programs.length ?? 0}}件) の情報・サムネイルはそのまま引き継がれます。
                </div>
                <v-text-field v-model="folderInput" label="新しいフォルダ名" variant="outlined" density="comfortable" hide-details="auto"
                    :counter="60" :disabled="busy" autofocus :error-messages="folderInputError" @keydown.enter="executeRename" />
            </v-card-text>
            <v-card-actions class="pt-4 px-6 pb-6">
                <v-spacer></v-spacer>
                <v-btn color="text" variant="text" :disabled="busy" @click="showRenameDialog = false">閉じる</v-btn>
                <v-btn class="px-3" color="primary" variant="flat"
                    :disabled="busy || folderInput.trim() === '' || folderInput.trim() === folderTarget?.name || folderInputError !== ''" @click="executeRename">変更する</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- 空のフォルダの削除 -->
    <v-dialog v-model="showDeleteFolderDialog" max-width="480" :persistent="busy">
        <v-card>
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">空のフォルダを削除</v-card-title>
            <v-card-text class="pt-2 pb-0">
                空のフォルダ「{{folderTarget?.name}}」を削除します。中に何かあるフォルダは削除されません。
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
            <v-card-title class="d-flex justify-center pt-6 font-weight-bold">{{selectedPrograms.length}}件の録画を削除</v-card-title>
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

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
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
    latest: string;
}

type IEntry =
    | { id: string; kind: 'folder'; folder: IFolderNode }
    | { id: string; kind: 'file'; program: IRecordedProgram; place: string };

type SortKey = 'start_time' | 'title' | 'file_size' | 'duration';
type ViewMode = 'details' | 'list' | 'tiles';

// 録画フォルダ直下 (フォルダ分けなし) を表すキー
const ROOT_KEY = '';

const router = useRouter();
const userStore = useUserStore();
const isAdmin = computed(() => userStore.user?.is_admin === true);
const rootEl = ref<HTMLElement | null>(null);

// ---- この端末のブラウザに覚えておく表示設定 ----

const PREF_KEY = 'konomitv.files.prefs';
const loadPrefs = (): Record<string, unknown> => {
    try {
        const parsed = JSON.parse(localStorage.getItem(PREF_KEY) ?? '{}');
        return typeof parsed === 'object' && parsed !== null ? parsed : {};
    } catch {
        return {};
    }
};
const prefs = loadPrefs();
const savePrefs = () => {
    try {
        localStorage.setItem(PREF_KEY, JSON.stringify({
            viewMode: viewMode.value, sortKey: sortKey.value, sortDesc: sortDesc.value,
            showThumbs: showThumbs.value, navWidth: navWidth.value,
        }));
    } catch {
        // 保存できなくても表示は変わらない
    }
};

const programs = ref<IRecordedProgram[]>([]);
const apiFolders = ref<{ name: string; path: string }[]>([]);
const is_loading = ref(true);
const currentKey = ref<string>(ROOT_KEY);
const searchText = ref<string | null>('');
const viewMode = ref<ViewMode>((['details', 'list', 'tiles'] as string[]).includes(prefs.viewMode as string) ? prefs.viewMode as ViewMode : 'details');
const sortKey = ref<SortKey>((['start_time', 'title', 'file_size', 'duration'] as string[]).includes(prefs.sortKey as string) ? prefs.sortKey as SortKey : 'start_time');
const sortDesc = ref<boolean>(typeof prefs.sortDesc === 'boolean' ? prefs.sortDesc : false);
const showThumbs = ref<boolean>(typeof prefs.showThumbs === 'boolean' ? prefs.showThumbs : true);
const navWidth = ref<number>(typeof prefs.navWidth === 'number' ? Math.min(520, Math.max(160, prefs.navWidth)) : 260);
const showTree = ref(false);

watch([viewMode, sortKey, sortDesc, showThumbs], savePrefs);

const sortItems: { title: string; value: SortKey }[] = [
    { title: '名前', value: 'title' },
    { title: '放送日', value: 'start_time' },
    { title: '長さ', value: 'duration' },
    { title: 'サイズ', value: 'file_size' },
];
const viewModes: { title: string; value: ViewMode; icon: string }[] = [
    { title: '詳細', value: 'details', icon: 'fluent:text-bullet-list-20-regular' },
    { title: '一覧', value: 'list', icon: 'fluent:list-20-regular' },
    { title: '大アイコン', value: 'tiles', icon: 'fluent:grid-20-regular' },
];
const viewIcon = (mode: ViewMode): string => viewModes.find(m => m.value === mode)?.icon ?? 'fluent:text-bullet-list-20-regular';

const setSort = (key: SortKey) => {
    if (sortKey.value === key) {
        sortDesc.value = !sortDesc.value;
    } else {
        sortKey.value = key;
        sortDesc.value = key === 'start_time' ? sortDesc.value : false;
    }
};

// ---- 左側の幅 (境界をドラッグして変える) ----

const startResize = (event: PointerEvent) => {
    const startX = event.clientX;
    const startWidth = navWidth.value;
    const onMove = (e: PointerEvent) => {
        navWidth.value = Math.min(520, Math.max(160, startWidth + e.clientX - startX));
    };
    const onUp = () => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        savePrefs();
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
};

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
            latest: list.reduce((latest, p) => p.start_time > latest ? p.start_time : latest, ''),
        });
    }
    result.sort((a, b) => a.name.localeCompare(b.name, 'ja', { numeric: true }));
    return result;
});

const rootPrograms = computed(() => programs.value.filter(p => keyOf(p) === ROOT_KEY));
const currentFolder = computed(() => folders.value.find(f => f.key === currentKey.value) ?? null);
const currentName = computed(() => currentKey.value === ROOT_KEY ? '録画フォルダ' : (currentFolder.value?.name ?? baseName(currentKey.value)));
const placeOf = (program: IRecordedProgram): string => {
    const key = keyOf(program);
    return key === ROOT_KEY ? '未分類' : baseName(key);
};

// ---- 検索・並べ替え ----

const normalizeForSearch = (s: string): string => Array.from(s.normalize('NFKC').toLowerCase())
    .map(c => {
        const code = c.charCodeAt(0);
        return code >= 0x30a1 && code <= 0x30f6 ? String.fromCharCode(code - 0x60) : c;
    })
    .join('')
    .replace(/[\s・!?~〜]/g, '');

const matchesSearch = (text: string, query: string): boolean => normalizeForSearch(text).includes(query);

// いま表示している項目 (フォルダが先、あとにファイル)
const entries = computed<IEntry[]>(() => {
    const query = normalizeForSearch(searchText.value ?? '');
    const dir = sortDesc.value ? -1 : 1;

    let folderList: IFolderNode[] = [];
    let fileList: IRecordedProgram[];
    if (query !== '') {
        // 検索は、いま開いているフォルダとその中を探す (録画フォルダなら全フォルダ)
        fileList = (currentKey.value === ROOT_KEY ? programs.value : (currentFolder.value?.programs ?? []))
            .filter(p => matchesSearch(`${p.title} ${baseFileName(p)}`, query));
        if (currentKey.value === ROOT_KEY) folderList = folders.value.filter(f => matchesSearch(f.name, query));
    } else if (currentKey.value === ROOT_KEY) {
        folderList = folders.value;
        fileList = rootPrograms.value;
    } else {
        fileList = currentFolder.value?.programs ?? [];
    }

    const sortedFolders = [...folderList].sort((a, b) => {
        switch (sortKey.value) {
            case 'start_time': return a.latest.localeCompare(b.latest) * dir;
            case 'file_size': return (a.size - b.size) * dir;
            case 'duration': return (a.programs.length - b.programs.length) * dir;
            default: return a.name.localeCompare(b.name, 'ja', { numeric: true }) * dir;
        }
    });
    const sortedFiles = [...fileList].sort((a, b) => {
        switch (sortKey.value) {
            case 'title': return a.title.localeCompare(b.title, 'ja', { numeric: true }) * dir;
            case 'file_size': return (a.recorded_video.file_size - b.recorded_video.file_size) * dir;
            case 'duration': return (a.recorded_video.duration - b.recorded_video.duration) * dir;
            default: return a.start_time.localeCompare(b.start_time) * dir;
        }
    });

    const showPlace = query !== '' && currentKey.value === ROOT_KEY;
    return [
        ...sortedFolders.map((folder): IEntry => ({ id: `f:${folder.key}`, kind: 'folder', folder })),
        ...sortedFiles.map((program): IEntry => ({ id: `v:${program.id}`, kind: 'file', program, place: showPlace ? placeOf(program) : '' })),
    ];
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
    if (size >= 1024 * 1024 * 1024) return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`;
    return `${Math.round(size / 1024 / 1024)} MB`;
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
    // 開いていたフォルダがなくなっていたら、録画フォルダに戻る
    if (currentKey.value !== ROOT_KEY && !folders.value.some(f => f.key === currentKey.value)) {
        currentKey.value = ROOT_KEY;
        navHistory.value = [ROOT_KEY];
        historyIndex.value = 0;
    }
    // 消えた項目は選択から外す
    const alive = new Set([...programs.value.map(p => `v:${p.id}`), ...folders.value.map(f => `f:${f.key}`)]);
    selection.value = selection.value.filter(id => alive.has(id));
};

// ---- フォルダ移動の履歴 (戻る・進む・上へ) ----

const navHistory = ref<string[]>([ROOT_KEY]);
const historyIndex = ref(0);
const canGoBack = computed(() => historyIndex.value > 0);
const canGoForward = computed(() => historyIndex.value < navHistory.value.length - 1);

const openFolder = (key: string, record: boolean = true) => {
    if (key === currentKey.value && record) {
        showTree.value = false;
        return;
    }
    currentKey.value = key;
    selection.value = [];
    anchorIndex.value = -1;
    searchText.value = '';
    showTree.value = false;
    if (record) {
        navHistory.value = [...navHistory.value.slice(0, historyIndex.value + 1), key];
        historyIndex.value = navHistory.value.length - 1;
    }
    rootEl.value?.focus({ preventScroll: true });
};

const goBack = () => {
    if (!canGoBack.value) return;
    historyIndex.value--;
    openFolder(navHistory.value[historyIndex.value], false);
};
const goForward = () => {
    if (!canGoForward.value) return;
    historyIndex.value++;
    openFolder(navHistory.value[historyIndex.value], false);
};
const goUp = () => {
    if (currentKey.value !== ROOT_KEY) openFolder(ROOT_KEY);
};

const openVideo = (id: number) => {
    router.push(`/videos/watch/${id}`);
};

const openEntry = (entry: IEntry) => {
    if (entry.kind === 'folder') openFolder(entry.folder.key);
    else openVideo(entry.program.id);
};

const addPageLink = computed(() => currentKey.value === ROOT_KEY
    ? '/videos/upload' : `/videos/upload?folder=${encodeURIComponent(currentName.value)}`);

// ---- 選択 (エクスプローラーと同じ: クリック=1つ選ぶ / Ctrl=追加・解除 / Shift=範囲) ----

const selection = ref<string[]>([]);
const anchorIndex = ref(-1);
const isCoarse = window.matchMedia('(pointer: coarse)').matches;

const isSel = (id: string): boolean => selection.value.includes(id);

const rowClass = (entry: IEntry) => ({
    'is-selected': isSel(entry.id),
    'is-dragging': entry.kind === 'file' && dragIds.value.includes(entry.program.id),
    'is-drop': entry.kind === 'folder' && dropTarget.value === entry.folder.key,
});

const toggleSel = (id: string, index: number) => {
    selection.value = isSel(id) ? selection.value.filter(v => v !== id) : [...selection.value, id];
    anchorIndex.value = index;
};

const onItemClick = (event: MouseEvent, entry: IEntry, index: number) => {
    closeContextMenu();
    rootEl.value?.focus({ preventScroll: true });
    if (isCoarse) {
        // スマホ・タブレットは、タップで選択を切り替える (フォルダはそのまま開く)
        if (entry.kind === 'folder') openFolder(entry.folder.key);
        else toggleSel(entry.id, index);
        return;
    }
    if (event.shiftKey && anchorIndex.value >= 0) {
        const from = Math.min(anchorIndex.value, index);
        const to = Math.max(anchorIndex.value, index);
        const range = entries.value.slice(from, to + 1).map(e => e.id);
        selection.value = event.ctrlKey || event.metaKey ? [...new Set([...selection.value, ...range])] : range;
    } else if (event.ctrlKey || event.metaKey) {
        toggleSel(entry.id, index);
    } else {
        selection.value = [entry.id];
        anchorIndex.value = index;
    }
};

const onBackgroundClick = () => {
    closeContextMenu();
    selection.value = [];
    rootEl.value?.focus({ preventScroll: true });
};

const allSelected = computed(() => entries.value.length > 0 && entries.value.every(e => isSel(e.id)));
const someSelected = computed(() => selection.value.length > 0);
const toggleSelectAll = () => {
    selection.value = allSelected.value ? [] : entries.value.map(e => e.id);
};

const selectedPrograms = computed(() => {
    const ids = new Set(selection.value.filter(id => id.startsWith('v:')).map(id => Number(id.slice(2))));
    return programs.value.filter(p => ids.has(p.id));
});
const selectedSize = computed(() => selectedPrograms.value.reduce((sum, p) => sum + p.recorded_video.file_size, 0));

// 「名前の変更」「空のフォルダを削除」の対象: 選んだフォルダが1つならそれ、何も選んでいなければ開いているフォルダ
const folderTarget = computed<IFolderNode | null>(() => {
    const selectedFolders = selection.value.filter(id => id.startsWith('f:'));
    if (selectedFolders.length === 1 && selectedPrograms.value.length === 0) {
        return folders.value.find(f => `f:${f.key}` === selectedFolders[0]) ?? null;
    }
    if (selection.value.length === 0 && currentKey.value !== ROOT_KEY) return currentFolder.value;
    return null;
});

// ---- キーボード操作 ----

const anyDialogOpen = computed(() => showMoveDialog.value || showCreateDialog.value || showRenameDialog.value
    || showDeleteFolderDialog.value || showDeleteDialog.value);

const scrollToEntry = async (id: string) => {
    await nextTick();
    rootEl.value?.querySelector<HTMLElement>(`[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: 'nearest' });
};

const moveFocus = (delta: number, extend: boolean) => {
    if (entries.value.length === 0) return;
    const lastSelected = selection.value.length > 0 ? entries.value.findIndex(e => e.id === selection.value[selection.value.length - 1]) : -1;
    let next = lastSelected < 0 ? (delta > 0 ? 0 : entries.value.length - 1) : lastSelected + delta;
    next = Math.min(entries.value.length - 1, Math.max(0, next));
    if (extend && anchorIndex.value >= 0) {
        const from = Math.min(anchorIndex.value, next);
        const to = Math.max(anchorIndex.value, next);
        selection.value = entries.value.slice(from, to + 1).map(e => e.id);
    } else {
        selection.value = [entries.value[next].id];
        anchorIndex.value = next;
    }
    scrollToEntry(entries.value[next].id);
};

const onKeydown = (event: KeyboardEvent) => {
    const target = event.target as HTMLElement | null;
    if (target && (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) && (target as HTMLInputElement).type !== 'checkbox' || target.isContentEditable)) return;
    if (anyDialogOpen.value || busy.value) return;
    switch (event.key) {
        case 'ArrowDown':
        case 'ArrowRight':
            if (event.altKey) return;
            event.preventDefault();
            moveFocus(1, event.shiftKey);
            break;
        case 'ArrowUp':
        case 'ArrowLeft':
            if (event.altKey) {
                event.preventDefault();
                if (event.key === 'ArrowUp') goUp(); else goBack();
                return;
            }
            event.preventDefault();
            moveFocus(-1, event.shiftKey);
            break;
        case 'Enter': {
            const first = entries.value.find(e => isSel(e.id));
            if (first) {
                event.preventDefault();
                openEntry(first);
            }
            break;
        }
        case 'Backspace':
            event.preventDefault();
            goUp();
            break;
        case 'Escape':
            closeContextMenu();
            selection.value = [];
            break;
        case 'a':
        case 'A':
            if (event.ctrlKey || event.metaKey) {
                event.preventDefault();
                selection.value = entries.value.map(e => e.id);
            }
            break;
        case 'Delete':
            if (isAdmin.value) {
                event.preventDefault();
                onDeleteCommand();
            }
            break;
        case 'F2':
            if (isAdmin.value && folderTarget.value !== null) {
                event.preventDefault();
                openRenameDialog();
            }
            break;
        case 'F5':
            event.preventDefault();
            reload();
            break;
        default:
            break;
    }
};

// ---- 右クリックメニュー ----

interface IContextItem {
    label: string;
    icon: string;
    action: () => void;
    disabled?: boolean;
    danger?: boolean;
}

const contextMenu = ref<{ x: number; y: number; items: IContextItem[] } | null>(null);

const closeContextMenu = () => {
    contextMenu.value = null;
};

const showContextMenu = (event: MouseEvent, items: IContextItem[]) => {
    const host = rootEl.value?.getBoundingClientRect();
    if (!host) return;
    const width = 220;
    const height = items.length * 36 + 12;
    const x = Math.min(event.clientX - host.left, Math.max(0, host.width - width - 8));
    const y = Math.min(event.clientY - host.top, Math.max(0, host.height - height - 8));
    contextMenu.value = { x, y, items };
};

const runContext = (item: IContextItem) => {
    closeContextMenu();
    item.action();
};

const onItemContext = (event: MouseEvent, entry: IEntry, index: number) => {
    rootEl.value?.focus({ preventScroll: true });
    if (!isSel(entry.id)) {
        selection.value = [entry.id];
        anchorIndex.value = index;
    }
    const items: IContextItem[] = [];
    if (entry.kind === 'folder') {
        items.push({ label: '開く', icon: 'fluent:folder-open-20-regular', action: () => openFolder(entry.folder.key) });
        if (isAdmin.value) {
            items.push({ label: '名前の変更', icon: 'fluent:rename-20-regular', action: openRenameDialog, disabled: folderTarget.value === null });
            items.push({ label: '空のフォルダを削除', icon: 'fluent:delete-20-regular', action: openDeleteFolderDialog, disabled: entry.folder.programs.length > 0, danger: true });
        }
    } else {
        items.push({ label: '再生', icon: 'fluent:play-20-filled', action: () => openVideo(entry.program.id) });
        if (isAdmin.value) {
            items.push({ label: `フォルダへ移動 (${selectedPrograms.value.length}件)`, icon: 'fluent:folder-arrow-right-20-regular', action: openMoveDialog });
            items.push({ label: `削除 (${selectedPrograms.value.length}件)`, icon: 'fluent:delete-20-regular', action: openDeleteDialog, danger: true });
        }
    }
    showContextMenu(event, items);
};

// 左のフォルダ一覧での右クリック
const onFolderContext = (event: MouseEvent, folder: IFolderNode) => {
    if (currentKey.value !== folder.key) openFolder(folder.key);
    const items: IContextItem[] = [{ label: '開く', icon: 'fluent:folder-open-20-regular', action: () => openFolder(folder.key) }];
    if (isAdmin.value) {
        items.push({ label: '名前の変更', icon: 'fluent:rename-20-regular', action: openRenameDialog });
        items.push({ label: '空のフォルダを削除', icon: 'fluent:delete-20-regular', action: openDeleteFolderDialog, disabled: folder.programs.length > 0, danger: true });
    }
    showContextMenu(event, items);
};

const onBackgroundContext = (event: MouseEvent) => {
    selection.value = [];
    const items: IContextItem[] = [{ label: '更新', icon: 'fluent:arrow-sync-20-regular', action: reload }];
    if (isAdmin.value) items.unshift({ label: '新規フォルダ', icon: 'fluent:folder-add-20-regular', action: openCreateDialog });
    showContextMenu(event, items);
};

// ---- 移動・削除などの共通処理 ----

const busy = ref(false);
const doneCount = ref(0);
const totalCount = ref(0);
const failures = ref<{ id: number; title: string; message: string }[]>([]);
// 直前の移動で、移動先に同名のファイルがあったためファイル名の末尾に -(1) などを付けた件数
const renamedCount = ref(0);

const INVALID_FOLDER_CHARS = '\\/:*?"<>|';
const hasInvalidFolderChar = (c: string): boolean => INVALID_FOLDER_CHARS.includes(c) || c.charCodeAt(0) < 32 || c.charCodeAt(0) === 127;

const validateFolderName = (raw: string): string => {
    const name = raw.trim();
    if (name === '') return '';
    if (name.length > 60) return '60文字までです。';
    if (Array.from(name).some(hasInvalidFolderChar)) return '使えない文字が含まれています。(\\ / : * ? " < > | )';
    if (name === '.' || name === '..' || name.endsWith('.')) return '末尾にドットは使えません。';
    return '';
};

// 指定した録画を、フォルダ (空文字なら録画フォルダ直下) へ移動する。移動に成功した件数を返す
const moveTo = async (ids: number[], folderName: string): Promise<number> => {
    const targets = programs.value.filter(p => ids.includes(p.id));
    busy.value = true;
    doneCount.value = 0;
    totalCount.value = targets.length;
    failures.value = [];
    renamedCount.value = 0;
    let succeeded = 0;
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
    if (!isSel(`v:${program.id}`)) selection.value = [`v:${program.id}`];
    dragIds.value = selectedPrograms.value.map(p => p.id);
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
    event.stopPropagation();
    const ids = dragIds.value;
    dragIds.value = [];
    dropTarget.value = null;
    if (ids.length === 0 || busy.value) return;
    // すでにそのフォルダにあるものは動かさない
    const moving = programs.value.filter(p => ids.includes(p.id) && keyOf(p) !== key).map(p => p.id);
    if (moving.length === 0) return;
    const label = key === ROOT_KEY ? '録画フォルダ直下' : baseName(key);
    const succeeded = await moveTo(moving, key === ROOT_KEY ? '' : baseName(key));
    selection.value = selection.value.filter(id => failures.value.some(f => `v:${f.id}` === id));
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
    if (selectedPrograms.value.length === 0) return;
    failures.value = [];
    moveToRoot.value = false;
    moveInput.value = currentKey.value === ROOT_KEY ? '' : currentName.value;
    showMoveDialog.value = true;
};

const executeMoveFromDialog = async () => {
    const target = moveTarget.value;
    if (target === null || moveNameError.value !== '') return;
    const ids = selectedPrograms.value.map(p => p.id);
    const succeeded = await moveTo(ids, target);
    selection.value = selection.value.filter(id => failures.value.some(f => `v:${f.id}` === id));
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
    if (folderTarget.value === null) return;
    folderInput.value = folderTarget.value.name;
    showRenameDialog.value = true;
};

const executeRename = async () => {
    const target = folderTarget.value;
    const name = (folderInput.value ?? '').trim();
    if (target === null || name === '' || name === target.name || folderInputError.value !== '' || busy.value) return;
    busy.value = true;
    const result = await Videos.renameFolder(target.name, name);
    busy.value = false;
    if (result.error !== null) {
        Message.error(result.error);
        return;
    }
    showRenameDialog.value = false;
    // 名前を変えるとファイルの場所 (キー) が変わるので、新しい場所を開き直す
    const wasCurrent = currentKey.value === target.key;
    const newKey = result.path;
    await reload();
    navHistory.value = [ROOT_KEY];
    historyIndex.value = 0;
    if (wasCurrent && newKey !== null) openFolder(newKey);
    Message.success(`フォルダ名を「${name}」に変更しました。`);
};

const openDeleteFolderDialog = () => {
    if (folderTarget.value === null || folderTarget.value.programs.length > 0) return;
    showDeleteFolderDialog.value = true;
};

const executeDeleteFolder = async () => {
    const target = folderTarget.value;
    if (target === null || busy.value) return;
    busy.value = true;
    const error = await Videos.deleteFolder(target.name);
    busy.value = false;
    if (error !== null) {
        Message.error(error);
        return;
    }
    showDeleteFolderDialog.value = false;
    if (currentKey.value === target.key) openFolder(ROOT_KEY);
    await reload();
    Message.success(`フォルダ「${target.name}」を削除しました。`);
};

// ---- 録画ファイルの削除 ----

const showDeleteDialog = ref(false);

const openDeleteDialog = () => {
    if (selectedPrograms.value.length === 0) return;
    failures.value = [];
    showDeleteDialog.value = true;
};

// 「削除」ボタン・Delete キー: 録画を選んでいれば録画の削除、空のフォルダを選んでいればそのフォルダの削除
const onDeleteCommand = () => {
    if (selectedPrograms.value.length > 0) openDeleteDialog();
    else if (folderTarget.value !== null && folderTarget.value.programs.length === 0) openDeleteFolderDialog();
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
    selection.value = selection.value.filter(id => failures.value.some(f => `v:${f.id}` === id));
    await reload();
    if (failures.value.length === 0) {
        showDeleteDialog.value = false;
        Message.success(`${succeeded}件を削除しました。`);
    } else {
        Message.warning(`${succeeded}件を削除しました。${failures.value.length}件は失敗しました。`);
    }
};

const onWindowClick = () => closeContextMenu();

onMounted(async () => {
    window.addEventListener('click', onWindowClick);
    await userStore.fetchUser();
    await reload();
});

onBeforeUnmount(() => {
    window.removeEventListener('click', onWindowClick);
});

</script>
<style lang="scss" scoped>

.fx-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
}

.fx {
    position: relative;
    display: flex;
    flex-direction: column;
    width: 100%;
    // エクスプローラーのように、画面いっぱいに使って中だけをスクロールさせる
    height: calc(100vh - 96px);
    min-height: 520px;
    padding: 8px 12px 12px;
    outline: none;
    min-width: 0;
    @include smartphone-horizontal {
        padding: 8px !important;
    }
    @include smartphone-vertical {
        height: auto;
        min-height: 0;
        padding: 4px 4px 12px !important;
    }

    &__notice {
        margin-bottom: 8px;
        padding: 8px 14px;
        border-radius: 8px;
        font-size: 14px;
        background: rgb(var(--v-theme-background-lighten-1));
        color: rgb(var(--v-theme-error));
    }
}

// ---- コマンドバー ----
.cmdbar {
    flex: none;
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 4px 6px;
    border-radius: 8px;
    background: rgb(var(--v-theme-background-lighten-1));
    overflow-x: auto;
    scrollbar-width: none;
    &::-webkit-scrollbar {
        display: none;
    }
    &__btn, &__tree {
        flex: none;
        letter-spacing: 0;
        text-transform: none;
        font-size: 13px;
    }
    &__tree {
        display: none;
        @include smartphone-vertical {
            display: inline-flex;
        }
    }
    &__sep {
        flex: none;
        width: 1px;
        height: 22px;
        margin: 0 6px;
        background: rgb(var(--v-theme-background-lighten-2));
    }
    &__spacer {
        flex: 1;
    }
    &__label {
        margin-left: 6px;
        @include smartphone-vertical {
            display: none;
        }
    }
}

// ---- アドレスバー ----
.addr {
    flex: none;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 0;
    @include smartphone-vertical {
        flex-wrap: wrap;
    }

    &__nav {
        flex: none;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: transparent;
        &:hover:not(:disabled) {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        &:disabled {
            opacity: 0.35;
            cursor: default;
        }
    }

    &__path {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 2px;
        min-width: 0;
        height: 34px;
        padding: 0 6px;
        border: 1px solid rgb(var(--v-theme-background-lighten-2));
        border-radius: 6px;
        overflow: hidden;
        background: rgb(var(--v-theme-background-lighten-1));
        @include smartphone-vertical {
            flex: 1 1 100%;
            order: 3;
        }
    }

    &__path-icon {
        flex: none;
        margin: 0 4px;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__chevron {
        flex: none;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__crumb {
        flex: none;
        max-width: 100%;
        padding: 3px 8px;
        border: none;
        border-radius: 4px;
        font-size: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: transparent;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        &--current {
            cursor: default;
            font-weight: 700;
            &:hover {
                background: transparent;
            }
        }
        &--drop {
            outline: 2px dashed rgb(var(--v-theme-primary));
        }
    }

    &__search {
        flex: none;
        position: relative;
        display: flex;
        align-items: center;
        width: 260px;
        height: 34px;
        @include smartphone-vertical {
            flex: 1 1 100%;
            order: 4;
            width: auto;
        }
    }

    &__search-icon {
        position: absolute;
        left: 10px;
        color: rgb(var(--v-theme-text-darken-1));
        pointer-events: none;
    }

    &__search-input {
        width: 100%;
        height: 100%;
        padding: 0 32px 0 34px;
        border: 1px solid rgb(var(--v-theme-background-lighten-2));
        border-radius: 6px;
        font-size: 14px;
        outline: none;
        color: rgb(var(--v-theme-text));
        background: rgb(var(--v-theme-background-lighten-1));
        &:focus {
            border-color: rgb(var(--v-theme-primary));
        }
    }

    &__search-clear {
        position: absolute;
        right: 4px;
        display: flex;
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
}

// ---- 本体 (左のナビゲーション | 境界 | 右の中身) ----
.body {
    flex: 1;
    display: flex;
    min-height: 0;
    @include smartphone-vertical {
        flex-direction: column;
    }
}

.nav {
    flex: none;
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 160px;
    max-width: 520px;
    padding: 6px 4px;
    overflow-y: auto;
    border-radius: 8px;
    background: rgb(var(--v-theme-background-lighten-1));
    @include smartphone-vertical {
        display: none;
        width: 100% !important;
        max-width: none;
        max-height: 45vh;
        margin-bottom: 8px;
        &--open {
            display: flex;
        }
    }

    &__node {
        display: flex;
        align-items: center;
        gap: 6px;
        width: 100%;
        min-height: 32px;
        padding: 4px 8px;
        border: none;
        border-radius: 6px;
        text-align: left;
        font-size: 14px;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: transparent;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        &--on {
            background: rgb(var(--v-theme-background-lighten-2));
            box-shadow: inset 3px 0 0 rgb(var(--v-theme-primary));
        }
        &--child {
            padding-left: 28px;
        }
        &--drop {
            outline: 2px dashed rgb(var(--v-theme-primary));
            outline-offset: -2px;
            background: rgb(var(--v-theme-background-lighten-2));
        }
    }

    &__chevron {
        flex: none;
        color: rgb(var(--v-theme-text-darken-1));
    }

    &__icon {
        flex: none;
        &--folder {
            color: #f2c14e;
        }
        &--muted {
            color: rgb(var(--v-theme-text-darken-1));
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

.splitter {
    flex: none;
    width: 9px;
    cursor: col-resize;
    position: relative;
    &::after {
        content: '';
        position: absolute;
        top: 0;
        bottom: 0;
        left: 4px;
        width: 1px;
        background: transparent;
    }
    &:hover::after {
        background: rgb(var(--v-theme-primary));
    }
    @include smartphone-vertical {
        display: none;
    }
}

.content {
    flex: 1;
    min-width: 0;
    overflow: auto;
    border-radius: 8px;
    background: rgb(var(--v-theme-background-lighten-1));
    @include smartphone-vertical {
        overflow: visible;
    }

    &__empty {
        padding: 48px 0;
        text-align: center;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

// 項目の共通部品
.item {
    &__folder-icon {
        flex: none;
        color: #f2c14e;
    }
    &__file-icon {
        flex: none;
        color: rgb(var(--v-theme-text-darken-1));
    }
    &__thumb {
        flex: none;
        width: 64px;
        aspect-ratio: 16 / 9;
        object-fit: cover;
        border-radius: 4px;
        background: rgb(var(--v-theme-background-lighten-2));
    }
    &__text {
        min-width: 0;
        flex: 1;
    }
    &__title {
        font-size: 14px;
        line-height: 1.35;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        @include smartphone-vertical {
            white-space: normal;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            word-break: break-all;
        }
    }
    &__sub {
        margin-top: 1px;
        font-size: 11.5px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        color: rgb(var(--v-theme-text-darken-1));
        &--sp {
            display: none;
            @include smartphone-vertical {
                display: block;
            }
        }
        @include smartphone-vertical {
            &:not(.item__sub--sp) {
                display: none;
            }
        }
    }
}

// 項目の選択・ドラッグの見た目 (エクスプローラーと同じ水色系)
.is-selected {
    background: rgba(var(--v-theme-primary), 0.22) !important;
    box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.6);
}
.is-dragging {
    opacity: 0.45;
}
.is-drop {
    outline: 2px dashed rgb(var(--v-theme-primary));
    outline-offset: -2px;
}

// ---- 詳細 ----
.details {
    display: flex;
    flex-direction: column;
    min-width: 560px;
    @include smartphone-vertical {
        min-width: 0;
    }

    &__head {
        position: sticky;
        top: 0;
        z-index: 2;
        display: flex;
        align-items: center;
        height: 32px;
        font-size: 12.5px;
        border-bottom: 1px solid rgb(var(--v-theme-background-lighten-2));
        color: rgb(var(--v-theme-text-darken-1));
        background: rgb(var(--v-theme-background-lighten-1));
        @include smartphone-vertical {
            display: none;
        }
    }

    &__sort {
        border: none;
        background: transparent;
        color: inherit;
        font-size: inherit;
        cursor: pointer;
        text-align: left;
        gap: 4px;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
    }

    &__row {
        display: flex;
        align-items: center;
        min-height: 46px;
        border-radius: 4px;
        cursor: default;
        user-select: none;
        &:hover {
            background: rgba(var(--v-theme-primary), 0.1);
        }
        @include smartphone-vertical {
            min-height: 56px;
            padding: 2px 4px;
        }
    }

    &__cell {
        flex: none;
        display: flex;
        align-items: center;
        padding: 0 10px;
        font-size: 13px;
        white-space: nowrap;
        color: rgb(var(--v-theme-text-darken-1));
        height: 100%;
        &--check {
            width: 32px;
            padding: 0 0 0 8px;
            input {
                width: 16px;
                height: 16px;
                accent-color: rgb(var(--v-theme-primary));
            }
        }
        &--name {
            flex: 1;
            min-width: 0;
            gap: 10px;
            color: rgb(var(--v-theme-text));
        }
        &--date {
            width: 140px;
        }
        &--duration {
            width: 72px;
            justify-content: flex-end;
        }
        &--size {
            width: 96px;
            justify-content: flex-end;
        }
        @include smartphone-vertical {
            &--date, &--duration, &--size {
                display: none;
            }
        }
    }
}

// ---- 一覧 ----
.list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1px 8px;
    padding: 6px;
    @include smartphone-vertical {
        grid-template-columns: minmax(0, 1fr);
    }

    &__item {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
        height: 32px;
        padding: 0 8px;
        border-radius: 4px;
        cursor: default;
        user-select: none;
        &:hover {
            background: rgba(var(--v-theme-primary), 0.1);
        }
        @include smartphone-vertical {
            height: 40px;
        }
    }

    &__name {
        min-width: 0;
        font-size: 13.5px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

// ---- 大アイコン ----
.tiles {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 8px;
    padding: 10px;
    @include smartphone-vertical {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        padding: 6px;
    }

    &__item {
        position: relative;
        min-width: 0;
        padding: 8px;
        border-radius: 8px;
        cursor: default;
        user-select: none;
        &:hover {
            background: rgba(var(--v-theme-primary), 0.1);
        }
    }

    &__visual {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        aspect-ratio: 16 / 9;
        overflow: hidden;
        border-radius: 6px;
        background: rgb(var(--v-theme-background-lighten-2));
        img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
    }

    &__check {
        position: absolute;
        top: 6px;
        left: 6px;
        width: 18px;
        height: 18px;
        accent-color: rgb(var(--v-theme-primary));
        opacity: 0;
    }
    &__item:hover &__check, &__item.is-selected &__check {
        opacity: 1;
    }
    @media (pointer: coarse) {
        &__check {
            opacity: 1;
        }
    }

    &__name {
        margin-top: 6px;
        font-size: 13px;
        line-height: 1.35;
        word-break: break-all;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    &__meta {
        margin-top: 2px;
        font-size: 11.5px;
        color: rgb(var(--v-theme-text-darken-1));
    }
}

// ---- ステータスバー ----
.status {
    flex: none;
    display: flex;
    align-items: center;
    gap: 16px;
    height: 30px;
    padding: 0 8px;
    margin-top: 6px;
    border-radius: 6px;
    font-size: 12.5px;
    color: rgb(var(--v-theme-text-darken-1));
    background: rgb(var(--v-theme-background-lighten-1));

    &__selected {
        color: rgb(var(--v-theme-text));
    }
    &__spacer {
        flex: 1;
    }
    &__view {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 24px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        color: rgb(var(--v-theme-text-darken-1));
        background: transparent;
        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        &--on {
            color: rgb(var(--v-theme-text));
            background: rgb(var(--v-theme-background-lighten-2));
            box-shadow: inset 0 -2px 0 rgb(var(--v-theme-primary));
        }
    }
}

// ---- 右クリックメニュー ----
.ctx {
    position: absolute;
    z-index: 20;
    width: 220px;
    padding: 6px;
    border-radius: 8px;
    border: 1px solid rgb(var(--v-theme-background-lighten-2));
    background: rgb(var(--v-theme-background-lighten-1));
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4);

    &__item {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        height: 36px;
        padding: 0 10px;
        border: none;
        border-radius: 6px;
        text-align: left;
        font-size: 13.5px;
        cursor: pointer;
        color: rgb(var(--v-theme-text));
        background: transparent;
        &:hover:not(:disabled) {
            background: rgb(var(--v-theme-background-lighten-2));
        }
        &:disabled {
            opacity: 0.4;
            cursor: default;
        }
        &--danger {
            color: rgb(var(--v-theme-error));
        }
    }
}

// ---- ダイアログ ----
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
