# T007 armB2_r1 報告

## 進め方

ファイル1本あたり10万トークン級（行数は392〜1497行だが幾何行が極端に長い）で、
17本を1つの文脈に載せられない。そこで**1ファイル1体の下請け**を立て、
各体には「集計」ではなく**素材の転記**だけをさせた。転記させたのは
(a) 全エンティティ型名のヒストグラム、(b) 全 IfcProduct の `#id 型名`、
(c) IFC***TYPE の `HasPropertySets`、(d) RelAggregates / RelContainedInSpatialStructure /
RelAdheresToElement / RelDefinesByProperties / RelDefinesByType の引数、
(e) PropertySet・Property・ElementQuantity・Quantity の id と名前、(f) 異常。
**13問の計算は17本ぶん親（この走行）が一人で行った。**下請けごとに数え方が
ぶれるのを避けるため。ヒストグラムは「PRODUCTS 一覧に落ちがないか」の検算に使った
（型別件数の和と一覧の件数が一致するかを17本すべてで確認した）。

## 各設問をどう数えたか

共通の前処理。製品を2つに分けた。
- **空間**＝IFCPROJECT ＋ IfcSpatialElement 下位型（本コーパスに実在したのは
  SITE / BUILDING / BUILDINGSTOREY / SPACE / SPATIALZONE / BRIDGE / BRIDGEPART /
  ROAD / ROADPART / RAILWAY / RAILWAYPART）。
- **物理要素**＝残りの IfcElement 下位型。除外したのは規則どおり
  IFCZONE（2件）・IFCDISTRIBUTIONSYSTEM（1件）・全 IFC***TYPE・空間。
  IFCANNOTATION / IFCGRID / IFCDISTRIBUTIONPORT / アライメント系は
  **17本のどのヒストグラムにも1件も現れなかった**ので除外は空振り。
  IFCEARTHWORKSFILL・IFCSURFACEFEATURE・IFCCOURSE・IFCRAIL・IFCTRACKELEMENT・
  IFCSIGN・IFCGEOGRAPHICELEMENT・IFCELEMENTASSEMBLY・IFCMEMBER は物理要素に入れた。

1. **spatial_all 228** 上の空間の実数。17本とも IFCPROJECT はちょうど1件。
2. **spatial_no_project 211** ＝ 228 − 17。
3. **spatial_depth0 17** 空間のうち、IfcRelAggregates の RelatedObjects にも
   IfcRelContainedInSpatialStructure の RelatedElements にも現れないもの。
   結果は各ファイルの IFCPROJECT 1件のみ。
4. **spatial_depth0_aggregate_only 19** 親を集約だけで決めた場合。
   差の2は Building-Architecture の ifc4x3 版 #385 と ifc4 版 #448 の IFCSPATIALZONE で、
   どちらも集約木に載っておらず、IFCRELCONTAINEDINSPATIALSTRUCTURE の
   RelatedElements に**空間なのに**入っている。**この2件だけがQ3とQ4を分けている。**
5. **element_all 629** 物理要素の実数。集約の親・部品・付着要素を全部1行で数えた。
6. **element_direct_only 552** RelContainedInSpatialStructure の RelatedElements に
   現れる物理要素。同リストに混ざっていた空間（上の SPATIALZONE 2件）は除いた。
   落ちる77件の内訳は、集約の部品57件（屋根の下のスラブ、橋のピア組立の下の柱・基礎、
   ランドスケープの組立の下の部材・プロキシ）と、付着のみの20件。
7. **element_no_adheres 609** ＝ 629 − 20。付着でしか空間に繋がっていない20件は
   **ifc4x3/Infra-Road の IFCSURFACEFEATURE 20件のみ**（4本の
   IFCRELADHERESTOELEMENT が母体1つにつき5件を貼っている）。その20件は
   RelContained のどのリストにも出てこず、集約の子でもない。
   母体4件（#167 #326 #636 #789 の IFCCOURSE）は直接収容されているので残る。
   IFCRELADHERESTOELEMENT はこの1ファイルにしか存在しなかった。
