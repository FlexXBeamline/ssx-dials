# `ssx-dials`
Process serial oscillation crystallography data from CHESS beamline ID7B2

## Introduction

Serial crystallography data at id7b2 is collected using small oscillations per crystal, typically 1-5 degrees. The detector images from all of these sweeps are collected in a single h5 file (ending in master.h5) that includes metadata for the scan. However, there is not a good way to specify that a multi-crystal data dataset was collected, so a conventional processing program would interpret this file as a single sweep of continuous rotation data. 

The following DIALS command-line tools were written to facilitate ssx data processing:

- `ssx.import` -- Replaces `dials.import`, adding the additional argument `nimages=N` that will split the dataset into multiple experiments, each with the same oscillation range and `N` images.
- `ssx.filter_dose` -- Cut back on the number of images per scan, to reduce radiation damage. Works similarly to the `filter_dose` function in xia2.multiplex, except that image offsets are relative to the first image number in a scan.
- `ssx.find_hits` -- Discard experiments based on a variety of criteria. Can be run after spotfinding, indexing, and profile fitting.
- `ssx.combine` -- Apply a common beam / goniometer / detector model to the experiments before refining the geometry.

## Getting started

If you are processing data on a MacCHESS computer or CLASSE compute farm node, you can activate dials as follows:
```
source /nfs/chess/sw/macchess/dials/dials-current/dials_env.sh 
```

This repository contains custom command-line tools for ssx data processing. They are already installed into the MacCHESS DIALS version. If you need to process data off-site, see [Installation Notes](#installation-notes).

## Data processing steps

### 1. Importing

```
ssx.import <path-to-master.h5> nimages=<number>
```

The parameter `nimages` is the number of images per oscillation. If needed you can pass other options as you normally would to `dials.import`.

### 2. Spotfinding

For spotfinding, just follow the normal DIALS workflow.

```
dials.find_spots imported.expt
```

It's nice to get a plot of counts per image & resolution estimates, which helps estimate the hit rate and assess radiation damage or time-dependent quality decay.

```
dials.spot_counts_per_image imported.expt strong.refl plot=counts_per_image.png
```

Next, select out the 'hits'.
```
ssx.find_hits imported.expt strong.refl minspots=50
```

The parameter `minspots` sets the minimum number of strong reflections per series that constitutes a 'hit'. The default value is 20. You can also specify a maximum using `maxspots`. 

### 3. Indexing

[!TIP]
We can do a first-pass indexing run in P1 to see what unit cells we get. Alternatively, if you know the cell and space group, you can skip ahead. 

```
dials.index hits.expt hits.refl detector.fix=distance joint=False nproc=32
```
The options `detector.fix=distance` and `joint=False` are important for serial data. We'll refine the distance later.  In the version of DIALS I'm using (3.14.2), dials.index does not automatically run in parallel. You can force it by setting the number of processors to use (`nproc=32` in my case).

Next, inspect the unit cells
```
dials.show indexed.expt | grep "Unit cell"
```

Now, re-run indexing with a consensus unit cell (and space group, if known)
```
dials.index hits.{expt,refl} detector.fix=distance joint=False nproc=32 unit_cell=<a,b,c,alpha,beta,gamma>
```
(where items in brackets are replaced by correct values, for example `unit_cell=73,30.2,75.5,90,90,120`)

Check that it indexed consistently.
```
dials.show indexed.expt | grep "Unit cell"
```

Now, we can run the hit-finder again to reject any experiments that did not index (important for integration, later).
```
ssx.find_hits indexed.{expt,refl} minspots=50 output.experiments=hits2.expt output.reflections=hits2.refl
```

Next, we need to set a common beam / detector / goniometer model for all the datasets.
```
ssx.combine hits2.expt model=0
```
The `model` argument is which experiment to use as the reference geometry. The default value is 0, which should be fine in most cases.

Finally, refine the geometry.
```
dials.refine combined.expt hits2.refl scan_varying=False
```

### 4. Integration

[!TIP]
Before integration, it's a good idea to remove any crystals with abnormally high apparent mosaicity. These are probably indexing mistakes, and unlikely to improve data quality. Also, high mosaicity will force `dials.integrate` to use a lot of memory for shoeboxes, which can limit performance (for instance, by restricting the number of parallel processes).

To calculate the mosaicity, first fit a profile model:
```
dials.create_profile_model refined.{expt,refl}
```
A summary table will be printed with apparent mosaicity for each experiment (`sigma_m`). Typically, this will be comparable to / less than the oscillation width per frame. If there are outliers with large mosaicity (e.g. > 0.25 degrees), they can be removed as follows:

```
ssx.find_hits models_with_experiments.expt refined.refl mosaicity_cutoff=0.25 output.experiments=hits3.expt output.reflections=hits3.refl
```

Run dials.integrate as normal
```
dials.integrate hits3.{expt,refl}
```

[!TIP]
If this works, great! If you get an error about too few spots, you might need to revisit hitfinding parameters, or change the default thresholds for integration, as follows:
```
dials.integrate refined.refl hits3.{expt,refl} profile.gaussian_rs.min_spots.per_degree=10 profile.gaussian_rs.min_spots.overall=10
```

### 5. Symmetry determination, resolution cutoff, scaling, & merging

[!TIP]
These steps are most easily done using `xia2.multiplex`. However, I have found that multiplex often did not get the correct space group for SSX data, and I had to go back to indexing with the correct space group enforced. I'm not sure why this was necessary, but it was. You can also override the space group determination in xia2.multiplex.

A basic run looks like this:
```
mkdir multiplex
cd multiplex
xia2.multiplex ../integrated.refl ../integrated.expt 
```

Below is a set of options for multiplex that work well for serial. Explicit space group determination is included, as well as an extra step of data filtering to remove misfit crystals. The filtering step is slow (and could be omitted on the first pass), but it is very likely to improve data quality for serial, where non-isomorphism and other issues are likely to occur.

```
mkdir multiplex
cd multiplex
xia2.multiplex ../integrated.refl ../integrated.expt symmetry.cosym.space_group=<sg> symmetry.space_group=<sg> filtering.method=deltacchalf
```

where `<sg>` shoudl be replaced by the known space group, such as `space_group=P3121`

After running multiplex, carefully inspect the html reports, especially completeness and resolution determination. If all is well, use the mtz files in the multiplex folder to solve the structure.

[!TIP]
It may be necessary to go back to earlier steps in data processing (for instance, imposing space group during indexing). To avoid cluttering your directory, I recommend making new directories every time you change something. 

## Installation notes

The MacCHESS DIALS installation already contains the custom command-line tools for ssx data processing. If you are processing on-site, no installation is required.

To process CHESS data in a stand-alone DIALS environment, you will need to install our custom detector format class (to be remedied in future DIALS releases, see: https://github.com/FlexXBeamline/dials-extensions), as well as the `ssx-dials` package. 

With the DIALS environment activated, install the detector format as follows:

```
libtbx.python -m pip install git+https://github.com/FlexXBeamline/dials-extensions@faster-read-raw
```

The `ssx-dials` package is installed similarly:

```
libtbx.python -m pip install git+https://github.com/FlexXBeamline/ssx-dials
```

If you discover any issues with either package, please submit a ticket on GitHub or contact the developer directly.