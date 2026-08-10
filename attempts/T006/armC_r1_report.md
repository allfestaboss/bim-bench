# T006 armC_r1 報告

## 方法

自作の ISO-10303-21 パーサ（Python 標準ライブラリのみ、正規表現＋括弧深さによるトークナイザ）で
17ファイルを読み、実体 ID → 型名・引数リストの辞書を作って数えた。IFC 専用ライブラリは使っていない。

パーサの健全性は 2 段階で確認した。

1. 各ファイルの `^#N=` 行数と、パースできた実体数が 17 ファイル全てで完全一致（全実体が
   1 行 1 レコードで、複数行にまたがるレコードは無かった）。
2. 独立に書き直した 2 本目の実装（`verify2.py`、helper も別実装）で 13 問全て同値を再現。

出現する実体型は全 105 種で、全て列挙してから分類した（型名の推測漏れが無いことを確認）。

## 各設問の数え方

**空間構造の実体（spatial_all / spatial_no_project）**
規則の列挙どおり IFCPROJECT / IFCSITE / IFCBUILDING / IFCBUILDINGSTOREY / IFCSPACE /
IFCSPATIALZONE / IFCBRIDGE / IFCBRIDGEPART / IFCROAD / IFCROADPART / IFCRAILWAY /
IFCRAILWAYPART を数えた。IFCFACILITY / IFCFACILITYPART / IFCMARINEFACILITY /
IFCEXTERNALSPATIALELEMENT も集合に入れたが、この corpus には 1 件も出現しないので
規則末尾の「等」の解釈は結果に影響しない。内訳は 17+72+35+39+4+2+6+18+5+26+2+2 = 228。
IFCPROJECT は 17（ファイル数と一致）なので spatial_no_project = 211。

**spatial_depth0 / spatial_depth0_aggregate_only**
親 = IFCRELAGGREGATES の RelatingObject、または IFCRELCONTAINEDINSPATIALSTRUCTURE の
RelatingStructure（空間が RelatedElements 側に入っている場合）。前者だけで見ると 19、
両方を親とすると 17。差の 2 は ifc4x3 と ifc4 の Building-Architecture にある
IFCSPATIALZONE で、この 2 件だけが集約ではなく包含で空間の下に置かれている。
集約関係は spatial→spatial が 209 本、element→element が 57 本のみで、
空間が要素の下に集約されている例や親が 2 つある子は無く、判断に迷う箇所は無かった。

**物理要素（element_all ほか）**
IfcElement の下位型として次の 23 型を採った：IFCAIRTERMINAL, IFCBEAM,
IFCBUILDINGELEMENTPROXY, IFCCHIMNEY, IFCCOLUMN, IFCCOURSE, IFCDISCRETEACCESSORY,
IFCDUCTSEGMENT, IFCEARTHWORKSFILL, IFCELEMENTASSEMBLY, IFCFOOTING, IFCFURNITURE,
IFCGEOGRAPHICELEMENT, IFCMEMBER, IFCPIPESEGMENT, IFCRAIL, IFCRAILING, IFCROOF,
IFCSIGN, IFCSLAB, IFCSURFACEFEATURE, IFCTRACKELEMENT, IFCWALL。合計 629。
除外したのは規則の指定どおり IFCZONE(2), IFCDISTRIBUTIONSYSTEM(4), 全ての IFC***TYPE(177),
空間構造の実体、および IfcProduct だが IfcElement でないもの。
IFCANNOTATION / IFCGRID / IFCDISTRIBUTIONPORT / IFCPROXY / IFCALIGNMENT 系は
この corpus には出現しなかった。

- `element_direct_only` = 552。IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements に
  入っている物理要素の**相異なり数**。RelatingStructure は全 104 本とも空間構造の実体
  （IFCBUILDINGSTOREY/IFCSITE/IFCSPACE/IFCBUILDING/IFCBRIDGEPART/IFCRAILWAYPART/IFCROADPART）
  で、非空間に載っている例は無い。同じ要素が 2 本以上の包含関係に現れる例も無いので、
  「行 = 要素」か「行 = 関係×要素」かで値は変わらない。
