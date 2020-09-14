#!/usr/bin/env python

'''
Make morph plots, replace makefile
'''

import os
import pickle
from argparse import ArgumentParser
import shutil
from glob import glob
from pdb import set_trace

parser = ArgumentParser()
parser.add_argument('--mass', default='all', nargs='?', choices=['500', '600', 'all'], help='Choose mass point to check')
parser.add_argument('--channel', default='lj', nargs='?', choices=['ll', 'lj', 'all'])
parser.add_argument('--njets', default='all', nargs='?', choices=['3Jets', '4PJets', 'all'], help='Choose which jet multiplicity to use')
parser.add_argument('--boson', default='all', nargs='?', choices=['A', 'H', 'all'], help='Choose to make plots for one or both bosons')
args = parser.parse_args()

jobid = os.environ['jobid']
proj_dir = os.environ['PROJECT_DIR']

masses = [args.mass] if ((args.mass == '500') or (args.mass == '600')) else ['500', '600']
channels = [args.channel] if ((args.channel == 'll') or (args.channel == 'lj')) else ['lj', 'll']
bosons = [args.boson] if ((args.boson == 'A') or (args.boson == 'H')) else ['A', 'H']
njets = [args.njets] if ((args.njets == '3Jets') or (args.njets == '4PJets')) else ['3Jets', '4PJets']

def syscall(cmd):
    print 'Executing: %s' % cmd
    try:
        os.system(cmd)
    except:
        raise RuntimeError('Command failed! %s' % cmd)

for mass in masses:
    for njet in njets:
        checkdir = '%s/results/%s/checks/%s' % (proj_dir, jobid, njet)
        if not os.path.isdir(checkdir):
           os.makedirs(checkdir)
        
        for chan in channels:
            for boson in bosons:
                # get the FullSim point
                syscall('morph_mass.py {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}.root  {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_bkg_{JOBID}.root {BOSON} --algo NonLinearPosFractions --input_masses 400,500,600,750 --single {MASS} --nosystematics'.format(PROJDIR=proj_dir, CHAN=chan, NJETS=njet, JOBID=jobid, MASS=mass, BOSON=boson))
                
                # make the mass morphed of the same point
                syscall('morph_mass.py {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}.root  {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_bkg_{JOBID}.root {BOSON} --algo NonLinearPosFractions --input_masses 400,500,600,750 --fortesting {MASS} --nosystematics'.format(PROJDIR=proj_dir, CHAN=chan, NJETS=njet, JOBID=jobid, MASS=mass, BOSON=boson))
                
                # morph widths from the extracted 1D FullSim shapes
                syscall('morph_widths.py {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}_{BOSON}_M{MASS}.root --forchecks'.format(PROJDIR=proj_dir, CHAN=chan, NJETS=njet, JOBID=jobid, MASS=mass, BOSON=boson))
                
                ## double morphin, first width
                syscall('morph_widths.py {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}.root --forchecks  --nocopy --out {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}_widthmorphed.root'.format(PROJDIR=proj_dir, CHAN=chan, NJETS=njet, JOBID=jobid))
                # then mass
                syscall('morph_mass.py {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}_widthmorphed.root  {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_bkg_{JOBID}.root {BOSON} --algo NonLinearPosFractions --fortesting {MASS} --nosystematics --out {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}_{BOSON}_M{MASS}_doublemorphed.root'.format(PROJDIR=proj_dir, CHAN=chan, NJETS=njet, JOBID=jobid, MASS=mass, BOSON=boson))
                
                # make plots
                syscall('plot_morph_check.py {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}_{BOSON}_M{MASS}.root {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}_{BOSON}_mass_morph_testing.root {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}_{BOSON}_M{MASS}_width_morphed.root {PROJDIR}/data/{JOBID}/templates_{CHAN}_{NJETS}_sig_{JOBID}_{BOSON}_M{MASS}_doublemorphed.root {CHECKDIR} {BOSON} --mass={MASS}'.format(PROJDIR=proj_dir, CHAN=chan, NJETS=njet, JOBID=jobid, MASS=mass, CHECKDIR=checkdir, BOSON=boson))
