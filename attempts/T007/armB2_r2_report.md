# T007 armB2_r2 report

## Answers

| question | value |
|---|---|
| spatial_all | 228 |
| spatial_no_project | 211 |
| spatial_depth0 | 17 |
| spatial_depth0_aggregate_only | 19 |
| element_all | 629 |
| element_direct_only | 552 |
| element_no_adheres | 609 |
| element_no_feature | 589 |
| property_owner_physical_split | 308 |
| property_owner_physical_merged | 306 |
| property_owner_any_split | 324 |
| property_owner_any_merged | 322 |
| quantity_all | 250 |

All 13 answered. No question left blank.

## Per-file table

S = spatial (all / no-project / depth0 / depth0-aggregate-only),
E = element (all / direct-only / no-adheres / no-feature),
P = property (phys-split / phys-merged / any-split / any-merged), Q = quantity.

| file | lines | S1 | S2 | S3 | S4 | E1 | E2 | E3 | E4 | P1 | P2 | P3 | P4 | Q |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ifc4x3/Building-Architecture | 392 | 8 | 7 | 1 | 2 | 15 | 13 | 15 | 15 | 6 | 5 | 6 | 5 | 25 |
| ifc4x3/Building-Hvac | 162 | 5 | 4 | 1 | 1 | 6 | 6 | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| ifc4x3/Building-Landscaping | 167 | 3 | 2 | 1 | 1 | 7 | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| ifc4x3/Building-Structural | 359 | 5 | 4 | 1 | 1 | 18 | 10 | 18 | 18 | 0 | 0 | 0 | 0 | 34 |
| ifc4x3/Infra-Bridge | 892 | 28 | 27 | 1 | 1 | 50 | 50 | 50 | 50 | 0 | 0 | 0 | 0 | 27 |
| ifc4x3/Infra-Plumbing | 449 | 10 | 9 | 1 | 1 | 29 | 29 | 29 | 29 | 0 | 0 | 0 | 0 | 0 |
| ifc4x3/Infra-Rail | 737 | 11 | 10 | 1 | 1 | 75 | 75 | 75 | 75 | 0 | 0 | 0 | 0 | 0 |
| ifc4x3/Infra-Road | 896 | 38 | 37 | 1 | 1 | 55 | 35 | 35 | 35 | 0 | 0 | 0 | 0 | 0 |
| ifc4/Building-Architecture | 453 | 8 | 7 | 1 | 2 | 15 | 13 | 15 | 15 | 28 | 27 | 42 | 41 | 25 |
| ifc4/Building-Hvac | 165 | 5 | 4 | 1 | 1 | 6 | 6 | 6 | 6 | 0 | 0 | 1 | 1 | 0 |
| ifc4/Building-Landscaping | 167 | 3 | 2 | 1 | 1 | 7 | 7 | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| ifc4/Building-Structural | 416 | 5 | 4 | 1 | 1 | 18 | 10 | 18 | 18 | 31 | 31 | 32 | 32 | 34 |
| ifc4/Infra-Bridge | 962 | 21 | 20 | 1 | 1 | 57 | 40 | 57 | 57 | 21 | 21 | 21 | 21 | 27 |
| ifc4/Infra-Landscaping | 1497 | 19 | 18 | 1 | 1 | 112 | 92 | 112 | 112 | 126 | 126 | 126 | 126 | 0 |
| ifc4/Infra-Plumbing | 449 | 10 | 9 | 1 | 1 | 29 | 29 | 29 | 29 | 0 | 0 | 0 | 0 | 0 |
| ifc4/Infra-Rail | 737 | 11 | 10 | 1 | 1 | 75 | 75 | 75 | 75 | 0 | 0 | 0 | 0 | 0 |
| ifc4/Infra-Road | 1195 | 38 | 37 | 1 | 1 | 55 | 55 | 55 | 35 | 96 | 96 | 96 | 96 | 78 |
| **total** | | **228** | **211** | **17** | **19** | **629** | **552** | **609** | **589** | **308** | **306** | **324** | **322** | **250** |

