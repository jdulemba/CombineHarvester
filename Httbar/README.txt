'''
HOW TO COMPUTE MODEL INDEPENDENT LIMITS FOR H/A SEARCH

1. Computing model independent limits:
   a) Create condor.jdl file

        For running all points
	python scripts/batch_independent_scan.py {outdir} 'A,H' '400:751:50' '0.5,1,2.5,5,10,25' {njets} --runScan --twoPars --barlowBeeston --channels=lj --keep_nominal
        For evaluating only impacts for generated samples
	python scripts/batch_independent_scan.py {outdir} 'A,H' '400,500,600,750' '0.5,1,2.5,5,10,25' {njets} --runScan --twoPars --barlowBeeston --channels=lj --keep_all

	where {jobid} is part of the template file after sig/bkg_

	To test:
	    From within {outdir}

        python /afs/cern.ch/work/j/jdulemba/Htt_Limit/CMSSW_8_1_0/bin/slc7_amd64_gcc530/single_point_limit.py {arguments from con_0}

	Run all points:
	    From within {outdir}

	    condor_submit condor.jdl


2. Checking output root files for correctness:

   python scripts/batch_independent_check.py {outdir}

   a) If files didn't finish correctly a condor.rescue.jdl file will be created, resubmit it
   b) If files finished correctly a summary.npy file will be created that has all the limit info


3. Making plots:

   a) To make limits plots:
	python scripts/model_independent_limits_ext.py {outdir} 
	python scripts/model_independent_limits_ext.py {outdir} --zoom_out

   b) To make z-score plots:
	python scripts/htt_limit_outlier_plotter.py {outdir}

4. Making Impact plots:
    python scripts/batch_make_impacts.py {outdir}
    submit from IMPACTS directory


'''



''''
PRODUCING hMSSM LIMITS FOR H/A SEARCH

1. Compute hMSSM limits:
   a) Create condor.jdl file

	python scripts/batch_hMSSM_scan.py 'kfactor file' 'output dir' {njets} --channels=lj

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
''''


''''
CHECKING MASS/WIDTH INTERPOLATION

python scripts/morph_checks.py {mass} --{channel} --{njets} --{boson}

where
{mass} can be 500 or 600
{njets}= 3Jets or 4PJets
{boson}=A, H, or all
{channel}=ll, lj, or all
''''


