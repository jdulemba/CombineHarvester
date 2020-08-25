#!/usr/bin/env python

'''Given tan beta and mA values, produces combined datacard with morphed masses
and widths, using SusHi/2HDMC results as input.
'''

import os
import pickle
from argparse import ArgumentParser
import shutil
from glob import glob
from pdb import set_trace

def syscall(cmd):
	print 'Executing: %s' % cmd
	retval = os.system(cmd)
	if retval != 0:
		raise RuntimeError('Command failed!')

parser = ArgumentParser()
parser.add_argument('jobid')
parser.add_argument('parity')
parser.add_argument('mass', type=int)
parser.add_argument('width', type=float)
parser.add_argument('--noblind', action='store_true')
parser.add_argument('--keep', action='store_true')
parser.add_argument('--mergeLJ', action='store_true')
parser.add_argument('--channels', default='', help='leptonic decay type')
parser.add_argument('--ignore', default='', help='ignore systematics')
parser.add_argument('--extern', default='', help='externalize systematic')
parser.add_argument('--kfactor', default='$CMSSW_BASE/src/CombineHarvester/Httbar/data/kfactors.json', help='location of k factor json file (None if none)')
parser.add_argument('--runScan', action='store_true', help='run scan of AsymptoticLimits instead of limit only')
parser.add_argument('--twoPars', action='store_true', help='add both regular signal strength and coupling modifier to model')
parser.add_argument('--barlowBeeston', action='store_true', help='use Barlow-Beeston instead of separate MC statistical uncertainties')
args = parser.parse_args()

val2name = lambda x: str(x).replace('.','p').replace('p0','')

syscall('make_point.sh {} {} TESTME {}:{}:{}:1. ""'.format(
		args.jobid, args.kfactor, args.parity, args.mass, args.width
		))
syscall(
	'hadd -f templates_ALL_POINT.root TESTME.root '
	'%s/src/CombineHarvester/Httbar/data/templates_l?_bkg_%s.root' % (
		os.environ['CMSSW_BASE'],
		args.jobid
		))

if args.extern:
	syscall('externalize.py templates_ALL_POINT.root %s' % args.extern)

print '\n\ncreating workspace\n\n'
opts = ''
if args.mergeLJ:
	opts += "--channels=cmbLJ "
if args.channels:
	opts += "--channels={} ".format(args.channels)
if args.ignore:
	opts += "--ignore='%s' " % args.ignore
if args.barlowBeeston:
	opts += "--noBBB "
syscall((
		'setup_common.py POINT --parity={} --indir=./ --limitdir=./'
		' --masses="{}" --widths="{}" {}').format(
		args.parity, args.mass, val2name(args.width),
		opts
		))

interference = '.CombineTools.InterferencePlusFixed:interferencePlusFixed' if args.twoPars else '.CombineTools.InterferenceModel:interferenceModel'

syscall((
		'combineTool.py -M T2W -i {}_{}/* -o workspace.root -P CombineHarvester'
		'{}').format(
		args.parity, val2name(args.width), interference
		))

print '\n\nRunning LIMIT\n\n'
if not args.runScan:
	syscall((
			'combineTool.py -M AsymptoticLimits -d {}/{}/workspace.root --there'
			' -n .limit'
			' --rMin=0 --rMax=3 --rRelAcc 0.001 --cminPreScan --parallel 1 {} {}').format('_'.join([args.parity, val2name(args.width)]), args.mass, 
			'' if args.noblind else '--run blind -t -1',
			'--X-rtd MINIMIZER_analytic' if args.barlowBeeston else ''
			))

	syscall((
			'combineTool.py -M CollectLimits */*/higgsCombine.limit.AsymptoticLimits'
			'.mH[0-9][0-9][0-9].root'
			))
	fname = '%s_%d_%.1f.json' % (args.parity, args.mass, args.width)
	if args.extern:
		fname = fname.replace('.json', '_%s.json' % args.extern)
	shutil.move('limits.json', fname)
else:
		if not args.twoPars:
			syscall((
				'combineTool.py -M AsymptoticLimits -d {}/{}/workspace.root --there'
				' -n .limit'
				' --rMin=0 --rMax=3 --rRelAcc 0.001 --parallel 8  --singlePoint 0.:3.:0.03 --cminPreScan {} {}').format('_'.join([args.parity, val2name(args.width)]), args.mass, 
				'' if args.noblind else '--run blind -t -1',
				'--X-rtd MINIMIZER_analytic' if args.barlowBeeston else ''
				))
			syscall((
				'hadd {par}_{m}_{wid}_limits_gathered.root {par}_{wid}/{m}/higgsCombine.limit*POINT*AsymptoticLimits*.root'.format(
				par=args.parity, wid=val2name(args.width), m=args.mass)
				))
		else:
			for point in [0.01*i for i in xrange(int(3./0.01)+1)]:
				syscall((
				'combineTool.py -M AsymptoticLimits -d {}/{}/workspace.root --there'
				' -n .limitscan.POINT.{} --setParameters g={} --freezeParameters g '
				' --rMin=0 --rMax=2.4 --rRelAcc 0.001 --picky --singlePoint 1. --cminPreScan {} {}').format('_'.join([args.parity, val2name(args.width)]), args.mass, point, point,
				'' if args.noblind else '--run blind -t -1',
				'--X-rtd MINIMIZER_analytic' if args.barlowBeeston else ''
				))
			syscall((
			'hadd {par}_{m}_{wid}_limits_gathered.root {par}_{wid}/{m}/higgsCombine.limit*POINT*AsymptoticLimits*.root'.format(
			par=args.parity, wid=val2name(args.width), m=args.mass)
			))


if not args.keep:
	shutil.rmtree(
		'{}_{}/{}'.format(
			args.parity, val2name(args.width), args.mass, 
			)
		)
	if not args.runScan:
		for fname in glob('*.root'):
			os.remove(fname)
else:
	syscall((
			'tar -cvf {parity}_{mass}_{width}.tar'
			' *.root {parity}_{width}/').format(
			parity = args.parity,
			mass = args.mass,
			width = val2name(args.width)
			))
