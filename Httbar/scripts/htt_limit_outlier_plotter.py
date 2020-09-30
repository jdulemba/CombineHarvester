import os
from argparse import ArgumentParser
import json
from ROOT import TFile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pdb import set_trace
from matplotlib.ticker import (MultipleLocator, FormatStrFormatter,
                               AutoMinorLocator)
from matplotlib import rcParams
plt.rc('text', usetex=True)
plt.rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
rcParams['text.latex.preamble']=[
    r"\usepackage{amsmath}",
]
rcParams["mathtext.default"] = 'regular'
rcParams['font.size'] = 20
rcParams["savefig.format"] = 'png'
rcParams["savefig.bbox"] = 'tight'

parser = ArgumentParser()
parser.add_argument('submission_dir')
args = parser.parse_args()

val2name = lambda x: "%s%s" % (str(x).replace('.','p').replace('p0',''),"pc")
name2val = lambda x: float(x.replace('pc','').replace('p', '.'))

jdl = open('%s/condor.jdl' % args.submission_dir).read()
blocks = jdl.split('\n\n')
header = blocks[0]
block_map = {}
for block in blocks[1:]:
    key = tuple(block.split('Arguments = ')[1].split(' ')[1:4])
    block_map[key] = block

MAX_LIM = 3.
STEP_SIZE = 0.01

