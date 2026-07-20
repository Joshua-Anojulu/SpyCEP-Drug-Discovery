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

A compound in the SpeB control that is size-matched to the known inhibitor and is not expected
to bind it. Decoys form the null population the [Positive control](#positive-control) must
outrank. A decoy's only job is to be a plausible size-matched non-binder.

## Positive control

Q9D, the co-crystallised SpeB inhibitor (PDB 6UKD). The pipeline is judged by whether it
recovers Q9D from among the decoys. It does not.

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
