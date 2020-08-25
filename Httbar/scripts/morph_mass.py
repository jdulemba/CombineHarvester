#!/usr/bin/env python
from timeit import default_timer as timer

from os import path
import sys
import math
import resource
from argparse import ArgumentParser
from numpy import array
import gc
import numpy as np

parser = ArgumentParser()
parser.add_argument('inputfile')
parser.add_argument('bkgfile', help='used to check binning consistency')
parser.add_argument('parity', choices=['A', 'H'], help='parity of the resonance')
parser.add_argument('--algo', default='NonLinearPosFractions',
										choices=['Linear', 'NonLinear', 'NonLinearPosFractions', 'NonLinearLinFractions', 'SineLinear'],
                    help="Choose morphing algo")
parser.add_argument('--input_masses', default='400,500,600,750',
                    help='comma separated list of masses')
parser.add_argument('--widths', default='0p1,1,2p5,5,10,25,50',
                    help='comma separated list of widths')
parser.add_argument('--stepsize', default='50')
parser.add_argument('--interpolate', default='True')
parser.add_argument('--fortesting', type=int, default=0)
parser.add_argument('--kfactor', type=float, default=1.)
parser.add_argument('--nosystematics', action='store_true')
parser.add_argument('-q', action='store_true', help='quiet')
parser.add_argument('--single', type=int, default=0)
parser.add_argument('--out')

args = parser.parse_args()

import ROOT
from ROOT import TVectorD
from ROOT import RooDataHist, RooArgSet, RooArgList, RooMomentMorph, RooHistPdf
from pdb import set_trace

ROOT.TH1.AddDirectory(False)
ROOT.RooMsgService.instance().setGlobalKillBelow(ROOT.RooFit.WARNING)
ROOT.SetMemoryPolicy( ROOT.kMemoryStrict )

# ALL THE DANGEROUS CONSTANTS IN ONE PLACE
isLJ = ('_lj_' in args.inputfile)
OUTPUT_BINNING_LJ = [300.0, 340.0, 360.0, 380.0, 400.0, 420.0, 440.0, 460.0, 480.0, 500.0, 520.0, 540.0, 560.0, 580.0, 600.0, 625.0, 650.0, 675.0, 700.0, 730.0, 760.0, 800.0, 850.0, 900.0, 1000.0, 1200.0]
OUTPUT_BINNING_LL = [325., 355., 385., 415., 445., 475., 505., 535., 565., 595., 625., 655., 685., 715., 745., 775., 805., 837., 872., 911., 957., 1014., 1094., 1200.]

OUTPUT_BINNING = OUTPUT_BINNING_LJ if isLJ else OUTPUT_BINNING_LL
print 'Using mass binning: ', OUTPUT_BINNING
N_REGIONS = 5
MIN_MASS = 250.0 if isLJ else 325.0
MAX_MASS = 1200.0 if isLJ else 1400.0

TT_KFACTOR = 1.5732 # https://indico.cern.ch/event/663021/contributions/2786263/attachments/1555834/2447515/top_pp_v1.pdf

bkgfile = ROOT.TFile(args.bkgfile)

# Yield interpolation by hand (true) or via RooMorph (false)
do_interpolate = False if not args.interpolate or args.interpolate=='False' else True

available = sorted([int(m) for m in args.input_masses.split(',')])
stepsize = int(args.stepsize)
to_make = [min(available) + (i + 1) *
           stepsize for i in xrange((max(available) - min(available)) / stepsize)]
to_make = [m for m in to_make if m not in available]
if args.fortesting:
	to_make = [args.fortesting]
	if args.fortesting in available:
		available.remove(args.fortesting)
if args.single:
	if args.single in available:
		available = [args.single]
		to_make = []
	else:
		to_make = [args.single]

print 'Output masses:', to_make
print 'Available masses: ', available

val2name = lambda x: "%s%s" % (str(x).replace('.','p').replace('p0',''),"pc")
name2val = lambda x: float(x.replace('pc','').replace('p', '.'))
widths = args.widths.split(',')
widths_vals = [name2val(i) for i in widths]

