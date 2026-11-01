# 改造版 KonomiTV のインストール (Linux)

この改造版は、本家のインストーラー (`KonomiTV-Installer.elf`) では入りません。本家のインストーラーは本家のリポジトリから取得するためです。このファイルの手順で、手動で入れてください。

> [!WARNING]
> 個人の改造版です。本家のサポート対象ではありません。本家へ問い合わせないでください。動作の保証はなく、自己責任でお使いください。

## 動作確認している環境

- Ubuntu 22.04 / 24.04 (x64)。Ubuntu 24.04 では、何も入っていない環境で、このページの手順どおりに「新規インストール → モデルのダウンロード → CM 解析」まで通ることを確認しています (GPU なし、バックエンドは Mirakurun)。
- バックエンドは EDCB または Mirakurun (本家と同じ。事前準備は [本家の README](Readme.md#事前準備) のとおり)

## 必要なもの

- `git`、`curl`
- [uv](https://docs.astral.sh/uv/) (最新版)。入っていなければ、`curl -LsSf https://astral.sh/uv/install.sh | sh` で入れられます (入れたあとは、新しいターミナルを開くか `source $HOME/.local/bin/env` を実行してください)。Python 3.13 は、サードパーティーライブラリに同梱されたものを使うので、別に入れる必要はありません。
- PM2 と Node.js (サービスとして動かす場合のみ)
- クライアントは、ビルド済みのものを `client/dist/` に含めているので、Node.js や yarn はなくても動きます。

## 新規インストール

```bash
# 1. ダウンロード (既定のブランチは custom です)
cd /opt
sudo git clone https://github.com/mihalinn/KonomiTV.git
sudo chown -R $USER: /opt/KonomiTV
cd /opt/KonomiTV

# 2. 設定ファイルを作って編集する (backend / encoder / video.recorded_folders など)
cp -a config.example.yaml config.yaml
nano config.yaml

# 3. サードパーティーライブラリ (FFmpeg・Python・エンコーダーなど) を本家の CI から取得する
cd server/
uv run task update-thirdparty

# 4. 同梱の Python で仮想環境を作り、依存パッケージを入れる
uv sync --python ./thirdparty/Python/bin/python

# 5. 起動する (フォアグラウンド。止めるときは Ctrl+C)
uv run task serve
```

起動したら、`https://(サーバーの IP アドレスの . を - に変えたもの).local.konomi.tv:7000/` を開いてください (例: `https://192-168-1-11.local.konomi.tv:7000/`)。詳しくは [本家の README](Readme.md#httpsaa-bb-cc-ddlocalkonomitv7000-の-url-について) をご覧ください。

サービスとして動かす場合は、`server/` で次のようにします。

```bash
sudo npm install -g pm2
pm2 start .venv/bin/python --name KonomiTV -- KonomiTV.py
pm2 startup
pm2 save
```

## CM 解析 (AI) を使う

1. ブラウザで KonomiTV を開き、「設定」→「CM 解析設定」を開きます。
2. 「モデルをダウンロード」を押します。モデル (約 370MB) が、この改造版の Release (`cm-model-v1.1`) から取得され、`server/data/cm-detection-models/` に置かれます。sha256 は自動で検証されます。
3. 「CM 解析設定」で、CM 解析を有効にします。
4. 録画番組の一覧で番組を選んで「CM 解析する」を押すと、解析が始まります。新しい録画を自動で解析する設定もあります。

CM 解析は、既定では CPU で動きます。GPU に比べて、40 倍ほど遅くなります (筆者の環境での目安)。録画が多い場合は、下の GPU の設定をおすすめします。

### NVIDIA GPU で速くする (任意)

NVIDIA GPU とドライバーがある環境では、CM 解析を GPU で動かせます。`server/` で、次のコマンドを実行してください。

```bash
uv pip uninstall --python .venv/bin/python onnxruntime
uv pip install --python .venv/bin/python onnxruntime-gpu==1.23.2 \
  nvidia-cublas-cu12==12.9.2.10 nvidia-cuda-nvrtc-cu12==12.9.86 nvidia-cuda-runtime-cu12==12.9.79 \
  nvidia-cudnn-cu12==9.27.0.42 nvidia-cufft-cu12==11.4.1.4 nvidia-curand-cu12==10.3.10.19 nvidia-nvjitlink-cu12==12.9.86
.venv/bin/python -c "import onnxruntime as o; print(o.get_available_providers())"
```

最後の行に `CUDAExecutionProvider` が出れば、GPU が使えます。`uv sync` を実行すると CPU 版に戻るので、そのたびに上のコマンドを実行し直してください。

## CM 解析モデルの更新

新しいバージョンのモデルが出たときは、下の「更新」でコードを更新したあと、「設定」→「CM 解析設定」を開いてください。「現在のモデル」の下に「新しいモデル (AI x.x.x) があります」と表示されるので、「モデルを更新」を押すと、変わったファイルだけが取得されて入れ替わります (サーバーの再起動は要りません)。

- 手動で置いた独自のモデルは、この案内の対象にはなりません。
- 録画ごとに「どのバージョンで解析したか」が記録されます。モデルを更新しても、過去の解析結果は自動では解析し直されません。

## 更新

```bash
cd /opt/KonomiTV
git pull
cd server/
uv run task update-thirdparty   # Python のバージョンが変わったときなど
uv sync --python ./thirdparty/Python/bin/python
# (GPU を使っている場合は、上の GPU のコマンドを再実行)
pm2 restart KonomiTV
```

## 本家のインストーラーで入れた環境から切り替える場合

本家のインストーラーで入れた環境 (`git clone` で入っているもの) は、取得元を変えると、この改造版に切り替えられます。**必ず `config.yaml`・`server/data/` をバックアップしてから**行ってください。本家の 0.14.x からは、Python が 3.11 から 3.13 に変わるなど大きな差があるので、新規インストールのほうが安全です。

```bash
cd /opt/KonomiTV
git remote set-url origin https://github.com/mihalinn/KonomiTV.git
git fetch origin
git checkout -B custom origin/custom
cd server/
uv run task update-thirdparty
uv sync --python ./thirdparty/Python/bin/python
pm2 restart KonomiTV
```

## 本家に戻す場合

```bash
cd /opt/KonomiTV
git remote set-url origin https://github.com/tsukumijima/KonomiTV.git
git fetch origin
git checkout -B master origin/master
```

この改造版は DB に項目 (`cm_analysis_version`) を足しています。本家の版に戻したときの動作は確認していません。念のため、切り替える前に `server/data/database.sqlite` のバックアップを取っておき、問題があればバックアップから戻してください。
