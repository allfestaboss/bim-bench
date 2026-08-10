# T007 armC_r2 報告

## 使った手段

自作の ISO-10303-21 (STEP Physical File) パーサ。Python 標準ライブラリ（`re`, `collections`）のみ。
IFC 専用ライブラリ（ifcopenshell 等）は一切使っていない。**制約違反なし。**

- スクラッチパッドに `spf.py`（トークナイザ＋エンティティ分解）を書き、17ファイルを読み込んだ。
- 文字列内の `''` エスケープ、`/* */` コメント、複数行にまたがるエンティティ、
  `IFCLABEL(...)` のような型付きパラメータ、`$` / `*` を扱う。
- パーサの網羅性検証: 抽出したエンティティ総数 9,942 が
  `grep -c '^#[0-9]*='` の合計 9,942 と一致。取りこぼしゼロ。
- corpus 配下は `corpus/buildingsmart/` の対象17ファイルのみを開いた。
  `corpus/injected/` は task.json の `files` に無いので開いていない。
  `reference/` `bench/` `checker/` `out/` `README.md` `arms/` `docs/`、
  過去課題の `tasks/` `attempts/`、および `attempts/T007/` の他走行は開いていない。

## 属性位置の確認

規格の記憶に頼らず、各エンティティの実インスタンスを1件ずつ印字して
インデックスを目視確認してから使った。

- `IFCRELAGGREGATES` → [4]=RelatingObject, [5]=RelatedObjects
- `IFCRELCONTAINEDINSPATIALSTRUCTURE` → [4]=RelatedElements, [5]=RelatingStructure
- `IFCRELADHERESTOELEMENT` → [4]=RelatingElement, [5]=RelatedSurfaceFeatures
- `IFCRELDEFINESBYPROPERTIES` → [4]=RelatedObjects, [5]=RelatingPropertyDefinition
- `IFCRELDEFINESBYTYPE` → [4]=RelatedObjects, [5]=RelatingType
- `IFCPROPERTYSET` → [2]=Name, [4]=HasProperties
- `IFCELEMENTQUANTITY` → [2]=Name, [5]=Quantities
- `IFC***TYPE`（IfcTypeObject） → [5]=HasPropertySets
- `IFCPROPERTYSINGLEVALUE` / `IFCPROPERTYENUMERATEDVALUE` / `IFCQUANTITY*` → [0]=Name

## 各設問の数え方

### 対象型の確定

17ファイルに実在する型は105種。全105種を一覧化し、
「空間」「物理要素」「規則が明示的に除外したもの」「その他」に分類して、
その他の欄に IfcElement 下位型が紛れていないことを目視確認した。

**空間構造の実体（実在した12型）**:
IFCPROJECT 17 / IFCSITE 72 / IFCBUILDING 35 / IFCBUILDINGSTOREY 39 / IFCSPACE 4 /
IFCSPATIALZONE 2 / IFCBRIDGE 6 / IFCBRIDGEPART 18 / IFCROAD 5 / IFCROADPART 26 /
IFCRAILWAY 2 / IFCRAILWAYPART 2。
IFCFACILITY / IFCFACILITYPART / IFCEXTERNALSPATIALELEMENT は corpus に不在。

**物理要素（実在した23型、計629）**:
IFCAIRTERMINAL 4 / IFCBEAM 28 / IFCBUILDINGELEMENTPROXY 129 / IFCCHIMNEY 6 /
IFCCOLUMN 14 / IFCCOURSE 18 / IFCDISCRETEACCESSORY 4 / IFCDUCTSEGMENT 2 /
IFCEARTHWORKSFILL 21 / IFCELEMENTASSEMBLY 37 / IFCFOOTING 16 / IFCFURNITURE 2 /
IFCGEOGRAPHICELEMENT 84 / IFCMEMBER 26 / IFCPIPESEGMENT 48 / IFCRAIL 4 /
IFCRAILING 4 / IFCROOF 4 / IFCSIGN 4 / IFCSLAB 44 / IFCSURFACEFEATURE 40 /
IFCTRACKELEMENT 66 / IFCWALL 24。

