# ASMC-benchmark

A lightweight benchmarking wrapper around ASMC that runs an example and records the runtime.

---

This repository contains `asmc-benchmark.py`, which is intended to be run via the following [Azure Pipeline](https://dev.azure.com/OxfordRSE/ASMC-benchmark/_build).

The Pipeline is configured to run on an agent on the machine `rockpigeon` in the Department of Statistics, and is running via a [Singularity](https://sylabs.io/) instance.
Fergus has access to `rockpigeon`.

The Pipeline is run hourly and adds four benchmarking times to a local sql database.
An SVG graph is produced for each of the benchmarking times.
Each graph contains a single point per ASMC commit (unless multiple commits occur inside an hour), with all profiling times for a single commit being grouped and represented as a mean and standard deviation.

The database and SVG images are backed up daily via a cron job running on `rockpigeon`, which backs up to Fergus's home space on the Statistics network.

In addition, the SVG images are published as a Pipeline Artifact on each run, and are accessible through the [Azure Pipeline](https://dev.azure.com/OxfordRSE/ASMC-benchmark/_build) web interface:

- Select the relevant build
- Select the `Artifacts` dropdown in the top right
- Select `profiles`
- Download all as a `.zip`, or download an individual SVG
