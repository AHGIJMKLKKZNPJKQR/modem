#!/usr/bin/env python3
# vim:ts=4:sts=4:sw=4:expandtab
import struct
import math
import zlib
import sys
from bitarray import bitarray
import numpy
import wave
import pyaudio

CHANNELS = 1
SAMPLE_WIDTH = 2
SAMPLE_TYPE = numpy.dtype('<i2')
SAMPLE_MAX = 2**15 - 1
SAMPLERATE = 44000
FRAMERATE = .125
ONE = 800
ZERO = 440
CHUNK = math.floor(SAMPLERATE * FRAMERATE)

pa = pyaudio.PyAudio()

table = {
  '0000': bitarray('11110'), 
  '0001': bitarray('01001'), 
  '0010': bitarray('10100'), 
  '0011': bitarray('10101'), 
  '0100': bitarray('01010'), 
  '0101': bitarray('01011'), 
  '0110': bitarray('01110'), 
  '0111': bitarray('01111'), 
  '1000': bitarray('10010'), 
  '1001': bitarray('10011'), 
  '1010': bitarray('10110'), 
  '1011': bitarray('10111'),
  '1100': bitarray('11010'), 
  '1101': bitarray('11011'), 
  '1110': bitarray('11100'), 
  '1111': bitarray('11101')
}

def chunk(string):
  return [string[i:i + 4] for i in range(0, len(string), 4)]

def fourbfiveb(bits):
  ans = bitarray()
  ans.encode(table, chunk(bits.to01()))
  return ans

def nrzi(bits):
  encoded = bitarray()
  bit = 1
  for i in range(len(bits)):
    if bits[i] == 1:
      bit = 1 - bit
    encoded.append(bit)
  return encoded

def speaker_open():
  audio = pa.open(
    output = True,
    channels = CHANNELS,
    rate = SAMPLERATE,
    format = pa.get_format_from_width(SAMPLE_WIDTH)
  )
  return audio

def audio_write(frames, audio):
  raw = (numpy.array(frames) * SAMPLE_MAX).astype(numpy.dtype('<i2')).tobytes()
  if isinstance(audio, pyaudio.Stream):
    audio.write(raw)
  else:
    audio = wave.open(audio, 'wb')
    audio.setparams((CHANNELS, SAMPLE_WIDTH, SAMPLERATE, len(frames) // CHUNK, 'NONE', 'not compressed'))
    audio.writeframes(raw)
  audio.close()

def write_freq(freq):
  frames = [0] * CHUNK
  for i in range(CHUNK):
    frames[i] = numpy.sin(numpy.pi * i * 2 * freq / SAMPLERATE)
  return frames

def make_audio(bitarr, one, zero):
  frames = []
  for i in range(len(bitarr)):
    frames = frames + write_freq(one if bitarr[i] == 1 else zero)
  return frames

def encode(src, dst, msg):

  dst = struct.pack('!LH', dst//(2**16), dst%(2**16))
  src = struct.pack('!LH', src//(2**16), src%(2**16))
  #msg : bytes, str
  if isinstance(msg, str):
    msg = bytes(msg, 'utf8')

  # Skonstruować ramkę
  frame = bitarray()
  frame.frombytes(dst)
  frame.frombytes(src)
  frame.frombytes(struct.pack("!H", len(msg)))
  frame.frombytes(msg)
  
  # crc32: potraktuj bity jako współczynniki, dopisz 32 zera na końcu. Podziel z resztą przez 100000100110000010001110110110111 i zwrócić resztę z dzielenia.
  frame.frombytes(struct.pack("!L", zlib.crc32(frame.tobytes())))

  # w NRZI pierwszy bit reprezentujemy jako zmianę względem ostatniej jedynki w preambule.
  frame = nrzi(fourbfiveb(frame))

  # Skonstruować ciąg bitów do nadania
  preamble = bitarray('10101010' * 7 + '10101011')
  message = preamble + frame

  print(message)
  return message

print("Enter your message")
raw = input()
message = encode(1, 2, raw)
audio_write(make_audio(message, ONE, ZERO), sys.argv[1] if len(sys.argv) > 1 else speaker_open())
