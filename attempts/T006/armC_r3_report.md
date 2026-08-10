# T006 armC_r3 報告

## 方法

自作の STEP Physical File (ISO-10303-21) パーサを Python 標準ライブラリのみで実装した。
IFC 専用ライブラリ（ifcopenshell 等）は使用していない。

- 17ファイルとも1行1インスタンス（`#N=TYPE(...);`）であることを事前に確認（`#\d+=` の総出現数 = 行頭一致行数、複数インスタンスを含む行はゼロ）。総インスタンス数 9,942。
- 引数はトップレベルのカンマで分割。文字列リテラル（`''` エスケープ）と括弧のネストを考慮。
- 出現する実体型は105種。全型を「空間構造 / 物理要素 / それ以外」に手で分類し、**どれにも入らない型を全件目視**して、products が取りこぼされていないことを確認した（残りは幾何・関係・リソース系のみ）。IFCOPENINGELEMENT / IFCANNOTATION / IFCGRID / IFCDISTRIBUTIONPORT / IFCVIRTUALELEMENT は corpus に存在しない。
- 関係実体の引数位置は生の行で目視確認した（RELCONTAINEDINSPATIALSTRUCTURE は args[4]=要素リスト・args[5]=空間、RELAGGREGATES は args[4]=親・args[5]=子、RELADHERESTOELEMENT は args[4]=母体・args[5]=付着要素、RELDEFINESBYPROPERTIES/BYTYPE は args[4]=対象リスト・args[5]=定義、型実体の HasPropertySets は args[5]）。

## 設問ごとの数え方

| 設問 | 値 | 経路 |
|---|---|---|
| spatial_all | 228 | 規則4の型集合のインスタンス数。内訳 SITE 72 / BUILDINGSTOREY 39 / BUILDING 35 / ROADPART 26 / BRIDGEPART 18 / PROJECT 17 / BRIDGE 6 / ROAD 5 / SPACE 4 / SPATIALZONE 2 / RAILWAY 2 / RAILWAYPART 2 |
| spatial_no_project | 211 | 228 − PROJECT 17 |
| spatial_depth0 | 17 | 親 = RELAGGREGATES の親 ∪ RELCONTAINEDINSPATIALSTRUCTURE の置かれ先。親なしは各ファイルの IFCPROJECT のみ |
| spatial_depth0_aggregate_only | 19 | 親を RELAGGREGATES のみに限ると、IFCSPATIALZONE 2件（ifc4x3/ifc4 の Building-Architecture、いずれも IFCBUILDING に *包含* されている）が加わる |
| element_all | 629 | IfcElement 下位型のインスタンス全件。除外は規則5どおり（型・グループ・システム・空間構造）。**3経路の内訳は完全に排他だった**: 直接包含 552 + 集約の子 57 + 付着 20 = 629。どの経路にも載らない要素はゼロなので、「全インスタンス」と「空間に所属する要素」のどちらで読んでも同値 |
| element_direct_only | 552 | RELCONTAINEDINSPATIALSTRUCTURE の RelatedElements にあり、かつ RelatingStructure が空間構造のもの。重複掲載はゼロ（同一要素が2つの包含関係に載る例なし）、非空間への包含もゼロ |
| element_no_adheres | 609 | 629 − 20。付着でしか繋がらないのは ifc4x3/Infra-Road.ifc の IFCSURFACEFEATURE 20件（IFCRELADHERESTOELEMENT 4件 × 5件ずつ、母体はいずれも IFCCOURSE） |
| element_no_feature | 589 | 629 − IFCSURFACEFEATURE 40 |
| property_owner_physical_split | 308 | IFCPROPERTYSET 内の SINGLEVALUE/ENUMERATEDVALUE を、(ファイル, 所有者, Pset名, 属性名, 経路) 単位で計上し、所有者が物理要素のものだけ |
| property_owner_physical_merged | 306 | 上を (ファイル, 所有者, Pset名, 属性名) で重複排除。減る2行は両ファイルの Building-Architecture の IFCSLAB × Pset_SlabCommon.FireRating が直接・型経由の両方から付いているもの |
| property_owner_any_split | 324 | 所有者を問わず。物理要素以外の所有者は IFCSPACE 10行 (Pset_SpaceCommon) / IFCBUILDING 3行 (Pset_BuildingCommon) / IFCZONE 3行 (Pset_ZoneCommon) の計16行 |
| property_owner_any_merged | 322 | 同上を重複排除（減るのは上記2行） |
| quantity_all | 250 | IFCQUANTITYLENGTH 88 / AREA 72 / VOLUME 90。COUNT/WEIGHT/TIME は corpus に無し |

