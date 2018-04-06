import argparse
import socket
import sys
import threading
import time


class WebServer:

    def __init__(self, port=8080, doc_root="DOCUMENT_ROOT"):
        self.host = socket.gethostname().split('.')[0]
        self.port = port
        self.doc_root = doc_root
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        """
        Attempts to create and bind a socket to launch the server
        """
        try:
            print("Starting server on {host}:{port}".format(host=self.host, port=self.port))
            self.socket.bind((self.host, self.port))
            print("Server started on port {port}.".format(port=self.port))
        except Exception as e:
            print("Error: Could not bind to port {port}".format(port=self.port))
            self.shutdown()
            sys.exit(1)
        else:
            self._listen()  # Start listening for connections

    def shutdown(self):
        """
        Shutdown server
        """
        try:
            print("Shutting down server")
            self.socket.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            pass  # Pass if socket is already closed

    def _generate_headers(self, response_code):
        """
        Generate HTTP response headers.
        Parameters:
            - response_code: HTTP response code to add to the header. 200 and 404 supported
        Returns:
            A formatted HTTP header for the given response_code
        """
        header = ''
        if response_code == 200:
            header += 'HTTP/1.1 200 OK\n'
        elif response_code == 404:
            header += 'HTTP/1.1 404 Not Found\n'
        # How to count content length
        time_now = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        header += 'Date: {now}\n'.format(now=time_now)
        header += 'Server: Mikhail Samoylov for Otus Python Server\n'
        header += 'Content-lenght: \n'
        header += 'Content-type: \n'
        header += 'Connection: close\n\n'  # Signal that connection will be closed after completing the request
        return header

    def _listen(self):
        """
        Listens on self.port for any incoming connections
        """
        self.socket.listen(5)
        while True:
            (client, address) = self.socket.accept()
            client.settimeout(60)
            print("Recieved connection from {addr}".format(addr=address))
            threading.Thread(target=self._handle_client, args=(client, address)).start()

    def _handle_client(self, client, address):
        """
        Main loop for handling connecting clients and serving files from DOCUMENT_ROOT
        Parameters:
            - client: socket client from accept()
            - address: socket address from accept()
        """
        PACKET_SIZE = 1024
        while True:
            print("CLIENT", client)
            data = client.recv(PACKET_SIZE).decode()  # Recieve data packet from client and decode

            if not data: break

            request_method = data.split(' ')[0]
            print("Method: {m}".format(m=request_method))
            print("Request Body: {b}".format(b=data))

            if request_method == "GET" or request_method == "HEAD":
                # Ex) "GET /index.html" split on space
                file_requested = data.split(' ')[1]

                # If get has parameters ('?'), ignore them
                file_requested = file_requested.split('?')[0]

                if file_requested == "/":
                    file_requested = "/index.html"

                if file_requested == "/directory/":
                    file_requested = "/directory/index.html"

                filepath_to_serve = self.doc_root + file_requested
                print("Serving web page [{fp}]".format(fp=filepath_to_serve))

                # Load and Serve files content
                try:
                    f = open(filepath_to_serve, 'rb')
                    if request_method == "GET":  # Read only for GET
                        response_data = f.read()
                    f.close()
                    response_header = self._generate_headers(200)

                except Exception as e:
                    print("File not found. Serving 404 page.")
                    response_header = self._generate_headers(404)

                    if request_method == "GET":  # Temporary 404 Response Page
                        response_data = b"<html><body><center><h1>Error 404:" \
                                        b" File not found</h1></center><p>Head" \
                                        b" back to <a href="/">dry land</a>.</p></body></html>"

                response = response_header.encode()
                if request_method == "GET":
                    response += response_data

                client.send(response)
                client.close()
                break
            else:
                print("Unknown HTTP request method: {method}".format(method=request_method))


def parse_args():
    parser = argparse.ArgumentParser(
        description='Web Server For Education.')
    parser.add_argument("--p", dest="port", help="Server port.",
                        default=8080)
    parser.add_argument("--w", dest="workers", help="Workers count",
                        default=1)
    parser.add_argument("--r", dest="doc_root", help="Document Root directory.",
                        default="DOCUMENT_ROOT")
    return parser.parse_args()


def main():
    options = parse_args()


if __name__ == "__main__":
    main()
