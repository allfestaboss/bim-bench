# T007 armC_r3 報告

## 方法

自作の ISO-10303-21 パーサ（Python 標準ライブラリのみ、`re` と手書きトークナイザ）を
スクラッチパッドに書いて17ファイルを読んだ。IFC 専用ライブラリは一切使っていない。

- `DATA;` 以降を、文字列リテラル（`'...'`、`''` エスケープ）を尊重しながら `;` で分割。
- `#N=TYPE(...)` を正規表現で分解し、パラメータリストを再帰的にトークン化
  （参照 `#n` / 文字列 / 列挙 `.X.` / 数値 / `$` / `*` / 入れ子リスト）。
- 健全性検査: 各ファイルで「パースできた実体数」と「行頭 `#N=` の正規表現ヒット数」が
  17ファイルすべてで一致（444/156/158/407/953/1488/440/728/1186 と
  383/153/158/350/883/440/728/887）。複合実体（`#1=(A(..)B(..))`）は0件。
  つまり1実体＝1行で、取りこぼしは無い。
- 属性の位置は決め打ちではなく、実データでアリティを検査して確認した。
  `IFCRELDEFINESBYPROPERTIES` / `IFCRELDEFINESBYTYPE` / `IFCRELCONTAINEDINSPATIALSTRUCTURE` /
  `IFCRELAGGREGATES` / `IFCRELADHERESTOELEMENT` はすべてアリティ6。
  型実体は 10 または 11 で、いずれも index 5 が `HasPropertySets`。

## 型の分類

17ファイルに出現する実体型は105種。全部を列挙して手で分類した。

**空間構造の実体（出現したもの）**: IFCPROJECT 17 / IFCSITE 72 / IFCBUILDING 35 /
IFCBUILDINGSTOREY 39 / IFCSPACE 4 / IFCSPATIALZONE 2 / IFCBRIDGE 6 / IFCBRIDGEPART 18 /
IFCROAD 5 / IFCROADPART 26 / IFCRAILWAY 2 / IFCRAILWAYPART 2 = **228**。
規則65の「等」は今回無害だった。IFCFACILITY / IFCFACILITYPART / IFCEXTERNALSPATIALELEMENT /
IFCMARINEFACILITY 等は corpus に1件も無く、規則が明示した12型がそのまま全部だった。

**物理要素（IfcElement 下位型、出現したもの）**: IFCAIRTERMINAL 4 / IFCBEAM 28 /
IFCBUILDINGELEMENTPROXY 129 / IFCCHIMNEY 6 / IFCCOLUMN 14 / IFCCOURSE 18 /
IFCDISCRETEACCESSORY 4 / IFCDUCTSEGMENT 2 / IFCEARTHWORKSFILL 21 / IFCELEMENTASSEMBLY 37 /
IFCFOOTING 16 / IFCFURNITURE 2 / IFCGEOGRAPHICELEMENT 84 / IFCMEMBER 26 / IFCPIPESEGMENT 48 /
IFCRAIL 4 / IFCRAILING 4 / IFCROOF 4 / IFCSIGN 4 / IFCSLAB 44 / IFCSURFACEFEATURE 40 /
IFCTRACKELEMENT 66 / IFCWALL 24 = **629**。
規則66の除外対象（IFCZONE 2 / IFCDISTRIBUTIONSYSTEM 4 / IFC***TYPE 群）は除いた。
IFCANNOTATION / IFCGRID / IFCDISTRIBUTIONPORT / IFCGROUP / IFCSYSTEM /
IFCOPENINGELEMENT / IFCVIRTUALELEMENT は corpus に0件。

## 各設問の経路

- **spatial_all = 228** / **spatial_no_project = 211**（228 − IFCPROJECT 17）。
- **spatial_depth0 = 17**。親＝ `IFCRELAGGREGATES` の RelatedObjects に現れる、または
  `IFCRELCONTAINEDINSPATIALSTRUCTURE` の RelatedElements に現れる、の和。
  結果は各ファイル1件ずつ、すなわち17個の IFCPROJECT だけだった。
- **spatial_depth0_aggregate_only = 19**。集約のみで親を決めると、2つの IFCSPATIALZONE
  （ifc4/ と ifc4x3/ の Building-Architecture に各1）が親を失う。この2件は集約ではなく
  `IFCRELCONTAINEDINSPATIALSTRUCTURE` で空間に載っている。17 + 2 = 19。
  この2設問の差はまさにこの2件だけで生まれている。
