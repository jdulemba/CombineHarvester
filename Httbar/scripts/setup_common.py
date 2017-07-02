#!/usr/bin/env python
import os
import argparse

from collections import namedtuple

import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

from ROOT import RooWorkspace, TFile, RooRealVar

import CombineHarvester.CombineTools.ch as ch
from CombineHarvester.CombinePdfs.morphing import BuildRooMorphing

def createProcessNames(widths=['5', '10', '25', '50'], modes=['A'], chan):
	patterns = ['gg{mode}_pos-sgn-{width}pc-M', 'gg{mode}_pos-int-{width}pc-M',  'gg{mode}_neg-int-{width}pc-M']

	procs = {
		'sig': [pattern.format(mode=mode, width=width) for width in widths for pattern in patterns for mode in modes],
		'bkg': ['WJets', 'tWChannel', 'tChannel', 'sChannel', 'VV', 'ZJets', 'TT', 'TTV'],
		# 'bkg_mu':['QCDmujets'], # Ignore QCD for now because of extreme bbb uncertainties
		'bkg_mu':['QCDmujets'],
		'bkg_e':['QCDejets']
	}
	
	procs_ll = {
		'sig': [pattern.format(mode=mode, width=width) for width in widths for pattern in patterns for mode in modes],
		'bkg': ['WJets', 'tWChannel', 'VV', 'ZJets', 'TT', 'TTV'],
	}

	return procs if chan == 'lj' else procs_ll

def prepareDiLepton(cb, procs, in_file, masses=['400', '500', '600', '750']):
	cats = [(0, 'll')]
	cat_to_id = {a:b for b, a in cats}

	cb.AddObservations(['*'], ['httbar'], ['13TeV'], [''], cats)
	cb.AddProcesses(['*'],  ['httbar'], ['13TeV'], [''], procs['bkg'], [(0, 'll')], False)
	cb.AddProcesses(masses, ['httbar'], ['13TeV'], [''], procs['sig'], [(0, 'll')], True)

	print '>> Adding systematic uncertainties...'

	### RATE UNCERTAINTIES

	# THEORY

	LnNUnc = namedtuple('log_n_unc', 'procs name value')

	# lnN uncertainties
	theory_uncs = [
		LnNUnc(['VV'], 'CMS_httbar_VVNorm_13TeV', 1.5),
		LnNUnc(['TT'], 'TTXsec', 1.06), #FIXME?
		LnNUnc(['tWChannel'], 'CMS_httbar_tWChannelNorm_13TeV', 1.15),
		#LnNUnc(['tChannel'], 'CMS_httbar_tChannelNorm_13TeV', 1.20),
		#LnNUnc(['sChannel'], 'CMS_httbar_sChannelNorm_13TeV', 1.20),
		LnNUnc(['WJets'], 'CMS_httbar_WNorm_13TeV', 1.30),
		LnNUnc(['ZJets'], 'CMS_httbar_ZNorm_13TeV', 1.30),
		LnNUnc(['TTW'], 'CMS_httbar_TTVNorm_13TeV', 1.3),
		LnNUnc(['TTZ'], 'CMS_httbar_TTVNorm_13TeV', 1.3),
		LnNUnc(['TTG'], 'CMS_httbar_TTGNorm_13TeV', 1.3),		
	]

	for unc in theory_uncs:
		cb.cp().process(unc.procs).AddSyst(
		cb, unc.name, 'lnN', ch.SystMap()(unc.value))


	# EXPERIMENT
	cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(
		cb, 'lumi', 'lnN', ch.SystMap()(1.025))


	### SHAPE UNCERTAINTIES

	# GENERIC SHAPE UNCERTAINTIES

	shape_uncertainties = [
		'CMS_pileup', 'CMS_eff_b_13TeV', 'CMS_fake_b_13TeV', 
		'CMS_scale_j_13TeV', 'CMS_res_j_13TeV', 'CMS_METunclustered_13TeV',
		'CMS_eff_l', 'CMS_eff_trigger_l',
		]

	for shape_uncertainty in shape_uncertainties:
		cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(cb, shape_uncertainty, 'shape', ch.SystMap()(1.))

	# SPECIFIC SHAPE UNCERTAINTIES
	
	shape_uncertainties_tt = [
		'pdf', 'QCDscaleFSR_TT', 'QCDscaleISR_TT', 'Hdamp_TT', 
		'TMass', 'QCDscaleMERenorm_TT', 'QCDscaleMEFactor_TT'
		]

	for shape_uncertainty in shape_uncertainties_tt:
		cb.cp().process(['TT']).AddSyst(
			cb, shape_uncertainty, 'shape', ch.SystMap()(0.166667 if shape_uncertainty=='TMass' else 1.))

	print '>> Extracting histograms from input root files...'
	cb.cp().backgrounds().ExtractShapes(
		in_file, '$BIN/$PROCESS', '$BIN/$PROCESS_$SYSTEMATIC')
	cb.cp().signals().ExtractShapes(
		in_file, '$BIN/$PROCESS$MASS', '$BIN/$PROCESS$MASS_$SYSTEMATIC')



