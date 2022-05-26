import socket
import subprocess
import threading
import os
import psutil
import logging
import sys
import time

from enum import Enum


class MaximaServerNotAcceptingCommandException(Exception):
    pass


class NoMaximaPrompt(Exception):
    pass


class MaximaServerState(Enum):
    OFFLINE = 0
    WAITING_FOR_COMMAND = 1
    WAITING_FOR_MAXIMA = 2


class MaximaInterface:
    def __init__(self, port=65432, debug=False):
        self.debug = debug
        if self.debug:
            logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

        self.port = port
        self.host = "127.0.0.1"

        self.command_pipe_read = None
        self.command_pipe_write = None

        self.maxima_server_state = MaximaServerState.OFFLINE

        self.maxima_server_thread = None
        self.maxima_thread = None

        self.maxima_pid = -1

        self.open_command_pipe()
        self.start_maxima_server()
        self.start_maxima()

        # busy wait until maxima server accepts commands
        while self.maxima_server_state != MaximaServerState.WAITING_FOR_COMMAND:
            time.sleep(0.01)

        self.debug_message("initialized.")

    def debug_message(self, message):
        logging.debug(f"{self.__class__.__name__}: {message}")

    def check_if_prompt(self, response):
        if str.startswith(response, "(%i"):
            return True
        return False

    def interpret_maxima_response(self, response):
        # check if response is valid maxima output
        response = response.strip()
        if str.startswith(response, "(%o"):
            print(f"GOT OUTPUT: {response}")

    def open_command_pipe(self):
        self.command_pipe_read, self.command_pipe_write = os.pipe()

    def start_maxima_server(self):
        self.maxima_server_thread = threading.Thread(target=self.start_socket_server)
        self.maxima_server_thread.start()

    def start_socket_server(self):
        command = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            conn, addr = s.accept()
            with conn:
                while True:
                    # check if command is intended for server of for maxima
                    if command == "close":
                        self.debug_message(f"server: closing")
                        break

                    # send command to maxima
                    if command is not None:
                        self.debug_message(
                            f'server: sending command to maxima: "{command}"'
                        )
                        conn.sendall(command.encode())
                        command = None

                    # waiting for maximas response
                    self.maxima_server_state = MaximaServerState.WAITING_FOR_MAXIMA
                    self.debug_message(f"server: state={self.maxima_server_state}")
                    data = conn.recv(1024).decode()
                    if not data:
                        break

                    self.debug_message(f'server: received "{data}"')
                    self.interpret_maxima_response(data)

                    got_prompt = self.check_if_prompt(data)
                    self.debug_message(f"server: got prompt: {got_prompt}")

                    if got_prompt:
                        self.maxima_server_state = MaximaServerState.WAITING_FOR_COMMAND
                        self.debug_message(f"server: state={self.maxima_server_state}")
                        command = os.read(self.command_pipe_read, 1024).decode()
                        self.debug_message(f'server: received command: "{command}"')

    def start_maxima(self):
        self.maxima_thread = threading.Thread(target=self.connect_maxima_to_server)
        self.maxima_thread.start()

    def connect_maxima_to_server(self):
        maxima_command = f"maxima -s {self.port}"
        process = subprocess.Popen(
            maxima_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )

        self.maxima_pid = process.pid

        stdout_iterator = iter(process.stdout.readline, b"")

        for line in stdout_iterator:
            self.debug_message(f"maxima: {line.decode()}")

    def close(self):
        # send SIGTERM to maxima sub process
        self.kill_subprocess(self.maxima_pid)
        # terminate maxima thread
        self.maxima_thread.join()

        # send close command to maxima server
        os.write(self.command_pipe_write, b"close")

        # close command pipe
        os.close(self.command_pipe_read)
        os.close(self.command_pipe_write)

    def kill_subprocess(self, pid):
        process = psutil.Process(pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

    def raw_command(self, command_string):
        # check if maxima server is waiting for a command
        if self.maxima_server_state != MaximaServerState.WAITING_FOR_COMMAND:
            self.debug_message("server is not accepting commands.")
            raise MaximaServerNotAcceptingCommandException()

        else:
            # send command to maxima server
            self.debug_message(f'sending command to server: "{command_string}"')
            os.write(self.command_pipe_write, command_string.encode())
