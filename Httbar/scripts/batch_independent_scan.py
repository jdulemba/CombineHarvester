#! /bin/env python

import os
import pickle
from argparse import ArgumentParser
from distutils import spawn
from numpy import arange
from pdb import set_trace
import subprocess

parser = ArgumentParser()
parser.add_argument('outdir')
parser.add_argument('parities')
parser.add_argument('masses')
parser.add_argument('widths')
parser.add_argument('--doNotRemove')
parser.add_argument('--noblind', action='store_true')
parser.add_argument('--nokfactors', action='store_true')
parser.add_argument('--runScan', action='store_true')
parser.add_argument('--twoPars', action='store_true')
parser.add_argument('--barlowBeeston', action='store_true')
parser.add_argument('--channels', default='', help='leptonic decay type')
args = parser.parse_args()

if not os.path.isdir(args.outdir):
	os.makedirs(args.outdir)

    # set environment variables
jobid = os.environ['jobid']
proj_dir = os.environ['PROJECT_DIR']
pypath = '/'.join(subprocess.Popen("which python", stdout=subprocess.PIPE, shell=True).stdout.read().split('\n')[0].split('/')[:-1])

do_not_remove = set(args.doNotRemove.split(',')) if args.doNotRemove else set()

masses = [str(j) for j in arange(*[int(i) for i in args.masses.split(':')])] \
	if ':' in args.masses else args.masses.split(',')

    ## write batch_job.sh
with open('%s/batch_job.sh' % args.outdir, 'w') as batch_job:
    batch_job.write("""#!/bin/bash

export PATH={PYPATH}:$PATH
echo  "which python"
which python

echo "python path"
echo $PYTHONPATH

echo "SCRAM_ARCH: " $SCRAM_ARCH

EXE="${{@}}"
echo $EXE

echo "Executing: python {exe}" $EXE
python {exe} $EXE
""".format(PYPATH=pypath, exe=spawn.find_executable('single_point_limit.py')) )


    ## write condor.jdl file
with open('%s/condor.jdl' % args.outdir, 'w') as jdl:
	jdl.write("""
Should_Transfer_Files = YES
WhenToTransferOutput = ON_EXIT
getenv = True
executable = %s/%s/batch_job.sh
+MaxRuntime = 21600
""" %  (proj_dir, args.outdir) )
	idx = 0
	for parity in args.parities.split(','):
		for mass in masses:
			for width in args.widths.split(','):
				jdl.write("""
Output = con_{idx}.out
Error = con_{idx}.err
Log = con_{idx}.log
Arguments = {jobid} {parity} {mass} {width} {blind} {keep} {kfactor} {scan} {twoPars} {bb} {channels}
Queue
""".format(
				idx=idx,
				jobid=jobid,
				parity=parity,
				mass=mass,
				width=width,
				blind='--noblind' if args.noblind else '',
				keep='--keep' if ':'.join([parity, mass, width]) in do_not_remove else '',
				kfactor='--kfactor None' if args.nokfactors else '',
				scan='--runScan' if args.runScan else '',
				twoPars='--twoPars' if args.twoPars else '',
				bb='--barlowBeeston' if args.barlowBeeston else '',
				channels="--channels={}".format(args.channels) if args.channels else '',
				))
				idx += 1
