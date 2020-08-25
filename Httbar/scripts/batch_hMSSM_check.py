#! /bin/env python

import os
import pickle
from argparse import ArgumentParser
import json
from pdb import set_trace
from ROOT import TFile
from CombineHarvester.Httbar.scantools import harvest_and_outlier_removal, andrey_harvest_and_outlier_removal

parser = ArgumentParser()
parser.add_argument('input_sushi')
parser.add_argument('submission_dir')
args = parser.parse_args()

with open(args.input_sushi) as sushi_pkl:
	mapping = pickle.load(sushi_pkl)

MAX_LIM=3

jdl = open('%s/condor.jdl' % args.submission_dir).read()
blocks = jdl.split('\n\n')
header = blocks[0]
block_map = {}
for block in blocks[1:]:
	key = ' '.join(block.split('Arguments = ')[1].split(' ')[1:3])
	block_map[key] = block

summary = {}
npass = 0
nbisected = 0
fails = []
mis_runs = 0
for entry in mapping.itervalues():
	mA = int(entry['m_A'])
	tanb = entry['tan(beta)']
	key = (mA, tanb)
	strkey = '%d %.1f' % (mA, tanb)
	#if strkey != '740 3.3': continue
	rname = '%s/mA%d_tanb%.1f_limits_gathered.root' % (args.submission_dir, mA, tanb)
	#print rname
	if entry['m_H'] > 759:
		print 'm(H) beyond accepted limits, will not compute'
		mis_runs += 1
	elif not os.path.isfile(rname):
		fails.append(strkey)
		print 'Point %s not computed successfully! (ROOT file missing)' % (key,), rname
		summary[key] = {}
	else:
		rfile = TFile.Open(rname)
		if rfile.IsZombie():
			fails.append(strkey)
			print 'Point %s not computed successfully! (ROOT file corrupt)' % (key,)
			summary[key] = {}
			continue

		limits = rfile.Get('limit')
		if not limits:
			print 'Point %s not computed successfully! (limit tree missing)' % (key,)
			summary[key] = {}
			continue
		print 'File', rname
		upper_limits, lower_limits = andrey_harvest_and_outlier_removal(
			#harvest_and_outlier_removal(
			limits, 
			#MAX_LIM=MAX_LIM, 
			plot=rname.replace('.root', '.png')
			)
		#set_trace()
		npass += 1
		if any(len(i) > 1 for i in upper_limits):
			nbisected += 1
		if upper_limits:
			summary[key] = [upper_limits, lower_limits]
		else: summary[key] = []
		
print '''Run Summary:
  Successful jobs: %d
  Failed jobs: %d
  Failed but outside m(H) boudaries: %d
  Number of bisected limits: %d
''' % (npass, len(fails), mis_runs, nbisected)

if fails:
    print 'dumping rescue job'
    with open('%s/condor.rescue.jdl' % args.submission_dir, 'w') as rescue:
        rescue.write(header)
        rescue.write('\n\n')
        rescue.write(
            '\n\n'.join([block_map[key] for key in fails])
            )

vals_list = []
lims = ['obs', 'exp-2', 'exp-1', 'exp0', 'exp+1', 'exp+2']
import numpy as np
for key, item in summary.items():
	mA, tanb = key
	if item:
		vals_list.append(tuple([mA, tanb] + [i[0] for i in item[0]] + [i[0] if i else MAX_LIM for i in item[1]] + [i[1] if len(i) > 1 else (MAX_LIM if j else np.nan) for i, j in zip(item[0], item[1])]))
	else:
		vals_list.append(tuple([mA, tanb] + [np.nan for _ in lims]*3))

with open('%s/summary.npy' % args.submission_dir, 'wb') as out:
    arr = np.array(
        vals_list,
        dtype = [('mA', 'i4'), ('tanb', 'f4')] + [(str(i), 'f4') for i in lims] + [(str(i)+'lower', 'f4') for i in lims] + [(str(i)+'upper', 'f4') for i in lims]
        )
    np.save(out, arr)
