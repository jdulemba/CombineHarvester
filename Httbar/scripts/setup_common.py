#!/usr/bin/env python
import os
import argparse

from collections import namedtuple

import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

from ROOT import RooWorkspace, TFile, RooRealVar

import CombineHarvester.CombineTools.ch as ch
from CombineHarvester.CombinePdfs.morphing import BuildRooMorphing
from pdb import set_trace
from fnmatch import fnmatch
from glob import glob

#
# ALL Systematic values in only one place
#

#lnN
LnNUnc = namedtuple('log_n_unc', 'procs name value')

common_theory_uncs = [
	LnNUnc(['VV'], 'CMS_httbar_VVNorm_13TeV', 1.5),
	LnNUnc(['TT'], 'TTXsec', 1.06), #FIXME?
	LnNUnc(['tWChannel'], 'CMS_httbar_tWChannelNorm_13TeV', 1.15),
	# LnNUnc(['ZJets'], 'CMS_httbar_ZNorm_13TeV', 1.5), #Removed here - decorrelated for l+j and dilepton
	LnNUnc(['TTV'], 'CMS_httbar_TTVNorm_13TeV', 1.3),
]

ll_theory_uncs = [
	LnNUnc(['ZJets'], 'CMS_httbar_ZNormll_13TeV', 1.5),
	]

lj_theory_uncs = [
	LnNUnc(['tChannel'], 'CMS_httbar_tChannelNorm_13TeV', 1.20),
	LnNUnc(['sChannel'], 'CMS_httbar_sChannelNorm_13TeV', 1.20),
	LnNUnc(['QCDmujets'], 'CMS_httbar_QCDmujetsNorm', 2.0),
	LnNUnc(['QCDejets'], 'CMS_httbar_QCDejetsNorm', 2.0),
	LnNUnc(['WJets'], 'CMS_httbar_WNorm_13TeV', 1.5),
	LnNUnc(['ZJets'], 'CMS_httbar_ZNormlj_13TeV', 1.5),
	]

lumi_unc = 1.025

#shape
common_shape_uncs = [
	'CMS_pileup', 
	#BTAG
	'CMS_eff_b_13TeV', 
	'CMS_fake_b_13TeV', 
]
lj_by_lepton_uncs = {
	'mu' : ['CMS_eff_trigger_m', 'CMS_eff_m'],
	'el' : ['CMS_eff_trigger_e', 'CMS_eff_e']
}
lj_shape_uncs = []
ll_shape_uncs = ['CMS_eff_trigger_l', 'CMS_eff_e', 'CMS_eff_m']

#tt shapes
common_tt_shape_uncs = [
	# Theory
	'CMS_httbar_PDF_alphaS', 'CMS_httbar_PDF_1', 'CMS_httbar_PDF_2', 
	'QCDscaleFSR_TT', 'Hdamp_TT', 
	'TMass', 'QCDscaleMERenorm_TT', 'QCDscaleMEFactor_TT',
	'CMS_TopPt1_TT', 'CMS_TopPt2_TT',
	#JES
	'CMS_scale_j_13TeV_AbsoluteStat',
	'CMS_scale_j_13TeV_AbsoluteScale',
	'CMS_scale_j_13TeV_AbsoluteMPFBias',
	'CMS_scale_j_13TeV_Fragmentation',
	'CMS_scale_j_13TeV_SinglePionECAL',
	'CMS_scale_j_13TeV_SinglePionHCAL',
	'CMS_scale_j_13TeV_FlavorQCD',
	'CMS_scale_j_13TeV_TimePtEta',
	'CMS_scale_j_13TeV_RelativeJEREC1',
	'CMS_scale_j_13TeV_RelativePtBB',
	'CMS_scale_j_13TeV_RelativePtEC1',
	'CMS_scale_j_13TeV_RelativeBal',
	'CMS_scale_j_13TeV_RelativeFSR',
	'CMS_scale_j_13TeV_RelativeStatFSR',
	'CMS_scale_j_13TeV_RelativeStatEC',
	'CMS_scale_j_13TeV_PileUpDataMC',
	'CMS_scale_j_13TeV_PileUpPtRef',
	'CMS_scale_j_13TeV_PileUpPtBB',
	'CMS_scale_j_13TeV_PileUpPtEC1',
	#JER
	'CMS_res_j_13TeV',
	#MET
	'CMS_METunclustered_13TeV'
]
ll_shape_uncertainties_tt = []
lj_shape_uncertainties_tt = [] #missing top pt! #should also LJ remove it?
#ll/TT_QCDscaleMEFactor_ggH-sgnDown
#ll/TT_QCDscaleMERenorm_ggH-sgnDown

