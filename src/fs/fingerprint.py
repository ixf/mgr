import os, binascii

def fingerprint(b=4):
    return binascii.b2a_hex(os.urandom(b)).decode('ascii')
