#! /bin/env python

import os
import pickle
from argparse import ArgumentParser
from distutils import spawn
from numpy import arange
from pdb import set_trace
import subprocess
import itertools

parser = ArgumentParser()
parser.add_argument('outdir')
parser.add_argument('parities')
parser.add_argument('masses')
parser.add_argument('widths')
parser.add_argument('njets', choices=['3', '4+'], help='Specify which jet multiplicity to use.')
parser.add_argument('--keep_all', action='store_true', help='keep info from all scanned points in order to evaluate impacts')
parser.add_argument('--keep_nominal', action='store_true', help='keep info from scanned points involving generated mass datasets in order to evaluate impacts')
parser.add_argument('--doNotRemove', help="List of points in phase space to keep in order to investigate impacts. Format is 'parity:mass:width,parity:mass:width'")
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

masses = [str(j) for j in arange(*[int(i) for i in args.masses.split(':')])] \
	if ':' in args.masses else args.masses.split(',')

widths = args.widths.split(',')
parities = args.parities.split(',')

#set_trace()
if args.keep_all:
    do_not_remove = set([':'.join(point) for point in sorted(itertools.product(parities, masses, widths))])
elif args.keep_nominal:
    do_not_remove = set([':'.join(point) for point in sorted(itertools.product(parities, ['400', '500', '600', '750'], widths))])
else:
    do_not_remove = set(args.doNotRemove.split(',')) if args.doNotRemove else set()

    ## write batch_job.sh
with open('%s/batch_job.sh' % args.outdir, 'w') as batch_job:
    batch_job.write("""#!/bin/bash

export PATH={PYPATH}:$PATH
#echo  "which python"
#which python
#
#echo "python path"
#echo $PYTHONPATH
#
#echo "SCRAM_ARCH: " $SCRAM_ARCH

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
	for parity in parities:
		for mass in masses:
			for width in widths:
				jdl.write("""
Output = con_{idx}.out
Error = con_{idx}.err
Log = con_{idx}.log
Arguments = {jobid} {parity} {mass} {width} {njets} {blind} {keep} {kfactor} {scan} {twoPars} {bb} {channels}
Queue
""".format(
				idx=idx,
				jobid=jobid,
				parity=parity,
				mass=mass,
				width=width,
				njets='3Jets' if args.njets == '3' else '4PJets',
				blind='--noblind' if args.noblind else '',
				keep='--keep' if ':'.join([parity, mass, width]) in do_not_remove else '',
				kfactor='--kfactor None' if args.nokfactors else '',
				scan='--runScan' if args.runScan else '',
				twoPars='--twoPars' if args.twoPars else '',
				bb='--barlowBeeston' if args.barlowBeeston else '',
				channels="--channels={}".format(args.channels) if args.channels else '',
				))
				idx += 1