- `element_no_adheres` = 609。3 経路（直接包含 / 集約の親をたどる / 付着の母体をたどる）で
  空間への到達可否を再帰的に判定し、**付着経路でしか到達できない要素だけ**を除いた。
  該当は ifc4x3/Infra-Road の IFCSURFACEFEATURE 20 件のみ。
- `element_no_feature` = 589（629 − IFCSURFACEFEATURE 40）。

3 経路の内訳は 552（直接）＋57（集約）＋20（付着のみ）= 629 でちょうど閉じており、
**どの経路でも空間に到達できない物理要素は 0 件**だった。したがって「element_all は
ファイル中の IfcElement 全インスタンスか、空間に到達できるものだけか」という
解釈の分岐は、この corpus では値に影響しない（下記「決まっていないと思った箇所」参照）。

**性能仕様（property_*）**
IFCPROPERTYSET の HasProperties にある IFCPROPERTYSINGLEVALUE / IFCPROPERTYENUMERATEDVALUE
のみを数え、IFCELEMENTQUANTITY 経由は性能仕様から除外した。付き先は
IFCRELDEFINESBYPROPERTIES の RelatedObjects（直接）と、IFCRELDEFINESBYTYPE が指す型の
HasPropertySets（型経由）。型経由の行の所有者は型そのものではなく**出現側の要素**とした。

- split の行キーは (ファイル, 所有者インスタンス, Pset 名, 属性名, 経路)、
  merged は (ファイル, 所有者インスタンス, Pset 名, 属性名)。
- 物理要素に限ると 308 / 306、所有者を問わないと 324 / 322。
- split の生の行数も 308 / 324 で、キーで潰しても減らない（重複行は無い）。
- merged で潰れたのは 2 件だけで、どちらも Building-Architecture（ifc4x3 と ifc4 の両方）の
  IFCSLAB に Pset_SlabCommon/FireRating が直接と型経由の両方から付いた組。
- 所有者が物理要素でない 16 行の内訳は IFCSPACE 10 / IFCZONE 3 / IFCBUILDING 3。
  324 − 308 = 16 と一致する。
- 型経由で属性を供給している型は corpus 全体で 2 件だけ（HasPropertySets が非空の
  IFC***TYPE が 2 件）で、それがそのまま上の 2 件の重複になっている。

**quantity_all**
IFCQUANTITYLENGTH/AREA/VOLUME/COUNT/WEIGHT/TIME を数えた（COUNT/WEIGHT/TIME は出現 0）。
250。この値は数え方に依存しない。ファイル中の実体数 250、付き先をたどった行数 250、
参照された相異なりインスタンス数 250 が全て一致する（IFCELEMENTQUANTITY 90 件は
それぞれちょうど 1 回だけ付いており、二重付与が無い）。IFCELEMENTQUANTITY 自体は
入れ物として数えていない。

## 読めなかった箇所

無し。全 17 ファイル・全 8,741 実体をパースでき、参照切れ（存在しない #N への参照）も
検出されなかった。IFCRELDEFINESBYPROPERTIES / IFCRELDEFINESBYTYPE が指す先も
IFCPROPERTYSET(139) と IFCELEMENTQUANTITY(90) の 2 種類だけで、
IFCPROPERTYSETDEFINITIONSET や IFCCOMPLEXPROPERTY のような扱いに迷う構造は無かった。

## 課題文が数え方を決めていないと思った箇所（3 件）

1. **element_all の母集団**。「物理要素の行数」が (a) ファイル中の IfcElement 全インスタンス
   なのか、(b) 規則で定義された 3 経路のいずれかで空間に到達できるものだけなのかを
   文面が決めていない。(a) を採ったが、**この corpus では到達できない物理要素が 0 件**なので
   両解釈とも 629 になる。差が出ないので実害は無い。