8. **element_no_feature 589** ＝ 629 − 40。IFCSURFACEFEATURE は
   ifc4x3/Infra-Road に20件、ifc4/Infra-Road に20件。
9. **property_owner_physical_split 308** IFCRELDEFINESBYPROPERTIES の
   RelatingPropertyDefinition が IFCPROPERTYSET のときだけ、その中の
   IFCPROPERTYSINGLEVALUE / IFCPROPERTYENUMERATEDVALUE を
   (対象オブジェクト × 属性) で1行。加えて IFCRELDEFINESBYTYPE の指す型の
   HasPropertySets ぶんを別行。所有者が物理要素のものだけ。
   RelatingPropertyDefinition が IFCELEMENTQUANTITY のものは除外した。
10. **property_owner_physical_merged 306** (ファイル, 要素, Pset名, 属性名) で潰した。
    潰れたのは2行だけ。Building-Architecture の両版で、同じスラブに
    直接 `Pset_SlabCommon` と 型経由 `Pset_SlabCommon` が付き、双方に
    `FireRating` がある（値は REI30 と REI60 で**違う**が、指定された鍵に値は入って
    いないので1行にまとめた）。
11. **property_owner_any_split 324** 所有者を問わない。物理でない所有者は16行で、
    内訳は ifc4/Building-Hvac の IFCBUILDING 1、ifc4/Building-Architecture の
    IFCBUILDING 1・IFCZONE 3・IFCSPACE 5・IFCSPACE 5、ifc4/Building-Structural の
    IFCBUILDING 1。
12. **property_owner_any_merged 322** 上と同じ2件が潰れる。
13. **quantity_all 250** IFCQUANTITYLENGTH / AREA / VOLUME の実数（COUNT / WEIGHT /
    TIME は17本とも0件）。IFCELEMENTQUANTITY は入れ物として除外。

## 下請けの体数と待ち

- **17体**（1ファイル1体）。ただし同時実行の上限に当たり、初回投入17件のうち
  4件が `Concurrent subagent limit reached` で起動できず、空きが出るたびに
  4回に分けて追い出した（最後の1本＝ifc4/Infra-Road が起動できたのは開始から
  かなり後）。
- 待ちは大きかった。最短の1体が約7分、最長が**約21分**（ifc4/Infra-Landscaping、
  ツール呼び出し159回）。全17体が揃うまで、こちらの体感で**40分以上**。
  起動できなかった4体ぶんの待ち直しがそのまま尻に足された。
- 親のツール呼び出しは概算で35回前後（task.json の読み 2、サイズ探りの Read 15、
  Agent 起動 23（うち失敗6）、Write/Edit 7、確認 Read 2）。
  下請け側の合計ツール呼び出しは17体で1000回超。

## 読めなかった箇所

**全17本とも最終行まで到達した。**ただし**単一行が Read の25000トークン上限を
超えて物理的に読めない行**が7本のファイルに合計62行あった。

| ファイル | 未読行数 |
|---|---|
| ifc4x3/Building-Hvac | 2 |
| ifc4x3/Infra-Bridge | 8 |
| ifc4x3/Infra-Road | 2 |
| ifc4/Infra-Bridge | 8 |
| ifc4/Infra-Landscaping | 38 |
| ifc4/Infra-Plumbing | 2 |
| ifc4/Infra-Rail | 2 |
| ifc4/Infra-Road | 2 |