hyperbolic = lambda width, a, b: (1./width-1./b)/(1./a-1./b)
linear = lambda width, a, b: (width-b)/(a-b)

def graph2arr(graph):
	xs = []
	ys = []
	x = ROOT.Double()
	y = ROOT.Double()
	for i in range(graph.GetN()):
		graph.GetPoint(i, x, y)
		xs.append(float(x))
		ys.append(float(y))
	return array(xs), array(ys)

def graph_interpolation(width, file_int, parity, name_format, interpolation):
	width_value = name2val(width)
	above = min(i for i in widths_vals if i > width_value)
	below = max(i for i in widths_vals if i < width_value)
	g_abv = file_int.Get(name_format.format(parity, val2name(above).replace('pc', '')))
	g_blw = file_int.Get(name_format.format(parity, val2name(below).replace('pc', '')))

	xs, y_above = graph2arr(g_abv)
	_, y_below = graph2arr(g_blw)
	factor = interpolation(width_value, above, below)
	y_new = y_below*(1-factor)+y_above*factor
	ret = g_blw.Clone(name_format.format(parity,width))
	for i, xy in enumerate(zip(xs, y_new)):
		ret.SetPoint(i, xy[0], xy[1])
	g_abv.Delete()
	g_blw.Delete()
	return ret
		

# widths = ['5', '10', '25', '50']

outname = args.inputfile.replace('.root', '_%s_morphed_mass.root' % args.parity)
if args.single:
	outname = outname.replace('morphed_mass', 'M%d' % args.single)
if args.fortesting:
	outname = outname.replace('morphed_mass', 'mass_morph_testing')
if args.out:
	outname = args.out
# shutil.copyfile(args.inputfile, outname)
infile = ROOT.TFile(args.inputfile)
ichunk = 0
outfile = ROOT.TFile(outname, 'RECREATE')

m_ttbar = ROOT.RooRealVar('mass', 'mass', MIN_MASS, MAX_MASS)
m_A = ROOT.RooRealVar('m_A', 'm_A', float(
    min(available)), float(max(available)))

# Get mass interpolation from Viola's file
file_int = ROOT.TFile(path.expandvars(
    '$CMSSW_BASE/src/CombineHarvester/Httbar/data/Spin0_xsecs_vs_mass.root'))
file_int_int = ROOT.TFile(path.expandvars(
    '$CMSSW_BASE/src/CombineHarvester/Httbar/data/Spin0_SEweight_and_NegEvtsFrac_vs_mass.root'))
# pattern_translator = {'pos-sgn':'res', 'pos-int':'int'}


def interpolate(masses, yields, test_mass, linear=True):
    if not linear:
        g = ROOT.TGraph(len(masses), array(
            [float(m) for m in masses]), array(yields))
        # import pdb; pdb.set_trace()
        return g.Eval(float(test_mass), 0)

    from bisect import bisect_left, bisect_right

    i_low = bisect_left(masses, test_mass) - 1
    i_high = bisect_right(masses, test_mass)
    m_below = masses[i_low]
    m_above = masses[i_high]
    y_below = yields[i_low]
    y_above = yields[i_high]
    if i_low == i_high:
        import pdb
        pdb.set_trace()

    delta_m = float(m_above - m_below)
    f_low = (test_mass - m_below) / delta_m
    f_high = (m_above - test_mass) / delta_m
    return f_low * y_below + f_high * y_above