2. **element_no_adheres の「空間に繋がっていない要素」の扱い**。「付着関係でしかつながって
   いないものを除く」だけが書かれており、どの経路でも繋がっていない要素を残すのか除くのかは
   未指定。これも該当 0 件なので値に影響しない。
3. **property split の行キー**。「直接付いたものと型経由で付いたものを別の行として数える」
   とあるが、同じ (要素, Pset 名, 属性名, 経路) が複数の関係インスタンスから来た場合に
   1 行か複数行かは未指定。キーで潰す解釈を採ったが、そもそも重複が無いため
   どちらでも 308 / 324 になる。

いずれも「決まっていないが、この corpus では値が割れない」種類のもので、
T005 で問題になった性能仕様の所有者範囲のような、値が実際に割れる未指定は今回は見つからなかった。

## 気づいた点（ファイル・課題側）

- **課題文が 13 問中 4 問の答えを明示している。** `note` の
  「物理要素に限れば 308/306、所有者を問わなければ 324/322」は、そのまま
  property_owner_physical_split / _merged / property_owner_any_split / _merged の
  正解値である。今回は自分で数えた値が 4 つとも一致したので追認にしかなっていないが、
  数えずに書き写しても満点が取れる状態なので、この 4 問は腕を分離しない。
  T005 の欠陥を説明するために書かれた文だと理解しているが、記録として挙げておく。
- **同名ファイルの ifc4 版と ifc4x3 版は同じモデルの別スキーマ書き出しだが、内容は同一ではない。**
  ifc4x3 側はインフラ空間型（IFCBRIDGE 6, IFCBRIDGEPART 18, IFCROAD 5, IFCROADPART 26,
  IFCRAILWAY 2, IFCRAILWAYPART 2）を使い、ifc4 側は同じ構造を IFCSITE / IFCBUILDING /
  IFCBUILDINGSTOREY に置き換えている（IFC4 に無い実体型を無理に書いてはいない）。
  結果としてファイル対ごとに要素数も違う（例: Infra-Bridge は ifc4x3 が 50、ifc4 が 57）。
  ifc4 側にだけ Infra-Landscaping があり、ifc4x3 側には無い（17 = 8 + 9 の内訳）。
- **Infra-Road の 2 版で付着の表現が違う。** ifc4x3/Infra-Road は 20 件の IFCSURFACEFEATURE を
  IFCRELADHERESTOELEMENT 4 本で母体要素に貼り付けているが、ifc4/Infra-Road の 20 件は
  IFCRELCONTAINEDINSPATIALSTRUCTURE で空間に直接載せている（IFC4 に
  IfcRelAdheresToElement が無いため）。corpus 全体で IFCRELADHERESTOELEMENT は
  ifc4x3/Infra-Road の 4 本のみ。この 1 ファイルだけが element_no_adheres と
  element_no_feature を分離させており、他の 16 ファイルではこの 2 問は同値になる。
- IFCPROPERTYENUMERATION(5) は列挙の定義であって属性ではないので数えていない。
  IFCPROPERTYENUMERATEDVALUE(82) と IFCPROPERTYSINGLEVALUE(242) の合計 324 は
  property_owner_any_split と一致する（全ての属性実体がちょうど 1 回ずつ付いている）。

## 制約の遵守

- IFC 専用ライブラリ（ifcopenshell 等）は使用していない。Python 標準ライブラリのみ
  （re, os, collections, json）。
- 参照解・抽出器・採点器（reference/ bench/ checker/ out/ README.md arms/ docs/）は開いていない。
  リポジトリ直下の `ls` でディレクトリ名が見えたのみ。
- 過去課題 T001〜T005 の attempts/ は開いていない。
- attempts/T006/ の他の走行（armC_r2.json が存在することは `ls` で見えたが、中身は開いていない。
  armB_* および r3 は未作成）の答案・報告は読んでいない。
- 違反は無い。