いずれも「行番号 = #id + 7」が全域で成り立つファイルなので、未読行に載っている
#id は確定できる。そしてどの未読 id も、直後の `IFCSTYLEDITEM(#id,...)` と
`IFCSHAPEREPRESENTATION(...,'Tessellation',(#id))` から参照されているので、
**IFCTRIANGULATEDFACESET とその IFCCARTESIANPOINTLIST3D** である。
幾何なので13問の集計には効かない。ただし**これは推定であって実読ではない。**
未読行に製品や関係が隠れていた場合、13問すべてがずれうる。
（1行142,905トークンという行が ifc4x3/Infra-Bridge と ifc4/Infra-Bridge に存在した。）

## 課題文が数え方を決めていないと思った箇所

1. **spatial_depth0 の母集合に IFCPROJECT が入るか。**
   Q1 が「IFCPROJECT を含め」、Q2 が「同上から IFCPROJECT を除いた」と
   わざわざ書き分けているのに、Q3 は「親を持たない空間」としか言わない。
   Q3 は「同上」で前問を引き継いでもいない。**入れる方に決めた。**
   規則の「空間構造の実体とは IFCPROJECT / … を指す」を定義として採り、
   Q3 の「空間」をその定義語の略と読んだ。
   **もし外す読みが正解なら Q3=0、Q4=2 になる。**17と19ではなく0と2。
   落とし穴の位置が真逆になるので、ここは是非はっきりさせてほしい。
   （0という答えは設問として不自然なので入れる方を採ったが、根拠は文面ではなく
   「その方が問いとして意味がある」という推測でしかない。）

2. **element_no_adheres の「付着関係でしか空間に繋がっていない」の外周。**
   どの経路でも空間に繋がっていない要素（孤児）は、
   「付着でしか繋がっていない」に当たるのか当たらないのか。
   **当たらない＝残す**方に決めた。本コーパスには孤児の物理要素が1件も無かったので
   結果は変わらないが、文面では決まっていない。

3. **quantity_all の「行数」が何の行か。**
   他の性能仕様の設問が (所有者 × 属性) の行を数えているので、数量も
   (所有者 × 数量) の行を数えるのが自然にも読める。一方
   「数量（IfcQuantity*）の行数」だけならエンティティの実数とも読める。
   **両方を計算したところ、17本すべてで一致した**（どの IFCELEMENTQUANTITY も
   ちょうど1本の IFCRELDEFINESBYPROPERTIES から1つの対象に付き、
   IFCQUANTITY* が共有されている例が無かった）。よってここは無害。
   ただし**無害だったのは偶然で、課題文が決めているからではない。**

4. **性能仕様の「同じ属性」の同一性に値が入らない。**
   Q10 / Q12 の鍵は (ファイル, 要素, Pset名, 属性名) で、**値は鍵に入っていない。**
   Building-Architecture の両版では、まさにその鍵で
   `FireRating = REI30`（直接）と `FireRating = REI60`（型経由）が1行に潰れる。
   文面どおりに潰したが、これは「性能仕様の行数」として意味を持つのか疑わしい。
   **指定が明示的なので従ったが、指定の側が壊れている可能性がある**と見ている。

5. **IfcElement 下位型の判定を課題文が渡していない。**
   「物理要素とは IfcElement の下位型を指す」とあり、除外リストは挙がっているが、
   採用リストは無い。IFCEARTHWORKSFILL / IFCCOURSE / IFCTRACKELEMENT /
   IFCSIGN / IFCGEOGRAPHICELEMENT のような型は、規格を知らないと判定できない。
   「規格の解釈は問わない」と note にあるが、**実際には規格の継承関係を知らないと
   element_all は出せない。**note と設問が食い違っている。
   （IFCALIGNMENT 系など、IfcProduct だが IfcElement ではない型が本当に
   1件も無かったのは幸運で、あれば同じ落とし穴が開いていた。）

## 課題文・指示の側の欠陥