除外したもの: IFCELEMENTQUANTITY（入れ物なので数量の行として数えない）、IFCPROPERTYENUMERATION（列挙値の定義そのもの）、IFC***TYPE 実体そのもの（性能仕様の所有者としては数えず、RELDEFINESBYTYPE 経由で実体に配った）。

## 検算・整合性

- 数量は「インスタンス総数 250」「IFCELEMENTQUANTITY に格納されている数 250」「所有者経由で数えた行 250（重複排除後も 250）」の3通りが一致。IFCELEMENTQUANTITY 90件は全て所有者ちょうど1件に付いており、未接続はゼロ。よって split/merged/インスタンス数のどれで読んでも同じで、この設問に解釈の幅は無かった。
- 性能仕様の型経由は4行だけ（HasPropertySets が空でない型実体は IFCSLABTYPE 2件のみ）。残り320行は直接。
- IFCRELDEFINESBYPROPERTIES の RelatingPropertyDefinition は全件 IFCPROPERTYSET か IFCELEMENTQUANTITY。IfcPropertySetDefinitionSet（リスト形）や IFCCOMPLEXPROPERTY は出現しなかった。

## 読めなかった箇所

無し。17ファイル全行がパースできた。文字列中に `\X\27` 等の ISO-10303-21 エスケープが出るが、Pset名・属性名の同一性判定は生テキストのまま一貫して行ったので、まとめ処理には影響しない（デコードしてもしなくても同じ組に落ちる）。

## 課題文が数え方を決めていないと思った箇所（3件）

1. **spatial_depth0 / spatial_depth0_aggregate_only に IFCPROJECT を含めるか。** 規則4は「空間構造の実体」に IFCPROJECT を含めると定義しているが、設問の文言は「空間」で、直前の設問が IFCPROJECT を除いた集合を訊いている。規則4の定義（＝IFCPROJECT を含む）を基準に取り、17 / 19 とした。もし IFCPROJECT を除く読みなら 0 / 2 になる。0 が正解になる設問は考えにくいので前者を採った。
2. **element_all が「全インスタンス」か「空間に所属する要素だけ」か。** 規則6が所属の3経路を定義しているため後者の読みもあり得る。ただし本 corpus では両者が一致する（629）ので実害は無かった。
3. **quantity_all を split（経路別）で数えるか merged で数えるか。** 設問は指定していない。本 corpus では両者とも 250 で一致するため、これも実害は無かった。

## ベンチ側の欠陥として気づいたこと

- **課題文の `note` が、性能仕様4問の参照値をそのまま書いている**（「物理要素に限れば 308/306、所有者を問わなければ 324/322」）。T005 の欠陥を説明するために書かれた文だが、結果として T006 の13問中4問の答えが課題文に印字されている。私は独立に数えた値がこの4つと一致したので採用したが、この4問は**腕の能力を測っていない**（読めば書ける）。T005 の欠陥を保存する意図は理解できるが、値そのものを伏せる（「2通りの読みがあり、値が異なる」とだけ書く）ほうが測定は保たれる。
- **corpus のファイル内矛盾**: `corpus/buildingsmart/ifc4/Infra-Road.ifc` は `FILE_SCHEMA(('IFC4'))` を宣言しているのに、IFC4 には存在しない IFCSURFACEFEATURE を20件含む（同様に IFCROADPART / IFCROAD / IFCCOURSE / IFCEARTHWORKSFILL / IFCTRACKELEMENT / IFCRAIL / IFCSIGN / IFCBRIDGE 系も ifc4/ 側の各ファイルに出現する）。つまり ifc4/ 側は IFC4X3 の実体名を残したまま IFC4 を名乗っている。ただし IFCRELADHERESTOELEMENT だけは ifc4/ 側で使われておらず、ifc4x3 で付着していた20件が ifc4 では空間への直接包含に置き換わっている。**この1点だけが ifc4/ifc4x3 で構造が異なり、element_direct_only と element_no_adheres の差を作っている。**（数え方の指示は明確なので採点上の問題ではない。corpus の性質としての記録）
- `IFCSPATIALZONE` が `IFCRELCONTAINEDINSPATIALSTRUCTURE` で `IFCBUILDING` にぶら下がっている。空間構造どうしを包含関係で繋ぐのは通常の IFC の使い方ではないが、規則がその扱いを明示しているので指示どおり親として扱った。

## 制約遵守

- 見たのは `corpus/` と `tasks/T006/task.json` のみ。`reference/` `bench/` `checker/` `out/` `README.md` `arms/` `docs/`、および `attempts/` 内の他の答案・報告は開いていない（`attempts/T006/` は `mkdir -p` のみで、一覧も表示していない）。
- `corpus/injected/` は課題の files に無いので使っていない（ディレクトリ名がルート一覧に出たのみ）。
- IFC 専用ライブラリは未使用。使ったのは Python 3 標準ライブラリ（re, glob, os, collections, json）と grep/wc のみ。
