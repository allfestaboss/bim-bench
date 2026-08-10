# T007 armB2_r3 — report

## The binding constraint, and the trick that got around it

Read-only, no code. The corpus is 10,095 lines but **6.78M tokens** — nearly all of it in a
few dozen monster geometry lines (single lines of 100k-143k tokens). Reading it linearly is
impossible for any context window.

The lever: **a Read that exceeds the 25,000-token cap fails, the failure is free, and the
failure message states the exact token count of the range requested.** So `Read(offset=1,
limit=k)` is a free ruler: it returns P(k) = tokens of lines 1..k whenever that prefix is
over the cap. Given P(x) and P(y) the block x+1..y costs exactly P(y)-P(x) — measurable
without reading it. Build a prefix table by free probes, read only the cheap blocks, bisect
the expensive ones until the giant lines are isolated, then never read them.

Net effect: ~6.78M tokens of file reduced to roughly 2M tokens actually read across all
workers, and the ~70 giant geometry lines were never loaded by anyone. Every giant line was
confirmed to be IFCTRIANGULATEDFACESET / IFCCARTESIANPOINTLIST3D by its neighbours
(IFCSTYLEDITEM / IFCSHAPEREPRESENTATION pointing at its id), so nothing countable was lost —
but note that this is inference from context, not observation; see "could not read" below.

## How each question was counted

Common extraction per file: spatial entities, IfcElement instances, IFCRELAGGREGATES,
IFCRELCONTAINEDINSPATIALSTRUCTURE, IFCRELADHERESTOELEMENT, IFCRELDEFINESBYPROPERTIES,
IFCRELDEFINESBYTYPE, IFCPROPERTYSET + members, IFCELEMENTQUANTITY + members, and every
IFC*TYPE line (needed for HasPropertySets, which is attribute 6).

- **spatial_all / spatial_no_project** — IFCPROJECT, IFCSITE, IFCBUILDING, IFCBUILDINGSTOREY,
  IFCSPACE, IFCSPATIALZONE, plus the 4.3 infra types actually present: IFCBRIDGE,
  IFCBRIDGEPART, IFCROAD, IFCROADPART, IFCRAILWAY, IFCRAILWAYPART. 228 total, one IFCPROJECT
  per file, so 211.
- **spatial_depth0** — parent via IFCRELAGGREGATES *or* IFCRELCONTAINEDINSPATIALSTRUCTURE.
  Exactly one parentless spatial per file (the IFCPROJECT) → 17.
