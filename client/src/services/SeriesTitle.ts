// [改造] 番組名からシリーズ名 (話数やサブタイトルを除いた部分) を取り出す。
// サーバー側の自動仕分けツール (series_sorter.py の series_title) と同じ規則で、同じ名前のフォルダになる。

const DECORATION = /[[【<＜(]\s*(?:新|終|字|再|デ|解|二|無|生|初|前|後|多|吹|映|声|手|SS|S|N|HV|STEREO)\s*[\]】>＞)]/gi;
const TAG = /\[[^\]]{1,4}\]/g;
const QUOTED_PREFIX = /^(?:TVアニメ|アニメ|日5|日曜5時)\s*[『「](.+?)[』」]/;
const PUBLIC_QUOTED = /【公式】.*?[『「](.+?)[』」]/;
const ANIME_WORD = /^(?:TV)?アニメ(?:[A-Z]・|\s+)/;
const LEAD_BRACKET = /^<[^>]*>\s*/;
const LEAD_QUOTE = /^[『「](.+?)[』」]/;
const SLOT_WORDS = /\s*(?:AnichU|FRIDAY ANIME NIGHT|ANiMAZiNG!*|アニメイズム|ノイタミナ)\s*$/i;
const ROMAN_SUFFIX = /\s*(?:II|III|IV|Season\s*\d+|\d+(?:st|nd|rd|th)\s*season)$/i;

// 最初に見つかったものでタイトルを打ち切る目印 (話数・サブタイトル開始など)
const CUT_MARKERS: RegExp[] = [
    /第\s*[0-9一二三四五六七八九十百零〇]+\s*[話回期章夜巻幕]/,
    /[#♯]\s*\d/,
    /Lesson\.?\s*\d/i,
    /Episode\s*\d/i,
    /\bEp\.?\s*\d/i,
    /[▽▼◇◆★]/,
    /\s\d{1,2}期/,
    /[【「『《〈<(]/,
    /\s[~\-―]/,
    /\s(?:Lv\d+|Vol\.?\s*\d+)/,
];

export function makeSeriesTitle(title: string): string {
    let s = title.normalize('NFKC');
    s = s.replace(DECORATION, ' ').replace(TAG, '').trim();

    s = s.replace(LEAD_BRACKET, '');
    const m = QUOTED_PREFIX.exec(s) ?? PUBLIC_QUOTED.exec(s) ?? LEAD_QUOTE.exec(s);
    if (m) {
        s = m[1];
    } else {
        s = s.replace(ANIME_WORD, '');
    }

    let cut = s.length;
    for (const pattern of CUT_MARKERS) {
        const found = pattern.exec(s);
        if (found && found.index > 0) cut = Math.min(cut, found.index);
    }
    s = s.slice(0, cut).trim();
    s = s.replace(SLOT_WORDS, '').trim();
    s = s.replace(ROMAN_SUFFIX, '').trim();
    return s.replace(/\s+/g, ' ');
}
