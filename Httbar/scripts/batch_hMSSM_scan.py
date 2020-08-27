#! /bin/env python

import os
import pickle
from argparse import ArgumentParser
from distutils import spawn
from pdb import set_trace
import subprocess

parser = ArgumentParser()
#parser.add_argument('jobid')
parser.add_argument('input_sushi')
parser.add_argument('outdir')
parser.add_argument('njets', choices=['3', '4+'], help='Specify which jet multiplicity to use.')
parser.add_argument('--noblind', action='store_true')
parser.add_argument('--channels', default='', help='leptonic decay type')
args = parser.parse_args()

if not os.path.isdir(args.outdir):
	os.makedirs(args.outdir)

    # set environment variables
jobid = os.environ['jobid']
proj_dir = os.environ['PROJECT_DIR']
pypath = '/'.join(subprocess.Popen("which python", stdout=subprocess.PIPE, shell=True).stdout.read().split('\n')[0].split('/')[:-1])

#osreqs = 'requirements = (OpSysAndVer =?= "SLCern6")' if 'slc6' in os.environ['SCRAM_ARCH'] else ''
#set_trace()
with open(args.input_sushi) as sushi_pkl:
	mapping = pickle.load(sushi_pkl)


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
""".format(PYPATH=pypath, exe=spawn.find_executable('produce_morph_files_tanb_mA.py')) )


with open('%s/condor.jdl' % args.outdir, 'w') as jdl:
	jdl.write("""
Should_Transfer_Files = YES
WhenToTransferOutput = ON_EXIT
getenv = True
executable = %s/%s/batch_job.sh
+MaxRuntime = 21600
""" %  (proj_dir, args.outdir) )
	for idx, point in enumerate(mapping.keys()):
		ma, tanb = point
		jdl.write("""
Output = con_{idx}.stdout
Error = con_{idx}.stderr
Log = con_{idx}.log
Arguments = {jobid} {ma} {tanb} {sushi} {njets} {blind} --runScan --twoPars --barlowBeeston {channels}
Queue
""".format(
				idx=idx,
				jobid=jobid,
				ma=int(ma),
				tanb=round(tanb, 2),
				sushi=os.path.realpath(args.input_sushi),
                njets='3Jets' if args.njets == '3' else '4PJets',
				blind= '--noblind' if args.noblind else '',
				channels="--channels={}".format(args.channels) if args.channels else '',
				))
