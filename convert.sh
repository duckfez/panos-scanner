#!/bin/bash
#
# Converts palo version list API response from device to the expected format
# Merges new entries into the existing version-list file
#
#
# 1. Log in to PAN-OS Admin UI
# 2. Go to "device" across top menu
# 3. Open browser debug tools, "network" tab
# 4. Click "Software" on left hand nav
# 5. Right click the "Software.get" API call, "Save Reponse As" (on firefox)

TEMP=$( mktemp )
trap "rm $TEMP" EXIT

VERSION_FILE=version-table.txt

jq -r '.result.result.entry[] | [ ( .version ), (.["released-on"] | strptime("%Y/%m/%d %T") | strftime("%b %e %Y") ) ] | @tsv ' $1  | 
	sort -V | awk '{ printf("%-10s %s  %2d  %s\n",$1,$2,$3,$4) }' > ${TEMP}


# Silliness to merge only the changes into the version file
# Maybe this should be a different script
CHANGED=0

while read VER DATE; do
	if ! grep -E -q "^$VER " $VERSION_FILE; then
		CHANGED=1
		printf "%-10s %s\n" "$VER" "$DATE" >> $VERSION_FILE
	fi
done < $TEMP


if [[ $CHANGED -gt 0 ]]; then
	mv $VERSION_FILE $VERSION_FILE.old
	sort -V $VERSION_FILE.old > $VERSION_FILE
	rm $VERSION_FILE.old
fi
