import socket
import subprocess
import threading
import os
import psutil
import logging
import sys


class MaximaInterface:
    def __init__(self, port=65432, debug=False):
        self.debug = debug
        if self.debug:
            logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

        self.port = port
        self.host = "127.0.0.1"

        self.maxima_thread = None
        self.maxima_server_thread = None

        self.maxima_pid = -1

        self.start_maxima_server()
        self.start_maxima()

        self.debug_message("initialized.")

    def debug_message(self, msg):
        logging.debug(f"{self.__class__.__name__}: {msg}")

    def check_if_prompt(self, data):
        string = data.decode()
        if str.startswith(string, "(%"):
            return True
        return False

    def start_maxima_server(self):
        self.maxima_server_thread = threading.Thread(target=self.start_socket_server)
        self.maxima_server_thread.start()

    def start_socket_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            conn, addr = s.accept()
            with conn:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    self.debug_message(f'server: received "{data}"')
                    got_prompt = self.check_if_prompt(data)
                    self.debug_message(f"server: got prompt: {got_prompt}")

    def start_maxima(self):
        self.maxima_thread = threading.Thread(target=self.connect_maxima_to_server)
        self.maxima_thread.start()

    def connect_maxima_to_server(self):
        maxima_cmd = f"maxima -s {self.port}"
        process = subprocess.Popen(
            maxima_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )

        self.maxima_pid = process.pid

        stdout_iterator = iter(process.stdout.readline, b"")

        for line in stdout_iterator:
            self.debug_message(f"maxima: {line}")

    def terminate(self):
        # send SIGTERM to maxima sub process
        self.kill_subprocess(self.maxima_pid)
        # terminate maxima thread
        self.maxima_thread.join()

    def kill_subprocess(self, pid):
        process = psutil.Process(pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()