6. **「Read だけ使える」という前提と、Read の実挙動が噛み合っていない。**
   指示は「探す手段は無い。読むしかない」と書いているが、
   `offset` だけ指定して `limit` を省いた Read は、このコーパスでは
   「File content exceeds maximum」で**1行も返さない**。
   `limit` を必ず添えて手探りでページを進める必要がある。
   さらに上のとおり、**`limit=1` でも読めない行が62行ある。**
   つまり「Read だけ」という条件では、**このコーパスは原理的に全読できない。**
   armB の設計上の条件だと明記されているので不備とは呼ばないが、
   「読めば必ず全部見える」は成立していない、という事実は記録しておく。

7. **下請けの同時実行上限（20）が課題側から見えない。**
   17体を一度に投げると4体が弾かれる（他に走っている体があるらしく、
   13体しか通らなかった）。弾かれた体は静かに落ちるので、
   投げっぱなしにすると**4ファイルぶん無言で欠測する。**
   起動結果を1件ずつ確認しないと気づけない。

## ファイルの内部矛盾（下請けが挙げたもののうち、集計に効きうるもの）

- **同じ基底名でもスキーマ版で中身が違う。**ifc4x3/Infra-Bridge には
  IFCPROPERTYSET が1件も無いのに、ifc4/Infra-Bridge には21件ある
  （Status のみ）。ifc4x3/Building-Architecture のプロパティは
  ifc4/Building-Architecture より大幅に少ない（Pset_SpaceCommon /
  Pset_WallCommon 等が丸ごと欠けている）。**同じシーンの版違いではなく、
  出力内容そのものが違う。**「両方を別のファイルとして数える」という規則は
  正しいが、両者は対照実験になっていない。
- **同じ Infra-Road でも、ifc4x3 版は IFCSURFACEFEATURE を
  IFCRELADHERESTOELEMENT で母体に貼っているのに、ifc4 版は同じ20件を
  IFCRELCONTAINEDINSPATIALSTRUCTURE で空間に直接収容している。**
  ここが element_direct_only と element_no_adheres の版間差の唯一の源。
- IFCPROPERTYENUMERATION の Name に Ruby の inspect 文字列
  `'#<BimTools::IfcManager::Types::IfcLabel:0x000001cc...>'` が
  メモリアドレスごと漏れている（ifc4/Infra-Bridge、ifc4/Infra-Road、
  ifc4/Infra-Landscaping、ifc4/Building-Architecture）。再出力すると値が変わる。
- ifc4/Infra-Landscaping の `SizeSet` の `Volume` が
  `IFCPOSITIVELENGTHMEASURE` で入っている（48件）。体積に長さ計測型。
- 中身の無い空間が複数（ifc4x3/Infra-Road #576、ifc4/Infra-Rail #23/#30/#723 ほか）。
  子も収容要素も持たない IFCSITE。Description が別の場所からのコピペで
  名前と食い違っている例も複数（'road - site' の説明が駐車場）。
- 部品を持たない IFCELEMENTASSEMBLY が複数ファイルにある
  （ifc4x3/Infra-Bridge #850/#857、ifc4/Infra-Road #821/#828 ほか）。
  「集約の親」として数えたが、実際には何も集約していない。

## 制約違反

**無し。**親も下請けも Read 以外の読み取り道具を使っていない。
Bash / シェル / Python / awk / sed / grep / スクリプトの作成と実行は
一切していない（Monitor ツールはシェルコマンドを要するため使わなかった）。
Write は答案・報告・作業メモの書き出しにのみ使った。
`reference/` `bench/` `checker/` `out/` `README.md` `arms/` `docs/` は開いていない。
`tasks/` は `tasks/T007/task.json` のみ。`attempts/T007/` は
本走行の2ファイルを書いただけで、他の走行の答案・報告は開いていない。
下請け17体すべてが「Read のみ・禁止ディレクトリ未オープン・違反なし」を自己申告した。
作業用の一時ファイルは
`/private/tmp/claude-501/-Users-boss-dev-01-projects/826e8fde-631a-4aed-a5c1-124ba794daae/scratchpad/T007_armB2_r1/`
のみに置いた。
