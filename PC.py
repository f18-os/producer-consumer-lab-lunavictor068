from threading import Thread
import time
import threading
import cv2
from collections import deque
import os


class Q:
    # producer, consumer queue. Got implementation idea from https://github.com/python/cpython/blob/2.7/Lib/Queue.py

    def __init__(self, maxsize=0):
        self.maxsize = maxsize
        self.queue = deque()
        self.mutex = threading.Lock()
        self.not_empty = threading.Condition(self.mutex)
        self.not_full = threading.Condition(self.mutex)

    def put(self, item):
        # Put an item into the queue, block if full
        self.not_full.acquire()
        try:
            while len(self.queue) == self.maxsize:
                self.not_full.wait()
            self.queue.append(item)
            self.not_empty.notify()
        finally:
            self.not_full.release()

    def get(self):
        # Remove and return an item from the queue, block if empty
        self.not_empty.acquire()
        try:
            while not len(self.queue):
                self.not_empty.wait()
            item = self.queue.popleft()
            self.not_full.notify()
            return item
        finally:
            self.not_empty.release()


# globals
image_q = Q(10)
greyscale_q = Q(10)
outputDir = 'frames'
clipFileName = 'clip.mp4'


class ExtractionThread(Thread):

    def run(self):
        global greyscale_q, outputDir, clipFileName
        # initialize frame count
        count = 0

        # open the video clip
        vidcap = cv2.VideoCapture(clipFileName)

        # create the output directory if it doesn't exist
        if not os.path.exists(outputDir):
            print("Output directory {} didn't exist, creating".format(outputDir))
            os.makedirs(outputDir)

        # read one frame
        success, image = vidcap.read()

        print("Reading frame {} {} ".format(count, success))
        while success:
            # write the current frame out as a jpeg image
            cv2.imwrite("{}/frame_{:04d}.jpg".format(outputDir, count), image)
            image_q.put(count)
            success, image = vidcap.read()
            print('Reading frame {}'.format(count))
            count += 1
        if not success:
            image_q.put(count)


class GrayScaleThread(Thread):

    def run(self):
        global greyscale_q, image_q
        # initialize frame count
        count = image_q.get()

        # get the next frame file name
        inFileName = "{}/frame_{:04d}.jpg".format(outputDir, count)

        # load the next file
        inputFrame = cv2.imread(inFileName, cv2.IMREAD_COLOR)

        while inputFrame is not None:
            print("Converting frame {}".format(count))

            # convert the image to grayscale
            grayscaleFrame = cv2.cvtColor(inputFrame, cv2.COLOR_BGR2GRAY)

            # generate output file name
            outFileName = "{}/grayscale_{:04d}.jpg".format(outputDir, count)

            # write output file
            cv2.imwrite(outFileName, grayscaleFrame)
            greyscale_q.put(count)
            count = image_q.get()

            # generate input file name for the next frame
            inFileName = "{}/frame_{:04d}.jpg".format(outputDir, count)

            # load the next frame
            inputFrame = cv2.imread(inFileName, cv2.IMREAD_COLOR)
            if inputFrame is None:
                greyscale_q.put(count)

GrayScaleThread().start()
ExtractionThread().start()
frameDelay = 42  # the answer to everything

# initialize frame count
count = greyscale_q.get()

startTime = time.time()

# Generate the filename for the first frame
frameFileName = "{}/grayscale_{:04d}.jpg".format(outputDir, count)

# load the frame
frame = cv2.imread(frameFileName)

while frame is not None:

    print("Displaying frame {}".format(count))
    # Display the frame in a window called "Video"
    cv2.imshow("Video", frame)

    # compute the amount of time that has elapsed
    # while the frame was processed
    elapsedTime = int((time.time() - startTime) * 1000)
    print("Time to process frame {} ms".format(elapsedTime))

    # determine the amount of time to wait, also
    # make sure we don't go into negative time
    timeToWait = max(1, frameDelay - elapsedTime)

    # Wait for 42 ms and check if the user wants to quit
    if cv2.waitKey(timeToWait) and 0xFF == ord("q"):
        break

        # get the start time for processing the next frame
    startTime = time.time()

    # get the next frame filename
    count = greyscale_q.get()
    frameFileName = "{}/grayscale_{:04d}.jpg".format(outputDir, count)

    # Read the next frame file
    frame = cv2.imread(frameFileName)

# make sure we cleanup the windows, otherwise we might end up with a mess
cv2.destroyAllWindows()