def prepareLeptonPlusJets(cb, procs, in_file, channel='cmb', masses=['400', '500', '600', '750']):

	cats = [(0, 'mujets'), (1, 'ejets')]
	cat_to_id = {a:b for b, a in cats}

	cb.AddObservations(['*'], ['httbar'], ['13TeV'], [''], cats)

	if channel in ['cmb', 'ej', 'lj']:
		cb.AddProcesses(['*'], ['httbar'], ['13TeV'], [''], procs['bkg'] + procs['bkg_e'], [(1, 'ejets')], False)
		cb.AddProcesses(masses, ['httbar'], ['13TeV'], [''], procs['sig'], [(1, 'ejets')], True)

	if channel in ['cmb', 'mj', 'lj']:
		cb.AddProcesses(['*'], ['httbar'], ['13TeV'], [''], procs['bkg'] + procs['bkg_mu'], [(0, 'mujets')], False)
		cb.AddProcesses(masses, ['httbar'], ['13TeV'], [''], procs['sig'], [(0, 'mujets')], True)

	print '>> Adding systematic uncertainties...'

	### RATE UNCERTAINTIES

	# THEORY

	LnNUnc = namedtuple('log_n_unc', 'procs name value')

	# lnN uncertainties
	theory_uncs = [
		LnNUnc(['VV'], 'CMS_httbar_VVNorm_13TeV', 1.5),
		LnNUnc(['TT'], 'TTXsec', 1.06),
		LnNUnc(['tWChannel'], 'CMS_httbar_tWChannelNorm_13TeV', 1.15),
		LnNUnc(['tChannel'], 'CMS_httbar_tChannelNorm_13TeV', 1.20),
		LnNUnc(['sChannel'], 'CMS_httbar_sChannelNorm_13TeV', 1.20),
		LnNUnc(['WJets'], 'CMS_httbar_WNorm_13TeV', 1.5),
		LnNUnc(['ZJets'], 'CMS_httbar_ZNorm_13TeV', 1.5),
		LnNUnc(['TTV'], 'CMS_httbar_TTVNorm_13TeV', 1.2),
		LnNUnc(['QCDmujets'], 'CMS_httbar_QCDmujetsNorm', 2.0),
		LnNUnc(['QCDejets'], 'CMS_httbar_QCDejetsNorm', 2.0),
	]

	for unc in theory_uncs:
		cb.cp().process(unc.procs).AddSyst(
		cb, unc.name, 'lnN', ch.SystMap()(unc.value))


	# EXPERIMENT
	cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(
		cb, 'lumi', 'lnN', ch.SystMap()(1.025))


	### SHAPE UNCERTAINTIES

	# GENERIC SHAPE UNCERTAINTIES

	shape_uncertainties = ['CMS_pileup', 'CMS_eff_b_13TeV', 'CMS_fake_b_13TeV', 'CMS_scale_j_13TeV', 'CMS_res_j_13TeV', 'CMS_METunclustered_13TeV']

	for shape_uncertainty in shape_uncertainties:
		cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(cb, shape_uncertainty, 'shape', ch.SystMap()(1.))

		if channel in ['cmb', 'mj', 'lj']:
			shape_uncertainties_mu = ['CMS_eff_m']
			for shape_uncertainty in shape_uncertainties_mu:
				cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')([cat_to_id['mujets']], 1.))

		if channel in ['cmb', 'ej', 'lj']:
			shape_uncertainties_e = ['CMS_eff_e']
			for shape_uncertainty in shape_uncertainties_e:
				cb.cp().process(procs['sig'] + procs['bkg']).AddSyst(cb, shape_uncertainty, 'shape', ch.SystMap('bin_id')([cat_to_id['ejets']], 1.))

	# SPECIFIC SHAPE UNCERTAINTIES
	
	shape_uncertainties_tt = ['pdf', 'QCDscaleFSR_TT', 'QCDscaleISR_TT', 'Hdamp_TT', 'TMass', 'QCDscaleMERenorm_TT', 'QCDscaleMEFactor_TT']

	for shape_uncertainty in shape_uncertainties_tt:
		cb.cp().process(['TT']).AddSyst(
			cb, shape_uncertainty, 'shape', ch.SystMap()(0.166667 if shape_uncertainty=='TMass' else 1.))

	print '>> Extracting histograms from input root files...'
	cb.cp().backgrounds().ExtractShapes(
		in_file, '$BIN/$PROCESS', '$BIN/$PROCESS_$SYSTEMATIC')
	cb.cp().signals().ExtractShapes(
		in_file, '$BIN/$PROCESS$MASS', '$BIN/$PROCESS$MASS_$SYSTEMATIC')


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

