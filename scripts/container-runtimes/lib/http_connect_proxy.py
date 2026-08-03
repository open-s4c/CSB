#!/usr/bin/env python3
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

"""Small authenticated CONNECT proxy for temporary cross-node downloads."""

import argparse
import base64
import select
import socket
import socketserver
import urllib.parse


class Proxy(socketserver.StreamRequestHandler):
    def handle(self):
        request = self.rfile.readline(8192).decode("latin1").strip()
        headers = {}
        while True:
            line = self.rfile.readline(8192).decode("latin1").strip()
            if not line:
                break
            key, _, value = line.partition(":")
            headers[key.lower()] = value.strip()
        expected = "Basic " + base64.b64encode(f"csb:{self.server.token}".encode()).decode()
        if headers.get("proxy-authorization") != expected:
            self.wfile.write(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
            return
        method, target, _ = request.split(" ", 2)
        if method != "CONNECT":
            url = urllib.parse.urlsplit(target)
            if method != "GET" or url.scheme != "http" or not url.hostname:
                self.wfile.write(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
                return
            with socket.create_connection((url.hostname, url.port or 80), timeout=30) as upstream:
                path = urllib.parse.urlunsplit(("", "", url.path or "/", url.query, ""))
                upstream.sendall(f"GET {path} HTTP/1.1\r\nHost: {url.netloc}\r\nConnection: close\r\n\r\n".encode())
                while data := upstream.recv(65536):
                    self.connection.sendall(data)
            return
        host, port = target.rsplit(":", 1)
        with socket.create_connection((host, int(port)), timeout=30) as upstream:
            self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self.wfile.flush()
            sockets = [self.connection, upstream]
            while True:
                readable, _, _ = select.select(sockets, [], [], 60)
                if not readable:
                    return
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (upstream if source is self.connection else self.connection).sendall(data)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18082)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    with Server((args.bind, args.port), Proxy) as server:
        server.token = args.token
        server.serve_forever()


if __name__ == "__main__":
    main()