除外したもの: 全 `IFC***TYPE`（58個体）、IFCZONE 2、IFCDISTRIBUTIONSYSTEM 4、
空間構造の実体228、および幾何・材料・単位・所有履歴・関係・プロパティ実体などの非製品型。
IFCANNOTATION / IFCGRID / IFCDISTRIBUTIONPORT / IFCGROUP / IFCSYSTEM は corpus に不在。

### spatial_all = 228 / spatial_no_project = 211
上記12型の個体数合計。IFCPROJECT 17 を引いて 211。

### spatial_depth0 = 17
親＝IFCRELAGGREGATES の RelatingObject、**または** IFCRELCONTAINEDINSPATIALSTRUCTURE の
RelatingStructure。どちらでも親を持たない空間は IFCPROJECT 17 個だけだった。
内訳の検算（全空間が過不足なく親に繋がる）:
SITE 72 = PROJECT→SITE 17 + SITE→SITE 55、BUILDING 35 = SITE→ 29 + BUILDING→ 6、
STOREY 39 = BUILDING→ 37 + STOREY→ 2、SPACE 4 = STOREY→ 4、
BRIDGEPART 18 = BRIDGE→ 9 + BRIDGEPART→ 9、ROADPART 26 = ROAD→ 6 + ROADPART→ 20、
BRIDGE 6 / ROAD 5 / RAILWAY 2 は SITE 配下、RAILWAYPART 2 は RAILWAY 配下。
SPATIALZONE 2 は集約の親を持たず、包含（IFCRELCONTAINEDINSPATIALSTRUCTURE の
RelatedElements 側）でのみ空間に載っている。

### spatial_depth0_aggregate_only = 19
親を集約のみで決めると、上の 17 に SPATIALZONE 2 が加わって 19。
（ifc4x3/Building-Architecture #385 と ifc4/Building-Architecture #448）

### element_all = 629
物理要素の個体数をそのまま合計。
所属経路で絞る解釈と一致するかを確認済み: 3経路のいずれにも繋がらない孤児は0個で、
629 = 直接載り 552 + 集約経由のみ 57 + 付着経由のみ 20 に厳密に分解できた。
したがってこの設問についてはどちらの解釈でも同じ値になる。

### element_direct_only = 552
IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements に現れる物理要素の個体数。
RelatedElements には物理要素以外に IFCSPATIALZONE が2件混ざっているので除外した
（554 件のうち 552 件が物理要素）。RelatingStructure は104件すべて空間型だった。

### element_no_adheres = 609
各物理要素について「空間に到達する経路の種類」を集合として求め、
それが `{付着}` だけの要素を除いた。該当は IFCSURFACEFEATURE 20 個体
（すべて ifc4x3/Infra-Road.ifc、IFCCOURSE に付着）。629 − 20 = 609。
付着の母体が空間に直接載っていない場合に備えて、集約・付着の連鎖を再帰的に辿った
（循環対策のスタック検査つき）。

### element_no_feature = 589
629 − IFCSURFACEFEATURE 40 = 589。

### property_owner_physical_split = 308
行 = (ファイル, 所有オブジェクト, Pset 名, 属性名, 経路)。
直接経路 = IFCRELDEFINESBYPROPERTIES の RelatingPropertyDefinition が IFCPROPERTYSET のもの（137件）。
型経由 = IFCRELDEFINESBYTYPE → 型の HasPropertySets 内の IFCPROPERTYSET。
属性は IFCPROPERTYSINGLEVALUE と IFCPROPERTYENUMERATEDVALUE のみ。
IFCELEMENTQUANTITY を RelatingPropertyDefinition に持つ90件はこの設問では除外。
所有者が物理要素の行だけを残した。所有者内訳:
SLAB 116 / GEOGRAPHICELEMENT 96 / MEMBER 30 / WALL 23 / BEAM 21 /
ELEMENTASSEMBLY 7 / FOOTING 7 / ROOF 4 / COLUMN 4 = 308。

