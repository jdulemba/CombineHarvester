'''
HOW TO COMPUTE MODEL INDEPENDENT LIMITS FOR H/A SEARCH

1. Computing model independent limits:
   a) Create condor.jdl file

	python scripts/batch_independent_scan.py {jobid} {outdir} 'A,H' '400:751:50' '2.5,5,10,25' --runScan --twoPars --barlowBeeston --channels=lj

	where {jobid} is part of the template file after sig/bkg_

	To test:
	    From within {outdir}

	    python /afs/cern.ch/user/j/jdulemba/Htt_4PJ_Limit/CMSSW_8_1_0/bin/slc6_amd64_gcc530/single_point_limit.py {arguments from con_0}

	Run all points:
	    From within {outdir}

	    condor_submit condor.jdl


2. Checking output root files for correctness:

   python scripts/batch_independent_check_from_root.py {outdir}

   a) If files didn't finish correctly a condor.rescue.jdl file will be created, resubmit it
   b) If files finished correctly a summary.npy file will be created that has all the limit info

3. Making plots:

   a) To make limits plots:
	From within {outdir}, execute
	
	python ../scripts/model_independent_limits_ext.py summary.npy

   b) To make z-score plots:
	python scripts/htt_limit_outlier_plotter.py {outdir}
'''



''''
PRODUCING hMSSM LIMITS FOR H/A SEARCH

1. Compute hMSSM limits:
   a) Create condor.jdl file

	python scripts/batch_hMSSM_scan.py 'jobid' 'kfactor file' 'output dir' --channels=lj

	To test:
	   python /afs/cern.ch/user/j/jdulemba/Htt_4PJ_Limit/CMSSW_8_1_0/bin/slc6_amd64_gcc530/produce_morph_files_tanb_mA.py 'Arguments from con_0'

	Run all points: from 'output dir'
	   condor_submit condor.jdl

   b) After submitting jobs, check output files with 
	python scripts/batch_hMSSM_check.py kfactors/sushi_out.pkl 'submission dir'

   c)

2. Making plots:
   From within directory that has the hMSSM files, execute

   python ../scripts/hMSSM_exclusion_plot.py summary.npy

   -- creates exclusion plots from summary files --
