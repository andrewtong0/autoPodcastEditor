from moviepy.editor import *
from tkinter import *
from tkinter.filedialog import askopenfilename
from scipy.io import wavfile
import subprocess
import math

# GLOBALS
INPUT_FILES = []                            # List of input files (in local directory)
TEMP_FOLDER = 'tmp/'                        # Temp folder name
OUTPUT_FOLDER = 'output/'                   # Output folder name
OUTPUT_FILE_NAME = "output"                 # Output file name
SAMPLE_RATE = 24                            # Number of samples to take per second to check volume level
THRESHOLD = 5                               # Required # of consecutive highest indices needed to take priority
EXCEEDS_BY = 4                              # Percentage (in decimal form) other clip(s) must exceed volume by to overtake
NO_OVERLAP_AUDIO = True                     # Restricts audio overlapping (False = overlap audio)


# INTERNAL GLOBALS (DO NOT TOUCH)
checkpoints = []  # Global storing tuples of array length + associated index, sorted from min-max by array length
checkpoint_counter = 0  # Determines which checkpoint currently at
ul_x = 10
ul_y = 10

# GUI CREATION
class Window(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master = master
        self.init_window()

    def init_window(self):
        self.master.title("AutoPodcastEditor")
        self.pack(fill=BOTH, expand=1)
        sync_notice = Label(self, text="Please ensure all input clips are in sync at start and don't go out of sync!")
        sync_notice.place(x=ul_x, y=ul_y)
        browseFileDir = Button(self, text="Add File", command=self.addFile)
        browseFileDir.place(x=ul_x, y=ul_y+25)

        sampleRateLabel = Label(self, text="Sample Rate")
        sampleRateLabel.place(x=ul_x, y=ul_y + 320)
        self.sampleRateEntry = Entry(self, width=3)
        self.sampleRateEntry.place(x=ul_x + 73, y=ul_y + 321)
        self.sampleRateEntry.insert(END, str(SAMPLE_RATE))

        thresholdLabel = Label(self, text="Threshold")
        thresholdLabel.place(x=ul_x + 120, y=ul_y + 320)
        self.thresholdEntry = Entry(self, width=3)
        self.thresholdEntry.place(x=ul_x + 65 + 120, y=ul_y + 321)
        self.thresholdEntry.insert(END, str(THRESHOLD))

        exceedsLabel = Label(self, text="Exceeds By")
        exceedsLabel.place(x=ul_x + 235, y=ul_y + 320)
        self.exceedsEntry = Entry(self, width=3)
        self.exceedsEntry.place(x=ul_x + 65 + 235, y=ul_y + 321)
        self.exceedsEntry.insert(END, str(EXCEEDS_BY))

        overlapAudioLabel = Label(self, text="Overlap Audio")
        overlapAudioLabel.place(x=ul_x + 345, y=ul_y + 320)
        self.overlapAudioBox = Checkbutton(self, command=self.toggleAudio)
        self.overlapAudioBox.place(x=ul_x + 65 + 360, y=ul_y + 319)

        outputNameLabel = Label(self, text="Output File Name")
        outputNameLabel.place(x=ul_x, y=ul_y + 345)
        self.outputNameEntry = Entry(self, width=57)
        self.outputNameEntry.place(x=ul_x + 102, y=ul_y + 346)
        self.outputNameEntry.insert(END, OUTPUT_FILE_NAME)

        processButton = Button(self, text="Process", command=self.confirmSettings, width=15, height=3)
        processButton.place(x=ul_x + 460, y=ul_y + 310)

    def confirmSettings(self):
        global SAMPLE_RATE
        SAMPLE_RATE = int(self.sampleRateEntry.get())
        global THRESHOLD
        THRESHOLD = int(self.thresholdEntry.get())
        global EXCEEDS_BY
        EXCEEDS_BY = float(self.exceedsEntry.get())
        global OUTPUT_FILE_NAME
        OUTPUT_FILE_NAME = self.outputNameEntry.get()
        self.spliceClips()

    def toggleAudio(self):
        global NO_OVERLAP_AUDIO
        NO_OVERLAP_AUDIO = not NO_OVERLAP_AUDIO

    def addFile(self):
        filename = askopenfilename()
        if filename != '':
            INPUT_FILES.append(filename)
            fileDir = Label(self, text=filename)
            fileDir.place(x=ul_x, y=ul_y+28+23*len(INPUT_FILES))

    # HELPER FUNCTIONS

    # TAKES RAW WAVEFORM DATA AND CREATES INTEGER WAVEFORM ARRAY
    # INPUT: audioRate  = audio sample rate
    #        audioArray = associated audio waveform array
    # OUTPUT: outputArray = downscaled audioArray based on SAMPLE_RATE
    def parseAudioData(self, audioRate, audioArray):
        sampleDivider = math.floor(audioRate / SAMPLE_RATE)
        outputArray = []
        sampleCounter = 0
        while sampleCounter <= audioArray.shape[0]:
            outputArray.append(audioArray[sampleCounter][0])
            sampleCounter += sampleDivider
        return outputArray

    # TAKES ARRAY OF AUDIOARRAYS AND OUTPUTS INDEX ARRAY INDICATING WHICH ARRAY IS LOUDEST AT GIVEN TIME
    # INPUT: audioArrays    = array of audioArrays for each clip to compare audio
    # OUTPUT: outputArray   = array with indices 1..numArrays indicating which clip should overlay
    def compareAudioArrays(self, audioArrays):
        priorityArray = 0  # Current array that should have video priority (zero-based)
        consecutiveArray = 0  # Which array currently has the highest waveform integer
        prevArray = 0  # Which array on previous iteration had highest waveform integer
        consecutiveCount = 0  # Number of consecutive times audio is larger than others
        counter = 0  # Current array index to compare
        outputArray = []

        audioArrays = self.normalizeArrays(audioArrays)  # Set arrays to equal lengths by concatenating zeroes

        while counter < len(audioArrays[0]):
            consecutiveArray = self.returnHighestIndex(audioArrays, counter, priorityArray)  # Find index of loudest clip
            # If loudest clip is a different one than the previous loudest clip, add 1 to consecutive counter
            if (consecutiveArray != prevArray):
                prevArray = consecutiveArray
                consecutiveCount = 1
            else:
                consecutiveCount += 1
            # If the overriding loudest clip has been louder >= THRESHOLD # of times, replace it
            if (consecutiveCount >= THRESHOLD):
                priorityArray = consecutiveArray
            for checkpoint in checkpoints:
                if checkpoint == counter:
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
    def returnHighestIndex(self, audioArrays, index, currentPriority):
        maxVal = 0  # Maximum waveform value found so far
        returnIndex = 0  # Index of array with highest waveform value
        for c in range(len(audioArrays)):
            if c != currentPriority:
                if abs(audioArrays[c][index]) > maxVal:
                    maxVal = abs(audioArrays[c][index])
                    returnIndex = c
            else:
                if abs(audioArrays[c][index]) * EXCEEDS_BY > maxVal:
                    maxVal = abs(audioArrays[c][index]) * EXCEEDS_BY
                    returnIndex = c
        return returnIndex

    # SETS ALL AUDIO ARRAYS TO SAME LENGTH BY CONCATENATING ZEROES TO SHORTER ARRAYS
    # INPUT: audioArrays  = array of audio arrays containing integer waveform data
    # OUTPUT: outputArray = array of audio arrays all equal length (concatenates 0 to shorter arrays)
    def normalizeArrays(self, audioArrays):
        maxArrayLen = 0
        outputArray = []
        # Get the length of the longest array
        for array in audioArrays:
            if len(array) > maxArrayLen:
                maxArrayLen = len(array)
            # checkpoints.append(len(array))
        # Fill shorter arrays with trailing zeroes
        for array in audioArrays:
            for c in range(maxArrayLen - len(array)):
                array.append(0)
            outputArray.append(array)
        return outputArray

    def spliceClips(self):
        # MAIN PROCESS
        audioDataArrays = []
        # Generate .wav files for each video clip, create associated outputArray
        for i in range(len(INPUT_FILES)):
            # Convert input to audio waveform and call via command in subprocess
            command = "ffmpeg -i " + INPUT_FILES[
                i] + " -ab 160k -ac 2 -y -vn " + TEMP_FOLDER + "audio" + str(i) + ".wav"
            subprocess.call(command, shell=False)
            audioRate, audioArray = wavfile.read(TEMP_FOLDER + 'audio' + str(i) + '.wav')
            audioDataArrays.append(self.parseAudioData(audioRate, audioArray))
        outputArray = self.compareAudioArrays(audioDataArrays)

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
                print(str(counter) + " [" + str(prevPriority) + "] || SPLIT_PT: " + "start: " + str(
                    prevEndPt) + " end: " + str(counter / SAMPLE_RATE))
                outputClipList.append(
                    VideoFileClip(INPUT_FILES[prevPriority], audio=NO_OVERLAP_AUDIO).subclip(prevEndPt,
                                                                                             counter / SAMPLE_RATE))
                prevPriority = outputArray[counter]
                prevEndPt = counter / SAMPLE_RATE
            counter += 1
        print(str(counter) + " [" + str(prevPriority) + "] || SPLIT_PT: " + "start: " + str(prevEndPt) + " end: " + str(
            counter / SAMPLE_RATE))
        outputClipList.append(
            VideoFileClip(INPUT_FILES[prevPriority], audio=NO_OVERLAP_AUDIO).subclip(prevEndPt, (
                        counter - 1) / SAMPLE_RATE))
        # Concatenate clips and output
        videoOutput = concatenate_videoclips(outputClipList)

        # If audio should be overlapped, create an audio file with all overlapped and mix with video
        if not NO_OVERLAP_AUDIO:
            for wavFileIndex in range(len(INPUT_FILES)):
                audioClipList.append(AudioFileClip(TEMP_FOLDER + "audio" + str(wavFileIndex) + ".wav"))
            audioOutput = CompositeAudioClip(audioClipList)
            videoOutput = videoOutput.set_audio(audioOutput)

        videoOutput.write_videofile(
            OUTPUT_FOLDER + OUTPUT_FILE_NAME + ".mp4")

root = Tk()
root.geometry("600x400")
app = Window(root)
root.mainloop()
