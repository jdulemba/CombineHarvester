#!/usr/bin/env python
from argparse import ArgumentParser
import numpy as np
parser = ArgumentParser()
parser.add_argument('inputfile')
parser.add_argument('--forchecks', action='store_true')
parser.add_argument('--nocopy', action='store_true', help='does not copy the file to add the points, but just create the new points')
parser.add_argument('--out', help='forces output name')
parser.add_argument('--kfactors')
parser.add_argument('--single', type=float)
parser.add_argument('--filter', default='*')
#parser.add_argument('--hyperbolic', action='store_true', help='use hyperbolic interpolation')
args = parser.parse_args()

import ROOT
import shutil
import re
from pdb import set_trace
from fnmatch import fnmatch
import json
import os

kfactors = None
if args.kfactors and args.kfactors not in ['None', 'none']:
	if not os.path.isfile(args.kfactors):
		raise IOError('File: %s does not exist' % args.kfactors)
	kfactors = json.loads(open(args.kfactors).read())

mapping = {
  '0p1pc' : .1,
  '1pc' : 1.0,
	'2p5pc' : 2.5,
	'5pc'   : 5.0,
	'10pc'  : 10.,
	'25pc'  : 25.,
	'50pc'  : 50., 
	}

checks = {
	5.0 : 'checks_5pc' ,
	10. : 'checks_10pc',
	25. : 'checks_25pc',	
}

xsections = ROOT.TFile(os.path.expandvars(
    '$CMSSW_BASE/src/CombineHarvester/Httbar/data/Spin0_xsecs_vs_mass.root'))
neg_ratio = ROOT.TFile(os.path.expandvars(
    '$CMSSW_BASE/src/CombineHarvester/Httbar/data/Spin0_SEweight_and_NegEvtsFrac_vs_mass.root'))
		

widths = np.arange(2.5,50,0.5)
val2name = lambda x: "%s%s" % (str(x).replace('.','p').replace('p0',''),"pc")
if args.single:
	widths = [args.single]
new_points = dictionary = dict((i, val2name(i)) for i in widths)
tomove = []
for key in mapping.values():
 if key in new_points: tomove.append(key)
 new_points.pop(key,None)
if args.forchecks:
	new_points = checks

available = set(mapping.values())
to_make = set(new_points.keys())
intersection = available.intersection(to_make)
if len(intersection) and not args.forchecks:
	raise ValueError('the points: %s are already computed, I will not do them again!' % ','.join(list(intersection)))

interpolation = {}
for point in to_make:
	above = [i for i in available if point < i]
	below = [i for i in available if point > i]
	if not above or not below:
		raise ValueError('I cannot interpolate %s as it is outside the provided range!' % point)
	interpolation[point] = (max(below), min(above))

def get_info(name):
	try:
		process, sigint, width, mass_sys = tuple(name.split('-',3))
	except:
		set_trace()
	key = (process, sigint, mass_sys)
	return key, mapping[width]

def make_name(key, width):
	process, sigint, mass_sys = key
	return '-'.join([process, sigint, new_points[width], mass_sys])

outname = args.inputfile.replace('.root', '_width_morphed.root')
if args.out:
	outname = args.out
if args.nocopy:
	infile = ROOT.TFile(args.inputfile)
	outfile = ROOT.TFile(outname, 'recreate')
	outfile.cd()
else:
	shutil.copyfile(args.inputfile, outname)
	infile = ROOT.TFile(outname, 'UPDATE')
	outfile = None

