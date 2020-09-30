#! /bin/env python

import os
from argparse import ArgumentParser
import numpy as np
from scipy.interpolate import interp1d
from pdb import set_trace

from ROOT import TFile

parser = ArgumentParser()
parser.add_argument('submission_dir')
args = parser.parse_args()

jdl = open('%s/condor.jdl' % args.submission_dir).read()
blocks = jdl.split('\n\n')
header = blocks[0]
block_map = {}
for block in blocks[1:]:
    key = tuple(block.split('Arguments = ')[1].split(' ')[1:4])
    block_map[key] = block

MAX_LIM = 3.

summary = {}
npass = 0
fails = []
mis_runs = 0
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
        lims = ['obs', 'exp-2', 'exp-1', 'exp0', 'exp+1', 'exp+2']
        quantiles = [-1, 0.025, 0.160, 0.5, 0.840, 0.975]

        all_cls = [[] for _ in range(len(lims))]


        print 'File', rname
        # First aggregate all CLs values (with the beautiful entry name entry.limit)
        for entry in limits:
            for i_q, quantile in enumerate(quantiles):
                if abs(entry.quantileExpected - quantile) < 0.0001:
                    all_cls[i_q].append((entry.g, entry.limit))


        upper_limits = [[] for _ in range(len(lims))]
        lower_limits = [[] for _ in range(len(lims))]
        limit_previous = [1.]*len(lims)

        # Then outlier removal and  limit determination
        for i_q, quantile in enumerate(quantiles):
            cls_vals = sorted(all_cls[i_q])
            
            cls_vals_plus_g = [(g, cls_val) for g, cls_val in cls_vals if cls_val >= 0. and abs(cls_val - 0.5)>0.001 and cls_val != 0.0]
            cls_vals = [cls_val for _, cls_val in cls_vals_plus_g if cls_val >= 0. and abs(cls_val - 0.5)>0.001 and cls_val != 0.0]
            g_vals = [g_val for g_val, cls_val in cls_vals_plus_g if cls_val >= 0. and abs(cls_val - 0.5)>0.001 and cls_val != 0.0]
            #len_vals = len(cls_vals)

            #set_trace()

                ## find where CLs crosses 0.05
            crossings = np.where(np.diff(np.sign(np.array(cls_vals) - 0.05)))[0] # finds index right before crossing
            np_cls, np_g_vals = np.array(cls_vals), np.around(np.array(g_vals), decimals=2)
            if crossings.size == 0:
                print 'No CLs values cross 0.05, need to investigate...'

            elif crossings.size == 1:
                    # get points before and after crossing to be used in interpolation
                cls_cross = np_cls[crossings[0]:crossings[0]+2]
                g_cross = np_g_vals[crossings[0]:crossings[0]+2]
                    # calculate interpolation and estimated new CLs values between the known points
                f_interp = interp1d(g_cross, cls_cross)
                g_new = np.linspace(g_cross[0], g_cross[1], 101)
                cls_new = f_interp(g_new)
                    # find where closest estimated point to g = 0.05 is
                estimated_g_crossing = g_new[np.where(np.abs(cls_new-0.05) == min(np.abs(cls_new-0.05)))[0]][0]

                if cls_cross[0] > cls_cross[1]: upper_limits[i_q].append(estimated_g_crossing.item()) # CLs values decreasing
                if cls_cross[0] < cls_cross[1]: lower_limits[i_q].append(estimated_g_crossing.item()) # CLs values increasing

            else:
                print 'There are %i crossings' % crossings.size
                upper_lims = []
                lower_lims = []
                for cross_idx in crossings:
                    #set_trace()
                        # get points before and after crossing to be used in interpolation
                    cls_cross = np_cls[cross_idx:cross_idx+2]
                    g_cross = np_g_vals[cross_idx:cross_idx+2]
                        # calculate interpolation and estimated new CLs values between the known points
                    f_interp = interp1d(g_cross, cls_cross)
                    g_new = np.linspace(g_cross[0], g_cross[1], 101)
                    cls_new = f_interp(g_new)
                        # find where closest estimated point to g = 0.05 is
                    estimated_g_crossing = g_new[np.where(np.abs(cls_new-0.05) == min(np.abs(cls_new-0.05)))[0]][0]

                    if cls_cross[0] > cls_cross[1]: upper_lims.append(estimated_g_crossing.item()) # CLs values decreasing
                    if cls_cross[0] < cls_cross[1]: lower_lims.append(estimated_g_crossing.item()) # CLs values increasing

                #set_trace()
                    ## add upper and lower limits
                upper_limits[i_q] = upper_lims if len(upper_lims) > 1 else upper_limits[i_q].append(upper_lims[0]) # CLs values decreasing
                lower_limits[i_q].append(lower_lims) if len(lower_lims) > 1 else lower_limits[i_q].append(lower_lims[0]) # CLs values increasing


        npass += 1
        summary[key] = [upper_limits, lower_limits]

#set_trace()
vals_list = []
for key, item in summary.items():
    #if key == ('A', '750', '5'): set_trace()
    parity, mass, width = key
    mass = int(mass)
    width = float(width)
    if item:
        vals_list.append(tuple([parity, mass, width] + [i[0] for i in item[0]] + [i[0] if i else MAX_LIM for i in item[1]] + [i[1] if len(i) > 1 else (MAX_LIM if j else np.nan) for i, j in zip(item[0], item[1])]))

print '''Run Summary:
  Successful jobs: %d
  Failed jobs: %d
  Out of which jobs not properly finished: %d
''' % (npass, len(fails), mis_runs)

if fails:
    print 'dumping rescue job'
    with open('%s/condor.rescue.jdl' % args.submission_dir, 'w') as rescue:
        rescue.write(header)
        rescue.write('\n\n')
        rescue.write(
            '\n\n'.join([block_map[key] for key in fails])
            )

#set_trace()
with open('%s/summary.npy' % args.submission_dir, 'wb') as out:
    arr = np.array(
        vals_list,
        dtype = [('parity', 'S1'), ('mass', 'i4'), ('width', 'f4')] + [(str(i), 'f4') for i in lims] + [(str(i)+'lower', 'f4') for i in lims] + [(str(i)+'upper', 'f4') for i in lims]
        )
    np.save(out, arr)
