import socket
import subprocess
import threading
import os
from typing import List, Optional
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
    def __init__(self, port: int = 65432, debug: bool = False) -> None:
        self.debug = debug
        if self.debug:
            logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

        self.port = port
        self.host = "127.0.0.1"

        self.command_pipe_read = None
        self.command_pipe_write = None

        self.result_pipe_read = None
        self.result_pipe_write = None

        self.maxima_server_state = MaximaServerState.OFFLINE

        self.maxima_server_thread = None
        self.maxima_thread = None

        self.maxima_pid = -1

        # setup connection between maxima and server
        self.open_command_pipe()
        self.open_result_pipe()
        self.start_maxima_server()
        self.start_maxima()

        # busy wait until maxima server accepts commands
        while self.maxima_server_state != MaximaServerState.WAITING_FOR_COMMAND:
            time.sleep(0.01)

        self.debug_message("initialized.")

    def debug_message(self, message: str) -> None:
        logging.debug(f"{self.__class__.__name__}: {message}")

    def open_command_pipe(self) -> None:
        self.command_pipe_read, self.command_pipe_write = os.pipe()

    def open_result_pipe(self) -> None:
        self.result_pipe_read, self.result_pipe_write = os.pipe()

    def start_maxima_server(self) -> None:
        self.maxima_server_thread = threading.Thread(target=self.start_socket_server)
        self.maxima_server_thread.start()

    def start_socket_server(self) -> None:
        # state variable to indicate that a result has been received
        # this to not overwrite the maxima's result as maxima sends the result
        # and the prompt at different times
        got_result = False

        # first command to maxima is to turn off pretty printing
        command = "display2d:false$"
        # open socket server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # wait for incoming connection from maxima
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

                    # a response is composed out of several lines
                    response = conn.recv(1024).decode()
                    if not response:
                        break
                    response = response.split("\n")

                    # interpret maxima's response
                    self.debug_message(f'server: received "{response}"')
                    if not got_result:
                        result = self.interpret_maxima_response(response)
                        self.debug_message(f'server: maxima result "{result}"')
                    if result is not None:
                        got_result = True
                        self.debug_message(f"server: got_result={got_result}")

                    # check if maxima is ready to accept new commands
                    got_prompt = self.check_if_prompt(response)
                    self.debug_message(f"server: got_prompt={got_prompt}")

                    if got_prompt:
                        self.maxima_server_state = MaximaServerState.WAITING_FOR_COMMAND
                        self.debug_message(f"server: state={self.maxima_server_state}")

                        # return result after the server is in correct state to accept a new command
                        if result is not None:
                            self.debug_message(f'server: returning result "{result}"')
                            os.write(self.result_pipe_write, result.encode())
                            got_result = False

                        # server waits for new command
                        command = os.read(self.command_pipe_read, 1024).decode()
                        self.debug_message(f'server: received command: "{command}"')

    def check_if_prompt(self, response) -> bool:
        for l in response:
            if str.startswith(l, "(%i"):
                return True
        return False

    def interpret_maxima_response(self, response: List[str]) -> Optional[str]:
        maxima_result = None

        for l in response:
            line = l.strip()

            # check if response is valid maxima output
            if str.startswith(line, "(%o"):
                # format result by removing prompt and white space
                end_of_prefix = line.find(")")
                maxima_result = line[end_of_prefix + 2 :].strip()
            return maxima_result

    def start_maxima(self) -> None:
        self.maxima_thread = threading.Thread(target=self.connect_maxima_to_server)
        self.maxima_thread.start()

    def connect_maxima_to_server(self) -> None:
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

    def close(self) -> None:
        # send SIGTERM to maxima sub process
        self.kill_subprocess(self.maxima_pid)
        # terminate maxima thread
        self.maxima_thread.join()

        # send close command to maxima server
        os.write(self.command_pipe_write, b"close")

        # close command pipe
        os.close(self.command_pipe_read)
        os.close(self.command_pipe_write)

        # close result pipe
        os.close(self.result_pipe_read)
        os.close(self.result_pipe_write)

    def kill_subprocess(self, pid: int) -> None:
        process = psutil.Process(pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

    def raw_command(self, command_string: str) -> None:
        # check if maxima server is waiting for a command
        if self.maxima_server_state != MaximaServerState.WAITING_FOR_COMMAND:
            self.debug_message("server is not accepting commands.")
            raise MaximaServerNotAcceptingCommandException()

        else:
            # send command to maxima server
            self.debug_message(f'sending command to server: "{command_string}"')
            os.write(self.command_pipe_write, command_string.encode())
            return os.read(self.result_pipe_read, 1024).decode()
