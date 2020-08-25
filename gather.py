from callbacks import Callbacks
from socket import *
from struct import *
import numpy as np
import time
from plot import DataMonitor, HistMonitor, Buttons
import matplotlib.pyplot as plt
from util import *
import asyncio

class Gather:
    def __init__(self, ip="192.168.2.122", port=51244, plot_interval=10, targetMarker='R 14'):
        self.con = socket(AF_INET, SOCK_STREAM)
        self.con.connect((ip, port))
        # Data handling
        self.blocks_per_s = 50
        self.block_counter = 0
        self.dataMemoryDurS = 5  # seconds of data memory
        self.block_dur_s = 0.02
        self.blockSize = None
        self.sr = None
        # Here the block number will be assigned to each piece of data in dataMemory
        self.blockMemory = [-1] * self.blocks_per_s * self.dataMemoryDurS
        self.startTime = None
        self.lag_s = None
        self.lastBlock = -1

        # Perform main loop until parameters like sr are there.
        while self.blockSize is None or self.sr is None:
            self.main()

        # External event handling
        self.targetMarker = targetMarker

        # Callbacks
        self.callbacks = Callbacks()

        # Plotting
        self.plot_interval = plot_interval
        self.update_size = self.plot_interval * self.blockSize

        self.fig = plt.figure(num=42, figsize=(13, 6))
        self.data_monitor = DataMonitor(self.sr, self.update_size, fig=self.fig)
        self.hist_monitor = HistMonitor(self.sr, fig=self.fig)
        self.buttons = Buttons(self.fig, self.callbacks)

        self.fresh_init()
        print("initialized Gather instance")

    def fresh_init(self):
        self.blockMemory = [-1] * self.blocks_per_s * self.dataMemoryDurS
        self.block_counter = 0
        self.dataMemory = np.array([np.nan]*int(self.dataMemorySize))  # nan array to store data in
        self.startTime = time.time()
        
    def main(self):
        # finish = False
        # while not finish:
                
        # Get message header as raw array of chars
        self.rawhdr = self.RecvData(24)

        # Split array into usefull information id1 to id4 are constants
        (id1, id2, id3, id4, msgsize, msgtype) = unpack('<llllLL', self.rawhdr)#.encode('utf-8', "replace"))

        # Get data part of message, which is of variable size
        self.rawdata = self.RecvData(msgsize - 24)

        # Perform action dependend on the message type
        if msgtype == 1:
            # Start message, extract eeg properties and display them
            self.GetProperties()
            # reset block counter
            self.lastBlock = -1

            print("Start")
            print("Number of channels: " + str(self.channelCount))
            print("Sampling interval: " + str(self.samplingInterval))
            print("Resolutions: " + str(self.resolutions))
            print("Channel Names: " + str(self.channelNames))

            # Calculate some important values:
            self.sr = int(1000 / (self.samplingInterval / 1000))  # Sampling rate
            self.blockSize = int(self.block_dur_s * self.sr)  # data points per block
            self.theoreticalLooptime = float(self.blockSize) / self.sr

            self.dataMemorySize = self.dataMemoryDurS * self.blocks_per_s * self.blockSize  # number of data points in memory
            self.dataMemory = np.array([np.nan]*int(self.dataMemorySize))  # nan array to store data in

            self.data = np.array([np.nan] * int(self.blockSize))

        elif msgtype == 4:
            # Data message, extract data and markers
            self.GetData()
            self.hist_monitor.update_data(self.data)
            # Check for overflow
            if self.lastBlock != -1 and self.block > self.lastBlock + 1:
                print("*** Overflow with " + str(self.block - self.lastBlock) + " datablocks ***" )
            self.lastBlock = self.block

            # Print markers, if there are some in actual block
            if self.markerCount > 0:
                for m in range(self.markerCount):
                    print("Marker " + self.markers[m].description + " of type " + self.markers[m].type)
                markerDescriptions = [marker.description for marker in self.markers]
                # Check if correct marker is incoming:
                if self.targetMarker in markerDescriptions:
                    self.hist_monitor.button_press()
                    self.hist_monitor.plot_hist()
            # TODO: delete unnecessary prints
            # print(np.mean(self.dataMemory))
            
            # Asynchronous plot
            if np.mod(self.block_counter, self.plot_interval) == 0:
                data_for_plot = self.dataMemory[-self.update_size:]

                stt = time.time()

                
                self.data_monitor.update(data_for_plot, lagtime=self.lag_s)
                endd = time.time()
                print(f'time elapsed: {1000*(endd-stt):.2f}')

            # Lag Calculation        
            if self.startTime is not None:
                endTime = time.time()
                measuredLoopTime = endTime - self.startTime
                calculatedEndTime = (self.theoreticalLooptime*(self.block_counter))
                # print(calculatedEndTime)
                self.lag_s = calculatedEndTime - measuredLoopTime
  
            
                

        elif msgtype == 3:
            # Stop message, terminate program
            print("Stop")
            self.quit()

        # Close tcpip connection
        # 


    # Helper function for receiving whole message
    def RecvData(self, requestedSize):
        returnStream = bytearray()#''
        while len(returnStream) < requestedSize:
            databytes = self.con.recv(requestedSize - len(returnStream))

            if str(databytes.decode('utf8', "replace")) == '':
                raise RuntimeError("connection broken")
            returnStream += databytes
        return returnStream   
    
    # Helper function for splitting a raw array of
    # zero terminated strings (C) into an array of python strings
    @staticmethod
    def SplitString(raw):
        stringlist = []
        s = ""
        raw = raw.decode('utf-8')
        for i in range(len(raw)):
            if raw[i] != '\x00':
                s = s + raw[i]
            else:
                stringlist.append(s)
                s = ""

        return stringlist

    # Helper function for extracting eeg properties from a raw data array
    # read from tcpip socket
    def GetProperties(self):

        # Extract numerical data
        (self.channelCount, self.samplingInterval) = unpack('<Ld', self.rawdata[:12])

        # Extract resolutions
        self.resolutions = []
        for c in range(self.channelCount):
            index = 12 + c * 8
            restuple = unpack('<d', self.rawdata[index:index+8])
            self.resolutions.append(restuple[0])

        # Extract channel names
        self.channelNames = self.SplitString(self.rawdata[12 + 8 * self.channelCount:])

        # return (channelCount, samplingInterval, resolutions, channelNames)

    # Helper function for extracting eeg and marker data from a raw data array
    # read from tcpip socket       
    def GetData(self):

        # Extract numerical data
        (self.block, self.points, self.markerCount) = unpack('<LLL', self.rawdata[:12])
        # Extract eeg data as array of floats
        self.old_data = self.data.copy()
        self.data = []
        for i in range(self.points * self.channelCount):
            index = 12 + 4 * i
            value = unpack('<f', self.rawdata[index:index+4])
            self.data.append(value[0])
        self.block_counter += 1
        self.update_data()
        try:
            if self.data == self.old_data:
                print("Its a copy")
        except:
            pass

        # Extract markers
        self.markers = []
        index = 12 + 4 * self.points * self.channelCount
        for m in range(self.markerCount):
            markersize = unpack('<L', self.rawdata[index:index+4])

            ma = Marker()
            (ma.position, ma.points, ma.channel) = unpack('<LLl', self.rawdata[index+4:index+16])
            typedesc = self.SplitString(self.rawdata[index+16:index+markersize[0]])
            ma.type = typedesc[0]
            ma.description = typedesc[1]

            self.markers.append(ma)
            index = index + markersize[0]

        # return (self.block, self.points, self.markerCount, self.data, self.markers)

    def update_data(self):
        ''' Collect new data and add it to the data memory.
        Parameters:
        -----------
        data_package : numpy.ndarray/list, new data retrieved from rda.
        '''
        if self.blockSize is None:
            self.blockSize = len(self.data)

        assert self.blockSize == len(self.data), "blockSize is supposed to be {} but data was of size {}".format(self.blockSize, len(self.data))

        self.dataMemory = insert(self.dataMemory, self.data)
        self.blockMemory = insert(self.blockMemory, self.block_counter)

    def quit(self):
        self.con.close()

class Marker:
    def __init__(self):
        self.position = 0
        self.points = 0
        self.channel = -1
        self.type = ""
        self.description = ""

# fig = plt.figure(num=42, figsize=(13, 6))

gather = Gather()
# data_monitor = DataMonitor(gather.sr, gather.blockSize, fig=fig)

# hist_monitor = HistMonitor(gather.sr, fig=fig)

gather.fresh_init()
cnt = 0
while True:
    # cnt +=1
    gather.main()

# data_monitor = DataMonitor(250, 10*5)

# plot_dur = []
# for _ in range(100):
#     start = time.time()
#     data_monitor.update(np.random.randn(50))
#     end = time.time()
#     plot_dur.append(end-start)
# mean_dur = np.mean(plot_dur)

# plt.clf()

# data_monitor = DataMonitor(250, 10*5)
# start = None 
# while True:
#     if start is None:
#         start = time.time()
#     data_monitor.update(np.random.randn(50), lagtime=time.time()-start)
#     time.sleep(0.2 - mean_dur)