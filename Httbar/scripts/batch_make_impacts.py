#! /bin/env python
from pdb import set_trace
import numpy as np
import os
from distutils import spawn
import subprocess

proj_dir = os.environ['PROJECT_DIR']
pypath = '/'.join(subprocess.Popen("which python", stdout=subprocess.PIPE, shell=True).stdout.read().split('\n')[0].split('/')[:-1])

val2name = lambda x: "%s%s" % (str(x).replace('.','p').replace('p0',''),"pc")
name2val = lambda x: float(x.replace('pc','').replace('p', '.'))

from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument('jobdir', help='Directory that jobs were run from.')
args = parser.parse_args()

orig_jobdir = os.path.join(proj_dir, args.jobdir)
outdir = os.path.join(orig_jobdir, 'IMPACTS')

    # check if jobs have already been submitted
if os.path.isfile(os.path.join(outdir, 'condor.jdl')):
    jdl = open(os.path.join(outdir, 'condor.jdl')).read()
    blocks = jdl.split('\n\n')
    header = blocks[0]
    block_map = {}
    #set_trace()
    for block in blocks[1:]:
        key = 'impacts_%s.pdf' % block.split('Arguments = ')[1].split('\n')[0].split(' ')[-1]
        block_map[key] = block

    #set_trace()
    npass = 0
    fails = []
    for fname, arguments in block_map.items():
        if not os.path.isfile(os.path.join(outdir, fname)):
            fails.append(fname)
        else:
            npass += 1

    #set_trace()
    print('''
Successful jobs: %d
Failed jobs: %d''' % (npass, len(fails)))

        # create and submit rescue jdl file
    if fails:
        print('dumping rescue job')
        with open(os.path.join(outdir, 'condor.rescue.jdl'), 'w') as rescue:
            rescue.write(header)
            rescue.write('\n\n')
            rescue.write(
                '\n\n'.join([block_map[key] for key in fails])
                )
        print('To submit:\ncd %s && condor_submit condor.rescue.jdl' % outdir)

else:
    os.chdir(orig_jobdir)
    
        ## find which mass/width points have been kept in order to find impacts
    points = [fname.split('.')[0] for fname in os.listdir(os.getcwd()) if fname.endswith('.tar')]
    
        ## get file with limits to find median expected coupling to be set in impacts
    pkl_file = 'summary.npy'
    if not os.path.isfile(pkl_file):
        raise ValueError("No summary.npy file found in %s" % args.jobdir)
    limits = np.load(open(pkl_file))
    
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    
        ## write batch_job.sh
    with open(os.path.join(outdir, 'batch_job.sh'), 'w') as batch_job:
        batch_job.write("""#!/bin/bash
    
export PATH={PYPATH}:$PATH
#echo  "which python"
#which python
#
#echo "python path"
#echo $PYTHONPATH
#
#echo "SCRAM_ARCH: " $SCRAM_ARCH

EXE="${{@}}"
echo $EXE

echo "Executing: bash {exe}" $EXE
bash {exe} $EXE

cp */*.pdf {OUTDIR}
""".format(PYPATH=pypath, exe=spawn.find_executable('impacts.sh'), OUTDIR=outdir) )
    
        ## write condor.jdl file
    with open(os.path.join(outdir, 'condor.jdl'), 'w') as jdl:
        jdl.write("""
Should_Transfer_Files = YES
WhenToTransferOutput = ON_EXIT
getenv = True
executable = %s/batch_job.sh
+MaxRuntime = 21600
""" %  outdir)
        idx = 0
        for point in points:
            parity, mass, width = point.split('_')
            if os.path.isfile('%s/impacts_%s.pdf' % (outdir, point)):
                print 'Impacts for %s, %s, %s already evaluated' % (parity, mass, width)
                continue
    
                # find corresponding point in limit
            lim = [lim for lim in limits if lim.tolist()[0:3] == (parity, int(mass), name2val(width))]
            if not lim:
                print 'Limit for %s, %s, %s not available, skipping' % (parity, mass, width)
                continue
            lim = lim[0]
            expected_g = round(lim[6], 5) # expected median limit to fix in impacts
    
            jdl.write("""
Output = con_{idx}.out
Error = con_{idx}.err
Log = con_{idx}.log
Arguments = {TARFILE} {MASS} {COUPLING} {POINT}
Queue
""".format(
            idx=idx,
            TARFILE='%s/%s.tar' % (orig_jobdir, point),
            MASS=mass,
            COUPLING=expected_g,
            POINT=point,
            ))
            idx += 1
    print('To submit:\ncd %s && condor_submit condor.jdl' % outdir)
