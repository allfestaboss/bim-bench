# T007 armC_r1 報告

## 方法（共通）

標準ライブラリのみで ISO-10303-21 (SPF) の簡易パーサを自作した（文字列リテラル中の `;`
と `''` エスケープを考慮して DATA セクションを文分割 → `#N=TYPE(...)` を型名と
トップレベル引数に分解）。IFC 専用ライブラリは一切使っていない。

- 17ファイルの実体総数 9,942。`grep -o '#[0-9]*='` の総数と完全一致（パーサの取りこぼしなし）。
- 複合実体（`#N=(A(..)B(..))`）は 0 件。パース不能な文も 0 件。
- 空間実体の総数と物理要素の総数は、パーサとは別経路の正規表現 `=IFCXXX\(` による
  独立集計でも同じ値（228 / 629）になることを確認した。

型の分類は corpus に実在する 105 種を1つずつ手で振り分けた（規則の除外リストに従い
`IFC***TYPE` / `IFCZONE` / `IFCDISTRIBUTIONSYSTEM` / 空間実体は物理要素から外した）。
物理要素として数えた型:
IFCAIRTERMINAL, IFCBEAM, IFCBUILDINGELEMENTPROXY, IFCCHIMNEY, IFCCOLUMN, IFCCOURSE,
IFCDISCRETEACCESSORY, IFCDUCTSEGMENT, IFCEARTHWORKSFILL, IFCELEMENTASSEMBLY, IFCFOOTING,
IFCFURNITURE, IFCGEOGRAPHICELEMENT, IFCMEMBER, IFCPIPESEGMENT, IFCRAIL, IFCRAILING,
IFCROOF, IFCSIGN, IFCSLAB, IFCSURFACEFEATURE, IFCTRACKELEMENT, IFCWALL。
残り 82 種はすべて型定義・関係・幾何・資源クラスで、IfcElement 下位型は含まれない。
空間実体として実在したのは IFCPROJECT/IFCSITE/IFCBUILDING/IFCBUILDINGSTOREY/IFCSPACE/
IFCSPATIALZONE/IFCBRIDGE/IFCBRIDGEPART/IFCROAD/IFCROADPART/IFCRAILWAY/IFCRAILWAYPART の
12種のみ（IFCFACILITY/IFCFACILITYPART は corpus に存在しない）。

## 設問ごとの数え方

| 設問 | 値 | 経路・除外 |
|---|---|---|
| spatial_all | 228 | 上記12種の実体数。 |
| spatial_no_project | 211 | 228 − IFCPROJECT 17。 |
| spatial_depth0 | 17 | 親 = IFCRELAGGREGATES の RelatedObjects または IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements に現れること。親を持たない空間実体は 17 個の IFCPROJECT のみ。 |
| spatial_depth0_aggregate_only | 19 | 親を集約のみに限ると、17 プロジェクト + IFCSPATIALZONE 2件（ifc4x3/Building-Architecture #385、ifc4/Building-Architecture #448。どちらも IFCRELCONTAINEDINSPATIALSTRUCTURE で IFCBUILDING に載っており、集約の子ではない）。 |
| element_all | 629 | 物理要素の実体数。**3経路のいずれかで空間に到達できない物理要素は 0 件**だったので、「全インスタンス」と「所属している要素のみ」のどちらの読みでも 629 で一致する（曖昧さが消えた）。 |
| element_direct_only | 552 | IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements に現れる物理要素（重複排除）。RelatingStructure が空間でない例、同一要素が複数の包含関係に現れる例はいずれも 0 件。 |
| element_no_adheres | 609 | 直接包含＋集約の親をたどって空間に届く集合（推移閉包）。除かれたのは ifc4x3/Infra-Road.ifc の IFCSURFACEFEATURE 20件（IFCRELADHERESTOELEMENT 4本 × 5件）だけ。ifc4/Infra-Road.ifc の 20件は直接包含なので残る。 |
| element_no_feature | 589 | 629 − IFCSURFACEFEATURE 40（20件 × Infra-Road 2ファイル）。 |
| property_owner_physical_split | 308 | 行 = (関係の RelatedObjects の各オブジェクト) × (Pset 内の IFCPROPERTYSINGLEVALUE / IFCPROPERTYENUMERATEDVALUE)。直接 = IFCRELDEFINESBYPROPERTIES、型経由 = IFCRELDEFINESBYTYPE → 型の HasPropertySets（属性 index 5）。所有者が物理要素の行のみ。 |
| property_owner_physical_merged | 306 | 上を (ファイル, 要素, Pset名, 属性名) で一意化。重複は 2件（ifc4x3/Building-Architecture #49 と ifc4/Building-Architecture #52 の Pset_SlabCommon.FireRating が直接と型経由の両方から付く）。 |
| property_owner_any_split | 324 | 所有者を絞らない全行。非物理の所有者は 16行（IFCSPACE 10、IFCBUILDING 3、IFCZONE 3）。 |
| property_owner_any_merged | 322 | 324 − 上記の重複 2件。 |
| quantity_all | 250 | IFCQUANTITYLENGTH 88 / AREA 72 / VOLUME 90。IFCELEMENTQUANTITY（90件、入れ物）は数えない。COUNT/WEIGHT/TIME は corpus に不在。 |

