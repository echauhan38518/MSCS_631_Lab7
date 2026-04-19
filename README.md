# MSCS_631_Lab7
# RTSP / RTP Video Streaming Lab

## Project Description
This project implements a simple video streaming application in Python using:

- RTSP (Real-Time Streaming Protocol) for control messages
- RTP (Real-time Transport Protocol) for video transmission
- UDP sockets for packet delivery
- Tkinter GUI for client-side playback

The server streams frames from `video.mjpeg` to the client.

---

## Files Included

- Server.py
- ServerWorker.py
- Client.py
- ClientLauncher.py
- RtpPacket.py
- VideoStream.py
- video.mjpeg

---

## Requirements

Install Python 3.x

Install Pillow:

pip install pillow

---

## How to Run

### Start Server

python Server.py 8554

### Start Client

python ClientLauncher.py localhost 8554 25000 video.mjpeg

---

## Controls

- Setup → Initialize session
- Play → Start streaming video
- Pause → Pause playback
- Teardown → End session

---

## Features

- RTSP request/response handling
- RTP packet creation and decoding
- MJPEG frame streaming
- Session management
- Playback controls

---

## Statistics Collected

- RTP packet loss rate
- Video data rate
- Frames received
- Sequence numbers
- Session duration

---

## Common Issues

### No Video Playback
- Ensure movie.Mjpeg exists
- Ensure server starts first
- Check firewall / UDP port

### PIL Error

pip install pillow

### Port Busy

Use another port:

python Server.py 9000

---

## Author

Enjal Chauhan