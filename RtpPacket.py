import time


class RtpPacket:
    HEADER_SIZE = 12

    def __init__(self):
        self.header = bytearray(self.HEADER_SIZE)
        self.payload = b""

    def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload):
        """Encode the RTP packet with header fields and payload."""
        timestamp = int(time.time())

        self.header = bytearray(self.HEADER_SIZE)

        # Byte 0: V(2 bits), P(1 bit), X(1 bit), CC(4 bits)
        self.header[0] = (version << 6) | (padding << 5) | (extension << 4) | (cc & 0x0F)

        # Byte 1: M(1 bit), PT(7 bits)
        self.header[1] = (marker << 7) | (pt & 0x7F)

        # Bytes 2-3: Sequence number
        self.header[2] = (seqnum >> 8) & 0xFF
        self.header[3] = seqnum & 0xFF

        # Bytes 4-7: Timestamp
        self.header[4] = (timestamp >> 24) & 0xFF
        self.header[5] = (timestamp >> 16) & 0xFF
        self.header[6] = (timestamp >> 8) & 0xFF
        self.header[7] = timestamp & 0xFF

        # Bytes 8-11: SSRC
        self.header[8] = (ssrc >> 24) & 0xFF
        self.header[9] = (ssrc >> 16) & 0xFF
        self.header[10] = (ssrc >> 8) & 0xFF
        self.header[11] = ssrc & 0xFF

        self.payload = payload

    def decode(self, byte_stream):
        """Decode the RTP packet."""
        self.header = bytearray(byte_stream[:self.HEADER_SIZE])
        self.payload = byte_stream[self.HEADER_SIZE:]

    def version(self):
        return int(self.header[0] >> 6)

    def seqNum(self):
        return int((self.header[2] << 8) | self.header[3])

    def timestamp(self):
        return int(
            (self.header[4] << 24)
            | (self.header[5] << 16)
            | (self.header[6] << 8)
            | self.header[7]
        )

    def payloadType(self):
        return int(self.header[1] & 127)

    def getPayload(self):
        return self.payload

    def getPacket(self):
        return bytes(self.header + self.payload)