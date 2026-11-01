# CM 解析モデルについての表記

この改造版の CM 解析 AI は、次の 2 つのモデルファイルを使います。どちらも GitHub Release (`cm-model-v1.1`) で配布しています。

| ファイル | 内容 |
|---|---|
| `clip_image.onnx` | OpenAI の CLIP (ViT-B/32) の画像エンコーダを ONNX に変換したものです。 |
| `cm_seq.onnx` | 録画番組の特徴から CM 区間を判定する、この改造版独自の学習結果です。 |

## OpenAI CLIP

`clip_image.onnx` の元になった CLIP の重みは、[openai/CLIP](https://github.com/openai/CLIP) で MIT ライセンスのもとに公開されています。

```
MIT License

Copyright (c) 2021 OpenAI

Permission is hereby granted, free of charge, to any person obtaining a copy
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
SOFTWARE.
```
