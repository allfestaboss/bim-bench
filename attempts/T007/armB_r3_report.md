# T007 armB_r3 — 報告

## 0. この走行の道具立て（測定条件として重要）

- **Grep も Glob もこのセッションには存在しなかった。** 課題文は「Read / Grep / Glob を使え」と
  書いているが、実際に呼ぶと `No such tool available: Grep. ... search file contents with
  grep via the Bash tool instead.` が返る。Bash は課題側で禁止されているので、
  **実質 Read だけで解いた。**
- 17ファイルは1ファイルあたり10万〜32万トークンあり、親のコンテキストには入らない。
  そこで**下請けエージェントを17体**立て、1体1ファイルで読ませた（下請けにも
  「Read のみ、Bash・スクリプト・他ファイル禁止」を明示した）。
- 同時実行上限が20体だったため、17体は3回に分けて起動した。
- **下請けの中継が壊れた。** 1体（ifc4/Infra-Landscaping）の最終報告は末尾の
  NOTES 節（注5〜12）しか親に届かず、データ本体（A〜N節）が欠落した。
  再送を依頼した SendMessage と、別途出した検算4件の応答は**いずれも親に戻らなかった**。
  運用側から「宛先が見つからないで失敗し、出力が運用側の通知へ流れた」と連絡を受けた。
  → 待機を打ち切り、**ifc4/Infra-Landscaping は親が自分の Read だけで読み直した。**
- そのため ifc4/Infra-Landscaping だけは他16ファイルと読み方が違う（下記4節）。

## 1. 設問ごとの数え方

対象は全17ファイル。各ファイルの値を出して合計した。

### spatial_all = 227
`#N=IFCTYPE(` の TYPE が
IFCPROJECT / IFCSITE / IFCBUILDING / IFCBUILDINGSTOREY / IFCSPACE / IFCSPATIALZONE /
IFCFACILITY / IFCFACILITYPART / IFCBRIDGE / IFCBRIDGEPART / IFCROAD / IFCROADPART /
IFCRAILWAY / IFCRAILWAYPART のインスタンス行を数えた。
実際に corpus に出たのは PROJECT / SITE / BUILDING / BUILDINGSTOREY / SPACE /
SPATIALZONE / BRIDGE / BRIDGEPART / ROAD / ROADPART / RAILWAY / RAILWAYPART の12種。
IFCMARINEFACILITY / IFCMARINEPART / IFCEXTERNALSPATIALELEMENT は出現しなかった。

### spatial_no_project = 210
上記から IFCPROJECT を除いた。IFCPROJECT は17ファイルに各1個ちょうど（227 − 17 = 210）。

### spatial_depth0 = 17
親を「IFCRELAGGREGATES の RelatedObjects に出ること」**または**
「IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements に出ること」で判定し、
どちらでも親を持たない空間を数えた。**結果は全17ファイルで IFCPROJECT ただ1個ずつ。**

### spatial_depth0_aggregate_only = 19
親を IFCRELAGGREGATES のみで判定した。差が出たのは2ファイルだけ:
- ifc4x3/Building-Architecture の `#385 IFCSPATIALZONE`
- ifc4/Building-Architecture の `#448 IFCSPATIALZONE`
この2つは集約されておらず、**IFCRELCONTAINEDINSPATIALSTRUCTURE で IFCBUILDING の
下に「載って」いるだけ**なので、集約のみだと深さ0に浮く。17 + 2 = 19。

### element_all = 628
IfcElement の下位型のインスタンス行。除外したのは課題文どおり
IFC***TYPE / IFCANNOTATION / IFCGRID / IFCDISTRIBUTIONPORT / IFCZONE / IFCGROUP /
IFCSYSTEM / IFCDISTRIBUTIONSYSTEM と、空間構造の実体すべて。
**IFCSPATIALZONE が IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements に
混じって出てくる箇所があるが、空間なので物理要素には数えていない**
（ifc4x3 と ifc4 の Building-Architecture 各1個）。
集約の親・部品・付着要素はすべて1行として数えた。
**全17ファイルで、物理要素は3経路のいずれかに必ず載っていた**（どこにも繋がっていない
孤児要素はゼロ）。したがって「全 IfcElement インスタンス」と「3経路で到達できる要素」は
一致し、この設問に解釈の分岐は生じなかった。

