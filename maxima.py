import socket
import subprocess
import threading

class Maxima:
    def __init__(self, port):
        self.port = port
        self.start_maxima_server()
        self.start_maxima()

    def check_if_prompt(self, data):
        print(data.decode())

    def start_maxima_server(self):
        maxima_server = threading.Thread(target=self.start_socket_server)
        maxima_server.deamon = True
        maxima_server.start()

    def start_socket_server(self):
        HOST = "127.0.0.1"  # Standard loopback interface address (localhost)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, self.port))
            s.listen()
            conn, addr = s.accept()
            with conn:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print(f"server: {data}")
                    #check_if_prompt(data)

    def start_maxima(self):
        maxima_thread = threading.Thread(target=self.connect_maxima_to_server)
        maxima_thread.deamon = True
        maxima_thread.start()

    def connect_maxima_to_server(self):
        maxima_cmd = f"maxima -s {self.port}"
        process = subprocess.Popen(maxima_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        stdout_iterator = iter(process.stdout.readline, b"")

        for line in stdout_iterator: 
            print(f"maxima: {line}")