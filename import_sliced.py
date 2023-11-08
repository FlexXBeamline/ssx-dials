"""
Import single sweep image stack and slice into multiple experiments with the same oscillation range

Examples::

  dials.python import_sliced.py <path-to-master.h5> invert_rotation_axis=True nimages=5
"""

import logging
import copy

import iotbx.phil
from dxtbx.model.experiment_list import ExperimentList, Experiment

from dials.util import Sorry, log, show_mail_handle_errors
from dials.util.options import ArgumentParser

from dials.command_line.dials_import import (
    _extract_or_read_imagesets, 
    MetaDataUpdater, 
    write_experiments,
)
from dials.util.version import dials_version

logger = logging.getLogger('dials.command_line.find_hits')

help_message = __doc__

phil_scope = iotbx.phil.parse(
"""\
  nimages = None
    .type = int(value_min=1)
    .help = "Number of images per oscillation"
    
  include scope dials.command_line.dials_import.phil_scope
  
  output {
      log = 'import_sliced.log'
            .type = str
            .help = "Name of log file"
  }
""",
    process_includes=True,
)

@show_mail_handle_errors()
def run(args=None):

    usage = 'dials.python import_sliced.py [options] <path-to-master.h5> nimages=5'
    parser = ArgumentParser(
        usage=usage,
        phil=phil_scope,
        read_experiments=True,
        read_experiments_from_images=True,
        epilog=help_message,
    )

    params, options, args = parser.parse_args(
        args, show_diff_phil=False, return_unhandled=True
    )
    
    log.config(verbosity=options.verbose, logfile=params.output.log)

    logger.info(dials_version())
    
    # Log the diff phil
    diff_phil = parser.diff_phil.as_str()
    if diff_phil != "":
        logger.info("The following parameters have been modified:\n")
        logger.info(diff_phil)
    
    imagesets = _extract_or_read_imagesets(params)

    metadata_updater = MetaDataUpdater(params)
    experiments = metadata_updater(imagesets)

    if len(experiments) > 1:
        raise Sorry('Found more than one experiment')
    
    experiment = experiments[0]

    beam = experiment.beam
    detector = experiment.detector
    goniometer = experiment.goniometer
    scan = experiment.scan
    imageset = experiment.imageset
    crystal = experiment.crystal

    total_images = scan.get_num_images()
    N = params.nimages

    elist = ExperimentList()

    ref_scan = copy.deepcopy(scan)
    ref_scan.swap(ref_scan[0:N])

    for id, j in enumerate(range(0,total_images,N),start=1):
        scanj = copy.deepcopy(scan)
        scanj.swap(scanj[j:(j+N)])
        scanj.set_oscillation(ref_scan.get_oscillation())

        isetj = copy.deepcopy(imageset)
        isetj = isetj[j:(j+N)]

        elist.append(Experiment(
            identifier=str(id),
            beam=beam,
            detector=detector,
            scan=scanj,
            goniometer=goniometer,
            crystal=crystal,
            imageset=isetj,
        ))
    
    logger.info('-'*80)
    logger.info(f'Chopped sequence of {total_images} images into {id} sweeps of {N} images each')
    logger.info("Writing experiments to %s", params.output.experiments)
    logger.info('-'*80)
    
    elist.as_file(params.output.experiments, compact=params.output.compact)

if __name__ == "__main__":
    run()