### element_direct_only = 551
IFCRELCONTAINEDINSPATIALSTRUCTURE の RelatedElements に直接現れる物理要素のみ。
差が出たのは、屋根の下に集約されたスラブ（Building-Architecture 2本）、
要素アセンブリの部品（Building-Structural 2本、ifc4/Infra-Bridge、ifc4/Infra-Landscaping）、
ifc4x3/Infra-Road の付着要素20個。

### element_no_adheres = 608
IFCRELADHERESTOELEMENT でしか空間に繋がっていない要素を除いた。
**該当したのは ifc4x3/Infra-Road の IFCSURFACEFEATURE 20個だけ**（55 − 20 = 35）。
IFCRELADHERESTOELEMENT は IFC4.3 で追加された関係なので、
ifc4/ 側の9ファイルには構文上そもそも存在しない。628 − 20 = 608。

### element_no_feature = 588
IFCSURFACEFEATURE を除いた。出現したのは2ファイル:
ifc4x3/Infra-Road に20個、ifc4/Infra-Road に20個。628 − 40 = 588。
**ifc4x3 側では付着（20個）と表面フィーチャ（20個）が同じ集合だが、
ifc4 側では表面フィーチャ20個が直接 IFCRELCONTAINEDINSPATIALSTRUCTURE に
載っている**ため、この2問の答えは一致しない。ここは意図的な分離点だと思う。

### property_owner_physical_split = 308 / merged = 306
IFCPROPERTYSET の HasProperties のうち **IFCPROPERTYSINGLEVALUE と
IFCPROPERTYENUMERATEDVALUE だけ**を数えた（IFCELEMENTQUANTITY は除外）。
2経路:
- 直接 = IFCRELDEFINESBYPROPERTIES の RelatedObjects × その Pset の属性数
- 型経由 = IFCRELDEFINESBYTYPE の RelatedObjects × RelatingType の HasPropertySets の属性数
所有者が**物理要素であるものだけ**を残した。
merged は (ファイル, 要素, Pset名, 属性名) で1行にまとめた。
**差が出たのは2ファイルのみ**:
- ifc4x3/Building-Architecture: `#49 IFCSLAB` に直接4属性（IsExternal, LoadBearing,
  FireRating=REI30, AcousticRating）＋型経由2属性（FireRating=REI60,
  SurfaceSpreadOfFlame）。FireRating が両経路で重なるので split 6 → merged 5。
- ifc4/Building-Architecture: 同じ `Pset_SlabCommon` の重なりで split 28 → merged 27。
つまり **308 − 306 = 2** は、この2ファイルの FireRating 1件ずつだけ。

### property_owner_any_split = 324 / merged = 322
所有者の種類を問わず数えた。物理要素以外の所有者は次だけだった:
- ifc4/Building-Architecture: `#30 IFCBUILDING` に1、`#80 IFCZONE` に3、
  `#89 IFCSPACE` に5、`#203 IFCSPACE` に5 → 計14
- ifc4/Building-Hvac: `#30 IFCBUILDING` に1
- ifc4/Building-Structural: `#30 IFCBUILDING` に1
308 + 16 = 324、306 + 16 = 322。
非物理の所有者側には両経路の重複がないので、split と merged の差は物理側と同じ2のまま。

### quantity_all = 250
IFCQUANTITYLENGTH / AREA / VOLUME / COUNT / WEIGHT / TIME のインスタンス行。
IFCELEMENTQUANTITY（入れ物）は数えていない。出たのは LENGTH / AREA / VOLUME のみで、
COUNT / WEIGHT / TIME はゼロ。
**この設問は数え方が2通りありうる**（下記2節）が、
本 corpus では**どの IFCELEMENTQUANTITY もちょうど1個の所有者にしか付いていない**ため、
「生のインスタンス行数」と「所有者×数量の行数」が全ファイルで一致した。
つまり解釈による差は出ない。250はどちらの読みでも同じ。

## 2. 課題文が数え方を決めていないと思った箇所