#signal shape uncertainties
signal_shape_uncertainties = [
	'QCDscaleMERenorm_ggA-int',
	'QCDscaleMEFactor_ggA-int',
	'QCDscaleMERenorm_ggA-sgn',
	'QCDscaleMEFactor_ggA-sgn',
	
	'QCDscaleMERenorm_ggH-int',
	'QCDscaleMEFactor_ggH-int',
	'QCDscaleMERenorm_ggH-sgn',
	'QCDscaleMEFactor_ggH-sgn',
]

#Bin by bin template
ll_bbb_template = 'TT_CMS_httbar_%s_MCstatBin'
lj_bbb_template = 'TT_CMS_httbar_%s_MCstatBin'

def createProcessNames(widths=['5', '10', '25', '50'], modes=['A'], chan='cmb', masses=None):
	patterns = ['gg{mode}_pos-sgn-{width}pc-M{mass}', 'gg{mode}_pos-int-{width}pc-M{mass}',  'gg{mode}_neg-int-{width}pc-M{mass}']

	procs = {
        'bkg': ['WJets', 'tWChannel', 'tChannel', 'sChannel', 'VV', 'ZJets', 'TT', 'TTV'],
		# 'bkg_mu':['QCDmujets'], # Ignore QCD for now because of extreme bbb uncertainties
		'bkg_mu':['QCDmujets'],
		'bkg_e':['QCDejets']
	}
	procs_ll = {
	    'bkg': ['tWChannel', 'VV', 'ZJets', 'TT', 'TTV'],
	}

	if not any('A:' in x or 'H:' in x for x in widths):
		procs['sig'] = [pattern.format(mode=mode, width=width, mass='') for width in widths for pattern in patterns for mode in modes]
		
		procs_ll['sig'] = [pattern.format(mode=mode, width=width, mass='') for width in widths for pattern in patterns for mode in modes]
	else:
		procs['sig'] = []
		procs_ll['sig'] = []
		for mode in modes:
			mode_masses = [a.split(':')[1] for a in masses if mode+':' in a]
			mode_widths =  [a.split(':')[1] for a in widths if mode+':' in a]
			procs['sig'] += [pattern.format(mode=mode, width=width, mass=mass) for width in mode_widths for pattern in patterns for mass in mode_masses]
			procs_ll['sig'] += [pattern.format(mode=mode, width=width, mass=mass) for width in mode_widths for pattern in patterns for mass in mode_masses]

	return procs if chan == 'lj' else procs_ll

