import socket
import subprocess
import threading

def check_if_prompt(data):
    print(data.decode())


def start_maxima_server(port):
    maxima_server = threading.Thread(target=start_socket_server, args=(port,))
    maxima_server.deamon = True
    maxima_server.start()

def start_socket_server(port):
    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

    print("test")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, port))
        s.listen()
        conn, addr = s.accept()
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"server: {data}")
                #check_if_prompt(data)

def start_maxima(port):
    maxima_thread = threading.Thread(target=connect_maxima_to_server, args=(port,))
    maxima_thread.deamon = True
    maxima_thread.start()

def connect_maxima_to_server(port):
    maxima_cmd = f"maxima -s {port}"
    process = subprocess.Popen(maxima_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    stdout_iterator = iter(process.stdout.readline, b"")

    for line in stdout_iterator: 
        print(f"maxima: {line}")

if __name__ == "__main__":
    print("Start maxima server")
    start_maxima_server(65432)
    print("Start maxima")
    start_maxima(65432)

    print("loop")
    while True:
        pass