1. **quantity_all の「行数」が、数量インスタンスの数なのか
   (所有者 × 数量) の組の数なのか書かれていない。**
   性能仕様のほうは split / merged と明示的に2問に割られているのに、数量は1問しかなく、
   「所有者の種類を問わず」としか言っていない。今回はたまたま両者が一致したので
   採点に影響しないが、Pset を複数要素で共有する corpus に替えた瞬間に割れる。
   → 一致することを確認したうえで250を提出した。

2. **element_all が「全 IfcElement インスタンス」なのか
   「3経路で空間に到達できる要素」なのかが決まっていない。**
   規則(67)は所属の経路を3つ定義しているが、設問文は「物理要素の行数」としか言わない。
   今回は孤児要素がゼロだったので両者一致。
   → 一致することを確認したうえで628を提出した。
   なお IFCOPENINGELEMENT / IFCVOIDINGFEATURE の類は corpus に1つも無く、
   IFCRELVOIDSELEMENT もゼロだったので、この論点は今回は顕在化しなかった。

3. **spatial_depth0 / spatial_depth0_aggregate_only に IFCPROJECT を含めるのか
   明示がない。** 規則(65)が IFCPROJECT を空間構造の実体に含めており、
   設問2だけが明示的に除外している。よって深さ0の2問には**含める**と決めた。
   除外していたら両方0になり、設問として成立しないので、含める読みが正しいはず。

4. **「空間構造の実体」の infra 型の列挙が「等」で閉じられている。**
   IFCMARINEFACILITY / IFCMARINEPART / IFCEXTERNALSPATIALELEMENT を含めるのか
   文面からは決まらない。今回は corpus に1つも出現しなかったので影響なし。

5. **性能仕様として数える属性型が IFCPROPERTYSINGLEVALUE と
   IFCPROPERTYENUMERATEDVALUE の2つに限定されているが、
   IFCCOMPLEXPROPERTY の入れ子をどう扱うかは書かれていない。**
   corpus には出現しなかったので影響なし。

## 3. 課題文・指示の側の欠陥だと思った箇所

1. **課題文が指定する道具（Grep / Glob）が実行環境に無い。**
   これは「読んで数える腕」と「コード実行する腕」を比較するベンチなので、
   使える道具の集合がずれていると腕の比較が成立しない。
   armB は事実上「Read のみ」で走った。他走行が Grep を使えていたなら、
   同じ armB でも道具立てが違うことになる。**測定条件として記録すべき差だと思う。**

2. **下請けの中継が壊れており、待ちが発生した。**
   1体の最終報告が末尾しか届かず、再送依頼と検算4件の応答が親に戻らなかった。
   結果として ifc4/Infra-Landscaping は親が読み直す羽目になった。
   これは課題文の欠陥ではなく実行基盤の欠陥だが、**下請けを使う戦略の実測コストに
   直結する**ので記録しておく。

3. **`note` が T006 の欠陥を説明する文の中で、今回の corpus の性質をかなり具体的に
   述べている。** 「性能仕様が付く先の範囲を課題文が決めていなかったこと」と
   明かしているので、性能仕様の2問（physical / any）が**所有者の種類で割れる**ことが
   設問を読む前から分かる。数値そのものは漏れていないので T006 のような致命傷では
   ないが、**どこに罠があるかのヒントにはなっている。**

4. **`grade_levels` に `"Q10"` とあるが、設問は13問ある。** 対応が読み取れない。

5. Read ツールの1回あたり25000トークン上限のせいで、
   **単独で25000トークンを超える行は原理的に読めない。**
   corpus には1行12万トークン級の IFCTRIANGULATEDFACESET / IFCCARTESIANPOINTLIST3D が
   多数ある。今回は全て幾何データで、13問の答えには一切効かないが、
   **「Read だけで数える」腕には物理的な死角がある**ことは記録に値する。

## 4. 読めなかった箇所と、その理由

- 上記5のとおり、各ファイルに単独で25000トークンを超える行が存在する
  （例: ifc4x3/Infra-Bridge に8行、ifc4/Infra-Bridge に8行、
  ifc4/Building-Landscaping に8行、ifc4/Infra-Plumbing に2行、
  ifc4/Infra-Landscaping に多数）。
  いずれも IFCTRIANGULATEDFACESET と IFCCARTESIANPOINTLIST3D のペアで、
  前後の行からの参照（IFCSTYLEDITEM の第1引数、IFCSHAPEREPRESENTATION の Items）と
  id の連番性から型を確定した。**13問のどれにも寄与しない型なので、答えには影響しない。**
