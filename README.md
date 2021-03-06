# autoPodcastEditor
A program made for video podcasts to expedite the editing process by automatically switching video clips based on who is talking

### See it in action!
[![Demo Video](https://i.imgur.com/ClN1S6f.png)](https://www.youtube.com/watch?v=kMJ4Bx4BBBo&feature=youtu.be)

Made a short video explaining what autoPodcastEditor does with examples (9:43).
Timestamps
- 0:00 - What it does and why
- 2:30 - Introduction to example clips
- 3:40 - First input clip display
- 4:27 - Second input clip display
- 5:35 - Quick explanation on global variables (sample rate, tolerance, exceed req. no audio overlap)
- 6:57 - First example of program combining clips (audio overlap)
- 8:19 - Second example of program combining clips (no audio overlap)

### What it does and why
- Many modern video podcasts have cameras pointed at each participant, which makes the editing process long and tedious. The process of selecting whose camera to show when they're talking is a chore that could be done autonomously. This program aims to solve that.
- autoPodcastEditor exports a final video clip that switches between the cameras of each podcast participant depending on who's talking to make the editing process a breeze.
- Use cases besides podcasts include things like D&D campaigns, group video game sessions, or even security camera footage to highlight significant events (assuming they have sound).

### Dependencies
- **ffmpeg** - converts video clips to audio waveform arrays (great installation instructions can be found [here](https://www.wikihow.com/Install-FFmpeg-on-Windows))
- **subprocess** - calls ffmpeg commands via command line
- **moviepy** - concatenates and exports video clips
- **math** - processes split point calculations

### How it works
- ffmpeg converts the input files to audio clips (.wav files) and converts the audio clips to integer arrays representing the audio waveform levels throughout the clips
- parseAudioData() cleans the audio arrays and shrinks them to an appropriate size based on the SAMPLE_RATE global
- compareAudioArrays() 'normalizes' all of the arrays (i.e. makes them all the same length by concatenating zeroes; representing no sound, to shorter arrays), compares each entry of the cleaned audio arrays (using returnHighestIndex() to do so), and outputs an array of numbers representing which clip should be displayed based on its audio level at a given time (number is zero based, from 0 to number_input_clips - 1)
- returnHighestIndex() compares the audio level at a given time between all clips, but gives the current clip priority - the EXCEEDS_BY global indicates by what percentage (in decimal form) another clip must exceed the current clip by in sound level to take priority; returns the index of the clips that should be given priority
- After compareAudioArrays() generates the outputArray (priority timeline of which clip should be shown when), moviepy grabs the snippets of the video clips and concatenates them appropriately

### Notes
- All video clips must be synced at the start (i.e. synced at time = 0s) differing lengths of clips is fine, though (longer clips will override)
- Does not currently support separate video + audio clips (planning on adding support soon)
- Plan to add an option overlapping audio so you can hear audio from all clips simultaneously (mainly for podcasts where multiple people may be talking at once, since the program's main purpose is video switching)
- No testing has been done for quality retainment and file size - unsure whether quality is dropped via the script or if there is a maximum file size limit

Clips and audio must already be set to right startpoint 
Quality testing
Bound SAMPLE_RATE positive and less than or equal to native rate



### Compatibility
- Confirmed working on Windows 10, have not confirmed on other operating systems
