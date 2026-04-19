from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import os
import socket
import threading
import tempfile
import time

from RtpPacket import RtpPacket


CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)

        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename

        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.frameNbr = 0

        self.totalPackets = 0
        self.lostPackets = 0
        self.totalBytes = 0
        self.startTime = None
        self.lastSeqNum = 0
        self.totalFramesDisplayed = 0

        self.connectToServer()
        self.createWidgets()

    def createWidgets(self):
        """Build GUI."""
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)

        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)

        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)

        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5)

    def setupMovie(self):
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        self.printStats()
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()
        try:
            os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)
        except OSError:
            pass

    def pauseMovie(self):
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        if self.state == self.READY:
            self.playEvent = threading.Event()
            self.playEvent.clear()
            threading.Thread(target=self.listenRtp, daemon=True).start()
            self.sendRtspRequest(self.PLAY)

    def listenRtp(self):
        """Listen for RTP packets."""
        print("[CLIENT] RTP listener started")
        if self.startTime is None:
            self.startTime = time.time()
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    currFrameNbr = rtpPacket.seqNum()
                    payload = rtpPacket.getPayload()

                    self.totalPackets += 1
                    self.totalBytes += len(payload)

                    if self.lastSeqNum != 0 and currFrameNbr > self.lastSeqNum + 1:
                        self.lostPackets += (currFrameNbr - self.lastSeqNum - 1)

                    self.lastSeqNum = currFrameNbr
                    print("Current Seq Num: " + str(currFrameNbr))

                    if currFrameNbr > self.frameNbr:
                        self.frameNbr = currFrameNbr
                        self.totalFramesDisplayed += 1
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except socket.timeout:
                print("[CLIENT] RTP socket timeout")
                if self.playEvent.is_set():
                    print("[CLIENT] Play event set, stopping RTP listener")
                    break
                if self.teardownAcked == 1:
                    try:
                        print("[CLIENT] Teardown acknowledged, closing RTP socket")
                        self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    except Exception:
                        pass
                    self.rtpSocket.close()
                    break
            except Exception as e:
                print("[CLIENT] RTP receive error:", e)
                break

    def writeFrame(self, data):
        """Write received frame to temp image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        with open(cachename, "wb") as file:
            file.write(data)
        return cachename

    def updateMovie(self, imageFile):
        """Update image in GUI."""
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image=photo, height=288)
        self.label.image = photo

    def connectToServer(self):
        """Connect to the server over RTSP/TCP."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except Exception:
            tkinter.messagebox.showwarning("Connection Failed", f"Connection to '{self.serverAddr}' failed.")

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply, daemon=True).start()
            self.rtspSeq += 1
            request = (
                f"SETUP {self.fileName} RTSP/1.0\n"
                f"CSeq: {self.rtspSeq}\n"
                f"Transport: RTP/UDP; client_port= {self.rtpPort}"
            )
            self.requestSent = self.SETUP

        elif requestCode == self.PLAY and self.state == self.READY:
            self.rtspSeq += 1
            request = (
                f"PLAY {self.fileName} RTSP/1.0\n"
                f"CSeq: {self.rtspSeq}\n"
                f"Session: {self.sessionId}"
            )
            self.requestSent = self.PLAY

        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            self.rtspSeq += 1
            request = (
                f"PAUSE {self.fileName} RTSP/1.0\n"
                f"CSeq: {self.rtspSeq}\n"
                f"Session: {self.sessionId}"
            )
            self.requestSent = self.PAUSE

        elif requestCode == self.TEARDOWN:
            self.rtspSeq += 1
            request = (
                f"TEARDOWN {self.fileName} RTSP/1.0\n"
                f"CSeq: {self.rtspSeq}\n"
                f"Session: {self.sessionId}"
            )
            self.requestSent = self.TEARDOWN
        else:
            return

        self.rtspSocket.send(request.encode())
        print("\nData sent:\n" + request)

    def recvRtspReply(self):
        """Receive RTSP reply from server."""
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            if self.requestSent == self.TEARDOWN:
                try:
                    self.rtspSocket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse RTSP reply from server."""
        print("RTSP reply received:\n" + data)

        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])

        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])

            if self.sessionId == 0:
                self.sessionId = session

            if self.sessionId == session:
                code = int(lines[0].split(' ')[1])

                if code == 200:
                    if self.requestSent == self.SETUP:
                        self.state = self.READY
                        self.openRtpPort()

                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING

                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        self.playEvent.set()

                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket."""
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            self.rtpSocket.bind(('', self.rtpPort))
            self.rtpSocket.settimeout(0.5)
            print("[CLIENT] RTP socket bound to port", self.rtpPort)
        except Exception:
            tkinter.messagebox.showwarning(
                "Unable to Bind",
                f"Unable to bind PORT={self.rtpPort}"
            )

    def handler(self):
        """Handle GUI close."""
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:
            self.playMovie()
    
    def printStats(self):
        if self.startTime is None:
            print("No RTP data received.")
            return

        duration = time.time() - self.startTime
        if duration <= 0:
            duration = 1

        expectedPackets = self.totalPackets + self.lostPackets
        lossRate = (self.lostPackets / expectedPackets * 100) if expectedPackets > 0 else 0
        byteRate = self.totalBytes / duration
        bitRate = (self.totalBytes * 8) / duration
        fps = self.totalFramesDisplayed / duration if duration > 0 else 0
        avgFrameSize = self.totalBytes / self.totalFramesDisplayed if self.totalFramesDisplayed > 0 else 0

        print("\n========== STREAM STATISTICS ==========")
        print(f"Session duration: {duration:.2f} sec")
        print(f"Packets received: {self.totalPackets}")
        print(f"Packets lost: {self.lostPackets}")
        print(f"RTP packet loss rate: {lossRate:.2f}%")
        print(f"Total video bytes received: {self.totalBytes}")
        print(f"Video data rate: {byteRate:.2f} bytes/sec")
        print(f"Video data rate: {bitRate:.2f} bits/sec")
        print(f"Frames displayed: {self.totalFramesDisplayed}")
        print(f"Average frame size: {avgFrameSize:.2f} bytes")
        print(f"Display frame rate: {fps:.2f} frames/sec")
        print("=======================================\n")