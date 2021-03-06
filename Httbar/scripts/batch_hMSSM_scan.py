#! /bin/env python

import os
import pickle
from argparse import ArgumentParser
from distutils import spawn

parser = ArgumentParser()
parser.add_argument('jobid')
parser.add_argument('input_sushi')
parser.add_argument('outdir')
parser.add_argument('--noblind', action='store_true')
args = parser.parse_args()

if not os.path.isdir(args.outdir):
	os.makedirs(args.outdir)

with open(args.input_sushi) as sushi_pkl:
	mapping = pickle.load(sushi_pkl)

with open('%s/condor.jdl' % args.outdir, 'w') as jdl:
	jdl.write('''
Should_Transfer_Files = YES
WhenToTransferOutput = ON_EXIT
getenv = True
executable = %s
+MaxRuntime = 21600

''' % spawn.find_executable('produce_morph_files_tanb_mA.py'))
	for idx, point in enumerate(mapping.keys()):
		ma, tanb = point
		jdl.write('''
Output = con_{idx}.stdout
Error = con_{idx}.stderr
Log = con_{idx}.log
Arguments = {jobid} {ma} {tanb} {sushi} {blind}
Queue
'''.format(
				idx=idx,
				jobid=args.jobid,
				ma=int(ma),
				tanb=round(tanb, 2),
				sushi=os.path.realpath(args.input_sushi),
				blind= '--noblind' if args.noblind else ''
				))
