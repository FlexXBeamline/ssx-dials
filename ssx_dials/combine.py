"""
Combine experiments with a common detector / beam / goniometer model

Examples::

  ssx.combine indexed.expt model=0
"""

import logging
import copy

import iotbx.phil
from dxtbx.model.experiment_list import ExperimentList, Experiment

from dials.util import Sorry, log, show_mail_handle_errors
from dials.util.options import ArgumentParser, flatten_experiments

logger = logging.getLogger('dials.command_line.combine')

help_message = __doc__

phil_scope = iotbx.phil.parse(
"""\
  model = 0
    .type = int
    .help = "Index for the model to use as a reference"
    
  output {
      experiments = 'combined.expt'
          .type = str
          .help = "Output experiments filename"
      log = 'ssx.combine.log'
          .type = str
          .help = "Name of log file"
  }
""",
    process_includes=True,
)

@show_mail_handle_errors()
def run(args=None):

    usage = 'ssx.combine [options] experiments.expt'
    parser = ArgumentParser(
        usage=usage,
        phil=phil_scope,
        read_experiments=True,
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
        
    
    experiments = flatten_experiments(params.input.experiments)
    
    beam = experiments[params.model].beam
    detector = experiments[params.model].detector
    goniometer = experiments[params.model].goniometer

    elist = ExperimentList()

    for expt in experiments:
        elist.append(Experiment(
            identifier=expt.identifier,
            beam=beam,
            detector=detector,
            scan=expt.scan,
            goniometer=goniometer,
            crystal=expt.crystal,
            imageset=expt.imageset,
        ))
    
    logger.info('-'*80)
    logger.info("Writing experiments to %s", params.output.experiments)
    logger.info('-'*80)
    
    elist.as_file(params.output.experiments)

if __name__ == "__main__":
    run()