summary = {}
npass = 0
fails = []
mis_runs = 0
produced = None
for key, submit in block_map.iteritems():
    parity, mass, width = key
    # width = ('%.1f' % float(width)).replace('.', 'p').replace('p0', '')
    width = width.rstrip('.').replace('.', 'p')
    name = '_'.join([parity, mass, width])
    rname = '%s/%s_limits_gathered.root' % (args.submission_dir, name)
    if not os.path.isfile(rname):
        fails.append(key)
        print 'Point %s not computed successfully! (ROOT file missing)' % (key,), rname
        summary[key] = {}
    else:
        rfile = TFile.Open(rname)
        if rfile.IsZombie():
            fails.append(key)
            print 'Point %s not computed successfully! (ROOT file corrupt)' % (key,)
            summary[key] = {}
            continue
    
    limits = rfile.Get('limit')
    
    #set_trace()
    expected_cls = np.array( [entry.limit for entry in limits if abs(entry.quantileExpected - 0.5) < 0.0001 if entry.limit > 0.0 if entry.limit != 0.5] )
    expected_g = np.array( [entry.g for entry in limits if abs(entry.quantileExpected - 0.5) < 0.0001 if entry.limit > 0.0 if entry.limit != 0.5] )
    observed_cls = np.array( [entry.limit for entry in limits if abs(entry.quantileExpected - -1.) < 0.0001 if entry.limit > 0.0 if entry.limit != 0.5] )
    observed_g = np.array( [entry.g for entry in limits if abs(entry.quantileExpected - -1.) < 0.0001 if entry.limit > 0.0 if entry.limit != 0.5] )
    
    print rname
    #set_trace()
    
    num_pt_comp = 3 # number of points on either side of point to be used for finding mean, stdev
    
    
                ##### try my outlier removal
    	### deal with CLs close to 0.5
    invalid_g = []
    invalid_cls = []
    invalid_inds = []
    
    lim0p5_idx = np.where( abs(observed_cls-0.5) < 0.05)[0] # indices where cls is close to 0.5
    consec = [i for i, df in enumerate(np.diff(lim0p5_idx)) if df!= 1]
    consec = np.hstack([-1, consec, len(lim0p5_idx)-1])
    consec = np.vstack([consec[:-1]+1, consec[1:]]).T
    consec = consec.astype(np.int64)
    first_inds = lim0p5_idx[consec][:,0] if lim0p5_idx.any() else lim0p5_idx # first indices of consecutive indices (could be standalone values)
    last_inds = lim0p5_idx[consec][:,1] if lim0p5_idx.any() else lim0p5_idx # first indices of consecutive indices (could be standalone values)
    # large jump from previous CLs value
    cls_jump = [abs(observed_cls[idx]-observed_cls[idx-1]) > 0.2 for idx in first_inds]
    #set_trace() 
    for j,k in enumerate(cls_jump):
        if k == True:
            for val in range(first_inds[j], last_inds[j]+1):
        	    invalid_cls.append( observed_cls[val] )
        	    invalid_g.append( observed_g[val] )
        	    invalid_inds.append( val )
    
    if invalid_inds:
        print 'Points have been removed for being outliers close to CLs = 0.5'
        #set_trace() 
    
    ### get rid of invalid indices
    observed_inds = [x for x in range(len(observed_cls)) if x not in invalid_inds]
    observed_cls = observed_cls[observed_inds]
    observed_g = observed_g[observed_inds]
    #set_trace() 
    
    z_scores = -1*np.ones(len(observed_cls))
    for i in range(len(observed_cls)):
        if i < num_pt_comp: # indices on lower edge of values
                #set_trace()
                bracket = observed_cls[:num_pt_comp+1]
                excluded = bracket[bracket != bracket[i]] # remove value corresponding to current index
                mean, std = excluded.mean(), excluded.std(ddof=1) #uses unbiased estimator for stdev
                z_scores[i] = np.nan if abs((bracket[i] - mean)/std) == np.inf else abs((bracket[i] - mean)/std)
    
        elif i >= len(observed_cls) - num_pt_comp: # indices on upper edge of values
                bracket = observed_cls[-num_pt_comp-1:]
                excluded = bracket[bracket != bracket[(i+num_pt_comp)-len(observed_cls)]] # remove value corresponding to current index
                mean, std = excluded.mean(), excluded.std(ddof=1) #uses unbiased estimator for stdev
                z_scores[i] = np.nan if abs((bracket[(i+num_pt_comp)-len(observed_cls)] - mean)/std) == np.inf else abs((bracket[(i+num_pt_comp)-len(observed_cls)] - mean)/std)
                #set_trace()
    
        else: # indices in middle 
                bracket = observed_cls[i-num_pt_comp:i+num_pt_comp+1]
                excluded = np.concatenate((bracket[:num_pt_comp], bracket[-num_pt_comp:]))
                mean, std = excluded.mean(), excluded.std(ddof=1) #uses unbiased estimator for stdev
                z_scores[i] = np.nan if abs((bracket[num_pt_comp] - mean)/std) == np.inf else abs((bracket[num_pt_comp] - mean)/std)
                #if i > 179: set_trace()
    
        if z_scores[i] > 2.0:
            print 'Limit value marked as outlier by z-score, continue, g = ', observed_g[i]
    #set_trace()
    
    #set_trace()
      ## find outlier indices
    outliers_inds = np.where(z_scores > 2.0)
    outliers_cls = observed_cls[ outliers_inds ]
    outliers_g = observed_g[ outliers_inds ]
    outliers_z = z_scores[ outliers_inds ]
    
    #set_trace()
      ## find valid and non-outlier indices from observed
    usable_inds = [x for x in range(len(observed_cls)) if x not in outliers_inds[0]]
    usable_cls = observed_cls[ usable_inds ]
    usable_g = observed_g[ usable_inds ]
    usable_z = z_scores[ usable_inds ]
    #if i == 0: continue
    
        # plot CLs and z scores vs g
    #set_trace()
    figtitle = r'm$_{\mathrm{\mathsf{%s}}}$ = %s\, GeV, $\Gamma_{\mathrm{\mathsf{%s}}}$/m$_{\mathrm{\mathsf{%s}}}$ = {%.1f}\%%' % (parity, mass, parity, parity, name2val(width))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=[10,10], gridspec_kw={"height_ratios": (1, 1)}, sharex=True)
    fig.subplots_adjust(hspace=.07)
    fig.suptitle('%s Limits and z-scores' % figtitle)
    
        ### plot limits
    ax1.scatter(usable_g, usable_cls, color='k', label='Observed')
    ax1.scatter(expected_g, expected_cls, color='g', label='Median exp.')
    if invalid_inds:
        ax1.scatter(invalid_g, invalid_cls, color='b', label='Invalid Points')
    if outliers_inds:
        ax1.scatter(outliers_g, outliers_cls, color='r', label='Outliers')
    ax1.grid(which='both')
    ax1.axhline(0.05, color='r', linestyle='--')
    ax1.set_xlim(0.0, round(observed_g.max()+0.1,2))
    ax1.set_ylim(0.001, 1.2)
    ax1.set_ylabel('$CL_{S}$')
    ax1.set_yscale('log')
    ax1.legend(loc='lower left', fontsize=8, scatterpoints=1)
    
        ### plot z-scores
    ax2.scatter(usable_g, usable_z, color='k', label='Observed')
    if outliers_inds:
        ax2.scatter(outliers_g, outliers_z, color='r', label='Outliers')
    ax2.grid(which='both')
    ax2.set_xlim(0.0, round(observed_g.max()+0.1,2))
    ax2.set_ylim(0.001, z_scores[ z_scores > 0. ].max()+1)
    ax2.set_xlabel('g')
    ax2.set_ylabel('z-score')
    ax2.legend(loc='lower left', fontsize=8, scatterpoints=1)
    ax2.set_yscale('log')
    #fig.savefig('test')
    #set_trace()
    fig.savefig('%s/%s_M%s_%s_limits_and_zscores.png' % (args.submission_dir, parity, mass, width))
    print '%s/%s_M%s_%s_limits_and_zscores.png    created' % (args.submission_dir, parity, mass, width)	
    plt.close()
