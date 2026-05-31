# Claims and limits

This repository supports the benchmarking and empirical analyses for the
associated radigest manuscript. It is organized to separate matched quantitative
comparisons from qualitative scope comparisons.

## Supported claim tiers

### Tier 1: synthetic digest correctness

Synthetic FASTA records and expected intervals validate digest semantics,
coordinate conventions, size bounds, ambiguous motifs, terminal-fragment
handling where supported, and GFF3 coordinate conversion.

### Tier 2: matched coordinate-level digest comparisons

Digital_RADs.py and DDRADSEQTOOLS `rsitesearch.py` are compared only after
normalizing their outputs to zero-based half-open cut-coordinate intervals.

### Tier 3: count-level comparisons

SimRAD is used as a count-level comparator where digest and size-selection
semantics overlap. It is not treated as a coordinate-level comparator.

### Tier 4: screening throughput and runtime/memory

Runtime, memory, and screening throughput are measured under documented
conditions. Claims should use medians and Q1-Q3 intervals. Do not claim linear
scaling unless the measured speedup supports it.

### Tier 5: empirical recovery modelling

Observed TLEN distributions from aligned empirical ddRAD datasets are used to
fit empirical fragment-size recovery profiles. These profiles can be applied
back to coordinate-resolved radigest fragment sets.

## Explicit non-claims

radigest is not:

- a read simulator;
- a PCR simulator;
- an adapter simulator;
- a SNP caller;
- a population-genetic simulator;
- a full downstream RADseq analysis pipeline;
- a complete replacement for interactive design tools such as ddgRADer.

## Interpretation of empirical recovery models

The fitted recovery curve is an empirical profile for an analysed alignment set.
It may reflect size selection, short-fragment representation, PCR, sequencing,
mapping, and filtering. It should not be interpreted as a pure laboratory
size-selection probability.

## Interpretation of comparator results

Comparator results are valid only for shared digest-level functionality.
Broader simulation, SNP-yield prediction, adapter/PCR modelling, read overlap,
and downstream genotyping are qualitative scope differences unless explicitly
benchmarked.