for category in [i.GetName() for i in infile.GetListOfKeys()]:
	counter = 0
	indir = infile.Get(category)
	indir.cd()
	shapes = [i.GetName() for i in indir.GetListOfKeys()]
	if outfile:
		odir = outfile.mkdir(indir.GetName())
		odir.cd()
	else:
		odir = indir
	if args.forchecks:
		shapes = [i for i in shapes if not (i.endswith('Up') or i.endswith('Down'))]
	shapes = [i for i in shapes if (i.startswith('ggA_') or i.startswith('ggH_')) and not i.endswith('_')]
	nMorph = len(shapes)*len(new_points)
	shapes = [i for i in shapes if fnmatch(i, args.filter)]
	counter = 0
	shapes = { "sgn" : (i for i in shapes if '_pos-sgn' in i), "int" : (i for i in shapes if '-int-' in i)}
	#there are still a lot of spurious shapes, remove them
	shapes_map = { "sgn": {}, "int": {}}
	hyperbolic = { "sgn": True, "int": False}
	for _type in shapes:
	 for shape in shapes[_type]:
	  # print shape
	  k, w = get_info(shape)
	  if k not in shapes_map[_type]:
	   shapes_map[_type][k] = {}
	  shapes_map[_type][k][w] = indir.Get(shape)
	  
	  key = '_'.join([
			k[0].split('_')[0]+'_'+k[1],
			k[2][:4], #remove everything after the mass
			'%.1f' % w
	  ])
	  
	  if kfactors:
	   if key not in kfactors:
	    print 'WARNING: k-factors: skipping key %s as not found in json' % key
	    continue
	   shapes_map[_type][k][w].Scale(kfactors[key])
	
	#extrapolation (if needed)
	print 'Extrapolating to 1% width'
	for width_value, width_name in [(1., '1'), (0.1, '0p1')]:
		for val in shapes_map.itervalues():
			for info, vval in val.iteritems():
				parity_and_sign, proc, mass = info
				mass = int(mass[1:4])
				parity = parity_and_sign[2]
				sign = parity_and_sign[-3:]
				proc = proc.replace('sgn', 'res')
				xsec_2p5 = xsections.Get(
					'pp_{}0_RES_SL_w2p5_toterr'.format(parity.lower())
					).Eval(mass) \
					if proc == 'res' else \
					neg_ratio.Get(
						'pp_{}0_INT_SL_w2p5_SEweight'.format(parity.lower())
						).Eval(mass)
		
				xsec_1 = xsections.Get(
					'pp_{}0_RES_SL_w{}_toterr'.format(parity.lower(), width_name)
					).Eval(mass) \
					if proc == 'res' else \
					neg_ratio.Get(
						'pp_{}0_INT_SL_w{}_SEweight'.format(parity.lower(), width_name)
						).Eval(mass)
				
				if proc == 'int':
					frac_2p5 = neg_ratio.Get(
						'pp_{}0_INT_SL_w2p5_NegEvts_Frac'.format(parity.lower())
						).Eval(mass)
					frac_1 = neg_ratio.Get(
						'pp_{}0_INT_SL_w{}_NegEvts_Frac'.format(parity.lower(), width_name)
						).Eval(mass)
					xsec_2p5 *= frac_2p5 if sign == 'neg' else (1-frac_2p5)
					xsec_1 *= frac_1 if sign == 'neg' else (1-frac_1)
					
				vval[width_value] = vval[2.5].Clone(
					vval[2.5].GetName().replace('2p5', width_name)
					)
				vval[width_value].Scale(xsec_1/xsec_2p5)
	
	#compute new histograms
	for _type in shapes_map:
	 for key in shapes_map[_type]:
	  if args.nocopy:
	   for point in tomove:
	    shapes_map[_type][key][point].Write()
	  for width in new_points.keys():
	   b, a = interpolation[width]
	   if hyperbolic[_type]:
	    factor = (1./width-1./b)/(1./a-1./b)
	   else:
	    factor = (width-b)/(a-b)
	   below = shapes_map[_type][key][b]
	   above = shapes_map[_type][key][a]
	   new_name = make_name(key, width)
	   new_hist = below.Clone(new_name)
	   new_hist.Scale(1-factor)
	   new_hist.Add(above, factor)
	   new_hist.Write()
	   counter += 1
	   if counter % 10 == 0:
		   print "Category-{} done: {}/{}".format(category,counter,nMorph)
