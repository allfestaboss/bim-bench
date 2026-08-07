# 出典

## corpus

**buildingSMART/Sample-Test-Files** https://github.com/buildingSMART/Sample-Test-Files
PCERT-Sample-Scene（IFC 4.3.2.0 / IFC4X3_ADD2）の8ファイル。

利用条件は同リポジトリの LICENSE に原文でこうある。

> (C) buildingSMART International Ltd.
>
> This work is licensed under the Creative Commons Attribution 4.0 International License.
> More info and a link to the full license text is available on
> http://creativecommons.org/licenses/by/4.0/

**CC BY 4.0 なので出典表示だけで再配布できる。** `corpus/buildingsmart/` 以下は
上記から取得したものである。LICENSE も同梱してある。

なお同じ組織の `buildingSMART/IFC4.3.x-sample-models` は**ライセンス表示が無い**
（GitHub の判定でも「なし」）。既定では全権利留保になるので使っていない。
`buildingsmart-community/Community-Sample-Test-Files` は CC BY 4.0 だが
**公式ではない**と明記されているため、参照解の入力には使わない。

## 形式

**ISO 10303-21**（STEP 交換ファイル）— IFC の器。1行目が `ISO-10303-21;`。
**ISO 16739**（IFC）— スキーマ。本 corpus は `IFC4X3_ADD2`。

パーサ `bench/step.py` は kikai-bench（STEP AP242）のものを1行も変えずに流用している。
CAD横断シリーズの土木・機械・建築BIMの3業界が、同じ ISO 10303-21 の器を共有している。

## 制度的な空席の根拠

**国土交通省 BIM/CIM 関連基準要領等** https://www.mlit.go.jp/tec/tec_fr_000184.html
実施方針・取扱要領・活用ガイドライン（全9編）が無償公開されている。
照査については **`3次元モデル照査時チェックシート`（Word形式）** が提供されており、
モデルの内容を機械検査する仕組みは示されていない。

## 使わなかったもの

**日本自動車工業会 3D図面お手本データ**（kikai-bench で検討）は再配布禁止だった。
経緯は kikai-bench の docs/SOURCES.md に記載。
