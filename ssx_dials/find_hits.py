"""
Hit Finder for Serial Oscillation Crystallography

Remove sweeps based on number of reflections less than or exceeding a cutoff. If data are indexed, then only indexed reflections are used.

Examples::

  ssx.find_hits imported.expt strong.refl minspots=20 maxspots=500
  
  ssx.find_hits indexed.expt indexed.refl minspots=20 output.experiments=indexed_filtered.expt output.reflections=indexed_filtered.refl
"""

# This is based on a script that Graeme Winter posted on dials-slack on October 31, 2023
# Modified by Steve Meisburger 

import logging

import iotbx.phil
from dxtbx.model.experiment_list import ExperimentList

from dials.array_family import flex
from dials.util import Sorry, log, show_mail_handle_errors
from dials.util.options import ArgumentParser, reflections_and_experiments_from_files

help_message = __doc__

phil_scope = iotbx.phil.parse(
"""\
  minspots = 20
    .type = int(value_min=0)
    .help = "Minimum number of spots per sweep"
    
  maxspots = 100000
    .type = int
    .help = "Maximum number of spots per sweep"
    
  mosaicity_cutoff = 1
    .type = float(value_min=0)
    .help = "Maximum sigma_m in degrees (mosaicity), if fitted profile model is available"
    
  output {
     experiments = 'hits.expt'
        .type = str
        .help = "The filtered experiments output filename"
     reflections = 'hits.refl'
        .type = str
        .help = "The filtered reflections output filename"
     log = 'ssx.find_hits.log'
        .type = str
        .help = "Name of log file"
    }
""",
    process_includes=True,
)

logger = logging.getLogger('dials.command_line.index.find_hits')

#@show_mail_handle_errors()
def run(args=None):
    
    usage = 'ssx.find_hits imported.expt strong.refl [options]'
    parser = ArgumentParser(
        usage=usage,
        phil=phil_scope,
        read_experiments=True,
        read_reflections=True,
        epilog=help_message,
    )

    params, options, args = parser.parse_args(
        args, show_diff_phil=False, return_unhandled=True
    )
    
    log.config(verbosity=options.verbose, logfile=params.output.log)
    
    # Log the diff phil
    diff_phil = parser.diff_phil.as_str()
    if diff_phil != "":
        logger.info("The following parameters have been modified:\n")
        logger.info(diff_phil)
    
    refl, expt = reflections_and_experiments_from_files(
        params.input.reflections, params.input.experiments
    )
    refl = refl[0] # why is this a list?

    # keep only indexed reflections
    indexed = refl.select(refl.get_flags(refl.flags.indexed))
    if indexed.size() > 0:
        logger.info(f'Keeping indexed reflections only ({indexed.size()} / {refl.size()})')
        refl = indexed
    else:
        logger.info('These are unindexed reflections')

    ids = refl["id"]

    keep_expt = ExperimentList()
    keep_refl = flex.reflection_table()

    for j, e in enumerate(expt):
        if e.profile is not None and e.profile.sigma_m() > params.mosaicity_cutoff:
            logger.info(f'Experiment {j} rejected: mosaicity {e.profile.sigma_m()} above cutoff')
        else:
            nn = (ids == j).count(True)
            if (nn < params.minspots):
                logger.info(f'Experiment {j} rejected: {nn} is fewer than the minimum number of spots')
            elif (nn > params.maxspots):
                logger.info(f'Experiment {j} rejected: {nn} exceeds the maximum number of spots')
            else:
                keep = refl.select(ids == j)
                keep["id"] = flex.int(keep.size(), len(keep_expt))
                keep_refl.extend(keep)
                keep_expt.append(e)

    logger.info('-'*80)
    logger.info(f'Found {len(keep_expt)} hits ({len(keep_expt)}/{len(expt)} = {(len(keep_expt)/len(expt)):.1%})')
    logger.info(f'Saving hits to {params.output.experiments}, {params.output.reflections}')
    logger.info('-'*80)
    
    keep_expt.as_file(params.output.experiments)
    keep_refl.as_file(params.output.reflections)
    
if __name__ == "__main__":
    run()
