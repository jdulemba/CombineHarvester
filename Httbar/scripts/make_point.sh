#! /bin/env bash

set -o nounset
set -o errexit

#
# Creates a single hMSSM point workspace
# Usage: make_point.sh jobid pointName ASetting HSetting
# A/H setting mini-syntax 'A/H:MASS:WIDTH:kfactor'
#

jobid=$1
kfactorfile=$2
njets=$3
tagname=$4
settings1=$5
settings2=$6

torm=""
toadd=''
for setting in $settings1 $settings2; do
		IFS=':' read -r -a options <<< "$setting"
		for chan in 'lj'; do
		#for chan in 'll' 'lj'; do
				wmorph=temp_$chan'_widthmorph'.$setting.root
                $PROJECT_DIR/scripts/morph_widths.py $CMSSW_BASE/src/CombineHarvester/Httbar/data/$jobid/templates_$chan'_'$njets'_sig_'$jobid.root --single="${options[2]}" \
                        --filter='gg'"${options[0]}"'*' --nocopy --out $wmorph --kfactors=$kfactorfile
				mmorph=temp_$chan'_massmorph'.$setting.root
                $PROJECT_DIR/scripts/morph_mass.py $wmorph $CMSSW_BASE/src/CombineHarvester/Httbar/data/$jobid/templates_$chan'_'$njets'_bkg_'$jobid.root \
                        "${options[0]}" --algo NonLinearPosFractions --single "${options[1]}" --kfactor ${options[3]} --out $mmorph -q
				toadd=$toadd' '$mmorph
				torm=$wmorph' '$torm
		done
done

hadd -f $tagname.root $toadd
rm -r $toadd $torm
