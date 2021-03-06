filebot \
	-script fn:amc \
	--output "$OUTPUT" \
	--action copy -non-strict \
	"$INPUT" \
	-no-xattr \
	--log-file /mnt/amc.log \
	--conflict auto \
	--def subtitles=en \
	--def excludeList=/mnt/amc.txt \
	--def minLengthMS=300000 \
	--def unsorted=n \
	--def music=y \
	--def movieFormat="{vf == /2160p/ ? 'Movies4K' : 'Movies'}/{n} ({y})/{n} ({y}) [{resolution}]" \
	--def seriesFormat="TV/{localize.English.n}/{episode.special ? 'Special' : 'Season '+s.pad(2)}/{localize.English.n} - {episode.special ? 'S00E'+special.pad(2) : s00e00} - {t} [{resolution}]" \
	--lang English


	# --def subtitles=en \
