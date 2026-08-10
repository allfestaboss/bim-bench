# T006 armC_r2 報告

## 方法

自作の STEP (ISO-10303-21) パーサを Python 標準ライブラリだけで書いた
(`re` / `os` / `json` / `collections` のみ)。IFC 専用ライブラリは使っていない。

パーサの作り:

- `DATA;` 以降を対象に、`#<数字> = <TYPE>(...)` を文字列リテラル
  (`'...'`、`''` エスケープ) とネスト括弧を意識して走査し、
  インスタンス (id, 型名, 引数文字列) に切り出す。改行をまたぐ実体にも対応。
- 引数は深さ0のカンマで分割。参照は `#(\d+)` を抽出。
- 検証: 各ファイルで `grep -c -E "^#[0-9]+ *= *[A-Za-z(]"` の行数とパース数が
  17ファイル全て一致 (合計 9942 実体)。複合実体 (`#5=(A(...),B(...))`) は
  17ファイル中 0 件だったので、その分岐は不要だった。
- 出現した実体型は 105 種類。全型を「空間 / 物理要素 / それ以外」に明示的に
  分類し、未分類が 0 件であることを機械で確認した (取りこぼし防止)。

## 各設問の数え方

### 空間構造

コーパスに実在した空間型: IFCPROJECT 17, IFCSITE 72, IFCBUILDING 35,
IFCBUILDINGSTOREY 39, IFCSPACE 4, IFCSPATIALZONE 2,
IFCBRIDGE 6, IFCBRIDGEPART 18, IFCROAD 5, IFCROADPART 26,
IFCRAILWAY 2, IFCRAILWAYPART 2。IFCFACILITY / IFCFACILITYPART は0件。

- **spatial_all = 228** — 上記の合計。
- **spatial_no_project = 211** — 228 − 17 (IFCPROJECT)。
- **spatial_depth0 = 17** — 親を IFCRELAGGREGATES (RelatedObjects 側) と
  IFCRELCONTAINEDINSPATIALSTRUCTURE (RelatedElements 側) の両方から取り、
  どちらの子にもなっていない空間。結果は各ファイル1件ずつ = IFCPROJECT のみ。
- **spatial_depth0_aggregate_only = 19** — 親を IFCRELAGGREGATES のみで決めた場合。
  17 (Project) + 2。増えた2件は ifc4x3/ifc4 双方の Building-Architecture.ifc の
  IFCSPATIALZONE で、集約されず IFCRELCONTAINEDINSPATIALSTRUCTURE で
  IFCBUILDING に載っている。この2問が割れる唯一の要因。

### 物理要素

IfcElement 下位型として数えた23型 (合計629):
IFCAIRTERMINAL 4, IFCBEAM 28, IFCBUILDINGELEMENTPROXY 129, IFCCHIMNEY 6,
IFCCOLUMN 14, IFCCOURSE 18, IFCDISCRETEACCESSORY 4, IFCDUCTSEGMENT 2,
IFCEARTHWORKSFILL 21, IFCELEMENTASSEMBLY 37, IFCFOOTING 16, IFCFURNITURE 2,
IFCGEOGRAPHICELEMENT 84, IFCMEMBER 26, IFCPIPESEGMENT 48, IFCRAIL 4,
IFCRAILING 4, IFCROOF 4, IFCSIGN 4, IFCSLAB 44, IFCSURFACEFEATURE 40,
IFCTRACKELEMENT 66, IFCWALL 24。

除外したもの: 空間型、`*TYPE` で終わる型 (IFCWALLTYPE 等 全て型定義)、
IFCZONE 2、IFCDISTRIBUTIONSYSTEM 4、IFCREL* 全て、
幾何・表現・材料・単位・所有履歴・プロパティ/数量関連の型。
IFCANNOTATION / IFCGRID / IFCDISTRIBUTIONPORT / IFCGROUP / IFCSYSTEM は
コーパスに0件だった。

- **element_all = 629** — 上記の合計。空間へ全く繋がっていない物理要素は0件だったので、
  「全実体を数える」と「3経路のいずれかで空間に繋がっているものを数える」は同値。
- **element_direct_only = 552** — IFCRELCONTAINEDINSPATIALSTRUCTURE の
  RelatedElements に現れ、かつ RelatingStructure が空間型であるもの (重複排除、1要素1行)。
  RelatingStructure が非空間だった関係は 0 件。
- **element_no_adheres = 609** — 629 − 20。空間への到達を
  (1) 直接包含、(2) 集約の親を再帰的に辿る、(3) 付着母体を辿る、で判定し、
  (3) を禁じると到達できなくなる要素だけを除いた。該当は
  ifc4x3/Infra-Road.ifc の IFCSURFACEFEATURE 20件のみ
  (IFCRELADHERESTOELEMENT 4件 × 5件ずつ)。
- **element_no_feature = 589** — 629 − IFCSURFACEFEATURE 40。

### 性能仕様

