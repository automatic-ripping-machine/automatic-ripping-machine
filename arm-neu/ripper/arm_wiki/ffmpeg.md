# FFMPEG General use
The purpose of this page is to explain the general use of using **Fffmpeg** as a **HandBrake** alternative for video transcoding as it has better support for Hardware Acceleration especially for QSV.

Note: You will have to install drivers and prerequisites for some Hardware Acceleration, and ensure that your GPU/iGPU supports encode of the relevent codec

## USE_FFMPEG flag
Set to true to use ffmpeg instead of Handbreak
Default value is *False*

## FFMPEG_PRE_FILE_ARGS
These are arguments that will be passed in before the `-i "file_name"` use them to control things like:


## FFMPEG_POST_FILE_ARGS
These are arguments that will be passed in after the `-i "file_name"` and before the output file, use them to control things like: 
- subtitle/audio tracks to include in the final output file
- encoded format of the final output file

Use ```ffmpeg -h``` for a full list of arguments but some common ones used are:
- `-c` this is used to select the codec of the output file's audio, video or subtitles (or data), use `ffmpeg -encoders` to get a full list of options
  - `-c:v` used to choose the codec of the output file video, some commonly used optons are:
    - CPU-Only: `libx265`, `libx264`, `libsvtav1`(SVT)
    - Nvidia Nvenc Encoder: `h264_nvenc`, `hevc_nvenc`, `av1_nvenc`
    - AMD AMF Encoder: `h264_amf`, `hevc_amf`, `av1_amf`
    - Intel Quicksync Encoder: `h264_qsv`, `hevc_qsv`, `av1_qsv`
  - `-c:a` used to used to choose the codec of the output file audio use `copy` to copy it from the source file,
  - `-c:s` used to used to choose the codec of the output file subtitles use `copy` to copy it from the source file,

- `-map` this is used to define what tracks are included in the output file, either audio, video or subtitles (or data), it works numerically in the format: "-map input_file_index:track_type:track_index" but can also be handled via metadata using an `m` in place of `track_index`, 
Note: the first parameter defines the file used, this is primarily if you were processing more then one file at once but it should always be set to `0` as ARM transcodes files one at a time
  - `-map 0:a` maps all audio tracks from the source to the destination
  - `-map 0:a:m:language:eng` will map all audio tracks of a certain language (English demonstrated here)
  - `-map 0:a:0` maps just the first audio track, if you want specific numeric audio tracks you can use more then one statement
  - `-map 0:s` maps all subtitle tracks from the source to the destination
  - `-map 0:s:m:language:eng` will map all subtitle tracks of a certain language (English demonstrated here)

## FFMPEG_CLI

Specifies the command used to call **FFmpeg**.  


## FFMPEG_LOCAL

Specifies the **path** to the FFmpeg binary.  
This can be the same as `FFMPEG_CLI`.  
See `HANDBRAKE_LOCAL` for more details.