def writeCards(cb, jobid='dummy', mode='A', width='5', doMorph=False, verbose=True):
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
	writer.WriteCards('output{jobid}/{mode}_{width}'.format(jobid=jobid, mode=mode, width=width), cb)
	# writer.WriteCards('output_comb/', cb)


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('jobid')
	parser.add_argument('--channels' , choices=['ej', 'mj', 'll', 'lj', 'cmb'], help='choose leptonic decay type', default='cmb')
	parser.add_argument('--masses', default='400,500,600,750', help='comma separated list of masses')
	parser.add_argument('--parity', default='A', help='comma separated list of parity (A,H only)')
	parser.add_argument('--widths', default='2p5,5,10,25,50', help='comma separated list of widths')
	parser.add_argument(
		'--noBBB', action='store_false', dest='addBBB', help='add bin-by-bin uncertainties', default=True)
	parser.add_argument(
		'--doMorph', action='store_true', dest='doMorph', help='apply mass morphing', default=False)
	# parser.add_argument(
	#	 '--lj_file', dest='lj_file', default='templates1D_240317.root')
	parser.add_argument(
		'--ll_file', dest='ll_file', default='ttBSM_13TeV_2D_PS_M400_RelW5_tagv3.root')
	parser.add_argument(
		'--silent', action='store_true', dest='silent', default=False)

	args = parser.parse_args()
	addBBB = args.addBBB
	doMorph = args.doMorph

	aux_shapes = os.environ['CMSSW_BASE'] + '/src/CombineHarvester/Httbar/data/'
	in_file_lj = aux_shapes + 'templates_lj_%s.root' % args.jobid #1D_161110
	in_file_lj = aux_shapes + 'templates_ll_%s.root' % args.jobid #1D_161110

	masses = args.masses.split(',')
	widths = args.widths.split(',')#['5', '10', '25', '50'] # in percent
	modes = args.parity.split(',')

	print masses, widths, modes

	for mode in modes:
		for width in widths:

			cb = ch.CombineHarvester()

			if args.channels != 'll':
				procs = createProcessNames([width], [mode], 'lj')
				prepareLeptonPlusJets(cb, procs, in_file_lj, args.channels, masses)

			if args.channels in ['ll', 'cmb']:
				procs = createProcessNames([width], [mode], 'll')
				prepareDiLepton(cb, procs, in_file_ll, masses)

			if addBBB:
				addBinByBin(cb)
			
			if doMorph:
				f_masses = [float(m) for m in masses]
				performMorphing(cb, procs, min(f_masses), max(f_masses))

			writeCards(cb, args.jobid, mode, width, doMorph, verbose=not args.silent)

	print '>> Done!'