- **spatial_depth0_aggregate_only** — 19. The extra 2 are the IFCSPATIALZONE in each
  Building-Architecture: they sit in an IFCRELCONTAINEDINSPATIALSTRUCTURE (4x3 #385 in #335,
  ifc4 #448 in #387) but in no IFCRELAGGREGATES, so dropping containment orphans them. This
  pair is the *only* thing separating the two questions.
- **element_all** — IfcElement subtypes; excluded IFCZONE, IFCGROUP, IFCSYSTEM,
  IFCDISTRIBUTIONSYSTEM, all IFC*TYPE, and all spatial entities per the rules. Counted
  aggregate parents, aggregate parts and adhering features alike.
- **element_direct_only** — 552. The 77 excluded are: roof-slab children under IFCROOF (2+2),
  roof girders/shoes under IFCROOF (8+8), 17 pier parts under IFCELEMENTASSEMBLY in
  ifc4/Infra-Bridge, 20 marker posts/signs under IFCELEMENTASSEMBLY in ifc4/Infra-Landscaping,
  and the 20 adhering surface features in ifc4x3/Infra-Road.
- **element_no_adheres** — 609. Only ifc4x3/Infra-Road has IFCRELADHERESTOELEMENT (4 relations
  x 5 features); those 20 reach a space by no other path, so only they are removed.
- **element_no_feature** — 589. IFCSURFACEFEATURE appears in both Infra-Road files, 20 each.
- **property_owner_physical_split / _merged** — rows are (file, owner, pset name, property
  name), IFCPROPERTYSINGLEVALUE + IFCPROPERTYENUMERATEDVALUE only. IFCPROPERTYENUMERATION was
  **not** counted (it is the enumeration definition, not a property). Merged differs from split
  in exactly one place: ifc4x3 and ifc4 Building-Architecture both attach 'Pset_SlabCommon' to
  the same IFCSLAB twice — directly and via IFCSLABTYPE #47/#50's HasPropertySets — and
  'FireRating' occurs on both paths, so 6→5 and 28→27.
- **property_owner_any_*** — adds owners that are not physical elements: IFCBUILDING
  (Pset_BuildingCommon), IFCZONE (Pset_ZoneCommon), IFCSPACE x2 (Pset_SpaceCommon), all in
  the ifc4 Building files.
- **quantity_all** — (owner, quantity) rows for IFCQUANTITYLENGTH/AREA/VOLUME/COUNT/WEIGHT/TIME,
  IFCELEMENTQUANTITY not counted. In this corpus every IFCELEMENTQUANTITY is attached by exactly
  one IFCRELDEFINESBYPROPERTIES with exactly one RelatedObject, so row-count and entity-count
  coincide and the ambiguity below never bites.

## Subcontractors and waiting

**23 agents in total.** 1 size-probe agent, 21 transcription agents, 1 replacement. They ran in
waves: the harness reported "concurrent subagent limit reached" repeatedly even while claiming a
limit of 20 — I only ever got 5-8 to start at once, so launching took 5 rounds. Individual agents
took 78s to 772s. Longest single wait about 13 minutes; total wall time dominated by the tail.
Splits used: ifc4x3/Infra-Bridge and ifc4/Infra-Bridge in 2 ranges each, ifc4/Infra-Landscaping in
3. Split boundaries were verified by me directly (lines 480/481 and 1000/1001 read by hand).

I did ifc4x3/Building-Hvac myself, and I independently re-read a block of
ifc4x3/Building-Architecture (lines 54-65) to check one agent's fidelity — it matched character
for character.

## Things that went wrong

- **One agent's answer was truncated in transit.** The ifc4/Infra-Road worker reported
  `COVERAGE: lines 1-1195` but only lines 873-1195 actually reached me; the first 872 lines were
  cut off. This is a real hazard of this design: the coverage claim survived, the data did not.
  I recovered by (a) resuming that agent with a request for a compact re-emission, (b) launching
  an independent replacement, and (c) reconstructing lines 1-872 myself with ~35 targeted small
  reads. My own reconstruction completed first and is what the answer uses. Both agents were
  still running when I finished.
- Two agents quoted IFCRELASSOCIATESMATERIAL verbatim despite it being on my "boring" list.
  Harmless.

## Could not read

Two distinct categories, and I conflated them at first — the distinction matters:

1. **Genuinely unreadable.** Some single lines exceed the 25,000-token cap and cannot be opened
   at any granularity; the largest measured is ~143,000 tokens. These are concentrated in the
   Landscaping files (706k tokens over 167 lines) and the Bridge files. Their sizes are known
   exactly from free probes, and their identity as tessellation / point-list geometry is
   established by the entities that reference them (each is the argument of the immediately
   following IFCSTYLEDITEM and of an IFCSHAPEREPRESENTATION), but **none was ever opened.**
   If a countable entity were hiding on one, no arm under this constraint could see it. I judge
   the risk near zero because the id sequence is gapless and every referencing entity is
   accounted for — but it is an assumption, not an observation.
2. **Skipped by choice, not necessity.** Many lines recorded as unread were merely expensive,
   not impossible. The independent ifc4/Infra-Road worker measured its whole assigned range and
   found that **no line in 1-872 exceeds the cap at all** — the largest is 12,797 tokens. The 34
   lines it skipped there were a cost decision. Same for most of what the other workers skipped.

So the honest statement is: the corpus contains a few dozen truly unopenable geometry lines, and
a larger number that were skipped to save budget. Both were verified to be geometry only by
reference structure, never by reading.

## Cross-check on the one file that had a transit failure

Because ifc4/Infra-Road lost its first 872 lines in transit, that file ended up counted **twice
by independent routes** — once by my own hand-reconstruction (~35 targeted reads) and once by a
replacement worker that had never seen my work. The two agree exactly on every figure that feeds
an answer: 38 spatial (1 project + 6 sites + 11 IFCBUILDING + 20 IFCBUILDINGSTOREY), 55 elements
(32 IFCSLAB + 20 IFCSURFACEFEATURE + 2 IFCELEMENTASSEMBLY + 1 IFCBUILDINGELEMENTPROXY), all 55
directly contained, no IFCRELADHERESTOELEMENT present, 32 psets x 3 properties = 96 property
rows, and 26 of the 32 slabs carrying Qto_SlabBaseQuantities x 3 = 78 quantity rows. The six
slabs with no quantities are the "asphalt surface course" instances #222, #459, #669, #791,
#877, #1064 — note that the two *parking* surface courses (#86, #364) do have quantities, so the
omission is not a clean rule, which is exactly the kind of thing a plausible-looking guess would
get wrong.

This is the only file with an independent second count. The other sixteen rest on a single
transcription each, plus my own spot-check of ifc4x3/Building-Architecture.

## Where I think the task statement does not decide the counting

1. **"数量（IfcQuantity*）の行数" — entity or row?** The property questions explicitly define a
   row as an (owner, property) pair and explicitly split by path; quantity_all says only "count
   them all, regardless of owner kind". I counted (owner, quantity) pairs to match the property
   convention. In this corpus the two readings give the same number, so the answer is safe — but
   the wording alone does not decide it, and on a corpus where one IFCELEMENTQUANTITY is shared
   by several elements the two readings would diverge.
2. **quantity_all and the type path.** The property rules spell out both paths (direct and via
   IFCRELDEFINESBYTYPE). The quantity rule does not say whether type-borne IFCELEMENTQUANTITY
   counts. No type in this corpus carries a quantity set, so it does not matter here.
3. **"深さ0" and containment for spatial entities.** IfcRelContainedInSpatialStructure normally
   relates *elements* to a spatial structure, not spatial to spatial. The task tells me to treat
   a space placed under another by containment as a child, which is what makes spatial_depth0 and
   spatial_depth0_aggregate_only different questions — but it relies on a schema-irregular usage
   that only occurs twice in the whole corpus.
4. **IFCPROPERTYENUMERATION.** The rule names IFCPROPERTYSINGLEVALUE and
   IFCPROPERTYENUMERATEDVALUE. IFCPROPERTYENUMERATION sits right next to the enumerated values
   in these files and is *not* a member of any pset, so excluding it is clearly right — but the
   rule never mentions it, and a careless extractor would sweep it in.

## Internal inconsistencies in the corpus itself

The task's rule "同じ基底名のファイルが2つのスキーマ版に存在する。両方を別のファイルとして数える"
implies the pairs are the same model in two schemas. They are not, and the differences are large
enough to dominate several answers:

- **ifc4 files carry Pset_*Common sets that their ifc4x3 twins simply lack.**
  Building-Architecture 6 vs 42 property rows; Building-Structural 0 vs 32; Infra-Road 0 vs 96;
  Infra-Bridge 0 vs 21. Over half of `property_owner_any_split` comes from ifc4-only content.
- **ifc4x3 uses real infrastructure types where ifc4 falls back to buildings.**
  IFCBRIDGE/IFCBRIDGEPART → IFCBUILDING/IFCBUILDINGSTOREY; IFCROAD/IFCROADPART → same;
  IFCRAILWAY/IFCRAILWAYPART → same; IFCRAIL/IFCTRACKELEMENT/IFCCOURSE → IFCBUILDINGELEMENTPROXY;
  IFCEARTHWORKSFILL/IFCCOURSE → IFCSLAB.
- **That fallback moves entities across the spatial/physical line.** In ifc4x3/Infra-Bridge the
  three piers are IFCBRIDGEPART (spatial); in ifc4/Infra-Bridge the same piers are
  IFCELEMENTASSEMBLY (physical), with their columns/footings/beams aggregated under them instead
  of directly contained. Hence 28 spatial / 50 elements / 50 direct versus 21 / 57 / 40 for
  what is nominally the same bridge.
- **The line markings are attached by different mechanisms.** ifc4x3/Infra-Road uses
  IFCRELADHERESTOELEMENT (4.3-only); ifc4/Infra-Road puts the same 20 IFCSURFACEFEATURE straight
  into IFCRELCONTAINEDINSPATIALSTRUCTURE. So `element_no_adheres` loses 20 from one file and 0
  from its twin, while `element_no_feature` loses 20 from each.
- **ifc4/Infra-Road has Qto_SlabBaseQuantities (78 rows) where ifc4x3/Infra-Road has none.**
- **ifc4/Building-Hvac gives IFCBUILDING a Pset_BuildingCommon; ifc4x3/Building-Hvac does not.**
- Smaller: PredefinedType enums differ (.BEAM. vs .USERDEFINED., .VEGETATION. vs .USERDEFINED.),
  and ifc4 IFCSPACE/IFCSPACETYPE carry LongName where ifc4x3 leaves it $.

None of this makes the questions unanswerable — the rules are mechanical and I applied them as
written. But anyone reading the totals as "the same scene counted twice" would be wrong: the two
halves of the corpus are materially different models.
