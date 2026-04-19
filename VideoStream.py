class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
        except OSError as exc:
            raise IOError(f"Could not open file: {filename}") from exc
        self.frame_num = 0

    def nextFrame(self):
        """Get next frame from the MJPEG file."""
        data = self.file.read(5)
        if not data:
            return None

        try:
            frame_length = int(data)
        except ValueError:
            return None

        frame_data = self.file.read(frame_length)
        if len(frame_data) != frame_length:
            return None

        self.frame_num += 1
        return frame_data

    def frameNbr(self):
        return self.frame_num