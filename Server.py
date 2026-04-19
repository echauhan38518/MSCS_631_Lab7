from socket import socket, AF_INET, SOCK_STREAM
import sys

from ServerWorker import ServerWorker


def main():
    if len(sys.argv) != 2:
        print("Usage: python Server.py <server_port>")
        sys.exit(1)

    server_port = int(sys.argv[1])

    rtsp_socket = socket(AF_INET, SOCK_STREAM)
    rtsp_socket.bind(('', server_port))
    rtsp_socket.listen(5)

    print(f"RTSP server listening on port {server_port}...")

    while True:
        client_info = {}
        client_info['rtspSocket'] = rtsp_socket.accept()
        ServerWorker(client_info).run()


if __name__ == "__main__":
    main()