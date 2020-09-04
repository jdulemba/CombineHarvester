#!/usr/bin/env python
#import matplotlib
#import matplotlib.pyplot as plt
#from matplotlib import rcParams
#rcParams['font.size'] = 20
#rcParams["savefig.format"] = 'png'
#rcParams["savefig.bbox"] = 'tight'

from argparse import ArgumentParser
import os
from pdb import set_trace
parser = ArgumentParser()
parser.add_argument('standard', help='Input filepath for standard (mass, width) point')
parser.add_argument('mmorphed', help='Input filepath for mass morphed point')
parser.add_argument('wmorphed', help='Input filepath for width morphed point')
parser.add_argument('doublemorphed', help='Input filepath for mass and width morphed point')
parser.add_argument('output_dir')
parser.add_argument('boson', help='Input boson')
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
if not os.path.isfile(args.mmorphed):
	raise IOError('File %s does not exist!' % args.mmorphed)
if not os.path.isfile(args.wmorphed):
	raise IOError('File %s does not exist!' % args.wmorphed)
if not os.path.isfile(args.doublemorphed):
	raise IOError('File %s does not exist!' % args.doublemorphed)

proc_dict = {
    'pos-sgn' : 'Resonant',
    'neg-int' : 'Int., w < 0',
    'pos-int' : 'Int., w > 0',
}

njets = '3Jets' if '3Jets' in args.standard else '4PJets'

import ROOT

ROOT.gROOT.SetStyle('Plain')
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptTitle(0)

standard = ROOT.TFile.Open(args.standard)
mmorphed = ROOT.TFile.Open(args.mmorphed)
wmorphed = ROOT.TFile.Open(args.wmorphed)
doublem = ROOT.TFile.Open(args.doublemorphed)

for category in categories:
    for process in processes:
        canvas = ROOT.TCanvas('as', 'sad', 800, 600)
            # standard dist
        std = standard.Get('%s/gg%s_%s-%spc-M%d' % (category, args.boson, process, args.width, args.mass))
        std.SetFillStyle(0)
        std.SetLineColor(ROOT.kBlack)
        std.SetLineStyle(1)
        std.SetLineWidth(2)
        std.GetXaxis().SetTitleOffset(1.15)
        std.GetXaxis().SetTitle('m(t#bar{t}) [GeV] #otimes cos #theta*_{t_{lep}}')
        std.GetYaxis().SetTitle('Events')
            # mass morphed dist
        mmorph = mmorphed.Get('%s/gg%s_%s-%spc-M%d' % (category, args.boson, process, args.width, args.mass))
        mmorph.SetFillStyle(0)
        mmorph.SetLineColor(ROOT.kBlue)
        mmorph.SetLineWidth(2)
        mmorph.SetLineStyle(2)
            # width morphed dist
        wmorph = wmorphed.Get('%s/gg%s_%s-checks_%spc-M%d' % (category, args.boson, process, args.width, args.mass))
        wmorph.SetFillStyle(0)
        wmorph.SetLineColor(ROOT.kGreen+2)
        wmorph.SetLineWidth(2)
        wmorph.SetLineStyle(2)
            # mass and width dist
        dmorph = doublem.Get('%s/gg%s_%s-checks_%spc-M%d' % (category, args.boson, process, args.width, args.mass))
        dmorph.SetFillStyle(0)
        dmorph.SetLineColor(ROOT.kRed)
        dmorph.SetLineWidth(2)
        dmorph.SetLineStyle(2)
        std.Draw('h')
        mmorph.Draw('h same')
        wmorph.Draw('h same')
        dmorph.Draw('h same')
        if category == 'll':
            legend = ROOT.TLegend(0.1, 0.7, 0.35, 0.9)
        else:
            legend = ROOT.TLegend(0.65, 0.7, 0.9, 0.9)
        legend.SetHeader("m_{%s}=%i GeV, #Gamma_{%s}/m_{%s}=%.1f%%, %s" % (args.boson, int(args.mass), args.boson, args.boson, float(args.width), proc_dict[process]))
        legend.AddEntry(std, "Nominal simulation", "l")
        legend.AddEntry(mmorph, "Mass interpolation", "l")
        legend.AddEntry(wmorph, "Width interpolation", "l")
        legend.AddEntry(dmorph, "Width and mass interpolation", "l")
        legend.Draw()
        pngname = '%s/mass_morph_%s_%stoTT_%s_%s-%spc-M%d.png' % (output_dir, njets, args.boson, category, process, args.width, args.mass)
        canvas.SaveAs(pngname)
        canvas.SaveAs(pngname.replace('.png', '.pdf'))
