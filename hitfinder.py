""" 
Hit Finder for Serial Oscillation Crystallography
"""

# This is based on a script from Graeme Winter on October 31, 2023

import argparse

from dials.array_family import flex
from dxtbx.model.experiment_list import ExperimentList

# I'm using argparse because that's what I know how to do... would be better to use phil parameters for consistency with DIALS
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument('exptfile', metavar='EXPT', type=str, default='imported.expt',
                    help='dials experiment file')
parser.add_argument('reflfile', metavar='REFL', type=str, default='strong.refl',
                    help='dials spotfinder file')
parser.add_argument('--minspots', metavar='N', type=int, default=20, 
                    help='minimum number of spots per series')
parser.add_argument('--maxspots', metavar='N', type=int, default=100000, 
                    help='maximum number of spots per series')
parser.add_argument('--output', metavar='PRE', type=str, default='hits', 
                    help='prefix for output .expt and .refl files')
args = parser.parse_args()

# Print the options
print(__doc__)
for k,v in args.__dict__.items():
    print(f'{k} = {v}')

# Load experiments and reflections
expt = ExperimentList.from_file(args.exptfile, check_format=False)
refl = flex.reflection_table.from_file(args.reflfile)

ids = refl["id"]

keep_expt = ExperimentList()
keep_refl = flex.reflection_table()

for j, e in enumerate(expt):
    nn = (ids == j).count(True)
    if (nn > args.minspots) and (nn < args.maxspots):
        keep = refl.select(ids == j)
        keep["id"] = flex.int(keep.size(), len(keep_expt))
        keep_refl.extend(keep)
        keep_expt.append(e)

print()
print(f'Found {len(keep_expt)} hits ({len(keep_expt)}/{len(expt)} = {(len(keep_expt)/len(expt)):.1%})')
print()

output_expt = f"{args.output}.expt"
output_refl = f"{args.output}.refl"

print(f'Saving hits to {output_expt}, {output_refl}')
keep_expt.as_file(output_expt)
keep_refl.as_file(output_refl)