import sys

sys.byteorder  ##check endian system of the processor
from struct import pack, unpack, unpack_from

##packing: converting interger 1 to little endian, then convert to hex string
version = pack('<I', 1).encode('hex_codec')  ##format string: < little-endia, I unsigned int
version
##for long number such as 256-bit, struct will not work
##convert to byte sequence first
prev_block = '00000000000008a3a41b85b8b29ad444def299fee21793cd8b9e567eab02cd81'.decode('hex')
##reverse the byte order, then convert back to hex string
prev_block = prev_block[::-1].encode('hex_codec')
prev_block
##using unhexlify for the same result
from binascii import unhexlify

prev_block = unhexlify('00000000000008a3a41b85b8b29ad444def299fee21793cd8b9e567eab02cd81')
prev_block[::-1].encode('hex_codec')
merkle_root = unhexlify('2b12fcf1b09288fcaff797d71e950e71ae42b91e8bdb2304758dfcffc2b620e3')
merkle_root = merkle_root[::-1].encode('hex_codec')
merkle_root
##timestamp, use calendar.timegm()
import datetime, calendar

btimestamp = '2011-05-21 17:26:31'  ##this is GMT, not local time
b_epoc = calendar.timegm(datetime.datetime.strptime(btimestamp, "%Y-%m-%d %H:%M:%S").timetuple())
timestamp = pack('<I', b_epoc).encode('hex_codec')
timestamp
##target bits
bits = pack('<I', 440711666).encode('hex_codec')
bits
##nonce
nonce = pack('<I', 2504433986).encode('hex_codec')
nonce
import hashlib

##concatenate all the hex digits into one string
headerHex = (version + prev_block + merkle_root + timestamp + bits + nonce)
headerByte = headerHex.decode('hex')  ##convert hex digits into a sequence of bytes
##run through the double SHA256 hashing
hash = hashlib.sha256(hashlib.sha256(headerByte).digest()).digest()
hash.encode('hex_codec')  ##aggregate a sequence of bytes into a hex string
hash = hash[::-1].encode('hex_codec')  ##reverse the order in hex
hash



### difficulty

##max Bitcoin target threshold
MAX_TARGET = int("00000000FFFF0000000000000000000000000000000000000000000000000000", 16)            ## Hex, Base16
Difficulty = 244112.49                           ##from Block 125552
target = int(MAX_TARGET / Difficulty)
target32 = '{:0>64x}'.format(target)             ##convert to 32 byte hex notation; nBits = 1a44b9f2 or 440711666
print target32, hash < target32