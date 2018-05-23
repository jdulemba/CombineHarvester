# create a model with insane statistics and no real
# deviation except the poisson fluctuations

import math
import json
import os
from array import array
import numpy as np

import ROOT

def reject_outliers(data, m=2.):
    median = np.median(data)
    print '### MEDIAN', median
    print '### DATA  ', sorted(data)
    abs_diffs = [abs(d - median) for d in data]
    mdev = np.median(abs_diffs)
    red_data = [d for d in data if abs(d - median) <= m * mdev]
    if data != red_data:
        print '### REJDATA', sorted(red_data)
    return red_data

def runToy(n_bins=15, addBBB=False, scaling=1./5., n_events=10**6, n_sys=1, sys_shift=1., coherent_shift=1., bbb_scale=1.):
    template = ROOT.TH1F('template', '', n_bins, 0, n_bins)
    evts_per_bin = n_events/n_bins

    tf = ROOT.TFile.Open('cards.root', 'recreate')
    tdir = tf.mkdir('cat0')
    tdir.cd()

    for name in ['bkg'] + ['bkg_Sys{}Up'.format(i) for i in xrange(n_sys)] + ['bkg_Sys{}Down'.format(i) for i in xrange(n_sys)]:
        shape = template.Clone(name)
        scale = 1.
        coh_scale = 1.
        if '0' in name or '1' in name:
            scale = sys_shift if 'Up' in name else 1./sys_shift
            coh_scale = coherent_shift if 'Up' in name else 1./coherent_shift
        for ibin in range(1, shape.GetNbinsX()+2):
            if scaling and evts_per_bin/scaling < 2100000000:
                val = ROOT.gRandom.Poisson(evts_per_bin/scaling) if scaling else evts_per_bin
            else:
                val = evts_per_bin
            shape.SetBinContent(
                ibin, val*scale*coh_scale if ibin == 1 else val*coh_scale)
            # shape.SetBinError(ibin, math.sqrt(val))
            shape.SetBinError(ibin, math.sqrt(
                bbb_scale*val) if scaling and bbb_scale*val > 0. else 0.)
        shape.Scale(scaling if scaling else 1.)  # also scales error
        shape.Write()

    shape = template.Clone('data_obs')
    shape.Write()
    shape = template.Clone('signal')
    for ibin in range(1, shape.GetNbinsX()+2):
        if ibin == 1:
            val = 1000
        # val = 10.*ibin
        else:
            val = 0.1
        shape.SetBinContent(ibin, val)
        # shape.SetBinError(ibin, math.sqrt(val))
    shape.Write()

    tf.Close()

    #
    # Make txt cards
    #
    import CombineHarvester.CombineTools.ch as ch

    def syscall(cmd):
        print '\n\nExecuting: %s\n\n' % cmd
        retval = os.system(cmd)
        if retval != 0:
            raise RuntimeError('Command failed!')

    cb = ch.CombineHarvester()
    cb.AddObservations(['*'], ['toy'], ['13TeV'],
                       [''], [(0, 'cat0')])
    cb.AddProcesses(['*'], ['toy'], ['13TeV'], [''],
                    ['bkg'], [(0, 'cat0')], False)
    cb.AddProcesses(['*'], ['toy'], ['13TeV'], [''],
                    ['signal'], [(0, 'cat0')], True)

    for i in xrange(n_sys):
        cb.cp().process(['bkg']).AddSyst(
            cb, 'Sys{}'.format(i), 'shape', ch.SystMap()(1.)
        )

    cb.cp().backgrounds().ExtractShapes(
        'cards.root', '$BIN/$PROCESS', '$BIN/$PROCESS_$SYSTEMATIC'
    )
    cb.cp().signals().ExtractShapes(
        'cards.root', '$BIN/$PROCESS', '$BIN/$PROCESS_$SYSTEMATIC'
    )

    if addBBB:
        bbb = ch.BinByBinFactory().SetAddThreshold(
            0.).SetFixNorm(False).SetMergeThreshold(0.5)
        bbb.MergeAndAdd(cb.cp().process(['bkg']), cb)

    ch.SetStandardBinNames(cb)
    cb.PrintAll()
    writer = ch.CardWriter(
        '$TAG/$ANALYSIS_$CHANNEL_$BINID.txt',
        '$TAG/$ANALYSIS_$CHANNEL.input.root')
    writer.SetWildcardMasses([])
    writer.SetVerbosity(1)
    limit_dir = 'toy_limits'
    writer.WriteCards(limit_dir, cb)

    #
    # Make workspace
    #
    syscall(
        'combineTool.py -M T2W -i %s -o workspace.root ' % limit_dir
    )
    syscall(
        'combine -M FitDiagnostics -t -1 {}/workspace.root --expectSignal=1'.format(limit_dir)
    )

    f_fit_out = ROOT.TFile('fitDiagnostics.root')
    fit_b = f_fit_out.Get('fit_b')
    

    systs = ['Sys{}'.format(i) for i in xrange(n_sys)]
    constraints = {}
    imps = {}
    signal_strength = [0., 0., 0.]
    for syst in systs:
        if fit_b.status() == 0:
            sys_fit = fit_b.floatParsFinal().find(syst)
            nuisIsSymm = abs(abs(sys_fit.getErrorLo())-abs(sys_fit.getErrorHi())) < 0.01 or sys_fit.getErrorLo() == 0
            if nuisIsSymm:
                constraints[syst] = [-sys_fit.getError(), 0., sys_fit.getError()]
                imps[syst] = 0.
            else:
                import pdb; pdb.set_trace()
        else:
            constraints[syst] = [0., 0., 0.]
            imps[syst] = 0.

    fit_s = f_fit_out.Get('fit_s')
    if fit_s.status() == 0:
        par_r = fit_s.floatParsFinal().find('r')
        signal_strength = [par_r.getErrorLo(), par_r.getVal(), par_r.getErrorHi()]

    # print 'initial fit'
    # syscall('combineTool.py -M Impacts -d %s/workspace.root -m 120 --doInitialFit --robustFit 1 -t -1 --expectSignal=1 &> initial_fit.log' % limit_dir)
    # print 'impacts'
    # syscall('combineTool.py -M Impacts -d %s/workspace.root -m 120 --robustFit 1 --doFits --parallel 8 -t -1 --expectSignal=1 &> impacts.log' % limit_dir)
    # print 'making json'
    # syscall('combineTool.py -M Impacts -d %s/workspace.root -m 120 -o impacts.json' % limit_dir)
    # print 'making plots'
    # syscall('plotImpacts.py -i impacts.json -o impacts')

    # with open('impacts.json') as f_imp:
    #     impacts = json.loads(f_imp.read())
    #     signal_strength = impacts['POIs'][0]['fit']
    #     systs = [p for p in impacts['params'] if 'Sys' in p['name']]
    #     constraints = {s['name']: s['fit'] for s in systs}
    #     imps = {s['name']: s['impact_r'] for s in systs}

    return constraints, imps, signal_strength