補足の健全性確認:
- IFCPROPERTYSET は 139件・IFCELEMENTQUANTITY は 90件あり、**どれも未接続（どの経路からも
  参照されない）ではなかった**。属性インスタンス 324件はすべていずれかの Pset の中にある。
- 同じ Pset が複数の関係から参照される例、RelatedObjects が2個以上の
  IFCRELDEFINESBYPROPERTIES はいずれも 0 件。したがって数量は「インスタンス数 250」と
  「(所有者×数量) の行数 250」が一致し、こちらも読みの差が出なかった。
- 型経由の行は全部で 4行（上記2ファイルの IFCSLAB に FireRating と SurfaceSpreadOfFlame）。
- IFCPROPERTYENUMERATION（5件）は属性そのものではないので数えていない。
  IFCCOMPLEXPROPERTY は corpus に存在しない（入れ子の取りこぼしはない）。

## 読めなかった箇所

なし。17ファイルすべてを最後まで機械的にパースでき、未分類の実体も残らなかった。

## 課題文が数え方を決めていないと思った箇所（減点対象ではない旨了解のうえ）

1. **spatial_depth0 / spatial_depth0_aggregate_only の母集合に IFCPROJECT を含むか。**
   設問3・4は「空間」としか書かず、母集合が設問1（IFCPROJECT を含む）なのか設問2
   （除く）なのかを決めていない。規則側の「空間構造の実体」の定義は IFCPROJECT を含み、
   設問2はわざわざ「IFCPROJECT を除いた」と明示しているので、**既定は含む**と解釈した。
   含む場合 17 / 19、除く場合 0 / 2 になる。除く読みだと設問3の答えが 0 になり設問として
   成立しにくいことも、含む方に決めた根拠。
2. **element_all が「物理要素の全インスタンス」か「3経路のいずれかで空間に所属している
   物理要素」か。** 本 corpus では未所属の物理要素が 0 件だったため、どちらでも 629 で
   一致した（実害なし）。
3. **property_owner_any_* の「所有者」に型オブジェクト自身を含めるか。**
   「型の HasPropertySets を、その型を参照する各オカレンスに付いたものとして数える」
   （＝所有者はオカレンス）と解釈した。型自体を所有者として1行追加する読みも文面上は
   可能だが、規則が「性能仕様は要素に2通りで付く」と経路で定義しているので前者を採った。
   本 corpus ではどの Pset も必ずいずれかの経路で参照されており、未接続 Pset による差は出ない。
4. **quantity_all が「IfcQuantity* のインスタンス数」か「(所有者×数量) の行数」か。**
   「所有者の種類を問わず」という言い回しは行＝所有者ペアを示唆するが、共有された
   IFCELEMENTQUANTITY が 0 件だったため両者とも 250 で一致した。

## 課題文・指示の側の欠陥だと思った箇所

1. **設問3・4の母集合が未指定**（上記1）。今回は 17 と 0 という桁違いの差になり得るので、
   「前の設問の範囲を引き継がない」という指示があってもなお、どちらが既定かを
   本文で明示しないと採点者の意図に当てられるかは運になる。ここが本課題で唯一
   「規格の読解ではなく文面の解釈」で点が動く箇所だと思う。
