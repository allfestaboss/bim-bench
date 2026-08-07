# bim-bench — AIは BIM モデルの空間構造をどこまで読めるか

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

## これから

- 腕を走らせて分離を確認。**採点器はその後**
  （jiban-bench で採点器を作り込んでから飽和が判明した順序の誤りを繰り返さない）
- 採点器と敵対テスト
- コスト計測（`bench/cost.py` は移植済み）

## 出典

corpus は [buildingSMART/Sample-Test-Files](https://github.com/buildingSMART/Sample-Test-Files)
の PCERT-Sample-Scene（IFC 4.3.2.0 / IFC4X3_ADD2）である。
(C) buildingSMART International Ltd. / CC BY 4.0。
