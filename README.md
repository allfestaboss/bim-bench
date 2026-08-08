# bim-bench — AIは BIM モデルの空間構造をどこまで読めるか

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21847249.svg)](https://doi.org/10.5281/zenodo.21847249)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

IFC に入っている**空間構造・要素の所属・数量**を読み取る能力を、機械採点で測るベンチマーク。
AI実務到達度インデックスの7本目で、**CAD横断シリーズの4業界目**
（建築2D DXF → 土木 SXF → 機械 STEP AP242 → 建築BIM IFC）。

## 4行目で分かったこと — 形式は違っていなかった

このシリーズは「業界ごとに形式が違う。**形式が違うこと自体が測る対象**」という
見立てで始めた。4行目に来て、それが半分しか当たっていなかったと分かった。

```
doboku-bench  SXF    ->  ISO 10303-21 の器に SXF フィーチャを詰めたもの
kikai-bench   AP242  ->  ISO 10303-21
bim-bench     IFC    ->  ISO 10303-21
```

**IFC ファイルの1行目は `ISO-10303-21;` である。** 3業界とも器は同じで、違うのはスキーマだった。
実際、kikai-bench の `bench/step.py` を1行も変えずに IFC が読める。

違うのは語彙のほう。AP242 は `GEOMETRIC_TOLERANCE`、IFC は `IFCWALL`。
測る対象は器ではなく**スキーマの読解**になる。この訂正自体が横断の成果である。

## 制度的な空席

国交省の BIM/CIM 関連基準は無償公開されており、照査の仕組みも用意されている。
ただしそれは **`3次元モデル照査時チェックシート`（Word形式）** である。

**モデルの中身を機械検査する仕組みは無く、人が目で見る前提になっている。**
そして人が見ているのは「要素が正しい空間に載っているか」「必要な属性があるか」——
すなわち本ベンチが測る対象そのものである。

土木では「検査する仕組みはあるが中身を見ない」、機械では「データは機械可読なのに
検査方法が決まっていない」だった。建築BIMは**「検査はしているが、Wordのチェックシートで人がやる」**。

## 参照解は buildingSMART が持っている

| | 出どころ | 誰が確定させたか |
|---|---|---|
| 入力 | buildingSMART PCERT 認証サンプル | buildingSMART International |
| 形式 | ISO 16739 (IFC 4.3.2.0 / IFC4X3_ADD2) | ISO |
| 参照解 | ファイルに実際に入っている空間構造・所属・数量 | **こちらは何も決めていない** |

**ライセンスは CC BY 4.0。** 出典表示だけで再配布できるので corpus を同梱できる。

> (C) buildingSMART International Ltd.
> This work is licensed under the Creative Commons Attribution 4.0 International License.

機械（JAMA）では日本の業界団体が再配布を禁じていて NIST に回った。
建築BIMでは buildingSMART が最初から CC BY で出している。

## corpus — 8ファイル、空間108・要素226・数量86

```
ファイル                        空間  要素  数量
Building-Architecture.ifc        8   14   25
Building-Hvac.ifc                5    6    0
Building-Landscaping.ifc         3    7    0
Building-Structural.ifc          5   10   34
Infra-Bridge.ifc                28   50   27
Infra-Plumbing.ifc              10   29    0
Infra-Rail.ifc                  11   75    0
Infra-Road.ifc                  38   35    0
```

建築系4・インフラ系4。IFC4.3 でインフラが入り、`IFCBRIDGE` / `IFCROAD` /
`IFCRAILWAY` と各 `PART` 型が加わっている。

## 較正 — 手読みが浅くて落ちた

`bench/selfcheck.py` は step.py も ifc.py も呼ばず、ファイルから直接読んだ行を
リテラルに書き下して突き合わせる。**建築系とインフラ系の両方で取る**
（kikai-bench で「1ファイルでは足りない」を踏んだため）。

最初、橋の空間階層の最大の深さを **4** と書いて較正が落ちた。実際は **5** だった。

```
#13  IFCPROJECT     'ifc silly sample scene - project'    深さ0
#20  IFCSITE        'environment - site'                  深さ1
#679 IFCSITE        'road rail bridge - site'             深さ2
#685 IFCBRIDGE      'rail bridge'                         深さ3
#692 IFCBRIDGEPART  'rail bridge - substructure'          深さ4
#726 IFCBRIDGEPART  'rail bridge - pier'                  深さ5
```

**`IFCBRIDGEPART` が `IFCBRIDGEPART` の中に入れ子になる**（下部構造 → 橋脚）。
敷地も敷地の中に入る。**「建物 → 階」という2段の型で考えると読み違える。**

同型の入れ子は corpus 全体に散っている。

| ファイル | 最大深さ | 同型の入れ子 |
|---|---|---|
| Infra-Road | 5 | **25件** |
| Infra-Bridge | 5 | **14件** |
| Infra-Rail / Infra-Plumbing | 4 / 3 | 5件 / 5件 |
| Building-* | 2〜5 | 各1件 |

抽出器が正しく、手読みが浅かった。**較正はこういうときのためにある。**

## 構成

```
bench/step.py        STEP Part21 パーサ（kikai-bench から1行も変えずに流用）
bench/ifc.py         空間構造・要素の所属・数量の抽出
bench/build_ref.py   参照解の生成
bench/selfcheck.py   生テキストの手読みとの較正（建築系＋インフラ系）
tasks/T001/          8ファイル横断の読解課題
corpus/buildingsmart/ buildingSMART PCERT サンプル（CC BY 4.0、再配布可）
```

## 外部検算 — ifcopenshell と突き合わせて2件見つけた

IFC には kikai-bench の `INTEGER_REPRESENTATION_ITEM` のような自己申告が無い。
代わりに **ifcopenshell（IFC の独立した実装）** を照合先にした。

**同じ経路を再実装しない。** 向こうは `util.element` の API から取る。

| | こちら | ifcopenshell |
|---|---|---|
| 空間の親 | `IFCRELAGGREGATES` を生でたどる | `get_aggregate(e)` |
| 要素の所属 | `IFCRELCONTAINEDINSPATIALSTRUCTURE` を生でたどる | `get_container(e)` |
| 数量 | `IFCELEMENTQUANTITY` を生でたどる | `get_psets(e, qtos_only=True)` |

到達経路が違うので、一致すれば意味がある。初回は **11件の食い違い**が出た。

### 1. 集合体の中の要素を落としていた（こちらのバグ）

```
#353=IFCRELAGGREGATES('09Xbpra…',#1,'house - roof container',$,#334,(#343,#367));
     → #334 IfcRoof が #343/#367 IfcSlab を束ねている
     → 屋根は建物に載っているので、スラブも建物に属する
```

こちらは `IFCRELCONTAINEDINSPATIALSTRUCTURE` の**直載せしか見ていなかった**。
ifcopenshell の `get_container()` は集合体を経由して所属を解決する。
Building-Structural では6件、Architecture では2件を落としていた。

**「どの要素がどの空間に載っているか」は、このベンチが測る対象そのものである。**
そこを落としていた。

### 2. 空間を物理要素として二重に数えていた（こちらのバグ）

`#385 IfcSpatialZone` は空間なのに `IFCRELCONTAINEDINSPATIALSTRUCTURE` に現れる。
こちらは空間としても要素としても数えていた。空間として扱い、要素からは外した。

### 3. `IfcProject` は定義の差（どちらも正しい）

`IfcProject` は `IfcContext` であって `IfcSpatialElement` ではない。
こちらは階層の根として空間に含めている。**どちらかが間違っているのではなく
定義が違う**ので、検算器側でそう明記して揃えた。

修正後、**8ファイル全て一致**。

## 腕が、独立実装でも届かない範囲を見つけた

外部検算が通ったあとに armC を走らせたら、**要素を255件**報告してきた。
こちらの参照解は235件。差は Infra-Road のちょうど +20 だった。

```
#194=IFCRELADHERESTOELEMENT('0DycPE6L…',#1,$,$,#167,(#178,#195,#203,#211,#219));
     → #167 IfcCourse（舗装層）に #178… IfcSurfaceFeature（路面標示）が貼り付いている
```

`IFCRELADHERESTOELEMENT` は Infra-Road に4件、各5件で計20件。
**ifcopenshell の `get_container()` は20件すべて `None` を返す。**
つまり独立実装との突き合わせでは絶対に出てこない差だった。

armC はこれを黙って使わず、こう書いてきた。

> This relation is not in the task's rule list; without it those 20 elements
> have no container at all.

**規則に無いことを明示したうえで採用している。** 課題側の不備を指摘する形になっている。

路面標示は物理的に舗装層の上にあり、舗装層は空間に載っている。
「そこにある」と答えるほうが実務的に正しい。規則に追加し、
`container_via` に `direct` / `aggregate` / `adheres` の経路を残すようにした。
検算器には**定義の差**として明記し、比較から外している。

### 単位系が量ごとに違う（armC の指摘）

```
IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.)     長さは mm
IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.)      面積は m2
IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.)     体積は m3
```

`Depth=250.0` は mm、`NetArea=25.75` は m2。**値だけ見ても意味が決まらない。**
こちらは単位を記録していなかった。宣言された単位を併記するようにした。

armC は `Volume = Area × Length/1000` が全ての三つ組で成り立つことまで確認して、
「宣言された単位系であって壊れているのではない」と結論している。

### 検算の階層が1段増えた

| 段 | 手段 | 見つけたもの |
|---|---|---|
| 1 | 手読みとの較正 | 空間階層の深さ（自分の読みが浅かった） |
| 2 | ifcopenshell との突き合わせ | 集合体経由の所属、空間の二重計上 |
| 3 | **腕** | **付着関係、単位系の不統一** |

**独立実装と一致しても、まだ上がある。** ifcopenshell も `IFCRELADHERESTOELEMENT` を
所属として扱っていない以上、そこで止めていたら20件を落としたままだった。

## 腕の試走 — 完遂では分離せず、コストで3.8倍

```
腕      ファイル  空間   要素   数量   所属一致   数量一致   トークン    所要   ツール
armB       8/8   108    235     86   235/255     86/86    371,572  36分38秒   321
armC       8/8   108    255     86   255/255     86/86     98,901   8分55秒    27
```

**両方とも8ファイル完走。** kikai T002 のように「片方が力尽きる」形にはならなかった。
分かれたのは**コストと網羅**である。

- **armC は armB の 1/3.8 のトークン、1/4.1 の時間**で終えた
- ツール呼び出しは **321回 対 27回**。armB は Read を321回叩いている
- 網羅は armC 255/255、armB 235/255（付着関係の20件を落とした）

### armB の解き方が面白い

Bash も grep も禁じられた状態で、最長271,816文字の幾何行をどう避けたか。
**書き出し側のブロック配置が一定であることを利用して、読まずに飛ばした。**

> from an element line `#E=IFC…(…,#P,#R,…)` the placement line sits at `L+(P−E)`
> and the geometry pair at `M+5, M+6`

しかも飛ばした範囲は**実体IDの連続性で検証**している（飛ばした行数 == 欠けたID数）。
黙って飛ばさず、飛ばしたことを確かめている。

それでも321回の Read と 371k トークンが要った。**同じ答えに 3.8倍の単価。**

### 両腕が、こちらの課題文の誤りを指摘した

`answer_format` の例に `#40 IFCBUILDINGSTOREY … "depth": 3` と書いていたが、
規則どおり数えると `13→20→23→30→40` で **4** である。数量の例も
`25.75` と丸めて書いていた（実データは `25.749999999991743`）。

> if the grader keys off the example literally, every Building-* depth will
> read one too high.

**2本とも規則に従い、例のほうを疑った。** そして正しかった。例を実データに直した。
規則と例が食い違っていること自体が課題の不備である。

## 採点

`./run.sh` が (1)較正 → (2)外部検算 → (3)敵対テスト → (4)採点 の順で走る。
どれか落ちたら数字を出さない。

```
提出         空間網羅 親と深さ 要素網羅     所属     数量      合計      %      tok      時間   tok/件   倍率
参照解          15/15    20/20    20/20    25/25    20/20  100.0/100 100.0%        -         -        -      -
armB            15/15    20/20    19/20    23/25     0/20   77.5/100  77.5%     372k  36分38秒     1457   3.8×
armC            15/15    20/20    20/20    25/25     0/20   80.0/100  80.0%      99k   8分55秒      388   1.0×
```

**Q4（要素の所属）を最も重くしてある（25点）。** 国交省の BIM/CIM 照査で
人が Word のチェックシートを見ながら確認しているのが当のものだからで、
このベンチが測る意味の中心がそこにある。

### この点数はまだ腕に不利である

**Q5 の単位要求と、空間の包含配置（`parent_via`）の規則は、腕が走った後に追加した。**
腕は訊かれていないことで減点されている。**単位を課さなければ armC 100.0 / armB 97.5。**

kikai-bench でも同じことをやって `grade_levels` を導入した。同じ轍を踏んだので、
記録に残しておく。**課題を後から強くしたら、その回の点数はその旨を添えて出す。**

### 敵対テスト — 実際の失敗をケースにした

T001 13/13 通過。ここでも自分たちが踏んだものを使っている。

| ケース | 由来 |
|---|---|
| `evil_depth_naive` | 深さを1つ浅く数える。**こちらが課題文の例で実際にやった誤り** |
| `evil_drop_adheres` | 付着要素20件を落とす。**armB が実際に落とし、ifcopenshell も解決しない** |
| `evil_zero_depth` | 深さ0（IfcProject）を null にする。**0は有効な値** |
| `evil_container_null` | 所属を全て null に。「載っていない」と「答えていない」の区別 |
| `evil_quantity_scale` | 数量を1000倍。長さmm・面積m2 の取り違えで出る形 |
| `evil_malformed` | カンマ落ち。kikai-bench の armB が実際にこれで壊れた |

課題が採点しない水準や、対象が存在しない変異は自動で飛ばす。

## T002 — 課題を2.5倍にしても到達範囲では分離しなかった

17ファイル・10,078行・13MB・1,107項目（T001 の2.5倍）。
**同じシーンの IFC 4.0 版と 4.3 版を両方入れてある。**

```
提出         空間網羅 親と深さ 要素網羅     所属     数量      合計      %      tok      時間   tok/件   倍率
参照解          15/15    20/20    20/20    25/25    20/20  100.0/100 100.0%        -         -        -      -
armB            15/15    20/20    20/20    25/25    20/20  100.0/100 100.0%     460k  39分57秒      732   5.1×
armC            15/15    20/20    20/20    25/25    20/20  100.0/100 100.0%      91k   9分24秒      144   1.0×
```

**両方とも満点。** kikai T002 のように片方が力尽きる形にはならなかった。

### コストの伸び方が正反対だった

| | T001（449項目） | T002（1,107項目） | 伸び |
|---|---|---|---|
| armB | 372k / 36分38秒 | **460k / 39分57秒** | 1.24× / 1.09× |
| armC | 99k / 8分55秒 | **91k / 9分24秒** | **0.92× / 1.05×** |

**armC は仕事量2.5倍でコストが横ばい**（むしろ微減）。パーサを一度書けば
8ファイルでも17ファイルでも同じという構造がそのまま出ている。
単価は **732 対 144 で5.1倍**に開いた（T001 では3.8倍）。

### armB は下請けを立てて突破した

> The corpus is ~3.5M tokens of raw STEP text, so I fanned out one Read-only
> reader per file (each under the same no-shell constraint) and merged their extractions

**ファイルごとに読み手を立てて分散させた。** 報告された460kトークンは統括分だけで、
実コストはこれより大きい。「コード禁止」の制約は、並列化までは禁じていなかった。

読めなかった行についても正直だった。

> a handful of individual lines (tessellated …) exceed the Read tool's single-response
> token cap even at `limit=1` and could not be rendered … These are provably geometry-only:
> entity ids are contiguous with `line = id + 7` in every file … Nothing was filled in by guessing.

**読めなかったことを、読めなかったと報告したうえで、影響が無いことを証明している。**

### 腕がこちらの検出漏れを1件見つけた

armB が挙げた唯一の矛盾。

```
#49 IFCSLAB（床スラブ）
  型経由 #47 IFCSLABTYPE  -> #963 Pset_SlabCommon  FireRating = 'REI60'
  直接   #800 Pset_SlabCommon                      FireRating = 'REI30'
```

**同じスラブに、同じ名前の性能仕様が2つ付いていて、耐火等級が食い違う。**
確認したところ事実だった。こちらは property set を抽出していないので検出できていない。

耐火等級の食い違いは、まさに BIM 照査が捕まえるべきものである。
**測る対象として、次に足すならここ。**

### 版差の所見（両腕が一致）

- `Infra-Bridge` の7つの `pier` は 4.3 で `IFCBRIDGEPART`（空間）、4.0 では物理要素。
  **GlobalId は同一。** 28/50 と 21/57 の差はこれで全部説明がつく
- 路面標示20件は 4.3 で `IFCRELADHERESTOELEMENT`、4.0 では直接の包含関係。
  **同じものが版で仕組みを変えている**
- `ifc4/Infra-Road` は数量78件、`ifc4x3` は0件。4.3 のエクスポートが落としている
- 要素の語彙も退化する。`IFCRAIL` / `IFCCOURSE` / `IFCTRACKELEMENT` は
  4.0 で軒並み `IFCBUILDINGELEMENTPROXY` になる

### 採点して2件直した

**単位の書式**: こちらは `MILLI.METRE`、両腕は `MILLIMETRE`。同じ意味で、
読み取り能力の差ではない。点を全部落として比べるようにした。

**課題文の GlobalId が捏造だった**: 例に `1Ln2$YEIz2xxvw2$Q8dGpV` と書いていたが、
実データは `1Ano2ZUxnEIvVQ_beukl8b`。前回この例を「訂正」したとき、
ファイルから読まずにそれらしい文字列を書いていた。
**規則に「推測で埋めない」と書いておきながら課題文がそれを破っていた。**
以後は答案例を参照解から機械的に生成する。手で書かない。

## Q6 性能仕様を足した — 腕が見つけた矛盾を、参照解が拾えるようにした

armB が挙げた唯一の矛盾を、こちらは検出できていなかった。抽出対象に加えた。

```
#52 IFCSLAB（床スラブ）
  型経由 #50 IFCSLABTYPE の HasPropertySets -> #963 Pset_SlabCommon  FireRating = 'REI60'
  直接   IFCRELDEFINESBYPROPERTIES          -> #57  Pset_SlabCommon  FireRating = 'REI30'
```

**同じ要素に、同じ名前の性能仕様が両経路から付き、耐火等級が食い違う。**
IFC4.0版・IFC4.3版の両方に同じ矛盾が入っている（T002 で324属性中2件）。

型経由は324件中わずか4件しかない。**その4件の中に矛盾が2件ある。**
直接付いた320件だけを見れば全て整合して見える。稀な経路にこそ出る。

### 標準ライブラリの既定では、この矛盾は見えない

外部検算に使っている ifcopenshell で同じ床スラブを引くと、こうなる。

```python
ue.get_psets(slab)                      -> FireRating = 'REI30'   # 既定
ue.get_psets(slab, should_inherit=False)-> FireRating = 'REI30'   # 直接のみ
ue.get_psets(ue.get_type(slab))         -> FireRating = 'REI60'   # 型のみ
```

**既定の呼び方では REI60 が REI30 に上書きされて消える。** 仕様どおりの優先順位解決だが、
照査で拾いたいのは当の消えたほうである。検算側は2経路を別々に取って比べるようにした。

### 配点を組み替えた

```
Q1 空間の網羅 12 / Q2 親と深さ 16 / Q3 要素の網羅 16
Q4 要素の所属 22 / Q5 数量 17 / Q6 性能仕様 17
```

Q4 を最も重くしたのは変えていない。BIM 照査の中心が所属だからである。

### 外部検算が抽出器の穴を2つ出した

Q6 を採点対象にしてから、**採点する水準は必ず外から検算してから出す**を
自分で破っていたことに気づいた。突き合わせを性能仕様まで広げたところ:

| 出た穴 | 中身 |
|---|---|
| 列挙型の属性を丸ごと落としていた | `IFCPROPERTYSINGLEVALUE` だけを見ていた。`IFCPROPERTYENUMERATEDVALUE`（Status 等）が **82件**、コーパスの4分の1 |
| 値がリストのとき畳めていなかった | 列挙型は第3引数がリスト。IFC では列挙は複数値を取りうる |

242 → **324件**。この2つは較正（手読み）では出なかった。手読みでも
`IFCPROPERTYSINGLEVALUE` を探していたので、同じ思い込みで一緒に間違えていた。

### 敵対テストを3件足した

| ケース | 狙い |
|---|---|
| `evil_drop_type_properties` | 型経由の性能仕様を落とす。**矛盾が見えなくなること自体が失点** |
| `evil_merge_conflict` | 食い違う値を片方に揃える（矛盾を握りつぶした答案） |
| `evil_keep_typed_value` | `IFCLABEL('REI60')` のまま報告する（中身を取り出していない） |

T001・T002 とも **16/16 通過**。

### 第2回 — Q6 込みで回し直した。両腕とも矛盾を自力で見つけた

課題文から答え（矛盾そのもの）を消したうえで走らせた。

```
提出       空間網羅 親と深さ 要素網羅   所属   数量 性能仕様    合計       tok      時間  倍率
参照解        12/12   16/16   16/16  22/22  17/17   17/17  100.0/100    -        -      -
armB          11/12   15/16   16/16  22/22  17/17   17/17   97.9/100  527k+ 108分32秒  4.3×
armC          11/12   15/16   16/16  22/22  17/17   17/17   97.9/100   123k  15分47秒  1.0×
```

**性能仕様は両腕とも 324/324。列挙型（`IFCPROPERTYENUMERATEDVALUE`）も含めて取り切っている。**
こちらが外部検算でようやく塞いだ穴に、腕は最初から落ちていなかった。

矛盾も両腕が独立に見つけた。

> armC: `#49` carries `Pset_SlabCommon.FireRating` from both routes with different
> values: direct=`'REI30'`, type=`'REI60'`
>
> armB: 床スラブに同名 `Pset_SlabCommon` が2経路から付き `FireRating` が食い違う。
> **Pset の GlobalId も末尾1文字違い（`…fSRNs7` / `…fSRNs1`）でコピー痕**

armB は矛盾がどうやって作られたかまで見ている。

### 失点は腕の側ではなく、こちらの課題文にあった

両腕とも `IFCPROJECT` を `spatials` に入れなかった。理由も同じである。

> IfcProject is `IfcContext`, not a space; the rules use it only as the depth origin.
> This is the single biggest set-level risk if the reference decided otherwise.

**規則が決めていなかった。** ISO 16739 上は armC の読みが正しく、
こちらは「集約ツリーの根だから」という便宜で入れていた。規則に明記した。

この17行を外すと **両腕とも 100.0/100、答案は集合として完全に一致する。**
Q6 を足しても到達範囲では分離しなかった。

### 課題文の誤り1件が、腕の予算を989,423トークン焼いた

`answer_format` が `ifc4x3/Building-Architecture.ifc` のファイル名の下に、
**実際には `ifc4/` 版にしかない属性3件**を置いていた。4.3版を担当した armB の
下請けは「自分が見落としたのか」を確かめに全行を実読しにいった。

| 下請け | 裏取りに使った量 |
|---|---|
| 4x3 Hvac | 81,585 |
| 4x3 Architecture | 124,396 |
| 4x3 Structural | 162,365 |
| 4x3 Bridge | 356,945 |
| 4x3 Road | 264,132 |
| **計** | **989,423** ← 第1回の armB 全体(460k)の2.1倍 |

**この回のコスト軸は armB について無効である。** 腕の実力ではなくこちらの不備を測っている。

同時に、これは分離そのものでもある。**仕様書が壊れているとき、知識のみの腕は
破滅的にコストが膨らみ、コード実行の腕は自分で真値を計算して先へ進む。**
armC は同じ曖昧さ（IFCPROJECT）に気づいたうえで、判断を書き添えて 123k で完走した。

### 「例に答えが書いてある」は4回目だった

| 回 | 誤り |
|---|---|
| 1 | 手で書いた GlobalId が実データと違う（捏造） |
| 2 | `depth` の例が規則と食い違う |
| 3 | `anomalies` の例に、測りたい矛盾そのものを書いていた |
| 4 | **3回目を直す作業で、別ファイルの属性を元のファイル名の下に置いた** |

機械生成にしただけでは足りなかった。**生成したものを参照解に照合し直す**検査を
`selfcheck` に入れた。名乗ったファイルに実在しない行、および答えの漏れを落とす。
今回の誤りは両方ともこれで検出できることを確認済み。

## これから

- Q6 込みで腕を回し直す（矛盾に気づくかを測る）
- `bench/report.py` の移植（課題をまたいだコストの伸び）

## 出典

corpus は [buildingSMART/Sample-Test-Files](https://github.com/buildingSMART/Sample-Test-Files)
の PCERT-Sample-Scene（IFC 4.3.2.0 / IFC4X3_ADD2）である。
(C) buildingSMART International Ltd. / CC BY 4.0。


## 関連研究 — この位置づけ

| 研究 | 対象 | 本ベンチとの違い |
|---|---|---|
| [BIM-Edit](https://arxiv.org/abs/2606.20146v1) (2026) | IFC の自然言語**編集**。324タスク | 本ベンチは**読解**。既存モデルを書き換えるのではなく、構造と数量を正しく取り出せるかを問う |
| [BIM Information Extraction via LLM-based Adaptive Exploration](https://arxiv.org/pdf/2605.01698) | IFC からの情報抽出 | 近接する。本ベンチは腕を分けてコストまで測る点が異なる |
| [AECV-Bench](https://api.emergentmind.com/topics/aecv-bench) | 建築・工学図面の多モーダル理解 | 図面画像。IFC はグラフであって画像ではない |

IFC を対象とする研究は 2026 年に入って増えており、**本ベンチは先行研究のある領域**である。BIM-Edit は編集、本ベンチは読解と、課すものが異なる。シリーズとしての価値は単独の新規性ではなく、同一設計で他業界と並べられる点にある。

なお**コストを併記すること自体は 2026 年時点で標準的**であり、本ベンチの新規性ではない。
主要リーダーボードは cost-per-task を既定で並べている。シリーズとして測っているのは、
業界をまたいで条件を揃えたときの**単価の差**のほうである。

## ライセンスと引用

**コードと文章は MIT。** → `LICENSE`

**同梱データは MIT の対象外**で、それぞれの配布条件に従う。詳細は `NOTICE`。

引用は `CITATION.cff` を参照（GitHub の「Cite this repository」からも取得できる）。

```
Ohkubo, B. (Allfesta Corp.) (2026). bim-bench: AIは BIM モデルの空間構造をどこまで読めるか.
https://orcid.org/0009-0007-8300-0039
Zenodo. https://doi.org/10.5281/zenodo.21847249
```