- **element_all = 629**。規則67の3経路（直接包含 / 集約の親をたどる / 付着の母体をたどる）で
  推移的に空間到達性を計算したところ、**629件全部が到達した**（到達しないものは0件）。
  したがって「全 IfcElement 実体数」と「3経路で空間に繋がるものの数」は一致し、
  この設問の解釈ゆれは結果に影響しなかった（下記「決めた箇所」参照）。
  内訳: 直接 552 / 集約経由のみ 57 / 付着経由のみ 20。
- **element_direct_only = 552**。`IFCRELCONTAINEDINSPATIALSTRUCTURE` の RelatedElements に
  直接現れる物理要素。104個の包含関係の RelatingStructure は全て空間型だった。
- **element_no_adheres = 609**。付着でしか繋がらない20件（ifc4x3/Infra-Road.ifc の
  IFCSURFACEFEATURE、`IFCRELADHERESTOELEMENT` 4件× 5件ずつ、母体は IFCCOURSE）を除いた。
- **element_no_feature = 589**。IFCSURFACEFEATURE 40件を全部除いた。
- **property_owner_physical_split = 308** / **_merged = 306**。
- **property_owner_any_split = 324** / **_merged = 322**。
  直接は `IFCRELDEFINESBYPROPERTIES`（RelatingPropertyDefinition が IFCPROPERTYSET のもの137件。
  残り90件は IFCELEMENTQUANTITY なので性能仕様からは除外）、
  型経由は `IFCRELDEFINESBYTYPE` → 型の HasPropertySets。
  split の324は IFCPROPERTYSINGLEVALUE 242 + IFCPROPERTYENUMERATEDVALUE 82 と一致した。
  所有者の内訳: IFCSLAB 116 / IFCGEOGRAPHICELEMENT 96 / IFCMEMBER 30 / IFCWALL 23 /
  IFCBEAM 21 / IFCSPACE 10 / IFCFOOTING 7 / IFCELEMENTASSEMBLY 7 / IFCROOF 4 / IFCCOLUMN 4 /
  IFCBUILDING 3 / IFCZONE 3。非物理は IFCSPACE 10 + IFCZONE 3 + IFCBUILDING 3 = 16 で、
  324 − 16 = 308、322 − 16 = 306。
- **quantity_all = 250**。IFCQUANTITYLENGTH 88 / AREA 72 / VOLUME 90。
  COUNT / WEIGHT / TIME は0件。IFCELEMENTQUANTITY 90件は入れ物として除外。
  90件の IFCELEMENTQUANTITY はすべて `IFCRELDEFINESBYPROPERTIES` で所有者1件に付いており、
  型経由で数量が付く例は0件、孤立した数量も0件。よって
  「実体数」「(所有者, 数量) 行数」「まとめた行数」がすべて250で一致し、解釈ゆれが無かった。

## 読めなかった箇所

無し。17ファイル全体で未パースの行、複合実体、IFCCOMPLEXPROPERTY、
IFCPROPERTYSETDEFINITIONSET、孤立した IFCPROPERTYSET / IFCELEMENTQUANTITY は
いずれも0件だった。

## 課題文が数え方を決めていないと思った箇所

1. **element_all の母集団**。「物理要素の行数」が (a) ファイル内の全 IfcElement 実体なのか、
   (b) 規則67の3経路で空間に繋がっているものだけなのかを課題文は決めていない。
   規則67がわざわざ3経路を定義していること、element_direct_only / element_no_adheres が
   経路の部分集合を訊いていることから (b) と読んだ。ただし今回は
   **どちらでも629で同値**（到達しない物理要素が0件）だったため、答えに影響しない。
   今後 corpus に IFCOPENINGELEMENT のような「3経路に載らない要素」が入ると、
   この曖昧さがそのまま採点差になる。今の corpus は開口要素を含まないので露見しない。
2. **quantity_all の行の定義**。「数量の行数」が実体数なのか (所有者, 数量) 対の数なのか、
   また split / merged のどちらなのかを課題文は決めていない。今回は3つとも250で一致した。
   もし1つの IFCELEMENTQUANTITY が複数オブジェクトに付く、または型経由でも付く corpus に
   なれば、ここは分岐する。
3. **spatial_depth0_aggregate_only の親の定義**。「IFCRELAGGREGATES でのみ決まる」の
   RelatingObject が空間型に限られるかを決めていない。「RelatedObjects に現れれば子」と
   広く取った。今回、空間実体が非空間の下に集約されている例は0件だったので同値。
