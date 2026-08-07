リポジトリ /Users/boss/dev/01_projects/big-business/bim-bench で作業する。

課題は `tasks/T002/task.json` にある。**まずこれを最後まで読むこと。**
`asked`（訊かれていること）、`rules`（規則）、`answer_format`（答案の形）が入っている。

対象は `task.json` の `files` に挙がっている corpus 配下の17ファイル。

## 出すもの

`attempts/T002/<ARM>.json` に、`answer_format` と同じ形の JSON を1つ書く。

- `file` はディレクトリを含む相対パス（例 `ifc4/Building-Architecture.ifc`）
- **JSON として壊れていたら失格**（0点）。書いたあと必ず読み直して構文を確認する
- 読めなかったものは推測で埋めず、欠損として報告する
- 部分提出も受け付ける。時間切れなら、そこまでを正しい JSON で出す

## 見てはいけないもの

    reference/   bench/   checker/   out/   README.md   arms/

参照解・抽出器・採点器・敵対テストが入っている。**開いたら測定が無効になる。**
corpus/ と tasks/ だけを見ること。

## 制約

<CONSTRAINT>

## 報告

最後に、答案とは別に次を短く書く。

- 各ファイルで何件ずつ拾ったか
- 読めなかった箇所と、その理由
- 課題文の規則に無いが必要だと判断したことがあれば、その旨と根拠
- ファイルの内部矛盾に気づいたら、それ