### property_owner_physical_merged = 306
上記から (ファイル, 所有オブジェクト, Pset 名, 属性名) で重複排除。
衝突は2件のみで、いずれも Pset_SlabCommon / FireRating が直接と型経由の両方から
同じスラブに付いていた例:
ifc4x3/Building-Architecture #49（直接 #800→#961、型経由 #963→#962）、
ifc4/Building-Architecture #52（直接 #57→#961、型経由 #963→#962）。
308 − 2 = 306。

### property_owner_any_split = 324 / property_owner_any_merged = 322
所有者を限定しないと、上の物理要素308 に IFCSPACE 10 / IFCBUILDING 3 / IFCZONE 3 が加わり324。
併合の衝突は上と同じ2件なので322。
検算: 17ファイルの IFCPROPERTYSINGLEVALUE 242 + IFCPROPERTYENUMERATEDVALUE 82 = 324 で
split と一致した。属性実体は必ずちょうど1つの Pset に属し、複数 Pset から共有された属性は0件。
Pset 139 個はすべてどこかから参照されていた（直接137、型の HasPropertySets 経由のみ2）。

### quantity_all = 250
IFCQUANTITYLENGTH 88 + IFCQUANTITYAREA 72 + IFCQUANTITYVOLUME 90 = 250。
IFCQUANTITYCOUNT / WEIGHT / TIME は corpus に不在。IFCELEMENTQUANTITY 90 は入れ物なので数えない。
「所有者ごとの行」として数え直しても同じ250だった
（IFCELEMENTQUANTITY はすべて IFCRELDEFINESBYPROPERTIES から1オブジェクトにのみ付き、
共有・重複参照は0件。IFCRELDEFINESBYTYPE 経由の IFCELEMENTQUANTITY も0件）。

## 読めなかった箇所

なし。17ファイル全9,942エンティティを構文エラーなく解析できた。
未知トークン・パース失敗・重複 ID・宙ぶらりん参照はいずれも発生しなかった。

## 課題文が数え方を決めていないと思った箇所

1. **spatial_depth0 / spatial_depth0_aggregate_only に IFCPROJECT を含めるか。**
   規則は「空間構造の実体」に IFCPROJECT を含めると明記し、設問は「空間」としか言わない。
   一方 spatial_all / spatial_no_project がわざわざ project 有無で対になっているので、
   無印の「空間」は project を含む側だと解釈した（含める）。
   含めない解釈だと答えは 0 と 2 になる。含める解釈で 17 と 19。
   **この2問は、この一点だけで値が丸ごと変わる。**

2. **element_all が「全 IfcElement 個体」か「3経路のいずれかで空間に繋がっている物理要素」か。**
   設問は「集約の親も部品も、付着している要素も、全て1行として数える」としか言わず、
   空間への所属を要求しているかが読めない。今回は corpus 側に孤児が0個だったため
   どちらでも 629 になり、実害は出なかった。孤児のある corpus では割れる。

3. **split の「行」に多重度があるか。**
   同じ (所有者, Pset, 属性) が同一経路で複数の関係インスタンスから生じた場合、
   1行にするか2行にするかが決まっていない。今回は多重発生が0件だったため
   重複排除しても・しなくても 324 で同じだった。両方計算して一致を確認済み。

4. **quantity_all の「行」が数量実体そのものか (所有者, 数量) の組か。**
   今回は共有が0件で、どちらでも 250。

## 課題文・指示の側の欠陥だと思った箇所

1. **規則の中に、ある設問の答えを一意に決める検算式が書かれている。**
   「性能仕様は IFCPROPERTYSET の中の属性を指す。IFCPROPERTYSINGLEVALUE と
   IFCPROPERTYENUMERATEDVALUE の両方を数える」という定義に従うと、
   属性実体の総数 324 が `grep -c` 2回でほぼ即座に出る。
   corpus では属性が複数 Pset に共有されておらず、かつ型経由でしか付かない Pset の
   属性も別個体だったため、この 324 がそのまま property_owner_any_split の答えになった。
   つまり **property_owner_any_split は所有関係を一切辿らずに解ける。**
   関係を辿る能力を測る設問のはずが、型名の grep で通ってしまう。
   （所有者を限定する physical 側や merged 側は辿る必要があるので、この抜けは1問分。）

