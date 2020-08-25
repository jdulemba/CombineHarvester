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
parser.add_argument('mA', type=int)
parser.add_argument('tanb')
parser.add_argument('input_sushi')
parser.add_argument('--noblind', action='store_true')
parser.add_argument('--keep', action='store_true')
parser.add_argument('--force', help='force the values for debugging')
parser.add_argument('--runScan', action='store_true', help='run scan of AsymptoticLimits instead of limit only')
parser.add_argument('--twoPars', action='store_true', help='add both regular signal strength and coupling modifier to model')
parser.add_argument('--barlowBeeston', action='store_true', help='use Barlow-Beeston instead of separate MC statistical uncertainties')
# parser.add_argument('inputs_bkg', help='comma separated list of bkg input files. Same order required as for signal files')
# parser.add_argument('outfile')
args = parser.parse_args()

val2name = lambda x: str(x).replace('.','p').replace('p0','')
mA = args.mA
tanb = args.tanb
# inputs_sig = args.inputs_sig.split(',')
# inputs_bkg = args.inputs_bkg.split(',')

mH = mA
widthH = 0.
widthA = 0.

with open(args.input_sushi) as sushi_pkl:
	mapping = pickle.load(sushi_pkl)
	values = [d for d in mapping.values() if d['m_A'] == mA and d['tan(beta)'] == eval(tanb)]
	
	if len(values) == 0:
		raise RuntimeError('No entry found for mA and tan(beta)', mA, tanb)
	if len(values) > 1:
		print 'Multiple entries found for mA and tan(beta)', mA, tanb, 'picking first'
	
	values = values[0]
	mH = int(round(float(values['m_H']))) 
	# Widths are relative and in per cent
	widthA = round(float(values['A_width'])/mA*100., 1)
	widthH = round(float(values['H_width'])/mH*100., 1)
	if args.force:
		print 'forcing output'
		for val in args.force.split(','):
			parity, mass, width = tuple(val.split(':'))
			if parity == 'A':
				mA = int(mass)
				widthA = float(width)
			elif parity == 'H':
				mH = int(mass)
				widthH = float(width)
	
	kFactorA = values['A_nnlo']/values['A_lo']
	kFactorH = values['H_nnlo']/values['H_lo']
	
	print 'For mA =', mA, 'tan(beta) =', tanb, 'obtain:'
	print '  widthA =', widthA
	print '  widthH =', widthH
	print '  mH =', mH
	print '  k factor A', kFactorA
	print '  k factor H', kFactorH

	## if widthH < 1. or widthA < 1.:
	## 	print 'LIMITING WIDTH TO 1%'
	## 	widthA = max(widthA, 1.)
	## 	widthH = max(widthH, 1.)
	if mH > 750 and mH < 759:
		print 'LIMITING m(H) TO 750'
		mH = 750
	if mH > 759:
		raise ValueError('mH beyond accepted limits')
	syscall('make_point.sh {} None TESTME A:{}:{}:{} H:{}:{}:{}'.format(args.jobid, mA, widthA, kFactorA, mH, widthH, kFactorH))
	syscall(
		'hadd -f templates_ALL_POINT.root TESTME.root '
		'%s/src/CombineHarvester/Httbar/data/templates_l?_bkg_%s.root' % (
			os.environ['CMSSW_BASE'], args.jobid
			)
		)
	print '\n\ncreating workspace\n\n'
	syscall((
			'setup_common.py POINT --indir=./ --limitdir=./'
			' --masses="A:{},H:{}" --widths="A:{},H:{}" {}').format(
			mA, mH, val2name(widthA), val2name(widthH), 
			'--noBBB' if args.barlowBeeston else ''
			))
	model = '.InterferencePlusFixed:interferencePlusFixed' if args.twoPars else '.InterferenceModel:interferenceModel'
	dirname = '_'.join(['A', val2name(widthA), str(mA), 'H', val2name(widthH), str(mH)])
	syscall((
			'combineTool.py -M T2W -i {} -o workspace.root -P CombineHarvester'
			'.CombineTools{}').format(dirname, model)
			)
	print '\n\nRunning LIMIT\n\n'

	if not args.runScan:
		syscall((
				'combineTool.py -M AsymptoticLimits -d {}/workspace.root --there'
				' -n .limit --rMin=0 --rMax=3 --rRelAcc 0.001 --cminPreScan --parallel 1 {} {}').format(
				dirname,
				'' if args.noblind else '--run blind -t -1',
				'--X-rtd MINIMIZER_analytic' if args.barlowBeeston else ''
				))
		syscall((
			'combineTool.py -M CollectLimits {}/*/higgsCombine.limit.AsymptoticLimits'
			'.mH[0-9][0-9][0-9].root'
			).format(dirname))
		shutil.move('limits.json', 'mA%d_tanb%s.json' % (mA, tanb))
	else:
		if not args.twoPars:
			syscall((
				'combineTool.py -M AsymptoticLimits -d {}/workspace.root --there'
				' -n .limit --rMin=0 --rMax=3 --rRelAcc 0.001 --parallel 8  '
				'--singlePoint 0.:3.:0.03 --cminPreScan {} {}').format(
					dirname, '' if args.noblind else '--run blind -t -1',
					'--X-rtd MINIMIZER_analytic' if args.barlowBeeston else ''
					))
			syscall(
				'hadd -f mA{}_tanb{}_limits_gathered.root {}/higgsCombine.limit*POINT*AsymptoticLimits*.root'.format(
					mA, tanb, dirname
				))
		else:
			import numpy as np
			for point in np.arange(0, 3.01, 0.01):
				syscall((
				'combineTool.py -M AsymptoticLimits -d {}/workspace.root --there'
				' -n .limitscan.POINT.{} --setParameters g={} --freezeParameters g '
				' --rMin=0 --rMax=2.4 --rRelAcc 0.001 --picky --singlePoint 1. --cminPreScan {} {}').format(
						dirname, point, point,
						'' if args.noblind else '--run blind -t -1',
						'--X-rtd MINIMIZER_analytic' if args.barlowBeeston else ''
						))
			syscall(
				'hadd -f mA{}_tanb{}_limits_gathered.root {}/higgsCombine.limit*POINT*AsymptoticLimits*.root'.format(
					mA, tanb, dirname
					))

if not args.keep:
	shutil.rmtree(
		'A_{}_{}_H_{}_{}'.format(
			val2name(widthA), mA, val2name(widthH), mH
			)
		)
	for fname in glob('*.root'):
		if not fname.endswith('_limits_gathered.root'):
			os.remove(fname)

