# ssx-dials
How to process serial oscillation crystallography from CHESS data using DIALS

## Getting started

First, you'll need DIALS. See: <https://dials.github.io/installation.html>

If you are processing data on a MacCHESS computer or CLASSE compute farm node, you can activate dials as follows:
```
source /nfs/chess/sw/macchess/dials/dials-current/dials_env.sh 
```

## Importing

Serial crystallography data at id7b2 is collected using small oscillations per crystal, typically 1-5 degrees. The detector images from all of these sweeps are collected in a single h5 file (_master.h5) which includes metadata for the scan. However, we do not currently store the motor positions, so a conventional processing program would interpret this file as a single sweep of continuous rotation data. We created the program `import_sliced.py` (download from this repository) to replace the `dials.import` step you would normally perform.

```
dials.python import_sliced.py <path-to-master.h5> invert_rotation_axis=True nimages=<number>
```

The parameter `nimages` is the number of images per oscillation. If needed you can pass other options as you normally would to `dials.import`.

## Spotfinding

For spotfinding, just follow the normal DIALS workflow.

```
dials.find_spots imported.expt
```

It's nice to get a plot of counts per image & resolution estimates, which helps estimate the hit rate and assess radiation damage or time-dependent quality decay.

```
dials.spot_counts_per_image imported.expt strong.refl plot=counts_per_image.png
```

Next, select out the 'hits'.  You'll need to download the python file `find_hits.py` in this repository.
```
dials.python find_hits.py imported.expt strong.refl minspots=50
```

The parameter `minspots` sets the minimum number of strong reflections per series that constitutes a 'hit'. The default value is 20. You can also specify a maximum using `maxspots`. 

## Indexing

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
dials.index hits.expt hits.refl detector.fix=distance joint=False nproc=32 unit_cell=<a,b,c,alpha,beta,gamma>
```

(where items in brackets are replaced by correct values, for example `unit_cell=73,30.2,75.5,90,90,120`)

Check that it indexed consistently.

```
dials.show indexed.expt | grep "Unit cell"
```

Now, we can run the hit-finder again to reject any experiments that did not index (important for integration, later).
```
dials.python find_hits.py indexed.expt indexed.refl minspots=50
```

Next, we need to set a common beam / detector / goniometer model for all the datasets. You'll need to download the python file `combine.py` in this repository.
```
dials.python combine.py indexed.expt model=0
```
The `model` argument is which experiment to use as the reference geometry. The default value is 0, which should be fine in most cases.

Finally, refine the geometry.
```
dials.refine combined.expt hits.refl
```

## Integration

Run dials.integrate as normal
```
dials.integrate refined.refl refined.expt
```

If this works, great! If you get an error about too few spots, you might need to revisit hitfinding parameters, or change the default thresholds for integration, as follows:

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

If all is well, use the mtz files in the multiplex folder to solve the structure.

## General advice

It may be necessary to go back to earlier steps in data processing (for instance, imposing space group during indexing). To avoid cluttering your directory, I recommend making new directories every time you change something. 

It's good practice to record what you did so that you can reproduce your workflow later.