4. **規則65の「等」**。IFC4.3 のインフラ空間型の列挙が開いている。今回は列挙外の空間型が
   corpus に0件だったので実害無し。ただし敵対テストで IFCFACILITY や
   IFCEXTERNALSPATIALELEMENT を足すと、この「等」の解釈だけで点が動く。

## 課題文・指示の側の欠陥だと思った箇所

1. **element_no_adheres と element_no_feature が、この corpus では独立していない疑い**。
   実際には609と589で違う値になったが、その差は「ifc4/Infra-Road.ifc では20個の
   IFCSURFACEFEATURE が IFCBUILDINGSTOREY に直接包含されており、
   ifc4x3/Infra-Road.ifc では同じ20個が IFCRELADHERESTOELEMENT で IFCCOURSE に付いている」
   という**同一モデルの2版間のエンコード差**だけから来ている。つまりこの2設問を分離しているのは
   規格の意味論ではなく変換ツールの都合であり、腕の実力ではなく
   「2版が別エンコードであることに気づいたか」を測っている。
2. **spatial_depth0 と spatial_depth0_aggregate_only の差が全17ファイル中2件しかない**。
   しかも同一の Building-Architecture が両版に入っている（実質1パターン×2）。
   この設問対は事実上「IFCSPATIALZONE が包含で載っていることに気づいたか」の1ビットで、
   ずれても1しか動かない。完全一致採点なので0点になる点は重いが、
   測っている情報量はほぼ無い。
3. **property の split / merged の差も全体で2しかない**（324 vs 322）。
   両方とも Building-Architecture の Pset_SlabCommon.FireRating が直接と型経由で
   二重に付いている1件ずつ。規則69が「同じ属性が両経路から付くことがある」と
   **わざわざ書いているので、事実上そこにヒントが置かれている**。
   規則が無ければ split/merged の区別は corpus から自力で発見する必要があり難度が高い。
   規則を書いた時点で、この設問対は「規則を読んだか」の確認に落ちている。
4. **課題文の note が T006 の欠陥内容を説明している**。「直前の課題の欠陥を説明するつもりで
   書いた文の中にその課題自身の答えを印字していた」と書いてあり、数値そのものは
   確かに外されている。ただし「腕の全ての走行が独立にこれを申告した」という一文は、
   T007 でも同種の申告が期待されていることを示唆しており、報告の内容に影響しうる。
   数値漏れではないので実害は無いと判断した。
5. **grade_levels に "Q10" とあるが、設問は13問**。対応関係が課題文からは読めない。
   採点対象の粒度が答案側から確認できない。

## ファイルの内部矛盾

1. **ifc4/ のファイルが IFC4 に存在しない実体型を含む**。FILE_SCHEMA は `('IFC4')` だが、
   IFCBRIDGE / IFCBRIDGEPART / IFCROAD / IFCROADPART / IFCRAILWAY / IFCRAILWAYPART /
   IFCCOURSE / IFCRAIL / IFCTRACKELEMENT / IFCEARTHWORKSFILL / IFCSIGN / IFCSURFACEFEATURE は
   いずれも IFC4.3 で追加された型で、IFC4 のスキーマには無い。
   つまり ifc4/ 側は「IFC4 と宣言しているが IFC4.3 の語彙で書かれた」ファイルである。
   規則73が「両方を別ファイルとして数える」と言っているので数える方針には影響しないが、
   スキーマ宣言を信じて型を絞る実装は壊れる。
2. **同名2版が完全に同じモデルではない**。ifc4x3/ には Infra-Landscaping.ifc が無い（9対8）。
   Infra-Bridge は空間28対21・要素50対57、Infra-Road は直接包含35対55と、
   同名でも構造が違う。上記1の欠陥指摘2と同じ根。
3. **ifc4/Infra-Road.ifc で IFCSURFACEFEATURE が IFCBUILDINGSTOREY に直接包含されている**。
   道路モデルに建物階が出てくること自体が変換の副作用と思われる。

## 制約の遵守

- IFC 専用ライブラリ（ifcopenshell 等）は使用していない。Python 標準ライブラリのみ。
- 参照解・抽出器・採点器（reference/ bench/ checker/ out/ README.md arms/ docs/）は開いていない。
- 他の走行（armC_r1 / armC_r2 / armB_*）の答案・報告は開いていない。
- 過去課題（T001〜T006）の tasks/ attempts/ は開いていない。
- 見たのは corpus/buildingsmart/ 配下の17ファイルと tasks/T007/task.json のみ。
  作業スクリプトはスクラッチパッドに置き、リポジトリには残していない。
