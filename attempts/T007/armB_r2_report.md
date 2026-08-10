# T007 armB_r2 報告

## 経路（どうやって数えたか）

17ファイルを1体ずつ下請けエージェントに割り当て（合計17体）、各ファイルを **Read だけ**で
全行ページングさせ、実体ID一覧を明示的に列挙させたうえで各設問の元になる数値を報告させた。
親（本エージェント）は17ファイル分の値を足し合わせただけである。コードは一切実行していない。

各ファイルから取った素の数値と、そこからの設問への写像:

| 設問 | 数え方 |
|---|---|
| spatial_all | 空間型インスタンスの実数。合計 228 |
| spatial_no_project | 228 − IFCPROJECT 17件 = 211 |
| spatial_depth0 | IFCRELAGGREGATES の RelatedObjects にも IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements にも現れない空間。全ファイルで IFCPROJECT の1件だけ = 17 |
| spatial_depth0_aggregate_only | IFCRELAGGREGATES の RelatedObjects に現れない空間。ifc4x3/Building-Architecture と ifc4/Building-Architecture だけ IFCSPATIALZONE が包含で親を持つため +1 ずつ。17 + 2 = 19 |
| element_all | IfcElement 下位型のインスタンス実数 = 629 |
| element_direct_only | IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements に現れる物理要素（重複排除）= 552 |
| element_no_adheres | 629 − 「付着でしか空間に届かない要素」20（ifc4x3/Infra-Road のみ）= 609 |
| element_no_feature | 629 − IFCSURFACEFEATURE 40（ifc4x3/Infra-Road 20 + ifc4/Infra-Road 20）= 589 |
| property_owner_physical_split | 直接（IFCRELDEFINESBYPROPERTIES→IFCPROPERTYSET）と型経由（IFCRELDEFINESBYTYPE→型の HasPropertySets）を別行として、(関係, 対象物理要素, 属性) の組を数えた = 308 |
| property_owner_physical_merged | 同上を (要素, Pset名, 属性名) で一意化 = 306 |
| property_owner_any_split | 所有者の種類を問わない同じ数え方 = 324 |
| property_owner_any_merged | 同上を一意化 = 322 |
| quantity_all | IfcQuantity*（LENGTH/AREA/VOLUME/COUNT/WEIGHT/TIME）= 250 |

除外したもの:
- IFC***TYPE（型オブジェクト）は空間にも物理要素にも数えない。
- IFCZONE / IFCGROUP / IFCSYSTEM / IFCDISTRIBUTIONSYSTEM / IFCANNOTATION / IFCGRID /
  IFCDISTRIBUTIONPORT は物理要素から除外（ただし性能仕様の「所有者を問わず」では所有者として数える）。
- IfcPositioningElement 系（IFCALIGNMENT*, IFCREFERENT）と IfcStructuralItem 系も
  IfcElement ではないので物理要素から除外。実際にはコーパス中に1件も出現しなかった。
- IFCPROPERTYENUMERATION（属性ではなく値域定義）は属性として数えない。
- IFCELEMENTQUANTITY は入れ物なので数量にも性能仕様にも数えない。
- IFCPROPERTYSINGLEVALUE / IFCPROPERTYENUMERATEDVALUE 以外の属性型はコーパス中に存在しなかった。
- IFCGEOGRAPHICELEMENT は IfcElement なので物理要素に数えた（Landscaping 系で効く）。

## 読めなかった箇所

コーパスは行数は少ないがトークン量が巨大（例: ifc4x3/Building-Architecture は392行で約116,000トークン。
1行が120,000トークンを超えるジオメトリ行もある）。Read の出力上限は約25,000トークンで、
**offset/limit をどう与えても1行を分割して読む手段がない**ため、全17ファイル合計で概ね100行前後の
「単独で上限を超える行」が最後まで表示できなかった。

ただしこれらは全て IFCTRIANGULATEDFACESET とその IFCCARTESIANPOINTLIST3D で、
同じIDを参照する `IFCSTYLEDITEM(#n,...)` と `IFCSHAPEREPRESENTATION(...,'Tessellation',(#n))` が
すぐ近くの読めた行にあるため、種別は間接的に確定できた。空間・要素・属性・数量・関係のいずれにも
なり得ないので、報告した数値には影響しない。
（多くのファイルは `行番号 = ID + 7` が厳密に成り立ち、抜けが無いことを機械的でなく形式的に確認できた。
ID が非連続なのは ifc4x3/Building-Architecture と ifc4/Building-Architecture の2本のみ。）

