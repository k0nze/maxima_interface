"""
Author: Konstantin (k0nze) Lübeck
License: BSD 3-Clause License
Copyright (c) 2022 Konstantin (k0nze) Lübeck
"""

import socket
import subprocess
import threading
import os
import psutil
import logging
import sys
import time

from typing import List, Optional
from enum import Enum


class MaximaNotInstalled(Exception):
    def __str__(self):
        return "'maxima' command cound not be found on this system."


class MaximaServerNotAcceptingCommandException(Exception):
    def __str__(self):
        return "maxima server does not accept a command, it is waiting for a response from maxima."


class NoMaximaPrompt(Exception):
    def __str__(self):
        return "maxima does not accept a command."


class MaximaServerState(Enum):
    OFFLINE = 0
    WAITING_FOR_COMMAND = 1
    WAITING_FOR_MAXIMA = 2


class MaximaInterface:
    def __init__(self, port: int = 65432, debug: bool = False) -> None:
        """
        Starts a socket server at port and starts a maxima client process that connects
        to the socket server

        Raises:
            MaximaNotInstalled: when maxima command can not be found

        Args:
            port (int, optional): port for maxima/socket server communication. Defaults to 65432.
            debug (bool, optional): enables debug print outs. Defaults to False.
        """
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
        self.maxima_setup_command = "display2d:false$"

        # check if maxima is installedc$a
        if not self.__is_maxima_installed():
            raise MaximaNotInstalled()

        # setup connection between maxima and server
        self.__open_command_pipe()
        self.__open_result_pipe()
        self.__start_maxima_server()
        self.__start_maxima()

        # busy wait until maxima server accepts commands
        while self.maxima_server_state != MaximaServerState.WAITING_FOR_COMMAND:
            time.sleep(0.01)

        self.__debug_message("initialized.")

    def __debug_message(self, message: str) -> None:
        """
        prints a debug message
        Args:
            message (str): message to be printed
        """
        logging.debug(f"{self.__class__.__name__}: {message}")

    def __is_maxima_installed(self) -> bool:
        """checks if maxima is installed"""
        process = subprocess.Popen("which maxima", shell=True, stdout=subprocess.PIPE)
        return process.communicate()[0]

    def __open_command_pipe(self) -> None:
        """creates a names pipe to send commands to the socket server"""
        self.command_pipe_read, self.command_pipe_write = os.pipe()

    def __open_result_pipe(self) -> None:
        """creates a names pipe the socket server writes the maxima results into"""
        self.result_pipe_read, self.result_pipe_write = os.pipe()

    def __start_maxima_server(self) -> None:
        """starts socket server in a thread"""
        self.maxima_server_thread = threading.Thread(target=self.__start_socket_server)
        self.maxima_server_thread.start()

    def __start_socket_server(self) -> None:
        """implementation of the socket server itself"""
        # state variable to indicate that a result has been received
        # this to not overwrite the maxima's result as maxima sends the result
        # and the prompt at different times
        got_result = False

        # first command to maxima is to turn off pretty printing
        command = self.maxima_setup_command
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
                        self.__debug_message(f"server: closing")
                        break

                    # send command to maxima
                    if command is not None:
                        self.__debug_message(
                            f'server: sending command to maxima: "{command}"'
                        )
                        conn.sendall(command.encode())
                        command = None

                    # waiting for maximas response
                    self.maxima_server_state = MaximaServerState.WAITING_FOR_MAXIMA
                    self.__debug_message(f"server: state={self.maxima_server_state}")

                    # a response is composed out of several lines
                    response = conn.recv(1024).decode()
                    if not response:
                        break
                    response = response.split("\n")

                    # interpret maxima's response
                    self.__debug_message(f'server: received "{response}"')
                    if not got_result:
                        result = self.__format_maxima_result(response)
                        self.__debug_message(f'server: maxima result "{result}"')
                    if result is not None:
                        got_result = True
                        self.__debug_message(f"server: got_result={got_result}")

                    # check if maxima is ready to accept new commands
                    got_input_prompt = self.__check_if_input_prompt(response)
                    self.__debug_message(f"server: got_input_prompt={got_input_prompt}")

                    if got_input_prompt:
                        self.maxima_server_state = MaximaServerState.WAITING_FOR_COMMAND
                        self.__debug_message(
                            f"server: state={self.maxima_server_state}"
                        )

                        # return result after the server is in correct state to accept a new command
                        if result is not None:
                            self.__debug_message(f'server: returning result "{result}"')
                            os.write(self.result_pipe_write, result.encode())
                            got_result = False

                        # server waits for new command
                        command = os.read(self.command_pipe_read, 1024).decode()
                        self.__debug_message(f'server: received command: "{command}"')

    def __check_if_input_prompt(self, response: List[str]) -> bool:
        """
        returns if maxima returned an input prompt (%i[0-9]+)

        Args:
            response (List[str]): maxima's response

        Returns:
            bool: input prompt received
        """
        for l in response:
            if str.startswith(l, "(%i"):
                return True
        return False

    def __format_maxima_result(self, response: List[str]) -> Optional[str]:
        """
        checks if the maxima response contains a result line (%o[0-9]+)
        and if that is the case the result is formatted otherwise None is returned

        Args:
            response (List[str]): maxima's response

        Returns:
            Optional[str]: formatted result or None
        """
        maxima_result = None

        for l in response:
            line = l.strip()

            # check if response is valid maxima output
            if str.startswith(line, "(%o"):
                # format result by removing prompt and white space
                end_of_prefix = line.find(")")
                maxima_result = line[end_of_prefix + 2 :].strip()
            return maxima_result

    def __start_maxima(self) -> None:
        """starts maxima client process in a thread"""
        self.maxima_thread = threading.Thread(target=self.__connect_maxima_to_server)
        self.maxima_thread.start()

    def __connect_maxima_to_server(self) -> None:
        """starts maxima and connects it to socket server"""
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
            self.__debug_message(f"maxima: {line.decode()}")

    def __kill_subprocess(self, pid: int) -> None:
        """
        kills a subprocess (SIGTERM) with pid

        Args:
            pid (int): process id of process to kill
        """
        process = psutil.Process(pid)
        for proc in process.children(recursive=True):
            proc.kill()

        process.kill()

    def close(self) -> None:
        """kills maxima client process, closes socket server, and closes named pipes for commands and results"""
        # send SIGTERM to maxima sub process
        self.__kill_subprocess(self.maxima_pid)
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

    def raw_command(self, command_string: str) -> str:
        """
        sends a command as a string to maxima

        Args:
            command_string (str): string containing the command

        Raises:
            MaximaServerNotAcceptingCommandException: raised when server is not accepting commands

        Returns:
            str: maxima result
        """
        # check if maxima server is waiting for a command
        if self.maxima_server_state != MaximaServerState.WAITING_FOR_COMMAND:
            self.__debug_message("server is not accepting commands.")
            raise MaximaServerNotAcceptingCommandException()

        else:
            # send command to maxima server
            self.__debug_message(f'sending command to server: "{command_string}"')
            os.write(self.command_pipe_write, command_string.encode())
            return os.read(self.result_pipe_read, 1024).decode()
