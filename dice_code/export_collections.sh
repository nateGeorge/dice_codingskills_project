#!/bin/bash
# adapted from here: https://gist.github.com/mderazon/8201991
OIFS=$IFS;
IFS=";";
#Accepting Entry form the user
dbname='dice_jobs'
host=localhost:27017

# first get all collections in the database
# for (n in names.length) {names[n] = names[n].replace(' ', '_');}
collections=$(mongo --quiet $dbname --eval "rs.secondaryOk(); var names=db.getCollectionNames().join(';'); names");
echo $collections;

collectionArray=($collections);

# for each collection
for ((i=0; i<${#collectionArray[@]}; ++i));
do
echo 'exporting collection' ${collectionArray[$i]};
mongoexport -d $dbname -c ${collectionArray[$i]} -o /media/nate/nates/github/dice_codingskills_project/${collectionArray[$i]}.json --jsonArray --pretty
done

IFS=$OIFS;