## How each question was counted, and what was excluded

**spatial_all / spatial_no_project.** Counted instances of IFCPROJECT, IFCSITE,
IFCBUILDING, IFCBUILDINGSTOREY, IFCSPACE, IFCSPATIALZONE, IFCBRIDGE, IFCBRIDGEPART,
IFCROAD, IFCROADPART, IFCRAILWAY, IFCRAILWAYPART. Those twelve are the only spatial
types that actually occur; there is no IFCFACILITY / IFCFACILITYPART, no
IFCMARINEFACILITY / IFCMARINEPART, no IFCEXTERNALSPATIALELEMENT anywhere in the 17
files, so the open-ended "等" in the rule never had to be resolved. Exactly one
IFCPROJECT per file, hence spatial_no_project = spatial_all - 17.

**spatial_depth0.** A spatial instance has a parent if it appears in RelatedObjects
of any IFCRELAGGREGATES **or** in RelatedElements of any
IFCRELCONTAINEDINSPATIALSTRUCTURE. Only the 17 IFCPROJECTs are parentless.
IFCPROJECT was kept in scope: the rules put it inside "空間構造の実体", the question
does not exclude it, and the brief says not to carry over Q2's scope.

**spatial_depth0_aggregate_only.** Parent only via IFCRELAGGREGATES. This adds 2:
the IFCSPATIALZONE in each Building-Architecture file (ifc4x3 #385, ifc4 #448) is
placed into a spatial structure by an IFCRELCONTAINEDINSPATIALSTRUCTURE, never by an
aggregation. That pair of instances is the only thing separating Q3 from Q4 in the
whole corpus.

**element_all.** Every instance of an IfcElement subtype. Excluded: all spatial types
above, IFCZONE, IFCGROUP, IFCSYSTEM, IFCDISTRIBUTIONSYSTEM, every name ending in TYPE,
IFCANNOTATION, IFCGRID, IFCDISTRIBUTIONPORT, IFCPROXY, IFCPROJECTEDCRS /
IFCMAPCONVERSION, IFCPROPERTYENUMERATION. Included as elements: IFCSURFACEFEATURE,
IFCEARTHWORKSFILL, IFCCOURSE, IFCTRACKELEMENT, IFCRAIL, IFCSIGN,
IFCGEOGRAPHICELEMENT, IFCELEMENTASSEMBLY, IFCDISCRETEACCESSORY,
IFCBUILDINGELEMENTPROXY, plus the ordinary building and MEP types.
No IFCALIGNMENT / IFCALIGNMENTSEGMENT / IFCREFERENT and no IfcStructural* item occurs
in any file, so those exclusion calls never bit either.

**element_direct_only.** Element appears in RelatedElements of some
IFCRELCONTAINEDINSPATIALSTRUCTURE. The 77-element gap against element_all comes from
three places: roofs aggregating slabs/beams/accessories (both Building-Architecture
and both Building-Structural files), pier assemblies in ifc4/Infra-Bridge (17), the
"highway location marker" assemblies in ifc4/Infra-Landscaping (20), and the 20
IFCSURFACEFEATUREs in ifc4x3/Infra-Road that hang off IFCRELADHERESTOELEMENT.

**element_no_adheres.** element_all minus elements whose only route to a space is
IFCRELADHERESTOELEMENT. Only ifc4x3/Infra-Road has that relation at all (4 instances,
20 related surface features), so 629 - 20 = 609.

**element_no_feature.** element_all minus IFCSURFACEFEATURE. There are 40 of them,
20 in ifc4x3/Infra-Road and 20 in ifc4/Infra-Road, so 629 - 40 = 589.

**property_owner_\*.** Rows = (owner, property) pairs built two ways: (a) every
IFCRELDEFINESBYPROPERTIES whose RelatingPropertyDefinition is an IFCPROPERTYSET,
crossed with each IFCPROPERTYSINGLEVALUE / IFCPROPERTYENUMERATEDVALUE it holds;
(b) every IFCRELDEFINESBYTYPE, crossed with the properties in the relating type's
HasPropertySets. IFCELEMENTQUANTITY targets were excluded from (a). merged =
dedupe on (file, owner instance, pset Name, property Name).
Two structural facts dominate these four numbers:
- Only **two** IFC***TYPE instances in the entire corpus have a non-empty
  HasPropertySets: the IfcSlabType in each Building-Architecture file, each pointing
  at a 2-property 'Pset_SlabCommon'. Every other type object (roughly 130 of them)
  has `$` there. So the type route contributes 4 rows corpus-wide.
- Those same 4 rows are the only source of split/merged divergence: 'FireRating'
  appears both on the occurrence Pset and on the type Pset, both named
  'Pset_SlabCommon', on the same slab. Hence split - merged = 2 for both the
  physical and the any variant.
Non-physical owners contribute 16 rows: IfcBuilding in ifc4/Building-Architecture (1),
IfcZone there (3), two IfcSpaces there (5+5), IfcBuilding in ifc4/Building-Hvac (1),
IfcBuilding in ifc4/Building-Structural (1). That is exactly any_split - phys_split
= 324 - 308 = 16 and any_merged - phys_merged = 322 - 306 = 16.
No IFCCOMPLEXPROPERTY exists anywhere. No property set is shared between owners.

**quantity_all.** IFCQUANTITYVOLUME / LENGTH / AREA instances; IFCELEMENTQUANTITY not
counted. No IFCQUANTITYCOUNT, WEIGHT, TIME or NUMBER occurs. Only 4 files carry
quantities: both Building-Architecture (25 each), both Building-Structural (34 each),
both Infra-Bridge (27 each), ifc4/Infra-Road (78).

## Subagents and waiting

17 subagents, one per file, each restricted to Read only and to its single file.
The concurrency cap meant they went out in three rounds (5 started, then 5 more, then
the rest); launching all 17 took three attempts because the "20 concurrent" cap was
already partly consumed.

Runtimes: the fastest returned in about 2 minutes, most in 4-10 minutes, and the last
one (ifc4/Infra-Landscaping, the 1497-line file) returned **22.4 minutes** after it
was launched. I did not abort it; while waiting I re-verified finished files by hand.
Total wall clock from first launch to last result was roughly 35 minutes.

## What could not be read, and why

Every subagent hit the same wall: single lines of tessellated geometry that exceed the
Read tool's ~25000-token cap even at `limit 1`. Typical files had one such pair
(an IFCTRIANGULATEDFACESET plus its IFCCARTESIANPOINTLIST3D); ifc4/Infra-Landscaping
had 61 such lines. In every case the entity ids behind those lines were pinned exactly,
because these files are strictly one entity per line with contiguous ids
(line = id + 7 in most files), and because the following IFCSTYLEDITEM and
IFCSHAPEREPRESENTATION lines name the skipped id and label it 'Tessellation'.
So the skipped lines are provably geometry and cannot hide a product, relationship,
property or quantity. Nothing else went unread.

## Where the task statement does not decide the counting

1. **element_all (Q5) has two readings.** The rules define 物理要素 by *type*
   ("IfcElement の下位型"), but the neighbouring rule enumerates three membership
   routes, and Q5's clarifier ("集約の親も部品も、付着している要素も") lists exactly
   those routes. So Q5 could mean "every IfcElement subtype instance" or "every
   IfcElement subtype instance that reaches a space by one of the three routes".
   I chose the type-based reading. **This turned out to be moot**: every subagent
   independently reported that no element in any file fails to reach a space, so the
   two readings coincide at 629. If the corpus had contained an unattached
   IFCOPENINGELEMENT the ambiguity would have been live; it contains none.

2. **quantity_all (Q13) says "行数" without saying what a row is** - a quantity
   instance, or an (owner, quantity) pair. The rule "数量が付く先は所有者の種類を問わず
   全て数える" hints at pairs. Also moot: in all 17 files each IFCELEMENTQUANTITY is
   referenced by exactly one relationship with exactly one RelatedObject, so the two
   readings agree at 250.

3. **spatial_depth0 (Q3): what "包含関係" means.** I read it as
   IFCRELCONTAINEDINSPATIALSTRUCTURE with a spatial element in RelatedElements. The
   alternative (only IfcRelReferencedInSpatialStructure, or only spatial-to-spatial
   containment) would give the same 17 here, because the only affected instances are
   the two IfcSpatialZones and both are in an ordinary containment relation.

4. **Q3 and IFCPROJECT.** Q3 says "空間" where Q1 said "空間構造の実体を全て". Since
   the rules explicitly place IFCPROJECT inside 空間構造の実体, and the brief says the
   scope does not carry over from Q2, I counted IFCPROJECT. If the intended answer
   excludes it, Q3 would be 0 and Q4 would be 2. This is the single largest
   remaining risk in my submission.

## Defects I think are in the task statement / instructions

- The rules list the IFC4.3 infra spatial types with a trailing "等" (etc.). An
  open-ended type list is not a definition; had the corpus contained IFCFACILITYPART
  or IFCEXTERNALSPATIALELEMENT the answer would depend on how far "等" reaches. It
  happens not to, so the defect is latent rather than active here.
- The rules describe the three membership routes as if they were the definition of
  which elements count, but Q5 asks for "物理要素の行数" and the type-based definition
  of 物理要素 sits in a different rule. Two rules that would be equivalent on this
  corpus are stated as if they were one. See ambiguity 1 above.
- Q13 is the only question whose unit ("行") is never defined for the entity in
  question. Every other question either names a relationship path or a type set.

## File-internal contradictions found

1. **ifc4/Infra-Road declares `FILE_SCHEMA(('IFC4'))` on line 5 yet contains 20
   IFCSURFACEFEATURE instances** (e.g. line 269, `#262=IFCSURFACEFEATURE(...)`).
   IfcSurfaceFeature was introduced in IFC4X3 and does not exist in IFC4. I confirmed
   both lines myself. This matters because Q8 is the one question that names
   IFCSURFACEFEATURE explicitly, and half of the 40 instances live in a file whose
   declared schema does not have that entity.
2. In ifc4/Infra-Road the 20 line markings are attached to a storey by
   IFCRELCONTAINEDINSPATIALSTRUCTURE, while in ifc4x3/Infra-Road the same 20 markings
   adhere via IFCRELADHERESTOELEMENT. Same scene, two incompatible modellings. This is
   what makes element_direct_only and element_no_adheres differ between the twins
   (35 vs 55) while element_all and element_no_feature agree (55 and 35).
3. Several IFC4 files carry a leaked Ruby object string as the Name of their
   IFCPROPERTYENUMERATION, e.g.
   `'#<BimTools::IfcManager::Types::IfcLabel:0x000001cc1a1a45b8>'`
   in ifc4/Building-Structural and ifc4/Infra-Road. Exporter artefact; no effect on
   counts, but it means Pset names are not all clean.
4. In ifc4x3/Building-Architecture the slab #49 carries FireRating = 'REI30' from its
   occurrence Pset and FireRating = 'REI60' from its type Pset, both under the name
   'Pset_SlabCommon'. The merged count collapses two contradictory values into one row.
   Same in the ifc4 twin.
5. ifc4x3/Infra-Rail: site #723 is named 'road - site' but carries the description of
   'road parking - site' ("A designated parking area..."), a copy/paste artefact.
   ifc4/Infra-Landscaping repeats the same description on its 'road - site' #1324.
6. Several files have "grouping" IFCBUILDINGELEMENTPROXY instances (SketchUp groups)
   that are the *placement* parent of another element but have no IFCRELAGGREGATES to
   it; both end up as siblings in the same containment. Placement nesting was not
   treated as aggregation. Noted in ifc4x3/Building-Structural (#144 vs #154),
   ifc4/Building-Architecture (#345 vs #353), ifc4/Infra-Landscaping (#1032 vs #1042).
7. Several IFCELEMENTASSEMBLY instances aggregate nothing and have no geometry
   (ifc4x3/Infra-Rail #695/#702, ifc4/Infra-Bridge #920/#927, ifc4/Infra-Plumbing all
   four). They are still IfcElement subtypes and were counted.
8. ifc4/Infra-Road puts a tessellated Representation on twelve IFCBUILDINGSTOREY
   instances. Unusual for a spatial element, but they stay spatial.
9. The corpus is asymmetric: ifc4 has 9 files, ifc4x3 has 8. Infra-Landscaping exists
   only in the ifc4 set, so it is the one file with no twin to cross-check against.

## Cross-checks that gave me confidence

The two schema versions of the same scene must describe the same objects, and they do:

- **Infra-Bridge**: spatial 28 (4x3) vs 21 (4), elements 50 vs 57. The 7 pier
  assemblies are IFCBRIDGEPART (spatial) in 4x3 and IFCELEMENTASSEMBLY (element) in 4.
  The two deltas are exactly +/-7.
- **Infra-Rail**: spatial 11 = 11, elements 75 = 75. IfcRailway/IfcRailwayPart become
  IfcBuilding/IfcBuildingStorey; IfcTrackElement/IfcRail/IfcCourse become
  IfcBuildingElementProxy. Counts unchanged.
- **Infra-Road**: spatial 38 = 38 (5 IfcRoad + 26 IfcRoadPart = 31 vs 11 IfcBuilding +
  20 IfcBuildingStorey = 31), elements 55 = 55, no-feature 35 = 35.
- **Infra-Plumbing**: 10 = 10 and 29 = 29; 3 IfcBridge become 3 IfcBuilding.
- **Property deltas match line-count deltas.** Building-Hvac: 162 vs 165 lines, +3 =
  one property + one Pset + one rel, and indeed the ifc4 file has exactly 1 property
  row and the ifc4x3 file 0. Building-Architecture: 392 vs 453, +61, matching 11 extra
  Psets + 34 extra property values + 11 extra rels + 5 misc. Building-Structural:
  359 vs 416, +57 = 12 Psets + 32 properties + 12 rels + 1 enumeration.

I also re-read parts of five finished files myself to check the subagents rather than
trusting them: I reconstructed ifc4/Building-Architecture's property arithmetic
independently (12 direct Psets totalling 40 properties, plus 2 from the type route =
42 = any_split; minus 14 non-physical rows = 28 = phys_split; one FireRating collision
gives 27/41), and confirmed EOF line numbers, the Pset_SlabCommon pair, the
IfcSpatialZone containment, the IfcRelAdheresToElement in ifc4x3/Infra-Road, and the
Pset_SlabCommon shape in ifc4/Infra-Road. All matched.

## Constraint compliance

No code was executed. No Bash, no Grep, no Glob, no scripts, no Python/awk/sed, by me
or by any subagent. Every number in this submission came from reading the corpus files
with the Read tool. Subagents were told the same restriction explicitly and each one
reported working by reading only; one of them noted it used the Read tool's error
message (which states the token count of a requested slice) to locate oversized lines
without opening them, which is still Read-only.

I did not open reference/, bench/, checker/, out/, README.md, arms/, docs/, any other
task under tasks/, or any other file under attempts/T007/. Temporary notes were kept
only in the scratchpad path assigned to this run.

**One deviation to declare:** while waiting on the last subagent I read parts of
ifc4/Infra-Landscaping myself (header, the 8 IFCSITE lines, IFCBUILDING #1342, and the
EOF), which overlapped with the subagent that was still working on it. That is not a
constraint violation, only a duplication of effort; the subagent's numbers, not mine,
are what is reported for that file, and my probes agreed with its site list.
