# Misc notes for future me / developers

## TV Shows (and maybe proper movie titles)

Disc info can be obtained, it returns a lot more information about each disc instead of just the 'is disc inserted'
```makemkvcon -r info disc:[index]```

## Strings returned:

### Drive scan messages

	DRV:index, visible, enabled, flags, drive name, disc name
	index - drive index
	visible - set to 1 if drive is present
	enabled - set to 1 if drive is accessible
	flags - media flags, see AP_DskFsFlagXXX in apdefs.h
	drive name - drive name string
	disc name - disc name string

### Disc information output messages

	TCOUT:count
	count - titles count

### Disc, title and stream information

	CINFO:id,code,value
	TINFO:id,code,value
	SINFO:id,code,value

	id - attribute id, see AP_ItemAttributeId in apdefs.h
	code - message code if attribute value is a constant string
	value - attribute value


#### Example

Title count

	TCOUNT:7

C = Disc info

	CINFO:id,code,value
	CINFO:1,6209,"Blu-ray disc" 
	CINFO:2,0,"Breaking Bad: Season 1: Disc 1"
	CINFO:28,0,"eng"
	CINFO:29,0,"English"
	CINFO:30,0,"Breaking Bad: Season 1: Disc 1"
	CINFO:31,6119,"<b>Source information</b><br>"
	CINFO:32,0,"BREAKINGBADS1"
	CINFO:33,0,"0"

T = Title info

	TINFO:id,code,value
	TINFO:0,2,0,"Breaking Bad: Season 1: Disc 1"
	TINFO:0,8,0,"7"
	TINFO:0,9,0,"0:58:06"
	TINFO:0,10,0,"12.5 GB"
	TINFO:0,11,0,"13472686080"
	TINFO:0,16,0,"00763.mpls"
	TINFO:0,25,0,"1"
	TINFO:0,26,0,"262"
	TINFO:0,27,0,"Breaking_Bad_Season_1_Disc_1_t00.mkv"
	TINFO:0,28,0,"eng"
	TINFO:0,29,0,"English"
	TINFO:0,30,0,"Breaking Bad: Season 1: Disc 1 - 7 chapter(s) , 12.5 GB"
	TINFO:0,31,6120,"<b>Title information</b><br>"
	TINFO:0,33,0,"0"


	2 - Disc Title
	8 - Number of chapters in file
	9 - Length of file in seconds
	10 - File size in GB
	11 - File size in bytes
	27 - File name
	28 - audio short code
	29 - audio long code

S = Details of tracks (video, audio)

	SINFO:id,code,value
	SINFO:3,0,1,6201,"Video"
	SINFO:3,0,5,0,"V_MPEG2"
	SINFO:3,0,6,0,"Mpeg2"
	SINFO:3,0,7,0,"Mpeg2"
	SINFO:3,0,13,0,"9.6 Mb/s"
	SINFO:3,0,19,0,"720x576"
	SINFO:3,0,20,0,"4:3"
	SINFO:3,0,21,0,"25"
	SINFO:3,0,22,0,"0"
	SINFO:3,0,30,0,"Mpeg2"
	SINFO:3,0,31,6121,"<b>Track information</b><br>"
	SINFO:3,0,33,0,"0"
	SINFO:3,0,38,0,""
	SINFO:3,0,42,5088,"( Lossless conversion )"


	20 - File Aspect ratio  #  SINFO
	21 - File FPS  #  SINFO


## Preferred language

```CINFO``` provides title language, config this

	CINFO:28,0,"eng"
	CINFO:29,0,"English"

## Subtitles

	2014-07-21 22:29:18 - Filebot - DEBUG - Get [English] subtitles for 1 files
	2014-07-21 22:29:18 - Filebot - DEBUG - Looking up subtitles by hash via OpenSubtitles
	2014-07-21 22:29:18 - Filebot - DEBUG - Looking up subtitles by name via OpenSubtitles
	2014-07-21 22:29:18 - Filebot - DEBUG - Fetching [Smokin'.Aces.2006.720p.BRRiP.XViD.AC3-LEGi0N.srt]
	2014-07-21 22:29:18 - Filebot - DEBUG - Export [Smokin'.Aces.2006.720p.BRRiP.XViD.AC3-LEGi0N.srt] as: SubRip / UTF-8
	2014-07-21 22:29:18 - Filebot - DEBUG - Writing [Smokin'.Aces.2006.720p.BRRiP.XViD.AC3-LEGi0N.srt] to [Smokin' Aces (2006).eng.srt]



----------------

Originally from https://github.com/JasonMillward/Autorippr/blob/master/NOTES.md


# Info output explained

When running `makemkvcon -r --cache=1 info disc:9999` each line will be a drive and its details

`DRV:0,2,999,1,"DVD-ROM TEAC DVD-ROM DV28SV R.0C","WRATH_OF_THE_TITANS","/dev/sr0"`
the line should then be split by comma and you will get this information.
 
1. Drive number
2. Drive status (empty=0, Open=1, close=2?, loading=3, not-attached=256)
3. Unknown (Always 999)
4. Disc type (cd=0 & null, dvd=1, BD=12,28)
5. Drive details/name
6. Media title/label
7. Drive path