IFCPROPERTYSET.HasProperties のうち IFCPROPERTYSINGLEVALUE (242) と
IFCPROPERTYENUMERATEDVALUE (82) を対象、計324実体。IFCELEMENTQUANTITY は除外。
所有経路は IFCRELDEFINESBYPROPERTIES (RelatedObjects × Pset内属性) と
IFCRELDEFINESBYTYPE → RelatingType.HasPropertySets (引数index 5) × RelatedObjects。

- **property_owner_any_split = 324**
- **property_owner_any_merged = 322** — (ファイル, 要素, Pset名, 属性名) で重複排除。
  減った2件は ifc4x3/ifc4 双方の Building-Architecture.ifc の同一 IFCSLAB に
  `Pset_SlabCommon` / `FireRating` が直接経路と型経由の両方から付いているもの。
- **property_owner_physical_split = 308** — 324 − 16。
- **property_owner_physical_merged = 306** — 322 − 16。
  非物理な所有者の内訳は IFCSPACE 10 / IFCBUILDING 3 / IFCZONE 3 の計16行。
  重複2件は両方とも IFCSLAB (物理) 側なので、物理限定でも同じく2行減る。

### 数量

- **quantity_all = 250** — IFCQUANTITYLENGTH 88 + IFCQUANTITYAREA 72 +
  IFCQUANTITYVOLUME 90。COUNT / WEIGHT / TIME は0件。IFCELEMENTQUANTITY (90) は除外。

## 読めなかった箇所

なし。17ファイル全てが完全にパースでき、実体数はテキスト側の行カウントと一致した。

## 課題文が数え方を決めていないと思った箇所 (3件)

1. **quantity_all の「行」の定義。** 性能仕様の設問が (所有者 × 属性) のペアを行と
   しているのに対し、数量は「IfcQuantity* の行数」としか書いていない。
   数量実体そのものを1行と数えるのか、(所有者, 数量) のペアを1行と数えるのかが
   決まっていない。ただし本コーパスでは全ての IFCELEMENTQUANTITY が
   ちょうど1つの所有者に付いていたため、両解釈とも 250 で一致した。実害なし。
   同じ理由で「所有者に付いていない数量」も0件だった。

2. **element_all の母集団。** 「物理要素の行数」がファイル内の全 IfcElement 実体なのか、
   規則で定義された3経路のいずれかで空間に所属しているものだけなのかが決まっていない。
   本コーパスでは空間に繋がらない物理要素が0件だったため、両解釈とも 629 で一致した。
   実害なし。

3. **spatial_depth0 における IFCPROJECT の扱い。** 「親を持たない空間」の母集団が
   規則の「空間構造の実体」(IFCPROJECT を含む) と同じか否かが明示されていない。
   規則どおり IFCPROJECT を含むと解釈して 17 とした。除くと 0 になり設問として
   退化するので、含む解釈を採った。

## ファイルの内部矛盾・気づき

- ifc4 フォルダのファイルは IFC4 スキーマ宣言だが、`Infra-Bridge` などで
  IFCBRIDGE / IFCROAD / IFCRAILWAY / IFCCOURSE / IFCEARTHWORKSFILL /
  IFCTRACKELEMENT / IFCSIGN / IFCRAIL / IFCRELADHERESTOELEMENT を一切使わず、
  IFCBUILDING / IFCBUILDINGSTOREY / IFCBUILDINGELEMENTPROXY / IFCGEOGRAPHICELEMENT
  に置き換えている。つまり ifc4x3 版と ifc4 版は「同じ建物の別表現」であって
  実体数も構造も一致しない (例: ifc4x3/Infra-Bridge は空間28・要素50、
  ifc4/Infra-Bridge は空間21・要素57)。同じ基底名でも別ファイルとして数える規則は
  この点で本質的。
- IFCSURFACEFEATURE は両スキーマに20件ずつあるが、ifc4x3 では
  IFCRELADHERESTOELEMENT で母体に付着し、ifc4 では
  IFCRELCONTAINEDINSPATIALSTRUCTURE で直接空間に載っている。
  element_direct_only と element_no_adheres の差はほぼこの1点から出ている。
- IFCPROPERTYENUMERATEDVALUE / IFCPROPERTYENUMERATION は ifc4 フォルダにしか
  存在しない (ifc4x3 側は 0)。性能仕様の設問の値はほぼ ifc4 側だけで決まっている
  (ifc4x3 側で性能仕様を持つのは Building-Architecture の6行のみ)。
- 課題文の note 自体が性能仕様4問の答え (308/306, 324/322) を書いてしまっている。
  独自に計算した結果と完全に一致したので自分の集計の検証には使えたが、
  この4問は note を読んだだけで答えられてしまう。測定上の欠陥として記録しておく。

## 制約遵守

- reference/ bench/ checker/ out/ README.md arms/ docs/ は一切開いていない。
- 他の走行 (armC_r1 / armC_r3 / armB_*) の答案・報告、および T001〜T005 の
  attempts/ は開いていない (attempts/ 直下のディレクトリ名一覧を `ls` した以外は
  中身に触れていない)。
- IFC 専用ライブラリ (ifcopenshell 等) は使用していない。標準ライブラリのみ。
- 違反なし。
