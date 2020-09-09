#! /bin/bash

filter=${4:-"UNSET"}
echo 'filter - '$filter

set -o nounset
set -o errexit

tarfile=$1
mass=$2
coupling=$3
filename="${tarfile%.*}"

echo 'creating directory'
mkdir -p impacts_$filename
cp $tarfile impacts_$filename/.
cd impacts_$filename
echo 'untarring files'
tar -xf $tarfile

echo 'Running initial fit:'
echo "  combineTool.py -M Impacts -d */$mass/workspace.root -m $mass --cminPreScan --X-rtd MINIMIZER_analytic --doInitialFit --robustFit 1 -t -1 --expectSignal=1 --setParameters g=$coupling --freezeParameters g  --redefineSignalPOIs r > initial_fit.log"
combineTool.py -M Impacts -d */$mass/workspace.root -m $mass --cminPreScan --X-rtd MINIMIZER_analytic --doInitialFit --robustFit 1 -t -1 --expectSignal=1 --setParameters g=$coupling --freezeParameters g  --redefineSignalPOIs r > initial_fit.log
if [ "$filter" == "UNSET" ]; then
		echo '  Running impacts:'
        echo "      combineTool.py -M Impacts -d */$mass/workspace.root -m $mass --X-rtd MINIMIZER_analytic --robustFit 1 --cminPreScan --doFits --parallel 8 -t -1 --expectSignal=1 --setParameters g=$coupling --freezeParameters g  --redefineSignalPOIs r &> impacts.log"
		combineTool.py -M Impacts -d */$mass/workspace.root -m $mass --X-rtd MINIMIZER_analytic --robustFit 1 --cminPreScan --doFits --parallel 8 -t -1 --expectSignal=1 --setParameters g=$coupling --freezeParameters g  --redefineSignalPOIs r &> impacts.log
		echo '  Making json'
		combineTool.py -M Impacts -d */$mass/workspace.root -m $mass  --redefineSignalPOIs r -o impacts_$filename.json
else
		echo '  Running impacts:'
        echo "      combineTool.py -M Impacts -d */$mass/workspace.root -m $mass --X-rtd MINIMIZER_analytic --robustFit 1 --cminPreScan --doFits --parallel 8 -t -1 --expectSignal=1 --setParameters g={$coupling} --freezeParameters g  --redefineSignalPOIs r --filter=$filter &> impacts.log"
		combineTool.py -M Impacts -d */$mass/workspace.root -m $mass --X-rtd MINIMIZER_analytic --robustFit 1 --cminPreScan --doFits --parallel 8 -t -1 --expectSignal=1 --setParameters g={$coupling} --freezeParameters g  --redefineSignalPOIs r --filter=$filter &> impacts.log		
		echo '  Making json'
		combineTool.py -M Impacts -d */$mass/workspace.root -m $mass  --redefineSignalPOIs r -o impacts_$filename.json --filter=$filter
fi
echo '  Making plots'
plotImpacts.py -i impacts_$filename.json -o impacts_$filename
cd -