- ifc4/Infra-Landscaping は親が読み直したが、行番号 = id + 7 が全域で成立し
  （#1 が8行目、#1488 が1495行目、ENDSEC が1496行目）、
  id に欠番・重複が無いことを利用して、**関係・空間・要素・属性の行だけを
  アンカー読みで拾った。**幾何行は意図的に開いていない。
  そのため「全行を目で見た」とは言えない。到達性は id の連番性で担保している。

## 5. ファイル内部の矛盾・気づいた点

- **ifc4x3 系と ifc4 系で同名ファイルの中身が体系的に違う。**
  「同じモデルを2版で書いた」ものではない。特に:
  - Infra-Bridge: ifc4x3 は橋脚を IFCBRIDGEPART（空間）で表し、
    ifc4 は IFCELEMENTASSEMBLY（物理要素）で表す。
    このため spatial_all が 28 対 21、element_all が 50 対 57 と逆転する。
  - Infra-Road: ifc4x3 は表面フィーチャを IFCRELADHERESTOELEMENT で貼り、
    ifc4 は同じ20個を直接 IFCRELCONTAINEDINSPATIALSTRUCTURE に載せる。
  - 性能仕様は ifc4 側に集中しており、ifc4x3 側はほぼ空（Building-Architecture の
    2 Pset を除く）。一方 IFCELEMENTQUANTITY は
    Building-Architecture(25)、Building-Structural(34)、Infra-Bridge(27) で
    両版が完全に一致する。
- **ifc4/Infra-Landscaping の「りんご」48個に付く `SizeSet` の属性名が
  `Volume` と `Height` で、値型が `IFCPOSITIVELENGTHMEASURE`。**
  名前は数量に見えるが実体は IFCPROPERTYSINGLEVALUE なので、
  quantity_all には数えず property 側に数えた。ここは引っかけだと思う。
  （同ファイルの IFCELEMENTQUANTITY / IFCQUANTITY* は本当にゼロ。）
- ifc4/Infra-Bridge の `#329 IFCPROPERTYENUMERATION` の Name が
  `'#<BimTools::IfcManager::Types::IfcLabel:0x000001cc59b6e668>'` という
  Ruby のオブジェクト inspect 文字列。オーサリングツールの漏れ。
  ifc4/Infra-Landscaping の `#799` も同じ症状。
- ifc4x3/Building-Architecture は**インスタンス行が id 順に並んでいない**
  （#961/#962/#970/#980/#800/#801 がファイル冒頭付近に前倒しされている）。
  他の16ファイルは行番号 = id + 7 が厳密に成立する。
  この1ファイルだけ並びが崩されているのは、**id 順を仮定して外挿する解法を
  落とすための仕掛け**だと思う。
- ifc4/Infra-Landscaping の `#1032 IFCBUILDINGELEMENTPROXY 'Group#16'` は
  SketchUp のグループが配置の親としてだけ残ったもので、
  子の木 `#1042` とは IFCRELAGGREGATES で繋がっていない（両方とも同じ
  IFCRELCONTAINEDINSPATIALSTRUCTURE `#944` に平置き）。
  集約で親子を辿ると取りこぼす形になっている。
