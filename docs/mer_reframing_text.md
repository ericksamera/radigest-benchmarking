# MER reframing text: abstract and honeysuckle design-space figure

## Recommended title

**radigest: a coordinate-resolved, target-driven design framework for reduced-representation sequencing**

## Succinct revised abstract

Reference genomes are increasingly available for ecological and evolutionary systems, but population-scale whole-genome sequencing remains unnecessary or cost-prohibitive for many studies. Reduced-representation sequencing therefore requires a constrained design choice: enzyme pairs and size selection must recover enough of the genome for inference while preserving sufficient depth across the intended sample number and sequencing budget. We present **radigest**, an open-source command-line toolkit for coordinate-resolved, target-driven design of reduced-representation sequencing libraries.

radigest identifies restriction cut sites in reference FASTA files, enumerates single- and double-digest fragments as exact genomic intervals, applies hard or weighted size-recovery models, and ranks candidate enzyme pairs against user-specified targets for recovered genome fraction and expected mean read-pair depth. Unlike read simulators, population-genetic simulators, downstream genotyping pipelines, or primarily interactive design tools, radigest provides a scriptable design layer that preserves predicted loci as BED/GFF/FASTA-exportable intervals for annotation, inspection, benchmarking, and post-sequencing validation.

We evaluated radigest using synthetic coordinate tests, comparisons with existing RAD design tools, broad enzyme-pair screening benchmarks, and empirical ddRAD datasets from *Oncorhynchus*, *Anopheles*, and *Rhododendron*. radigest passed all predefined coordinate-validation cases and showed exact interval agreement with coordinate-capable comparators after normalization. Empirical insert-size distributions were broader than strict hard-window predictions, while weighted recovery models better approximated observed recovery. In a honeysuckle design example, a 2% recovered-genome target was infeasible under the specified sample number, read layout, sequencing budget, and depth criterion; reducing the target to 1.5% produced feasible enzyme-pair designs.

radigest provides a reproducible framework for evaluating the trade-off among genome recovery, sequencing budget, sample number, and expected depth before library construction, while retaining predicted restriction fragments as auditable genomic intervals for downstream validation.

## Suggested Results section heading

**4.3. Target-driven screening identifies feasible and infeasible regions of the RRS design space**

## Suggested Figure 2 caption

**Figure 2. Target-driven honeysuckle enzyme-pair screening in recovery-depth design space.** Each point represents one of 435 enzyme pairs screened from the 30-enzyme panel on the honeysuckle GCA_021464415.1 reference under a 200–500 bp genomic insert window, paired-end 300 bp reads, 20 samples, a 50 million read-pair budget, soft-window size weighting, and a 60× target mean read-pair depth. The x-axis shows predicted weighted genome recovery and the y-axis shows expected mean read-pair depth per locus. Dashed horizontal lines mark the depth target, dotted vertical lines mark the requested recovered-genome target, and shaded boxes mark the feasible design region within ±0.25 percentage points of the target and above the depth threshold. The 2% target produced no feasible designs, whereas reducing the target to 1.5% moved the design into a feasible region with 14 enzyme pairs meeting both recovery and depth criteria.

## Suggested short insertion after the current honeysuckle paragraph

Visualizing all screened enzyme pairs in recovery-depth space clarifies why the 2% target failed and why the 1.5% target succeeded. The 2% screen placed the target region in a part of the design space where enzyme pairs approaching the requested genome recovery generally fell below the 60× depth criterion. In contrast, lowering the target recovered-genome fraction shifted the feasible region toward designs with sufficient expected depth, yielding 14 candidate pairs that met both criteria. This framing treats enzyme-pair choice as a constrained design problem rather than a search for the largest fragment set.