## 課題文が数え方を決めていないと思った箇所

1. **element_all の範囲。** 設問は「物理要素の行数」とだけ言い、規則6は所属経路を3通り定義している。
   「ファイル内の IfcElement インスタンス全部」なのか「3経路のいずれかで空間に届くものだけ」なのか
   文面からは決まらない。**両方を測った。17ファイル全てで一致した**（どのファイルにも空間に
   繋がらない浮いた要素が無かった）ので、答えは変わらない。
2. **quantity_all の行の単位。** 「数量の行数」が IfcQuantity* のインスタンス数なのか、
   (所有者 × 数量) の組の数なのか決まっていない。**両方を測り、17ファイル全てで一致した**
   （どの IFCELEMENTQUANTITY も RelatedObjects が1件で、数量が共有されていない）。
   インスタンス数で提出している。
3. **spatial_depth0 に IFCPROJECT を含めるか。** 設問2で明示的に IFCPROJECT を外しているので
   設問3も外すようにも読めるが、指示文の「前の設問の範囲を引き継がない」に従い、
   **IFCPROJECT を含む**として数えた。IFCPROJECT は必ず親を持たないので、この判断は
   spatial_depth0 と spatial_depth0_aggregate_only の両方を17ずつ押し上げている。
   もし除く読みが正解なら、正解は 0 と 2 になる。ここは分岐が大きい。
4. **「空間構造の実体 ... 等」の "等"。** 列挙が閉じていない。実際にコーパスに出現したのは
   IFCPROJECT / IFCSITE / IFCBUILDING / IFCBUILDINGSTOREY / IFCSPACE / IFCSPATIALZONE /
   IFCBRIDGE / IFCBRIDGEPART / IFCROAD / IFCROADPART / IFCRAILWAY / IFCRAILWAYPART のみで、
   IFCFACILITY / IFCFACILITYPART / IFCEXTERNALSPATIALELEMENT / marine 系は1件も無かったので、
   "等" の解釈が答えを動かす余地は結果的に無かった。
5. **型経由の性能仕様で、どの型を数えるか。** 規則は「IFCRELDEFINESBYTYPE が指す型の
   HasPropertySets」と書いており、どこからも参照されない型の HasPropertySets は数えない読みを採った。
   コーパスでは型の HasPropertySets はほぼ全て `$` なので、影響は
   ifc4x3/Building-Architecture と ifc4/Building-Architecture の各2行のみ。
6. **spatial_depth0 の「包含関係」。** IFCRELCONTAINEDINSPATIALSTRUCTURE と解した
   （IFCRELREFERENCEDINSPATIALSTRUCTURE はコーパスに存在しない）。

## 課題文・指示の側の欠陥だと思ったもの

1. **【重大・道具立て】指示は「Read / Grep / Glob の3つは使える」と書いているが、この走行の
   セッションには Grep も Glob も存在しなかった。** Grep を呼ぶと
   「No such tool available: Grep. Grep is not available in this session — search file contents
   with `grep` via the Bash tool instead」というエラーが返り、ToolSearch にも Grep/Glob は
   登録されていなかった。Bash は課題側で禁止されているので、実質 **Read 1本**で全コーパスを
   読むしかなかった。これは腕の道具立てを比較する課題としては条件が違ってしまう
   （「コード実行なし＋Grep あり」と「Read だけ」はコストが桁で違う）。
   走行間で Grep の有無が揃っていないなら、コスト比較は無効になる。
2. **Read の1行トークン上限が課題を物理的に完走不能にしかけている。** 1行が
   120,000トークンあるジオメトリ行は offset/limit で分割できず、原理的に中身を見られない。
   今回は参照関係から種別を確定できたので数値に影響しなかったが、
   「もし巨大行の中に属性や関係が入っていたら誰も正しく数えられない」構造になっている。
   ベンチ側で意図した難所ではないと思われる。
3. **設問 element_no_adheres と element_no_feature は、ほぼ同じものを測っている。**
   コーパス中で IFCRELADHERESTOELEMENT を使うのは ifc4x3/Infra-Road だけで、そこでは
   付着している要素が IFCSURFACEFEATURE 20件と完全一致する。両者を分離しているのは
   ifc4/Infra-Road が IFCSURFACEFEATURE 20件を**付着ではなく直接包含で**載せていることだけ。
   つまりこの2問の差 (609 vs 589) は、たった1ファイルのモデリング差1点に全体重が乗っている。
