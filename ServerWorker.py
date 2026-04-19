import os
import socket
import threading
import traceback
from random import randint

from VideoStream import VideoStream
from RtpPacket import RtpPacket


class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'

    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    client_info = {}

    def __init__(self, client_info):
        self.client_info = client_info
        self.event = None
        self.worker = None

    def run(self):
        threading.Thread(target=self.recvRtspRequest, daemon=True).start()

    def recvRtspRequest(self):
        """Receive RTSP requests from the client."""
        conn_socket = self.client_info['rtspSocket'][0]

        while True:
            try:
                data = conn_socket.recv(256)
                if data:
                    print("Data received:\n" + data.decode("utf-8"))
                    self.processRtspRequest(data.decode("utf-8"))
            except Exception:
                break

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        lines = data.split('\n')
        request_line = lines[0].split(' ')
        request_type = request_line[0]
        filename = request_line[1]

        seq = lines[1].split(' ')[1]

        # SETUP
        if request_type == self.SETUP:
            if self.state == self.INIT:
                print("processing SETUP\n")
                try:
                    self.client_info['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                except IOError:
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq)
                    return

                self.client_info['session'] = randint(100000, 999999)

                transport_line = lines[2]
                self.client_info['rtpPort'] = transport_line.split('client_port=')[1].strip()
                print("[SERVER] RTP port =", self.client_info['rtpPort'])
                self.replyRtsp(self.OK_200, seq)

        # PLAY
        elif request_type == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING

                self.event = threading.Event()
                self.replyRtsp(self.OK_200, seq)

                self.client_info['rtpSocket'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                self.worker = threading.Thread(target=self.sendRtp, daemon=True)
                self.worker.start()

        # PAUSE
        elif request_type == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY

                if self.event:
                    self.event.set()

                self.replyRtsp(self.OK_200, seq)

        # TEARDOWN
        elif request_type == self.TEARDOWN:
            print("processing TEARDOWN\n")

            if self.event:
                self.event.set()

            self.replyRtsp(self.OK_200, seq)

            try:
                if 'rtpSocket' in self.client_info:
                    self.client_info['rtpSocket'].close()
            except Exception:
                pass

    def sendRtp(self):
        """Send RTP packets over UDP."""
        print("[SERVER] RTP sender thread started")
        while True:
            if self.event.wait(0.05):
                break

            data = self.client_info['videoStream'].nextFrame()
            if data:
                frame_number = self.client_info['videoStream'].frameNbr()
                try:
                    address = self.client_info['rtspSocket'][1][0]
                    port = int(self.client_info['rtpPort'])
                    print("[SERVER] Sending RTP to", address, "port", port)

                    packet = self.makeRtp(data, frame_number)
                    self.client_info['rtpSocket'].sendto(packet, (address, port))
                    print("[SERVER] RTP packet sent for frame", frame_number)
                except Exception:
                    print("Connection error while sending RTP")
                    traceback.print_exc()
                    break

    def makeRtp(self, payload, frame_number):
        """Create RTP packet."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG
        seqnum = frame_number
        ssrc = 0

        rtp_packet = RtpPacket()
        rtp_packet.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)

        return rtp_packet.getPacket()

    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        conn_socket = self.client_info['rtspSocket'][0]

        if code == self.OK_200:
            reply = (
                "RTSP/1.0 200 OK\n"
                f"CSeq: {seq}\n"
                f"Session: {self.client_info['session']}\n"
            )
            conn_socket.send(reply.encode())
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")