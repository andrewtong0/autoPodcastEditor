from moviepy.editor import *
from scipy.io import wavfile
import subprocess
import math

# GLOBALS
INPUT_FILES = ['input0.mp4', 'input1.mp4']  # List of input files (in local directory)
TEMP_FOLDER = 'tmp/'                        # Temp folder name
INPUT_FOLDER = 'input/'                     # Input folder name
OUTPUT_FOLDER = 'output/'                   # Output folder name
SAMPLE_RATE = 24                            # Number of samples to take per second to check volume level
THRESHOLD = 5                               # Required # of consecutive highest indices needed to take priority
EXCEEDS_BY = 4                              # Percentage (in decimal form) other clip(s) must exceed volume by to overtake

NO_OVERLAP_AUDIO = True                     # Restricts audio overlapping (False = overlap audio)

# HELPER FUNCTIONS

# TAKES RAW WAVEFORM DATA AND CREATES INTEGER WAVEFORM ARRAY
# INPUT: audioRate  = audio sample rate
#        audioArray = associated audio waveform array
# OUTPUT: outputArray = downscaled audioArray based on SAMPLE_RATE
def parseAudioData(audioRate, audioArray):
    sampleDivider = math.floor(audioRate/SAMPLE_RATE)
    outputArray = []
    sampleCounter = 0
    while sampleCounter <= audioArray.shape[0]:
        outputArray.append(audioArray[sampleCounter][0])
        sampleCounter += sampleDivider
    return outputArray


# TAKES ARRAY OF AUDIOARRAYS AND OUTPUTS INDEX ARRAY INDICATING WHICH ARRAY IS LOUDEST AT GIVEN TIME
# INPUT: audioArrays    = array of audioArrays for each clip to compare audio
# OUTPUT: outputArray   = array with indices 1..numArrays indicating which clip should overlay
def compareAudioArrays(audioArrays):
    priorityArray = 0               # Current array that should have video priority (zero-based)
    consecutiveArray = 0            # Which array currently has the highest waveform integer
    prevArray = 0                   # Which array on previous iteration had highest waveform integer
    consecutiveCount = 0            # Number of consecutive times audio is larger than others
    counter = 0                     # Current array index to compare
    outputArray = []

    audioArrays = normalizeArrays(audioArrays)  # Set arrays to equal lengths by concatenating zeroes
    while counter < len(audioArrays[0]):
        consecutiveArray = returnHighestIndex(audioArrays, counter, priorityArray)  # Find index of loudest clip
        # If loudest clip is a different one than the previous loudest clip, add 1 to consecutive counter
        if (consecutiveArray != prevArray):
            prevArray = consecutiveArray
            consecutiveCount = 1
        else:
            consecutiveCount += 1
        # If the overriding loudest clip has been louder >= THRESHOLD # of times, replace it
        if (consecutiveCount >= THRESHOLD):
            priorityArray = consecutiveArray
        outputArray.append(priorityArray)
        counter += 1
    # Write output data to text file (for debugging)
    f = open(TEMP_FOLDER + "audioData.txt", "w")
    f.write(str(outputArray))
    f.close()
    return outputArray


# COMPARES AUDIO WAVEFORMS AT GIVEN TIME AND RETURNS INDEX OF LOUDEST
# INPUT: audioArrays     = array of audio waveforms
#        index           = index to compare waveform integers
#        currentPriority = current array that has priority (for EXCEEDS_BY)
# OUTPUT: rerturnIndex   = index of audioArray with highest waveform integer
def returnHighestIndex(audioArrays, index, currentPriority):
    maxVal = 0                # Maximum waveform value found so far
    returnIndex = 0           # Index of array with highest waveform value
    for c in range(len(audioArrays)):
        if c != currentPriority:
            if abs(audioArrays[c][index]) > maxVal:
                maxVal = abs(audioArrays[c][index])
                returnIndex = c
        else:
            if abs(audioArrays[c][index])*EXCEEDS_BY > maxVal:
                maxVal = abs(audioArrays[c][index])*EXCEEDS_BY
                returnIndex = c
    return returnIndex


