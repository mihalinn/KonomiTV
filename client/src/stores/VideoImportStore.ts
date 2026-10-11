
import { defineStore } from 'pinia';


/**
 * [改造] ファイルのアップロード取り込みダイアログの開閉状態を共有するストア
 * ダイアログは App.vue に 1 つだけ置き、どのページからでも開けるようにする (ページ移動してもアップロードが続く)
 */
const useVideoImportStore = defineStore('videoImport', {
    state: () => ({
        show: false as boolean,
        // 開いたときに追加先として最初に入れるフォルダ名 (空なら自動生成)
        initialFolder: '' as string,
        // 取り込みが完了した回数 (一覧の再読み込み用)
        importedCount: 0 as number,
    }),
    actions: {
        open(folder: string = ''): void {
            this.initialFolder = folder;
            this.show = true;
        },
        notifyImported(): void {
            this.importedCount++;
        },
    },
});

export default useVideoImportStore;