channels = [i.GetName() for i in infile.GetListOfKeys()]
for channel in channels:
    #check for binning consistency
    ttshape = bkgfile.Get('%s/TT' % channel) 
    if not ttshape:
        raise RuntimeError('The provided background file does not include the TT shape for the channel %s' % channel)
    shape_bins = ttshape.GetNbinsX()
    n_bins = (len(OUTPUT_BINNING)-1)*N_REGIONS
    if shape_bins != n_bins:
        raise RuntimeError('The output binning for the signal (%d bins) does not match the one of the background shapes (%d bins)' % (n_bins, shape_bins))
    
    tdir = infile.Get(channel)
    tdir.cd()
    outfile.mkdir(channel)
    mass_id = 'M%d' % available[0]
    h_names = set([key.GetName().replace(mass_id, 'M{MASS}') for key in tdir.GetListOfKeys() if mass_id in key.GetName()])		
    if args.nosystematics:
        h_names = [i for i in h_names if not (i.endswith('Up') or i.endswith('Down'))] #FIXME
    h_names = set([i for i in h_names if not i.endswith('_') and i.startswith('gg%s' % args.parity)])
    h_names = list(h_names)
    print 'Processing', len(h_names), 'different signal templates'
    for h_name in h_names: # it's not very nice - somehow need to make sure we extract all the histogram name but the mass
        start = timer()
        #set_trace()
        tmp_file = ROOT.TFile('_tmp.root', 'RECREATE')
        pattern = h_name[4:11]
        width = h_name.split('-')[2] 
        if not width:
            print 'Did not find width in histogram name', h_name
            import pdb; pdb.set_trace()
            continue
				
        g_int = None
        g_int_neg_frac = None
        if pattern == 'pos-sgn':
            g_int = file_int.Get(
							'pp_{}0_RES_SL_w{}_toterr'.format(
								args.parity.lower(), width.replace('pc','')
								)
							)
            if not g_int:
            	print "interpolating cross sections"
            	#set_trace()
            	g_int = graph_interpolation(
            		width, file_int, args.parity.lower(), 
            		'pp_{}0_RES_SL_w{}_toterr', hyperbolic
            		)
				
        if pattern in ['pos-int', 'neg-int']:
            g_int = file_int_int.Get(
							'pp_{}0_INT_SL_w{}_SEweight'.format(
								args.parity.lower(), width.replace('pc','')
								)
							)
            g_int_neg_frac = file_int_int.Get(
							'pp_{}0_INT_SL_w{}_NegEvts_Frac'.format(
								args.parity.lower(), width.replace('pc','')
								)
							)
            if not g_int:
            	print "interpolating cross sections"
            	#set_trace()
            	g_int = graph_interpolation(
            		width, file_int_int, args.parity.lower(), 
            		'pp_{}0_INT_SL_w{}_SEweight', linear
            		)
            	g_int_neg_frac = graph_interpolation(
            		width, file_int_int, args.parity.lower(),
            		'pp_{}0_INT_SL_w{}_NegEvts_Frac', linear
            		)
            # print pattern
            # for m in [400., 450., 500., 600., 700.]:
            #     print m, g_int.Eval(m) * g_int_neg_frac.Eval(m)
            #     print m, g_int.Eval(m) * (1. - g_int_neg_frac.Eval(m))
				
        if not g_int:
            import pdb; pdb.set_trace()
				
        mass_hists = {}
        mass_scales = {}
        # First get the histograms for all masses
				
        if not args.q: print '\n Processing:', h_name
				
				
        for mass in available:
            # print 'MASS', mass
            #print '{channel}/{h_name}'.format(
            #    channel=channel, h_name=h_name).format(MASS=mass)
            htmp = infile.Get('{channel}/{h_name}'.format(
                channel=channel, h_name=h_name).format(MASS=mass))					
            h_ori = htmp.Clone(
							h_name.format(MASS=mass)
							)
            #print 'MASS', mass, h_ori.GetName()
            htmp.Delete()
				
            scale = 1. / g_int.Eval(mass)
            h_ori.Scale(1. / g_int.Eval(mass))
				
            if pattern == 'pos-int':
                scale *= 1. / (1. - g_int_neg_frac.Eval(mass))
                h_ori.Scale(1. / (1. - g_int_neg_frac.Eval(mass)))
				
            if pattern == 'neg-int':
                scale *= 1. / g_int_neg_frac.Eval(mass)
                h_ori.Scale(1. / g_int_neg_frac.Eval(mass))
            # yields.append(h_ori.Integral())
				
            mass_scales[mass] = scale
            mass_hists[mass] = h_ori
				
				
        eval_time = 0.
        create_time = 0.
				
        # Split input histogram
        if mass_hists[available[0]].GetNbinsY() != N_REGIONS:
            raise RuntimeError(
							'the histogram %s has only %d y bins instead of %d expected' % \
								(h_ori.GetName(), h_ori.GetNbinsY(), N_REGIONS)
							)
        d_hists_region = {}
        for i_costheta in xrange(N_REGIONS):
            d_hists_region[i_costheta] = {}
            pdfs = RooArgList()
            keeper = []
            deleter = []
            vd = TVectorD(len(available))
            yields = []
            for i_m, mass in enumerate(available):
                h_all = mass_hists[mass]
                tmp_file.cd()
                h_region = h_all.ProjectionX(
									channel+h_all.GetName()+str(i_costheta)+"_finebinning",
									i_costheta+1, i_costheta+1
									)
                in_binning = set([h_region.GetBinLowEdge(i) for i in range(1, h_region.GetNbinsX()+2)])
                keeper.append(h_region)
                for i in OUTPUT_BINNING:
                    if i not in in_binning:
                        raise ValueError('Output bin edge %.2f is not included in the input bin edges' % i)
                d_hists_region[i_costheta][mass] = h_region.Rebin(
									len(OUTPUT_BINNING) - 1, 
									h_region.GetName().replace('_finebinning', ''), 
									array(OUTPUT_BINNING)
									)
                d_hists_region[i_costheta][mass].Scale(1./mass_scales[mass])
                yields.append(h_region.Integral())
						
                # if pattern == 'neg-int':
                # 	h_ori.Scale(-1.)
                #set_trace()
                data_hist = RooDataHist(
                    'm' + h_region.GetName().replace('_finebinning', ''), 
										'', RooArgList(m_ttbar), h_region, 1.
										)
                pdf = RooHistPdf(
									'pdf_m' + h_region.GetName().replace('_finebinning', ''),
									'', RooArgSet(m_ttbar), data_hist
									)
                pdfs.add(pdf)
                vd[i_m] = float(mass)
                keeper.append(pdf)
                keeper.append(data_hist)

            setting = getattr(ROOT.RooMomentMorph, args.algo)
            morph = RooMomentMorph(
                'morph' + channel + h_name.format(MASS='000'), '', m_A, RooArgList(m_ttbar), pdfs, vd, setting)
            #morph.useHorizontalMorphing(False)
            # morph.Print('v')

            # print 'Yields', i_costheta, pattern, yields #TORM
            for test_mass in to_make:
                m_A.setVal(float(test_mass))
                tmp_file.cd()
                h_morph_region = h_region.Clone(
                    'MORPH' + h_region.GetName().replace('_finebinning', '').replace(str(available[-1]), str(test_mass)))
						
                for i_bin in xrange(h_morph_region.GetNbinsX()):
								
                    x = h_morph_region.GetBinCenter(i_bin + 1)
                    # print 'mttbar = ', x
                    m_ttbar.setVal(x)
								
                    # for i_pdf in xrange(len(pdfs)):
                    # 	print pdfs[i_pdf].getVal()
                    # print 'Morphed val:', morph.getVal()
								
                    h_morph_region.SetBinContent(
                        i_bin + 1, 
												morph.getVal() * h_morph_region.GetBinWidth(i_bin + 1)
												)
                
                h_morph_region_rebin = h_morph_region.Rebin(
									len(OUTPUT_BINNING) - 1, 
									h_morph_region.GetName().replace('MORPH', ''), 
									array(OUTPUT_BINNING)
									)
								
                if do_interpolate:
                    scale = interpolate(available, yields, test_mass)
                    if scale == 0.:
                        import pdb; pdb.set_trace()
								
                    h_morph_region_rebin.Scale(
                        scale / h_morph_region_rebin.Integral())
                
                h_morph_region_rebin.Scale(g_int.Eval(test_mass))
                if pattern == 'pos-int':
                    h_morph_region_rebin.Scale(1. - g_int_neg_frac.Eval(test_mass))
                if pattern == 'neg-int':
                    h_morph_region_rebin.Scale(g_int_neg_frac.Eval(test_mass))
								
                d_hists_region[i_costheta][test_mass] = h_morph_region_rebin
                h_morph_region.Delete() # Save execution time (->ROOT)
                del h_morph_region # Save execution time (->ROOT)
            morph.Delete()
            del morph
            # Delete items as execution time grows extremely otherwise
            for item in keeper:
                item.Delete()
                del item
        
        # Now collate the hists from the different regions for all masses, including the available
	available_avg_err = []
        for test_mass in available+to_make:
            #even for single points dump everything, we need it to compute uncertainties
            n_bins_out = N_REGIONS*(len(OUTPUT_BINNING) - 1)
            #set_trace()
            outfile.cd()
            outdir = outfile.Get(channel)
            outdir.cd()
            h_out = ROOT.TH1D(d_hists_region[0][test_mass].GetName()[:-1].replace(channel, ''), '', n_bins_out, 0., float(n_bins_out))
                                
            for i_costheta in xrange(N_REGIONS):
                h_part = d_hists_region[i_costheta][test_mass]
                n_bins_part = h_part.GetNbinsX()
                y_t = None
                if test_mass not in available:
                    #assumes that available_avg_err has been properly computed beforehand in the same loop
                    x_b, y_b = min( #below
                        [(i, j) for i, j in available_avg_err if i < test_mass], 
                        key=lambda x: abs(x[0]-test_mass)
                        )
                    x_a, y_a = min( #above
                        [(i, j) for i, j in available_avg_err if i > test_mass], 
                        key=lambda x: abs(x[0]-test_mass)
                        )
                    y_t = (y_a-y_b)*(test_mass-x_b)/(x_a-x_b)+y_b

                for i_bin in xrange(n_bins_part):
                    content = h_part.GetBinContent(i_bin+1)
                    h_out.SetBinContent(i_bin+1 + i_costheta*n_bins_part, content)
                    if test_mass in available:
                        h_out.SetBinError(i_bin+1 + i_costheta*n_bins_part, h_part.GetBinError(i_bin+1))
                    else: 
                        h_out.SetBinError(i_bin+1 + i_costheta*n_bins_part, y_t*math.sqrt(content))
                            
            
            #save average event weight to propagate uncertainties to the signal
            if test_mass in available: 
                vals = []
                errs = []
                for ibin in range(1, h_out.GetNbinsX()+2):
                    val = h_out.GetBinContent(ibin)
                    err = h_out.GetBinError(ibin)
                    if val:
                        vals.append(val)
                        errs.append(err)
                vals = np.array(vals)
                errs = np.array(errs)
                ratios = errs/np.sqrt(vals)
                available_avg_err.append((test_mass, ratios.mean()))

            if args.kfactor != 1:
                if pattern in ['pos-int', 'neg-int']:
                    h_out.Scale(math.sqrt(args.kfactor*TT_KFACTOR))
                else:
                    print 'INFO: Using signal k factor of', args.kfactor
                    h_out.Scale(args.kfactor)

            h_out.Write()
            # print 'Writing', test_mass, h_out.Integral()

        tmp_file.Close()
        ROOT.RooExpensiveObjectCache.instance().clearAll()
        gc.collect()
        for obj in ROOT.gROOT.GetList(): #kill it, with FIRE!
            obj.Delete()
        for hist in mass_hists.itervalues():
            hist.Delete()
        if g_int: g_int.Delete()
        if g_int_neg_frac: g_int_neg_frac.Delete()
        for entry in d_hists_region.itervalues():
            for item in entry.itervalues():
                item.Delete()
                del item
        #set_trace() #d_hists_region
        if not args.q: print 'Time elapsed:', timer() - start
        if not args.q: print 'Peak mem used:', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    outfile.Write()
