# Context

The ubiquitous language of this project. Glossary only — no implementation detail, no decisions.
Decisions live in `docs/adr/`.

## Entity

A chemical compound as a member of the library, identified by `entity_id` (e.g. `vancomycin`,
`amoxicillin`). An entity is the unit the study reasons about scientifically: when the manuscript
says "compound", it means entity. Set-level statistics are counted over entities.

An entity is **not** a docking input. It becomes one only via a [State](#state).

## State

A single site-resolved protonation form of an [Entity](#entity), identified by `state_id`
(e.g. `alpha_ammonium`). A state fixes every ionisable site, so it has one definite structure and
formal charge, and is the actual thing docked.

Most entities have exactly one state. An [Ambiguous entity](#ambiguous-entity) has two.
An entity with more than one state contributes more than one docking result, which is why
entity and state must never be conflated when counting.

## Species key

The `(entity_id, state_id)` pair. Uniquely names a docked chemical form. Distinct from
[Claim](#claim), which additionally fixes the receptor and box.

## Ambiguous entity

An entity whose evidence does not establish a single dominant state at pH 7.4 — its contested
site has a pKₐ near physiological pH. The catalog marks these `tier: AMBIGUOUS`. Both plausible
states are docked and **no claim is made about their relative abundance**; the project holds no
speciation fractions even where the literature reports them.

Ambiguity is a property of the compound's chemistry, established before docking. It is never
inferred from a docking result.

## Set-level statistic

Any statistic computed over a population of entities rather than over docking rows — the
custom-versus-FDA comparison, triad-engagement counts, and the SpeB decoy population.
The defining property is one entity, one observation.

A statistic computed over rows instead of entities is **pseudo-replicated**: entities with more
than one state, receptor, or pose are counted more than once, inflating n and breaking the
independence the tests assume.

## Decoy

A compound that is property-matched to a known [Active](#active) and is not expected to bind the
target. Decoys form the null population an active must be recovered from. A decoy's only job is to
be a plausible property-matched non-binder.

Matching is on physicochemical properties — molecular weight, logP, hydrogen-bond donors and
acceptors, rotatable bonds, net charge — with topology deliberately dissimilar to the active. Size
alone is not matching; it is the weakest special case of it.

## Active

A compound with experimental evidence of binding the target in question. An active is what a
[Control](#control) asks the pipeline to recover from among the [Decoys](#decoy).

## Control

A target-plus-ligand system used to measure what the pipeline can resolve, as opposed to a
[Probe set](#probe-set) compound, which is a candidate being asked about. Controls are named by
what a failure would mean:

- A **sensitivity control** is one the pipeline is expected to pass. Failure indicates the pipeline
  is misassembled, not that the scoring function lacks resolution. Without one, every other failure
  is ambiguous.
- A **target-native control** uses an active co-crystallised with the study's own target.
- A **cross-target control** uses an active co-crystallised with a different protease, and is
  informative only to the extent that protease resembles the target.

A control is **confounded** when a property of the ligand, rather than the pipeline, predicts the
outcome. A covalent active scored by a non-covalent function is confounded in this sense: its
failure is expected behaviour and carries no information about the pipeline.

## Cognate re-docking

Docking an active into the receptor conformation its own co-complex produced, with the ligand
removed. The receptor is already shaped to the ligand, so this is the most favourable test a
docking pipeline can be given. Failure under cognate re-docking is therefore stronger evidence
than failure under cross-docking, and success under it is correspondingly weaker.

## Probe set

The curated compound collection this study interrogates the pipeline with — mechanistic chemotypes
plus approved comparators. It is a set of questions put to the scoring function, not an attempt to
sample chemical space, and its size is chosen for interpretability rather than coverage. Contrast
with a **screen**, which seeks candidates and whose size is what licenses its negative claims.

## Non-fit

A docking attempt that yielded no valid pose — either a non-negative Vina affinity (the ligand
does not fit the box) or exhaustion of the compute ceiling. A non-fit is a real, reportable
outcome, not a missing value, and never silently drops a compound from the population.

## Campaign

One complete, immutable execution of all four stages (WIDE, TIGHT, SpeB, BORON) under a single
`campaign_id`. A campaign is sealed on completion and is never appended to or rerun; a new
analysis means a new campaign with a new id.

## Claim

The unit of docking work: one [Species key](#species-key) against one receptor under one box.
The finest-grained addressable result.

Because the box is part of a claim's identity, the same species key against the same receptor under
a *different* box is a **different claim**. A result carried over from an earlier box is therefore
never the same claim as one produced under a new box rule, however identical the chemistry.

## Control run

A set of [Control](#control) claims executed together under one protocol version, for the purpose of
measuring what the pipeline can resolve.

A control run is **not** a [Campaign](#campaign). A campaign is the specific four-stage execution the
project already names; control work is a different kind of thing, asking what the pipeline can
resolve rather than producing the study's results. The two terms are kept apart so that neither
inherits the other's guarantees by accident.

## Ensemble

More than one receptor conformation over which a single [Species key](#species-key) is docked, with
the per-species result aggregated across them.

An ensemble is a property of a particular experiment, not of the project: a system docked against a
single receptor has **no** ensemble, and aggregate language ("best ensemble affinity") does not
apply to it. Where a system is single-receptor, results are reported over poses at that one
receptor and box, and must be named as such.

## Recovered

The outcome in which a [Control](#control)'s [Active](#active) ranks strictly first under the
preregistered primary endpoint for that control.

Strictly first means no [Decoy](#decoy) scores better and none ties it: a tie is not a recovery. An
active that merely ranks among the best is not recovered, and the word is never applied to a
secondary endpoint or to a rank short of first.

Which endpoint is primary, and how results combine across repeated decoy draws, are fixed by
preregistration for each control rather than by this glossary.
