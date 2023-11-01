# ssx-dials
How to process serial oscillation crystallography from CHESS data using DIALS

## Getting started

First, you'll need DIALS. See: <https://dials.github.io/installation.html>

If you are processing data on a MacCHESS computer or CLASSE compute farm node, you can activate dials as follows:
```
source /nfs/chess/sw/macchess/dials/dials-current/dials_env.sh 
```

## Importing

Serial crystallography data at id7b2 is collected using small oscillations per crystal, typically 1-5 degrees. The detector images from all of these sweeps are collected in a single h5 file (_master.h5) which includes metadata for the scan. However, we do not currently store the motor positions, so a conventional processing program would interpret this file as a single sweep of continuous rotation data. This adds an extra processing step in dials.

```
dials.import <path-to-master.h5> invert_rotation_axis=True
dials.slice_sequence imported.expt output.experiments_filename=imported.expt block_size=<total-angle>
```

The items in brackets should be replaced with correct values. IMPORTANT! set the block size to the total angular rotation per crystal. For example, for 5 frames of 0.25 degrees each, set `block_size=1.25`.

## Spotfinding

For spotfinding, just the normal DIALS workflow.

```
dials.find_spots imported.expt
```

It's nice to get a plot of counts per image & resolution estimates, which helps estimate the hit rate and assess radiation damage or time-dependent quality decay.

```
dials.spot_counts_per_image imported.expt strong.refl plot=counts_per_image.png
```

Next, select out the 'hits'.  You'll need to download the python file `hitfinder.py` in this repository.
```
dials.python hitfinder.py imported.expt strong.refl
```

If needed, there are options for the minimum and maximum number of spots per image (for info, run `dials.python hitfinder.py --help`).

## Indexing

We can do a first-pass indexing run in P1 to see what unit cells we get. Alternatively, if you know the cell and space group, you can skip ahead. 

The options `detector.fix=distance` and `joint=False` are important for serial data. We'll refine the distance later. 

In the version of DIALS I'm using (3.14.2), dials.index does not automatically run in parallel. You can force it by setting the number of processors to use (`nproc=32` in my case).

```
dials.index hits.expt hits.refl detector.fix=distance joint=False nproc=32
```

Next, inspect the unit cells

```
dials.show indexed.expt | grep "Unit cell"
```

Now, re-run indexing with a consensus unit cell (and space group, if known)

```
dials.index hits.expt hits.refl detector.fix=distance joint=False nproc=32 unit_cell=<a,b,c,alpha,beta,gamma>
```

(where items in brackets are replaced by correct values, for example `unit_cell=73,30.2,75.5,90,90,120`)

This should index things consistently.

```
dials.show indexed.expt | grep "Unit cell"
```

Now, refine the geometry

```
dials.refine indexed.expt indexed.refl
```

## Integration

Run dials.integrate as normal
```
dials.integrate refined.refl refined.expt
```

If this works, great! When I was testing this, it complained because there were too few spots per degree & spots overall, probably due to the narrow wedges. The defaults can be manually reset like this:

```
dials.integrate refined.refl refined.expt profile.gaussian_rs.min_spots.per_degree=10 profile.gaussian_rs.min_spots.overall=10
```

## Symmetry determination, resolution cutoff, scaling, & merging

These steps are most easily done using `xia2.multiplex`. However, I found that multiplex didn't get the correct space group out of the box, and I had to go back to indexing with the correct space group enforced. I'm not sure why this was necessary, but it was. You can also override the space group determination in xia2.multiplex. Again, this shouldn't be necessary, but serial is a tricky beast. 

A basic run looks like this:

```
mkdir multiplex
cd multiplex
xia2.multiplex ../integrated.refl ../integrated.expt 
```

I found it was necessary to set the space group explicitly. I also added a step of data filtering to remove misfit crystals, which is a bit slow but probably a good idea for serial. Here's what the full command looks like:

```
mkdir multiplex
cd multiplex
xia2.multiplex ../integrated.refl ../integrated.expt symmetry.cosym.space_group=<sg> symmetry.space_group=<sg> filtering.method=deltacchalf
```

where `<sg>` shoudl be replaced by the known space group, such as `space_group=P3121`

After running multiplex, carefully inspect the html reports. 

## General advice

It may be necessary to go back to earlier steps in data processing (for instance, imposing space group during indexing). To avoid cluttering your directory, I recommend making new directories every time you change something. 

It's good practice to record what you did so that you can reproduce your workflow later.


