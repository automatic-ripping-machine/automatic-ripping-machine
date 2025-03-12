# The .abcde.conf config file

 This is the config file for abcde, it only contains settings for the ripping of music CD's. 

The default location for this file is `/home/arm/.abcde.conf`

[Abcde Manual](https://linux.die.net/man/1/abcde) This is the full manual/user-guide covering each of the settings in the abcde.conf file. 
Here is some of the changes you can make with this file.

  - Metadata provider (default is musicbrainz - **Do not change this unless you know what you're doing** )
  - Output-type
    - 11 to choose from (ogg, mp3**, flac, aac, opus, etc.)
  - Output directory
  - Output formatting (artist-album or artist/album, etc.) 
  - Playlist
  - Merge CD into single track (for live albums)
  - Eject disc after rip is complete
  - Number of encoders to run at once
  - Lots of advanced settings



You can view the full file here  [.abcde.conf](https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/setup/.abcde.conf)