def dict_to_graph(d_xy, name, title, x_title='N_{bins}', y_title='Constraint', x_getter=lambda x: x, y_getter=lambda y: y, logx=False):
    n = len(d_xy)
    x, y = array('d'), array('d')

    xy = [(a, b) for a, b in d_xy.iteritems()]

    xy.sort()

    for val_x, val_y in xy:
        x.append(x_getter(val_x))
        y.append(y_getter(val_y))

    c = ROOT.TCanvas()
    c.SetBottomMargin(c.GetBottomMargin()*1.2)
    graph = ROOT.TGraph(n, x, y)
    graph.SetTitle(title)
    graph.Draw('APL')
    graph.SetMarkerSize(1.5)
    graph.SetMarkerStyle(20)
    graph.GetXaxis().SetTitle(x_title)
    graph.GetYaxis().SetTitle(y_title)
    graph.GetYaxis().SetTitleSize(0.05)
    graph.GetYaxis().SetLabelSize(0.05)
    graph.GetXaxis().SetTitleSize(0.05)
    graph.GetXaxis().SetLabelSize(0.05)
    graph.SetMinimum(0.)
    c.SetLogx(logx)
    c.Print(name+'.png')
    c.Print(name+'.pdf')
    c.Print(name+'.root')
    return graph


