#! /bin/bash

set -o nounset
set -o errexit

#for wdir in $(ls -d [AH]_[0-9]*); do 
combineTool.py -M Asymptotic -d */*/workspace.root --there -n .limit --minimizerTolerance=0.1 --minimizerStrategy=1 --parallel 10 --rMin=0 --rMax=4 $@
#done
