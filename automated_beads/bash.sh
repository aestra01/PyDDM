#!/bin/bash

# print out number of lines in conditions - similar to the csv
#numberoflines=$(sed -n '$=' conditions.txt)
#echo $numberoflines
i=1

# CHANGE THESE WITH NEW EXPERIMENTS 
export CURRENT_DIRECTORY='/Users/rosslabbie/Desktop/Post_PyDDM_Data/1024_5Vids/20240128_100nmBeads_ProgressiveLog/1st_0MUrea/0MUrea_100nmBeads_10msExp_1024.1024_100Urease001/'
export CURRENT_CSV=100nmBeads-Table.csv
export CURRENT_FILENAME_MIDDLE=_100nmBeads_10msExp_MiddleLane_100urease_1024_

pwdesc=$(echo $CURRENT_DIRECTORY | sed 's_/_\\/_g')

# make a directory if it doesn't exist already
mkdir -p results

# look at each line in
## Change name of *.csv file to read input arguments
cat $CURRENT_CSV | while read line 
do
    # inside the while loop
    mkdir -p results/$i

    # copy yaml file into the new directory and name it after the line number
    cp beads.yml results/$i/beads.yml
    echo "Starting run $i with arguments: " 
    echo $line
    linearr=(${line//,/ })
    sed -i -e "s/NEWDIR/${pwdesc}/g" results/$i/beads.yml

    molar=$(awk -F_ '{print $1}' <<< ${linearr[0]})
    filenum=$(awk -F_ '{print $2}' <<< ${linearr[0]})
    sed -i -e "s/NEWFILE/${molar}${CURRENT_FILENAME_MIDDLE}${filenum}.nd2/g" results/$i/beads.yml   
    # column d, line 5
    sed -i -e "s/FRAMEPS/${linearr[3]}/g" results/$i/beads.yml

    #column c, line 8
    sed -i -e "s/ENDFRAME/${linearr[2]}/g" results/$i/beads.yml
    
    # column e, line 9

    sed -i -e "s/LAGTIME/${linearr[4]}/g" results/$i/beads.yml

    # column f, line 11
    sed -i -e "s/LASTTIME/${linearr[5]}/g" results/$i/beads.yml
    
    # column b, line 12
    #export CROP_CHOICE=${linearr[1]}
    #echo ${crops['TopLeft']}
    if [ "${linearr[1]}" == "TopLeft" ];
    then
	sed -i -e "s/CROP/[0,512,0,512]/g" results/$i/beads.yml
    fi

    if [ "${linearr[1]}" == "TopRight" ];
    then
        sed -i -e "s/CROP/[0,512,512,1024]/g" results/$i/beads.yml
    fi

    if [ "${linearr[1]}" == "BottomLeft" ];
    then
        sed -i -e "s/CROP/[512,1024,0,512]/g" results/$i/beads.yml
    fi

    if [ "${linearr[1]}" == "BottomRight" ];
    then
        sed -i -e "s/CROP/[512,1024,512,1024]/g" results/$i/beads.yml
    fi
    
#    ['TopLeft']=[0,512,0,512]
#    ['TopRight']=[0,512,512,1024]
#    ['BottomLeft']=[512,1024,0,512]
#    ['BottomRight']=[512,1024,512,1024]

    #    sed -i -e "s/CROP/${crops[${linearr[1]}]}/g" results/$i/beads.yml
    
    # run the script using the arguments in the line and print (>) the results into a test file
    # move into that directory and do the script before leaving

    
#    python3.11 pyddm_script.py "results/$i/beads.yml"

    #mv q_vs_tau.png results/$i/.
    
    # add to the iterator to keep track of the current line number
    i=$((i+1))
done