def createPlot(name, title, addBBB=False, n_sys=1, coherent_shift=1., bbb_scale=1., scaling=1./5., sys_shift=1.):
    constr_vs_n_bins = {}
    r_unc_vs_n_bins = {}
    imp_unc_vs_n_bins = {}
    for n_bins in [1, 2, 3, 4, 5, 10, 20, 40, 60, 80, 100]:
        # if scaling < 1./100. and n_bins < 10: continue
        N_TOYS = 10.
        for _i_toy in xrange(int(N_TOYS)):
            constraints, imps, signal_strength = runToy(
                n_bins=n_bins, addBBB=addBBB, coherent_shift=coherent_shift, bbb_scale=bbb_scale, n_sys=n_sys, scaling=scaling, sys_shift=sys_shift)
            if n_bins in constr_vs_n_bins:
                constr_vs_n_bins[n_bins].append(constraints['Sys0'])
                r_unc_vs_n_bins[n_bins].append(signal_strength[2]-signal_strength[1])
                # imp_unc_vs_n_bins[scaling] = [x + y for x, y in zip(imp_unc_vs_n_bins[scaling], imps['Sys0'])]
                imp_unc_vs_n_bins[n_bins].append(imps['Sys0'])
            else:
                constr_vs_n_bins[n_bins] = [constraints['Sys0']]
                r_unc_vs_n_bins[n_bins] = [signal_strength[2]-signal_strength[1]]
                imp_unc_vs_n_bins[n_bins] = [imps['Sys0']]

        constr_vs_n_bins[n_bins] = [np.mean(reject_outliers([a[i] for a in constr_vs_n_bins[n_bins]])) for i in range(len(constr_vs_n_bins[n_bins][0]))]
        r_unc_vs_n_bins[n_bins] = np.mean(reject_outliers(r_unc_vs_n_bins[n_bins]))
        imp_unc_vs_n_bins[n_bins] = np.mean(reject_outliers(imp_unc_vs_n_bins[n_bins]))

    dict_to_graph(constr_vs_n_bins, name, title,
                  y_getter=lambda y: 0.5*(y[2]-y[0]))
    dict_to_graph(r_unc_vs_n_bins, 'r_'+name,
                  title, y_title='Uncertainty in r')
    dict_to_graph(imp_unc_vs_n_bins, 'imp_'+name, title, y_title='Impact on r')

    print constr_vs_n_bins

def createPlotVsScaling(name, title, addBBB=False, n_sys=1, coherent_shift=1., bbb_scale=1., n_bins=100, sys_shift=1.):
    constr_vs_n_bins = {}
    r_unc_vs_n_bins = {}
    imp_unc_vs_n_bins = {}
    for scaling in [0.00001, 0.0001, 0.001, 0.01, 0.1, 0.5, 1., 5.]:
        # if scaling < 1./100. and n_bins < 10: continue
        N_TOYS = 10.
        for _i_toy in xrange(int(N_TOYS)):
            constraints, imps, signal_strength = runToy(
                n_bins=n_bins, addBBB=addBBB, coherent_shift=coherent_shift, bbb_scale=bbb_scale, n_sys=n_sys, scaling=scaling, sys_shift=sys_shift)
            if scaling in constr_vs_n_bins:
                constr_vs_n_bins[scaling].append(constraints['Sys0'])
                r_unc_vs_n_bins[scaling].append((signal_strength[2]-signal_strength[0])/2.)
                # imp_unc_vs_n_bins[scaling] = [x + y for x, y in zip(imp_unc_vs_n_bins[scaling], imps['Sys0'])]
                imp_unc_vs_n_bins[scaling].append(imps['Sys0'])
            else:
                constr_vs_n_bins[scaling] = [constraints['Sys0']]
                r_unc_vs_n_bins[scaling] = [(signal_strength[2]-signal_strength[0])/2.]
                imp_unc_vs_n_bins[scaling] = [imps['Sys0']]


        

        constr_vs_n_bins[scaling] = [np.mean(reject_outliers([a[i] for a in constr_vs_n_bins[scaling]])) for i in range(len(constr_vs_n_bins[scaling][0]))]
        r_unc_vs_n_bins[scaling] = np.mean(reject_outliers(r_unc_vs_n_bins[scaling]))
        imp_unc_vs_n_bins[scaling] = np.mean(reject_outliers(imp_unc_vs_n_bins[scaling]))

    dict_to_graph(constr_vs_n_bins, name, title, x_title='MC stats scaling',
                  y_getter=lambda y: 0.5*(y[2]-y[0]), logx=True)
    dict_to_graph(r_unc_vs_n_bins, 'r_'+name,
                  title, x_title='MC stats scaling', y_title='Uncertainty in r', logx=True)
    dict_to_graph(imp_unc_vs_n_bins, 'imp_'+name, title, x_title='MC stats scaling', y_title='Impact on r', logx=True)

    print constr_vs_n_bins


