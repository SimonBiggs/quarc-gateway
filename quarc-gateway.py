# Copyright (C) 2016 Simon Biggs
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see
# http://www.gnu.org/licenses/.

from OpenSSL import crypto

import logging
import zipfile
import socket
import os
import webbrowser
import random

from getpass import getpass

import tornado.web
import tornado.autoreload
from tornado.log import enable_pretty_logging

from traitlets import Unicode
from kernel_gateway.gatewayapp import KernelGatewayApp
from notebook.base.handlers import IPythonHandler
import notebook.auth

CERT_DIRECTORY = "certificates"
CERT_FILE = "quarc.crt"
KEY_FILE = "quarc.key"


class BaseIndex(IPythonHandler):
    def get(self):
        with open('index.html', 'r') as f:
            self.write(f.read())


class Quarc(KernelGatewayApp):
    default_url = Unicode('/')
    
    def start(self):
        handlers = [
            ('/.*', BaseIndex)
        ]

        self.web_app.add_handlers(".*$", handlers)

        super(Quarc, self).start()


def create_certificate(ip):
    certificate_filepath = os.path.join(CERT_DIRECTORY, ip, CERT_FILE)
    key_filepath = os.path.join(CERT_DIRECTORY, ip, KEY_FILE)

    if os.path.exists(certificate_filepath) & os.path.exists(key_filepath):
        pass
    else:
        if not os.path.exists(CERT_DIRECTORY):
            os.mkdir(CERT_DIRECTORY)
        
        if not os.path.exists(os.path.join(CERT_DIRECTORY, ip)):
            os.mkdir(os.path.join(CERT_DIRECTORY, ip))

        # create a key pair
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 1024)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "AU"
        cert.get_subject().ST = "NSW"
        cert.get_subject().L = "Wagga Wagga"
        cert.get_subject().O = "Quarc"
        cert.get_subject().OU = "Quarc"
        cert.get_subject().CN = ip
        cert.set_serial_number(random.randrange(1000,10000000))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha1')

        with open(certificate_filepath, 'w') as file:
            file_contents = crypto.dump_certificate(
                crypto.FILETYPE_PEM, cert).decode()
            file.write(file_contents)
            
        with open(key_filepath, 'w') as file:   
            file_contents = crypto.dump_privatekey(
                crypto.FILETYPE_PEM, k).decode()
            file.write(file_contents)

    return certificate_filepath, key_filepath

def main():
    print("Define password:")
    password = notebook.auth.passwd(getpass())

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except:
        ip = socket.gethostbyname(socket.gethostname())

    certificate, key = create_certificate(ip)

    webbrowser.open("https://{}:7575".format(ip))

    Quarc.launch_instance(
        password=password, token='', port=7575,
        ip=ip, port_retries=0,
        allow_origin='https://quarc.services',
        allow_headers='X-XSRFToken,Content-Type',
        allow_methods="DELETE",
        certfile=certificate, 
        keyfile=key)


if __name__ == "__main__":
    main()