4. **設問 property_owner_*_merged が split と分かれる根拠も1ファイルに集中している。**
   同じ (要素, Pset名, 属性名) が両経路から来るのは Building-Architecture の2版だけで、
   しかも値が食い違う（FireRating が直接 REI30 / 型経由 REI60）。他15ファイルでは
   split == merged。設問4問（physical/any × split/merged）のうち実質1点しか分離していない。
5. **spatial_depth0 と spatial_depth0_aggregate_only も同様に、17ファイル中2ファイルの
   IFCSPATIALZONE 1件ずつ（差 +2）でしか分離しない。**
   規則の「包含関係で他の空間の下に置かれている空間は、置かれ先を親として扱う」は、
   この2件のためだけに存在する。
6. **note に「T006 と一字一句同じ」と書いてあるが、この文自体は T007 固有である。**
   note は答えを含まないので前回のような漏洩は無い。その点は直っていると確認した。

## ファイルの内部矛盾に気づいたもの

- **ifc4x3/Building-Architecture と ifc4/Building-Architecture:** 同じスラブ #49 / #52 に
  `Pset_SlabCommon.FireRating` が直接（REI30）と型経由（REI60）で二重に付いており、値が矛盾している。
  これは意図的に仕込まれた罠に見える。
- **ifc4/Building-Structural, ifc4/Infra-Bridge, ifc4/Infra-Landscaping:**
  IFCPROPERTYENUMERATION の Name が Ruby のオブジェクト inspect 文字列
  （`#<BimTools::IfcManager::Types::IfcLabel:0x...>`）になっている。エクスポータの不具合が
  そのままコーパスに残っている。
- **IFCSITE の入れ子。** 建築系の全ファイルで `environment - site` が `house - site` を
  IFCRELAGGREGATES で内包している。IFC 上は合法だが珍しい。
- **同名スキーマ版の非対称。** 同じシーンなのに ifc4x3 版は性能仕様（IFCPROPERTYSET）を
  ほぼ全て失っており（Building-Architecture に手で挿入された2件を除いて0件）、
  ifc4 版だけが Pset を持つ。行数差もそれで説明がつく
  （例: Building-Structural は 416 − 359 = 57 行 = 12 Pset + 32 属性 + 12 関係 + 1 列挙）。
  意図的な加工だと思うが、「同じ基底名のファイルが2つのスキーマ版に存在する」という
  規則の書き方からは、内容が大きく違うことは読み取れない。
- **ifc4/Infra-Rail の #723** は Name が `road - site` なのに Description が
  `A designated parking area...`（#23 からのコピー）。
- **ifc4/Infra-Road の複数の IFCBUILDINGSTOREY** が自前の Body 形状（路肩）を持っている。
  空間要素としては異例。
- **ifc4x3/Infra-Rail, ifc4/Infra-Rail, ifc4x3/Infra-Plumbing 等の IFCELEMENTASSEMBLY** は
  何も集約していない葉ノードになっている。
- **ifc4x3/Building-Architecture の #302/#172, ifc4x3/Building-Structural の #144/#154 など**は
  Tag の階層（`...2037932` が `...2037932.920033` の接頭辞）と IfcLocalPlacement の親子関係が
  集約関係を示唆しているのに、対応する IFCRELAGGREGATES が無い。
  Tag から親子を推測すると element_direct_only を取り違える。

## 制約違反の有無

- コードは実行していない。Bash / シェル / スクリプト / Python / awk / sed は一切使っていない。
  下請け17体にも同じ禁止を明示し、Read のみを使うよう指示した。
- reference/ bench/ checker/ out/ README.md arms/ docs/ と、過去課題の tasks/ attempts/ は
  開いていない。下請けにも同じ禁止を渡した。
- attempts/T007/ の他の走行（armB_r1 / armB_r3 / armC_*）の答案・報告は見ていない。
- 作業用一時ファイルは指定された
  `/private/tmp/.../scratchpad/T007_armB_r2/` の下（tally.md, notes.md）だけに書いた。
- 申告事項として、上の「欠陥」1に書いたとおり **Grep / Glob は使えなかった**。
  指示が許可した道具が実在しなかったのであって、こちらが使わなかったわけではない。
