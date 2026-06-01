#!/usr/bin/env Rscript

# Install archived SimRAD 0.96 after verifying that compiled Bioconductor
# dependencies are already present.
#
# Do not use this script to compile Biostrings/ShortRead/zlibbioc from source
# inside a minimal conda environment. Install those dependencies first:
#
#   mamba install -n radigest-simrad -c conda-forge -c bioconda -y \
#     zlib libzlib r-seqinr \
#     bioconductor-biostrings bioconductor-shortread bioconductor-zlibbioc
#
# Then run:
#
#   Rscript scripts/comparators/install_simrad_archive.R

options(repos = c(CRAN = "https://cloud.r-project.org"))

message("R version:")
print(R.version.string)
message("Library paths:")
print(.libPaths())

required <- c("seqinr", "Biostrings", "ShortRead", "zlibbioc")
available <- vapply(required, requireNamespace, logical(1), quietly = TRUE)

if (!all(available)) {
  missing <- required[!available]
  message("Missing required dependency package(s): ", paste(missing, collapse = ", "))
  message("")
  message("Install compiled dependencies with:")
  message("  mamba install -n radigest-simrad -c conda-forge -c bioconda -y \\")
  message("    zlib libzlib r-seqinr \\")
  message("    bioconductor-biostrings bioconductor-shortread bioconductor-zlibbioc")
  quit(status = 2)
}

if (requireNamespace("SimRAD", quietly = TRUE)) {
  message("SimRAD is already installed.")
  message("Installed SimRAD version: ", as.character(utils::packageVersion("SimRAD")))
  message("Session info:")
  print(sessionInfo())
  quit(status = 0)
}

simrad_url <- "https://cran.r-project.org/src/contrib/Archive/SimRAD/SimRAD_0.96.tar.gz"

message("Installing archived SimRAD from: ", simrad_url)
utils::install.packages(simrad_url, repos = NULL, type = "source")

if (!requireNamespace("SimRAD", quietly = TRUE)) {
  stop("SimRAD installation did not complete successfully.")
}

suppressPackageStartupMessages(library(SimRAD))
message("Installed SimRAD version: ", as.character(utils::packageVersion("SimRAD")))

message("Session info:")
print(sessionInfo())
