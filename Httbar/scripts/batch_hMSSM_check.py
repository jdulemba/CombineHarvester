#! /bin/env python

import os
import pickle
from argparse import ArgumentParser
import json
from pdb import set_trace

parser = ArgumentParser()
parser.add_argument('input_sushi')
parser.add_argument('submission_dir')
args = parser.parse_args()

with open(args.input_sushi) as sushi_pkl:
	mapping = pickle.load(sushi_pkl)

jdl = open('%s/condor.jdl' % args.submission_dir).read()
blocks = jdl.split('\n\n')
header = blocks[0]
block_map = {}
for block in blocks[1:]:
	key = ' '.join(block.split('Arguments = ')[1].split(' ')[1:3])
	block_map[key] = block

summary = {}
npass = 0
fails = []
mis_runs = 0
for entry in mapping.itervalues():
	mA = int(entry['m_A'])
	jname = '%s/mA%d_tanb%.1f.json' % (args.submission_dir, mA, entry['tan(beta)'])
	if not os.path.isfile(jname):
		fails.append('%d %.1f' % (mA, entry['tan(beta)']))
 		print 'Point (%d, %.2f) not computed successfully!' % (mA, entry['tan(beta)'])
		print 'Point Info: '
		print 'mA: %d width: %.2f%%' % (mA, float(entry['A_width'])/mA*100.)
		print 'mH: %.0f width: %.2f%%' % (entry['m_H'], float(entry['H_width'])/entry['m_H']*100.)
		summary[(mA, entry['tan(beta)'])] = {}
	else:
		jmap = json.loads(open(jname).read())
		if len(jmap['120.0']) < 5:
			mis_runs += 1
			fails.append('%d %.1f' % (mA, entry['tan(beta)']))
			print 'Point (%d, %.2f) ran but the result is wrong! (not the full set of infos were dumped)' % (mA, entry['tan(beta)'])
			print 'Point Info: '
			print 'mA: %d width: %.2f%%' % (mA, float(entry['A_width'])/mA*100.)
			print 'mH: %.0f width: %.2f%%' % (entry['m_H'], float(entry['H_width'])/entry['m_H']*100.)
			continue
		npass += 1
		summary[(mA, entry['tan(beta)'])] = jmap['120.0']
		

print '''Run Summary:
  Successful jobs: %d
  Failed jobs: %d
  Out of which jobs not properly finished: %d
''' % (npass, len(fails), mis_runs)

pickle.dump(
	summary, 
	open('summary.pkl', 'wb')
	)

if fails:
	print 'dumping rescue job'
	with open('%s/condor.rescue.jdl' % args.submission_dir, 'w') as rescue:
		rescue.write(header)
		rescue.write('\n\n')
		rescue.write(
			'\n\n'.join([block_map[key] for key in fails])
			)
