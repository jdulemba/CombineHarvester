#!/usr/bin/env python
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('jsons', nargs='+', help='json_file:label')
#FIXME add auto labels
parser.add_argument('-x', default='', help='x label')
parser.add_argument('-y', default='', help='y label')
parser.add_argument('-t', default='', help='title')
parser.add_argument('-o', default='out.png', help='output')
parser.add_argument('--autolabels', action='store_true', help='output')
parser.add_argument(
	'--use', choices=["exp+1", "exp+2", "exp-1", "exp-2", "exp0", 'obs'], 
	default='exp0', help='to use')
args = parser.parse_args()

from ROOT import gROOT, TCanvas, TGraph, TLegend
import json
import uuid
import os
from pdb import set_trace

def json2graph(jfile, topick):
	jinfo = json.loads(open(jfile).read())
	points = [(float(i), j[topick]) for i, j in jinfo.iteritems()]
	points.sort()
	gr = TGraph(len(points))
	for i, xy in enumerate(points):
		gr.SetPoint(i, xy[0], xy[1])
	gr.SetMarkerStyle(20)
	return gr, min(i[1] for i in points), max(i[1] for i in points)

uid = str(uuid.uuid1())
canvas = TCanvas(uid, uid, 800, 800)
legend = TLegend(0.1,0.7,0.48,0.9);
keep = []
ms = []
Ms = []
colors = [1, 2, 4, 8, 28, 46, 14, 41, 9]#[2,4,6,8,28,46,14,31,1]
if len(colors) < len(args.jsons):
	raise RuntimeError('I have more limits than colors to display them!')

first=True
for jfilelabel, color in zip(args.jsons, colors):
	if not args.autolabels:
		jfile, label = tuple(jfilelabel.split(':'))
	else:
		jfile = jfilelabel
		split = os.path.basename(jfile).split('_')
		if len(split) == 3:
			label = split[0]
		else:
			label = split[1]
			
	graph, m, M = json2graph(jfile, args.use)
	ms.append(m)
	Ms.append(M)
	graph.SetMarkerColor(color)
	graph.SetLineColor(color)
	legend.AddEntry(graph, label, 'lp')
	graph.SetTitle(args.t)
	keep.append(graph)

for graph in keep:
	if first:
		graph.Draw('ALP')
		graph.GetYaxis().SetRangeUser(min(ms)*0.8, max(Ms)*1.2)
		graph.GetXaxis().SetTitle(args.x)
		graph.GetYaxis().SetTitle(args.y)
		first = False
	else:
		graph.Draw('LP same')

legend.Draw()
canvas.SaveAs(args.o)