if __name__ == '__main__':

    # createPlotVsScaling('scaling_nobbb', 'One uncertainty, no BBB, 100 bins')
    # createPlotVsScaling('scaling_bbb', 'One uncertainty, BBB, 100 bins', addBBB=True)
    # createPlotVsScaling('scaling_bbb_10bins', 'One uncertainty, BBB, 10 bins', addBBB=True, n_bins=10)

    # createPlot('nbins_nobbb', 'One uncertainty, no BBB')
    # createPlot('nbins_bbb', 'One uncertainty, BBB', addBBB=True)
    # createPlot('nbins_3timesbbb', 'One uncertainty, #sqrt{3}BBB', addBBB=True, bbb_scale=3.)
    # createPlot('nbins_10timesbbb',
               # 'One uncertainty, #sqrt{10}BBB', addBBB=True, bbb_scale=10.)
    # createPlot('nbins_100timesbbb',
               # 'One uncertainty, #sqrt{100}BBB', addBBB=True, bbb_scale=100.)

    # createPlot('nbins_nobbb_10sys', '10 uncertainties, no BBB', n_sys=10)
    # createPlot('nbins_bbb_10sys', '10 uncertainties, BBB', addBBB=True, n_sys=10)
    # createPlot('nbins_3timesbbb_10sys', '10 uncertainties, #sqrt{3}BBB', addBBB=True, bbb_scale=3., n_sys=10)

    # createPlot('nbins_bbb_10sys_5000MC', '10 uncertainties, BBB (x 5000 MC)', addBBB=True, n_sys=10, scaling=1./1000.)
    # createPlot('nbins_nostats_10sys', '10 uncertainties, no MC variations', addBBB=True, n_sys=10, scaling=None)

    # createPlot('nbins_nobbb_coh1p2', 'One uncertainty, no BBB, coherent 0.02', coherent_shift=1.02)
    # createPlot('nbins_bbb_coh1p2', 'One uncertainty, BBB, coherent 0.02', addBBB=True, coherent_shift=1.02)
    # createPlot('nbins_3timesbbb_coh1p2', 'One uncertainty, #sqrt{3}BBB, coherent 0.02', addBBB=True, bbb_scale=3., coherent_shift=1.02)

    # createPlot('nbins_nobbb_10sys_coh1p2', '10 uncertainties, no BBB, coherent 0.02', n_sys=10, coherent_shift=1.02)
    # createPlot('nbins_bbb_10sys_coh1p2', '10 uncertainties, BBB, coherent 0.02', addBBB=True, n_sys=10, coherent_shift=1.02)
    # createPlot('nbins_3timesbbb_10sys_coh1p2', '10 uncertainties, BBB, coherent 0.02', addBBB=True, bbb_scale=3., n_sys=10, coherent_shift=1.02)

    # createPlot('nbins_nostats_10sys_coh1p2', '10 uncertainties, no MC variations, coherent 0.02', addBBB=True, n_sys=10, scaling=None, coherent_shift=1.02)

    # createPlot('nbins_nobbb_sys1p1', 'One uncertainty, no BBB, single bin 0.1', sys_shift=1.02)
    # createPlot('nbins_bbb_sys1p1', 'One uncertainty, BBB, single bin 0.1', addBBB=True, sys_shift=1.02)
    # createPlot('nbins_3timesbbb_sys1p1', 'One uncertainty, #sqrt{3}BBB, single bin 0.1', addBBB=True, bbb_scale=3., sys_shift=1.02)

    createPlot('nbins_nostats_sys1p1', 'One uncertainty, no MC variations single bin 0.1', addBBB=True, scaling=None, sys_shift=1.02)

    createPlot('nbins_nobbb_10sys_sys1p1', '10 uncertainties, no BBB, single bin 0.1', n_sys=10, sys_shift=1.02)
    createPlot('nbins_bbb_10sys_sys1p1', '10 uncertainties, BBB, single bin 0.1', addBBB=True, n_sys=10, sys_shift=1.02)

    createPlot('nbins_3timesbbb_10sys_sys1p1', '10 uncertainties, #sqrt{3}BBB, single bin 0.1', addBBB=True, n_sys=10, scaling=1./1000., sys_shift=1.02)
    createPlot('nbins_nostats_10sys_sys1p1', '10 uncertainties, no MC variations, single bin 0.1', addBBB=True, n_sys=10, scaling=None, sys_shift=1.02)
    
