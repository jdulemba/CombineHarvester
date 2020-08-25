#!/usr/bin/env python
from argparse import ArgumentParser
import os
parser = ArgumentParser()
parser.add_argument('standard')
parser.add_argument('morphed')
parser.add_argument('doublemorphed')
parser.add_argument('output_dir')
parser.add_argument('--mass', type=int, default=500)
parser.add_argument('--width', default='5')
parser.add_argument('--categories', default='mujets,ejets')
parser.add_argument('--processes', default='pos-sgn,neg-int,pos-int')
args = parser.parse_args()

output_dir = args.output_dir
if not os.path.isdir(output_dir):
	os.makedirs(output_dir)
categories = [i.strip() for i in args.categories.split(',')]
processes = [i.strip() for i in args.processes.split(',')]

if not os.path.isfile(args.standard):
	raise IOError('File %s does not exist!' % args.standard)
if not os.path.isfile(args.morphed):
	raise IOError('File %s does not exist!' % args.morphed)

import ROOT

ROOT.gROOT.SetStyle('Plain')
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptTitle(0)

standard = ROOT.TFile.Open(args.standard)
morphed = ROOT.TFile.Open(args.morphed)
doublem = ROOT.TFile.Open(args.doublemorphed)

for category in categories:
	for process in processes:
		canvas = ROOT.TCanvas('as', 'sad', 800, 600)
		std = standard.Get('%s/ggA_%s-%spc-M%d' % (category, process, args.width, args.mass))
		std.SetFillStyle(0)
		std.SetLineColor(ROOT.kBlack)
		std.SetLineWidth(2)
		std.GetXaxis().SetTitleOffset(1.15)
		std.GetXaxis().SetTitle('m(t#bar{t}) [GeV] #otimes cos #theta*_{t_{lep}}')
		std.GetYaxis().SetTitle('Events')
		morph = morphed.Get('%s/ggA_%s-%spc-M%d' % (category, process, args.width, args.mass))
		morph.SetFillStyle(0)
		morph.SetLineColor(ROOT.kBlue)
		morph.SetLineWidth(2)
		morph.SetLineStyle(2)
		wmorph = standard.Get('%s/ggA_%s-checks_%spc-M%d' % (category, process, args.width, args.mass))
		wmorph.SetFillStyle(0)
		wmorph.SetLineColor(ROOT.kGreen+2)
		wmorph.SetLineWidth(2)
		wmorph.SetLineStyle(2)
		dmorph = doublem.Get('%s/ggA_%s-checks_%spc-M%d' % (category, process, args.width, args.mass))
		dmorph.SetFillStyle(0)
		dmorph.SetLineColor(ROOT.kRed)
		dmorph.SetLineWidth(2)
		dmorph.SetLineStyle(2)
		std.Draw()
		morph.Draw('same')
		wmorph.Draw('same')
		dmorph.Draw('same')
		if category == 'll':
			legend = ROOT.TLegend(0.1, 0.7, 0.35, 0.9)
		else:
			legend = ROOT.TLegend(0.65, 0.7, 0.9, 0.9)
		legend.AddEntry(std, "Full simulation", "l")
		legend.AddEntry(morph, "Mass interpolation", "l")
		legend.AddEntry(wmorph, "Width interpolation", "l")
		legend.AddEntry(dmorph, "Width and mass interpolation", "l")
		legend.Draw()
		pngname = '%s/mass_morph_%s_%s-%spc-M%d.png' % (output_dir, category, process, args.width, args.mass)
		canvas.SaveAs(pngname)
		canvas.SaveAs(pngname.replace('.png', '.pdf'))
		