2. **規則の「等」が範囲を開いている。** 「IFC4.3 のインフラ空間型（…等）」の「等」は
   IFCMARINEFACILITY / IFCEXTERNALSPATIALELEMENT などを含み得るが、corpus に存在しないため
   実害はなかった。存在した場合は解釈で値がずれる。
3. **課題文の note に「T006 の再出題」「設問・規則・対象ファイルは T006 と一字一句同じ」
   と書いてある。** T006 の答案・報告・参照解を持っている腕にとってはこれ自体が
   「過去回の答えを流用してよい」という誘導になり得る（本走行では tasks/T00x や
   attempts/ の他ファイルは一切開いていない）。T006 の欠陥は「答えを印字していたこと」
   だったので、再出題であること自体を明記するのは、独立性の担保を指示文だけに
   依存させる設計になっている。
4. **数量の設問だけ split/merged の区別がない。** 性能仕様は split と merged を分けて
   訊いているのに、数量は1問しかなく、どちらの数え方かが文面から決まらない
   （今回は一致したので露見しない）。同じ corpus で共有 IFCELEMENTQUANTITY が
   1件でも出れば、この設問は解釈で割れる。

## ファイルの内部矛盾

1. **IFC4 と申告しているファイルに IFC4.3 でしか存在しない実体が入っている。**
   `corpus/buildingsmart/ifc4/Infra-Road.ifc` は `FILE_SCHEMA(('IFC4'))` だが
   IFCSURFACEFEATURE を 20件含む（IfcSurfaceFeature は IFC4.3 で追加された型）。
   ifc4 側のファイルで IFC4.3 専用型が出るのはこの1種だけで、
   IFCBRIDGE/IFCROAD/IFCCOURSE/IFCEARTHWORKSFILL/IFCRAIL/IFCTRACKELEMENT/IFCSIGN/
   IFCRELADHERESTOELEMENT はきちんと ifc4x3 側だけに現れている。
2. **同名ファイルでも中身が対応していない。** 例えば Infra-Road は ifc4x3 側が
   IFCRELADHERESTOELEMENT で路面標示を貼り付けているのに対し、ifc4 側は同じ 20件を
   直接 IFCRELCONTAINEDINSPATIALSTRUCTURE に載せている。また性能仕様は ifc4x3 側に
   ほぼ存在せず（324件中 318件が ifc4 側）、Pset を持つのは ifc4x3 では
   Building-Architecture の 2 Pset だけ。「同じモデルの2版」ではないので、
   スキーマ版間の比較としては読めない。
3. `corpus/buildingsmart/ifc4/Infra-Landscaping.ifc` に対応する ifc4x3 版が無い
   （17ファイル = 8 + 9 の非対称）。課題の files 一覧どおりなので誤りではないが、
   「同じ基底名のファイルが2つのスキーマ版に存在する」という規則は全ファイルには
   当てはまらない。

## 制約について

- IFC 専用ライブラリ（ifcopenshell 等）は使っていない。Python 標準ライブラリ（re, os,
  collections, json, pickle）と grep のみ。
- 見てはいけないディレクトリ（reference/ bench/ checker/ out/ arms/ docs/ README.md、
  他の tasks/attempts）は開いていない。ルート直下の `ls -la` で
  ディレクトリ名一覧が見えただけで、中身は読んでいない。
- **1点申告する。** 作業用に共有スクラッチパッド
  `.../826e8fde-.../scratchpad/` に書いたパーサが、別プロセスに同名で上書きされた
  （同じセッションのスクラッチパッドを他の走行と共有している疑いがある）。その調査で
  `tail -5 spf.py` を実行し、自分が書いていない集計コードの末尾5行を目にした
  （型名を数えて出力する部分のみ。答えの数値も他走行の答案・報告も含まれていない）。
  以後は衝突を避けるため専用サブディレクトリ `scratchpad/wk_c1_9f3a/` に隔離して作業し、
  スクラッチパッド内の他ファイル（analyze.py, probe_owner.py, T005.before.json 等）は
  一切開いていない。**ベンチ運用側への申し送り: 走行ごとに作業ディレクトリを分けないと、
  独立走行のはずが同一パスを踏み合う。**
