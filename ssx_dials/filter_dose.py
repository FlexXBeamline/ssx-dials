""" Filter dose """

# works similarly to the filter_dose function in xia2.multiplex, except that image offsets are relative to the 
# first image number in a scan
#
# https://github.com/xia2/xia2/blob/8a212b227d1cccc25b982bf8dd8e586c042b8980/src/xia2/Modules/MultiCrystal/data_manager.py#L88


import logging
import copy

import iotbx.phil
from dxtbx.model.experiment_list import ExperimentList, Experiment

from dials.array_family import flex
from dials.command_line.slice_sequence import slice_experiments, slice_reflections
from dials.util import Sorry, log, show_mail_handle_errors
from dials.util.options import ArgumentParser, reflections_and_experiments_from_files

logger = logging.getLogger('dials.command_line.filter_dose')

help_message = __doc__

phil_scope = iotbx.phil.parse(
"""\
  dose = None
      .type = ints(size=2, value_min=0)
      .short_caption = "Dose"
  
  output {
     experiments = 'filtered.expt'
        .type = str
        .help = "The filtered experiments output filename"
     reflections = 'filtered.refl'
        .type = str
        .help = "The filtered reflections output filename"
     log = 'ssx.filter_dose.log'
        .type = str
        .help = "Name of log file"
  }
""",
    process_includes=True,
)

def run(args=None):
    
    usage = 'ssx.filter_dose integrated.expt integrated.refl [options]'
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
    
    reflections, experiments = reflections_and_experiments_from_files(
        params.input.reflections, params.input.experiments
    )
    reflections = reflections[0] # why is this a list?

    dose_min, dose_max = params.dose # unpack the dose parameters
    
    first_image = [ expt.scan.get_image_range()[0] for expt in experiments ]
    last_image = [ expt.scan.get_image_range()[1] for expt in experiments ]
    
    image_range = [
        (
            max(dose_min + first - 1, first), 
            min(dose_max + first - 1, last),
        )
        for first, last in zip(first_image, last_image)
    ]
    
    logger.info(f"{image_range}")
    
    n_refl_before = reflections.size()
    
    #experiments = slice_experiments(experiments, image_range)
    
    # slice_experiments fails to index imagesets correctly, so let's do this manually
    # https://github.com/dials/dials/blob/main/src/dials/util/slice.py
    for exp, sr in zip(experiments, image_range):
        arr_start = exp.scan.get_array_range()[0]
        beg = sr[0] - 1 - arr_start
        end = sr[1] - arr_start
        exp.scan.swap(exp.scan[beg:end])
        if exp.imageset is not None:
            exp.imageset = exp.imageset[(sr[0]-1):sr[1]] # <-- is this right?
            #exp.imageset = exp.imageset[beg:end]
        # skip possibility of a scan-varying crystal for simplicity
        
    flex.min_max_mean_double(reflections["xyzobs.px.value"].parts()[2]).show()
    reflections = slice_reflections(reflections, image_range)
    flex.min_max_mean_double(reflections["xyzobs.px.value"].parts()[2]).show()
    
    logger.info('-'*80)
    logger.info(
        f"{reflections.size()} reflections out of {n_refl_before} remaining after filtering for dose"
    )
    logger.info(f'Saving filtered reflections to {params.output.experiments}, {params.output.reflections}')
    logger.info('-'*80)
    
    experiments.as_file(params.output.experiments)
    reflections.as_file(params.output.reflections)
    
    
if __name__ == "__main__":
    run()