- ifc4x3/Infra-Bridge の `#43`/`#103` は名前が 'road rail bridge - approach' だが
  実際は 'road river bridge'(#36) の配下。ソースデータの命名ミス。
- 複数ファイルで `IFCLOCALPLACEMENT` の個数が `IFCAXIS2PLACEMENT3D` より1多い。
  最後の geo-reference が原点配置 `#7` を使い回しているため。

## 6. ファイル別内訳（合計の検算用）

順: spatial_all / no_project / depth0 / depth0_agg / elem_all / elem_direct /
elem_no_adh / elem_no_feat / prop_phys_split / prop_phys_merged /
prop_any_split / prop_any_merged / quantity

```
ifc4x3 Building-Architecture   8   7  1  2 |  15  13  15  15 |   6   5   6   5 | 25
ifc4x3 Building-Hvac           5   4  1  1 |   6   6   6   6 |   0   0   0   0 |  0
ifc4x3 Building-Landscaping    3   2  1  1 |   7   7   7   7 |   0   0   0   0 |  0
ifc4x3 Building-Structural     5   4  1  1 |  18  10  18  18 |   0   0   0   0 | 34
ifc4x3 Infra-Bridge           28  27  1  1 |  50  50  50  50 |   0   0   0   0 | 27
ifc4x3 Infra-Plumbing         10   9  1  1 |  29  29  29  29 |   0   0   0   0 |  0
ifc4x3 Infra-Rail             11  10  1  1 |  75  75  75  75 |   0   0   0   0 |  0
ifc4x3 Infra-Road             38  37  1  1 |  55  35  35  35 |   0   0   0   0 |  0
ifc4   Building-Architecture   8   7  1  2 |  15  13  15  15 |  28  27  42  41 | 25
ifc4   Building-Hvac           5   4  1  1 |   6   6   6   6 |   0   0   1   1 |  0
ifc4   Building-Landscaping    3   2  1  1 |   7   7   7   7 |   0   0   0   0 |  0
ifc4   Building-Structural     5   4  1  1 |  18  10  18  18 |  31  31  32  32 | 34
ifc4   Infra-Bridge           21  20  1  1 |  57  40  57  57 |  21  21  21  21 | 27
ifc4   Infra-Landscaping      18  17  1  1 | 111  91 111 111 | 126 126 126 126 |  0
ifc4   Infra-Plumbing         10   9  1  1 |  29  29  29  29 |   0   0   0   0 |  0
ifc4   Infra-Rail             11  10  1  1 |  75  75  75  75 |   0   0   0   0 |  0
ifc4   Infra-Road             38  37  1  1 |  55  55  55  35 |  96  96  96  96 | 78
-------------------------------------------------------------------------------
合計                         227 210 17 19 | 628 551 608 588 | 308 306 324 322 |250
```

## 7. 信頼度の低い箇所（自己申告）

- **ifc4x3/Infra-Road の性能仕様0件・数量0件**は再確認を依頼したが、
  中継が壊れて応答が戻らなかった。ifc4 側の同名ファイルが Pset 32個・
  IFCELEMENTQUANTITY 26個（数量78）を持つのに対し、ifc4x3 側が両方ゼロという
  非対称になっている。性能仕様の非対称は他ファイルにも一貫してあるので妥当だが、
  **数量が両版で一致しないのはこのファイルだけ**なので、ここだけ確度が落ちる。
  誤りだった場合に動くのは quantity_all のみ（他12問には影響しない）。
- 同様に ifc4x3/Building-Structural と ifc4x3/Building-Hvac の Pset ゼロも
  再確認の応答が戻っていない。誤りだった場合は性能仕様の4問が動く。
- ifc4/Infra-Landscaping は親のアンカー読みなので、幾何行の隙間に
  関係行が紛れていた場合に取りこぼす可能性がある。
  ただし id の連番性と、7つの IFCRELCONTAINEDINSPATIALSTRUCTURE・
  16の IFCRELAGGREGATES が互いに整合していること
  （91直接 + 20部品 = 111、10アセンブリ × 2部品）で相互検算はできている。

## 8. 制約違反

- **なし。** Bash・スクリプト・Python 等は一切実行していない。
  Grep / Glob はセッションに存在しなかったため使えていない。
  ファイルは Read のみで読んだ。下請けにも同じ制約を明示し、
  応答を返した全12体が「Read のみを使った」と自己申告している。
- 禁止ディレクトリ（reference/ bench/ checker/ out/ arms/ docs/ README.md）、
  過去課題（T001〜T006）、attempts/T007 の他走行（armB_r1 / armB_r2 / armC_*）は
  一切開いていない。
- 一時ファイルは
  `/private/tmp/claude-501/-Users-boss-dev-01-projects/826e8fde-631a-4aed-a5c1-124ba794daae/scratchpad/T007_armB_r3/perfile.md`
  のみ。