# SETS ALL AUDIO ARRAYS TO SAME LENGTH BY CONCATENATING ZEROES TO SHORTER ARRAYS
# INPUT: audioArrays  = array of audio arrays containing integer waveform data
# OUTPUT: outputArray = array of audio arrays all equal length (concatenates 0 to shorter arrays)
def normalizeArrays(audioArrays):
    maxArrayLen = 0
    outputArray = []
    # Get the length of the longest array
    for array in audioArrays:
        if len(array) > maxArrayLen:
            maxArrayLen = len(array)
    # Fill shorter arrays with trailing zeroes
    for array in audioArrays:
        for c in range(maxArrayLen - len(array)):
            array.append(0)
        outputArray.append(array)
    return outputArray


# MAIN PROCESS
audioDataArrays = []
# Generate .wav files for each video clip, create associated outputArray
for i in range(len(INPUT_FILES)):
    # Convert input to audio waveform and call via command in subprocess
    command = "ffmpeg -i " + INPUT_FOLDER + INPUT_FILES[i] + " -ab 160k -ac 2 -y -vn " + TEMP_FOLDER + "audio" + str(i) + ".wav"
    subprocess.call(command, shell=False)
    audioRate, audioArray = wavfile.read(TEMP_FOLDER + 'audio' + str(i) + '.wav')
    audioDataArrays.append(parseAudioData(audioRate, audioArray))
outputArray = compareAudioArrays(audioDataArrays)

# Utilizes outputArray to determine which clips should be split and inserted where
outputClipList = []
audioClipList = []  # Only used if OVERLAP_AUDIO is set to 1
counter = 0
prevPriority = -1
prevEndPt = -1
while counter < len(outputArray):
    # Initialization of loop
    if prevEndPt == -1:
        prevPriority = outputArray[counter]
        prevEndPt = 0
    # If the 'priority clip' is different than previous, finalize previous clip and add to clip list
    elif prevPriority != outputArray[counter]:
        print(str(counter) + " [" + str(prevPriority) + "] || SPLIT_PT: " + "start: " + str(prevEndPt) + " end: " + str(counter/SAMPLE_RATE))
        outputClipList.append(VideoFileClip(INPUT_FOLDER + INPUT_FILES[prevPriority], audio=NO_OVERLAP_AUDIO).subclip(prevEndPt, counter/SAMPLE_RATE))
        prevPriority = outputArray[counter]
        prevEndPt = counter/SAMPLE_RATE
    counter += 1
print(str(counter) + " [" + str(prevPriority) + "] || SPLIT_PT: " + "start: " + str(prevEndPt) + " end: " + str(counter/SAMPLE_RATE))
outputClipList.append(VideoFileClip(INPUT_FOLDER + INPUT_FILES[prevPriority], audio=NO_OVERLAP_AUDIO).subclip(prevEndPt, (counter - 1)/SAMPLE_RATE))
# Concatenate clips and output
videoOutput = concatenate_videoclips(outputClipList)

# If audio should be overlapped, create an audio file with all overlapped and mix with video
if not NO_OVERLAP_AUDIO:
    for wavFileIndex in range(len(INPUT_FILES)):
        audioClipList.append(AudioFileClip(TEMP_FOLDER + "audio" + str(wavFileIndex) + ".wav"))
    audioOutput = CompositeAudioClip(audioClipList)
    videoOutput = videoOutput.set_audio(audioOutput)

videoOutput.write_videofile(OUTPUT_FOLDER + "output-SR" + str(SAMPLE_RATE) + "-T" + str(THRESHOLD) + "-EX" + str(EXCEEDS_BY) + "-OA" + str(int(NO_OVERLAP_AUDIO)) + ".mp4")
