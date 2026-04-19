from tkinter import Tk
import sys

from Client import Client


def main():
    if len(sys.argv) != 5:
        print("Usage: python ClientLauncher.py <server_host> <server_port> <rtp_port> <video_file>")
        sys.exit(1)

    server_host = sys.argv[1]
    server_port = sys.argv[2]
    rtp_port = sys.argv[3]
    file_name = sys.argv[4]

    root = Tk()
    root.title("RTPClient")
    app = Client(root, server_host, server_port, rtp_port, file_name)
    root.mainloop()


if __name__ == "__main__":
    main()