2. **「行」という単位が最後まで定義されていない。**
   spatial_* / element_* では明らかに「エンティティ個体1つ＝1行」なのに、
   property_* では「(所有者, Pset, 属性, 経路) の組＝1行」に意味が変わり、
   quantity_all では再びどちらとも取れる。同じ語が3通りに使われている。
   上の「決まっていない箇所」3・4はすべてこれに由来する。

3. **`grade_levels: ["Q10"]` が設問13問と対応していない。**
   13問あるのに採点段階の指定が1つしかない。設問ごとの重みや、
   どの問が Q10 なのかが答案側から分からない。

4. **規則「数量が付く先は所有者の種類を問わず全て数える」は設問 quantity_all の
   文面と完全に重複している。**害はないが、規則側で答えの範囲が確定しているため、
   この設問だけ「設問ごとに範囲が違う」という T007 の主眼から外れている。

5. **除外リストが corpus の実態と噛み合っていない。**
   物理要素から除けと指示された IFCZONE / IFCGROUP / IFCSYSTEM / IFCDISTRIBUTIONSYSTEM /
   IFCANNOTATION / IFCGRID / IFCDISTRIBUTIONPORT のうち、corpus に実在するのは
   IFCZONE（2）と IFCDISTRIBUTIONSYSTEM（4）だけ。残り5型は0個体なので、
   この規則を読み違えても点差が出ない。**除外規則を読めたかどうかを、この課題は測れていない。**
   同様に「IFC4.3 のインフラ空間型」として例示された IFCFACILITY / IFCFACILITYPART も0個体。

6. **T005 の欠陥診断の検証という位置づけと、設問の重さが釣り合っていない。**
   note は「両腕とも全問に到達するはず」と述べるが、
   上記1のとおり少なくとも1問は関係追跡なしで到達できるので、
   「全問到達＝課題文の欠陥だけが原因だった」という推論はそのままでは成り立たない。

## ファイルの内部矛盾

1. **`corpus/buildingsmart/ifc4/Infra-Road.ifc` はスキーマ違反。**
   `FILE_SCHEMA(('IFC4'))` を宣言しながら `IFCSURFACEFEATURE` を20個体含む。
   IfcSurfaceFeature は IFC4.3 で追加された型で IFC4 には存在しない。
   （同ファイルには IFCRELADHERESTOELEMENT は無く、20個体はすべて
   IFCRELCONTAINEDINSPATIALSTRUCTURE で直接空間に載っている。）
   この1ファイルのせいで element_no_feature と element_direct_only の値が動く。

2. **同名ファイルの ifc4 版と ifc4x3 版で空間構造の型付けが揃っていない。**
   ifc4x3/Infra-Road.ifc は IFCROAD 5 / IFCROADPART 26 を使うが、
   ifc4/Infra-Road.ifc は同じ38個の空間を IFCSITE 等で表現している（空間の個数は38で一致）。
   ifc4x3/Infra-Bridge.ifc は spatial 28（IFCBRIDGE 3 + IFCBRIDGEPART 18 を含む）だが
   ifc4/Infra-Bridge.ifc は spatial 21 で、**同名ファイルでも空間の個数自体が違う。**
   「両方を別のファイルとして数える」という規則があるので数え方の問題は無いが、
   両版が同一シーンの表現違いだという前提は成り立っていない。

3. **ifc4x3 側に Infra-Landscaping.ifc が存在しない**（ifc4 側にのみ9本目がある）。
   これは task.json の files 一覧とも整合しているので欠落ではないが、
   17 = 8 + 9 という非対称の理由がどこにも書かれていない。

4. **ifc4x3/Infra-Plumbing.ifc に IFCBRIDGE が3個体ある。**
   配管サンプルの空間構造が橋になっているのは意図が読めないが、
   ifc4x3/Infra-Bridge.ifc の IFCBRIDGE も3個体なので、
   シーンの一部を共有しているだけの可能性が高い。数え方には影響しない。