def prepareDiLepton(cb, cat_mapping, procs, in_file, masses=['400', '500', '600', '750'], addBBB=True):
	print '\n\n------------   LL LIMIT SETTING   ------------'
	cat_ids = [cat_mapping[i] for i in ['ll']]
	cats = [(cat_mapping[i], i) for i in ['ll']]

	cb.AddProcesses(['*'],  ['httbar'], ['13TeV'], [''], procs['bkg'], cats, False)
	cb.AddProcesses(masses, ['httbar'], ['13TeV'], [''], procs['sig'], cats, True)

	bbb_systematics = {}
	if addBBB:
		tf = ROOT.TFile(in_file)
		for category in ['ll']:
			cat_dir = tf.Get(category)
			histos = [i.GetName() for i in cat_dir.GetListOfKeys()]
			sys_name = ll_bbb_template % category
			bbbs = [i[3:-2] for i in histos if i.startswith(sys_name) and i.endswith('Up')] #strip tt_...Up
			bbb_systematics[cat_mapping[category]] = bbbs
			print 'found %d bin-by-bin uncertainties for %s' % (len(bbbs), category)
		tf.Close()

	print '>> Adding systematic uncertainties...'

	### RATE UNCERTAINTIES

	# THEORY
	for unc in common_theory_uncs+ll_theory_uncs:
		cb.cp().process(unc.procs).AddSyst(
		cb, unc.name, 'lnN', ch.SystMap('bin_id')(cat_ids, unc.value))

	# EXPERIMENT
	cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(
		cb, 'lumi_13TeV', 'lnN', ch.SystMap('bin_id')(cat_ids, lumi_unc))

	# GENERIC SHAPE UNCERTAINTIES
	for shape_uncertainty in common_shape_uncs+ll_shape_uncs:
		cb.cp().process(
			procs['bkg'] + procs['sig']
			).AddSyst(cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')(cat_ids, 1.))

	# SPECIFIC SHAPE UNCERTAINTIES
	for shape_uncertainty in common_tt_shape_uncs+ll_shape_uncertainties_tt:
		cb.cp().process(['TT']).AddSyst(
			cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')(cat_ids, 0.166667 if shape_uncertainty=='TMass' else 1.))

	#BIN BY BIN
	if addBBB:
		for category, bbbs in bbb_systematics.iteritems():
			for bbb in bbbs:
				cb.cp().process(['TT']).AddSyst(
					cb, bbb, 'shape', ch.SystMap('bin_id')([category], 1.))

	#SIGNAL SHAPE UNCERTAINTIES
	for unc_name in signal_shape_uncertainties:
		info = unc_name.split('_')[1]
		parity, proctype = tuple(info.split('-'))
		cb.cp().process(
			[i for i in procs['sig'] if i.startswith(parity) and ('-%s-' % proctype) in i]
			).AddSyst(
			cb, unc_name, 'shape',
			ch.SystMap('bin_id')(cat_ids, 1.)
			)

def prepareLeptonPlusJets(cb, cat_mapping, procs, in_file, channel='cmb', masses=['400', '500', '600', '750'], addBBB=True):
	print '\n\n------------   L+J LIMIT SETTING   ------------'
	cat_ids = [cat_mapping[i] for i in ['mujets', 'ejets']] \
	    if channel == 'cmb' or channel == 'lj' else \
	    [cat_mapping[i] for i in ['lj']]

	bbb_systematics = {}

	if addBBB:
		tf = ROOT.TFile(in_file)
		for category in (['lj'] if channel == 'cmbLJ' or channel == 'ljmerged' else ['mujets', 'ejets']):
			cat_dir = tf.Get(category)
			histos = [i.GetName() for i in cat_dir.GetListOfKeys()]
			sys_name = lj_bbb_template % category
			bbbs = [i[3:-2] for i in histos if i.startswith(sys_name) and i.endswith('Up')]
			bbb_systematics[cat_mapping[category]] = bbbs
			print 'found %d bin-by-bin uncertainties for %s' % (len(bbbs), category)
		tf.Close()

	if channel in ['cmb', 'ej', 'lj']:
		ecat = [(cat_mapping['ejets'], 'ejets')]
		cb.AddProcesses(['*'], ['httbar'], ['13TeV'], [''], procs['bkg'] + procs['bkg_e'], ecat, False)
		cb.AddProcesses(masses, ['httbar'], ['13TeV'], [''], procs['sig'], ecat, True)

	if channel in ['cmb', 'mj', 'lj']:
		mucat = [(cat_mapping['mujets'], 'mujets')]
		cb.AddProcesses(['*'], ['httbar'], ['13TeV'], [''], procs['bkg'] + procs['bkg_mu'], mucat, False)
		cb.AddProcesses(masses, ['httbar'], ['13TeV'], [''], procs['sig'], mucat, True)

	if channel == 'cmbLJ' or channel == 'ljmerged':
		cat = [(cat_mapping['lj'], 'lj')]
		cb.AddProcesses(
			['*'], ['httbar'], ['13TeV'], [''], 
			procs['bkg'] + procs['bkg_e'] + procs['bkg_mu'], 
			cat, False
			)
		cb.AddProcesses(
			masses, ['httbar'], ['13TeV'], [''], 
			procs['sig'], cat, True
			)

	print '>> Adding systematic uncertainties...'

	### RATE UNCERTAINTIES

	# THEORY
	for unc in common_theory_uncs+lj_theory_uncs:
		cb.cp().process(unc.procs).AddSyst(
		cb, unc.name, 'lnN', ch.SystMap('bin_id')(cat_ids, unc.value)
		)

	# EXPERIMENT
	cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(
		cb, 'lumi_13TeV', 'lnN', ch.SystMap('bin_id')(cat_ids, lumi_unc))

	# GENERIC SHAPE UNCERTAINTIES
	for shape_uncertainty in common_shape_uncs+lj_shape_uncs:
		cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')(cat_ids, 1.))

	if channel in ['cmb', 'mj', 'lj']:
		for shape_uncertainty in lj_by_lepton_uncs['mu']:
			cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(
				cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')([cat_mapping['mujets']], 1.)
				)

	if channel in ['cmb', 'ej', 'lj']:
		for shape_uncertainty in lj_by_lepton_uncs['el']:
			cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(
				cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')([cat_mapping['ejets']], 1.)
				)

	if channel == 'cmbLJ' or channel == 'ljmerged':
		for shape_uncertainty in lj_by_lepton_uncs['mu']:
			cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(
				cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')([cat_mapping['lj']], 1.)
				)
		for shape_uncertainty in lj_by_lepton_uncs['el']:
			cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(
				cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')([cat_mapping['lj']], 1.)
				)

	# SPECIFIC SHAPE UNCERTAINTIES
	for shape_uncertainty in common_tt_shape_uncs+lj_shape_uncertainties_tt:
		cb.cp().process(['TT']).AddSyst(
			cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')(cat_ids, 0.166667 if shape_uncertainty=='TMass' else 1.))

	#BIN BY BIN
	if addBBB:
		for category, bbbs in bbb_systematics.iteritems():
			for bbb in bbbs:
				cb.cp().process(['TT']).AddSyst(
					cb, bbb, 'shape', ch.SystMap('bin_id')([category], 1.))

	#SIGNAL SHAPE UNCERTAINTIES
	for unc_name in signal_shape_uncertainties:
		info = unc_name.split('_')[1]
		parity, proctype = tuple(info.split('-'))
		cb.cp().process(
			[i for i in procs['sig'] if i.startswith(parity) and ('-%s-' % proctype) in i]
			).AddSyst(
			cb, unc_name, 'shape',
			ch.SystMap('bin_id')(cat_ids, 1.)
			)

def addBinByBin(cb):
	bbb = ch.BinByBinFactory().SetAddThreshold(0.).SetFixNorm(False).SetMergeThreshold(0.5)
	bbb.MergeAndAdd(cb.cp().backgrounds(), cb)


def performMorphing(cb, procs, m_min=400., m_max=750., mass_debug=False):
	mA = RooRealVar('MH', 'MH', m_min, m_max) # it's most convenient to call it MH
	mA.setConstant(True)
	
	if mass_debug:
		f_debug = TFile('morph_debug.root', 'RECREATE')

	print 'Try to morph between masses'
	cb.ws = RooWorkspace('httbar', 'httbar') # Add to cb so it doesn't go out of scope
	bins = cb.bin_set()
	for bin in bins:
		for proc in procs['sig']:
			BuildRooMorphing(cb.ws, cb, bin, proc, mA, "norm", True, True, False, f_debug if mass_debug else None)

	if mass_debug:
		f_debug.Close()

	cb.AddWorkspace(cb.ws, False)
	cb.cp().process(procs['sig']).ExtractPdfs(cb, "httbar", "$BIN_$PROCESS_morph", "")

	# void BuildRooMorphing(RooWorkspace& ws, CombineHarvester& cb,
	#			   std::string const& bin, std::string const& process,
	#			   RooAbsReal& mass_var, std::string norm_postfix,
	#			   bool allow_morph, bool verbose, bool force_template_limit, TFile * file)

def writeCards(cb, jobid='dummy', mode='A', width='5', doMorph=False, verbose=True, limitdir = ""):
	print '>> Setting standardised bin names...'
	ch.SetStandardBinNames(cb)
	
	if verbose:
		cb.PrintAll()

	if not doMorph:
		writer = ch.CardWriter('$TAG/$MASS/$ANALYSIS_$CHANNEL_$BINID.txt',
							   # writer = ch.CardWriter('$TAG/$ANALYSIS_$CHANNEL_$BINID_$ERA.txt',
							   '$TAG/$ANALYSIS_$CHANNEL.input.root')
	else:
		writer = ch.CardWriter('$TAG/MORPH/$ANALYSIS_$CHANNEL_$BINID.txt',
							   '$TAG/$ANALYSIS_$CHANNEL.input.root')
		writer.SetWildcardMasses([])
	
	writer.SetVerbosity(1 if verbose else 0)
	if limitdir == "":
	 writer.WriteCards('output{jobid}/{mode}_{width}'.format(jobid=jobid, mode=mode, width=width), cb)
	else:
	 writer.WriteCards('{limitdir}/{mode}_{width}'.format(limitdir=limitdir, mode=mode, width=width), cb)
	# writer.WriteCards('output_comb/', cb)


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('jobid')
	parser.add_argument('--channels' , choices=['ej', 'mj', 'll', 'lj', 'cmb', 'cmbLJ', 'ljmerged'], help='choose leptonic decay type', default='cmb')
	parser.add_argument('--masses', default='400,500,600,750', help='comma separated list of masses')
	parser.add_argument('--parity', default='A', help='comma separated list of parity (A,H only)')
	parser.add_argument('--widths', default='2p5,5,10,25,50', help='comma separated list of widths')
	parser.add_argument(
		'--noBBB', action='store_false', dest='addBBB', help='add bin-by-bin uncertainties', default=True)
	parser.add_argument(
		'--doMorph', action='store_true', dest='doMorph', help='apply mass morphing', default=False)
	parser.add_argument(
		'--silent', action='store_true', dest='silent', default=False)
	parser.add_argument('--indir', default=os.environ['CMSSW_BASE'] + '/src/CombineHarvester/Httbar/data/', help='Input directories containing the data files')
	parser.add_argument('--limitdir', default="", help='Output limit directories') 
	parser.add_argument('--ignore', default="", help='ignore common systematics, supports POSIX regex, comma-separated list') 
	parser.add_argument('--add_sys', default="", help='Add systemactis uncertainties, higher importance than ignoring them') 

	args = parser.parse_args()
	addBBB = args.addBBB
	doMorph = args.doMorph
	if args.ignore:
		for ignore in args.ignore.split(','):
			common_shape_uncs = [i for i in common_shape_uncs if not fnmatch(i, ignore)]
	if args.add_sys:
		common_shape_uncs.extend(args.add_sys.split(','))
	
	aux_shapes = args.indir
	#set_trace()

	in_file = aux_shapes + 'templates_ALL_%s.root' % args.jobid
	in_file_lj = in_file # aux_shapes + 'templates_lj_%s.root' % args.jobid
	in_file_ll = in_file # aux_shapes + 'templates_ll_%s.root' % args.jobid

	masses = args.masses.split(',')
	widths = args.widths.split(',')#['5', '10', '25', '50'] # in percent
	modes = args.parity.split(',')
	
	#define categories
	categories_map = {
		'ej' : ['ejets'],
		'mj' : ['mujets'],
		'll' : ['ll'],
		'lj' : ['mujets', 'ejets'], 
		'cmb' : ['mujets', 'ejets', 'll'],
		'cmbLJ' : ['lj', 'll'],
		'ljmerged' : ['lj'],
		}
	categories = [i for i in enumerate(categories_map[args.channels])]
	category_to_id = {a:b for b, a in categories}

	print masses, widths, modes
    
	special = False
	#set_trace()
	if any('A:' in x or 'H:' in x for x in widths):
		widths = [widths]
		special = True
		modes = [['A', 'H']]
	else:
		modes = [[i] for i in modes]

	for mode in modes:
		for width in widths:
			cb = ch.CombineHarvester()
			cb.AddObservations(['*'], ['httbar'], ['13TeV'], [''], categories)
		
			if args.channels != 'll':
				procs = createProcessNames(width if special else [width], mode, 'lj', masses)
				prepareLeptonPlusJets(cb, category_to_id, procs, in_file_lj if args.channels == 'lj' else in_file, args.channels, [''] if special else masses, addBBB=addBBB)
		
			if args.channels in ['ll', 'cmb', 'cmbLJ']:
				procs = createProcessNames(width if special else [width], mode, 'll', masses)
				prepareDiLepton(cb, category_to_id, procs, in_file_ll if args.channels == 'll' else in_file, [''] if special else masses, addBBB=addBBB)
		
			print '>> Extracting histograms from input root files...'
			cb.cp().backgrounds().ExtractShapes(
				in_file, '$BIN/$PROCESS', '$BIN/$PROCESS_$SYSTEMATIC'
				)
			cb.cp().signals().ExtractShapes(
				in_file, '$BIN/$PROCESS$MASS', '$BIN/$PROCESS$MASS_$SYSTEMATIC'
				)
		
			## if addBBB:
			## 	addBinByBin(cb)
			
			if doMorph:
				f_masses = [float(m) for m in masses]
				performMorphing(cb, procs, min(f_masses), max(f_masses))
			mode_name = '_'.join(mode)
			width_name = width
			if special:
				mode_name = 'A_'
				mode_name += '_'.join([a.split(':')[1] for a in widths[0] + masses if 'A' in a])
				width_name = 'H_'
				width_name += '_'.join([a.split(':')[1] for a in widths[0] + masses if 'H' in a])
			writeCards(cb, '_%s_%s' % (args.channels, args.jobid), mode_name, width_name, doMorph, verbose=not args.silent, limitdir = args.limitdir)
			if not addBBB:
				driname = '/'.join([mode_name+'_'+width_name, '*']) if len(mode) == 1 else mode_name+'_'+width_name
				txt_files = glob('%s/httbar__*.txt' % driname)
				for txt_file in txt_files:
					with open(txt_file, 'a') as txt_card:
						txt_card.write('\n* autoMCStats 0.')


	print '>> Done!'

