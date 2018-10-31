'''
HOW TO COMPUTE MODEL INDEPENDENT LIMITS FOR H/A SEARCH

1. Computing model independent limits:
   a) for single (mass, width) point for A/H boson:

    python /afs/cern.ch/user/j/jdulemba/Htt_4PJ_Limit/CMSSW_8_1_0/bin/slc6_amd64_gcc530/single_point_limit.py 'jobid' 'parity(A/H)' 'mass' 'width' --runScan --twoPars --barlowBeeston --keep --channels=lj


   b) for multiple  points:

    python scripts/batch_independent_scan.py 'jobid' 'outdir' 'parities' 'masses' 'widths' --runScan --twoPars --barlowBeeston --channels=lj
    
    -creates condor.jdl file in 'jobid' that needs to be submitted with 'condor_submit condor.jdl'


2. Checking output root files for correctness:

   python scripts/batch_independent_check_from_root.py 'outdir'

   a) If files didn't finish correctly a condor.rescue.jdl file will be created, resubmit it
   b) If files finished correctly a summary.npy file will be created that has all the limit info

3. Making plots:

   From within the 'jobid' directory, execute

   python ../scripts/model_independent_limits_ext.py summary.npy

   which will create png files with the limits
'''



''''
PRODUCING hMSSM LIMITS FOR H/A SEARCH

1. Compute hMSSM limits:
   a) Create condor.jdl file
	python scripts/batch_hMSSM_scan.py 'jobid' 'kfactor file' 'output dir'

   b) After submitting jobs, check output files with 
	python scripts/batch_hMSSM_check.py kfactors/sushi_out.pkl 'submission dir'

   c)

2. Making plots:
   From within directory that has the hMSSM files, execute

   python ../scripts/hMSSM_exclusion_plot.py summary.npy

   -- creates exclusion plots from summary files --
