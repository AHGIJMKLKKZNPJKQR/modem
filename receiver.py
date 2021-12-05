import zlib
import struct
import wave
import sys
import math
import numpy
import random
import pyaudio
from bitarray import bitarray

CHANNELS = 1
SAMPLE_WIDTH = 2
SAMPLE_TYPE = numpy.dtype('<i2')
SAMPLE_MAX = 2**15 - 1
SAMPLERATE = 44000
FRAMERATE = .125
CHUNK = math.floor(SAMPLERATE * FRAMERATE)
ONE = 800
ZERO = 440
SHIFTS = 32
one = math.floor(ONE * FRAMERATE)
zero = math.floor(ZERO * FRAMERATE)

pa = pyaudio.PyAudio()

table = {
  '11110': bitarray('0000'), 
  '01001': bitarray('0001'),
  '10100': bitarray('0010'), 
  '10101': bitarray('0011'), 
  '01010': bitarray('0100'),
  '01011': bitarray('0101'),
  '01110': bitarray('0110'),
  '01111': bitarray('0111'), 
  '10010': bitarray('1000'), 
  '10011': bitarray('1001'), 
  '10110': bitarray('1010'), 
  '10111': bitarray('1011'),
  '11010': bitarray('1100'), 
  '11011': bitarray('1101'), 
  '11100': bitarray('1110'), 
  '11101': bitarray('1111')
}

def chunk(string):
  return [string[i:i + 5] for i in range(0, len(string), 5)]

# bits are a bitarray
def undonrzi(bits):
  ans = bitarray()
  prev = 1
  for i in range(len(bits)):
    ans.append(bits[i] != prev)
    prev = bits[i]
  return ans

# bits are a bitarray
def undo4b5b(bits):
  ans = bitarray()
  ans.encode(table, chunk(bits.to01()))
  return ans

# msg is bitarray
def checkcrc32(msg):
  bits = bitarray()
  bits.frombytes(struct.pack('!L', zlib.crc32(msg[:-32].tobytes())))
  return bits == msg[-32:]

def cutpreamble(msg):
  if isinstance(msg, str):
    msg = bitarray(msg)    
  return msg[64:]

# msg is either bitarray or string of 0s and 1s
def decode(msg):
  msg = undo4b5b(undonrzi(msg))

  # Checking checksum
  if not checkcrc32(msg):
    print('CRC32 checksum does not match message!\n')
    return

  dst = struct.unpack('!LH', msg[:48].tobytes())
  dst = dst[0] * (2 ** 16) + dst[1]
  src = struct.unpack('!LH', msg[48:96].tobytes())
  src = src[0] * (2 ** 16) + src[1]
  datalen = struct.unpack('!H', msg[96:112].tobytes())[0]

  print('Destination:', dst)
  print('Source:', src)
  print('Length of data:', datalen)
  print('Message:', msg[112:-32].tobytes().decode('utf-8'))

def mic_open():
  audio = pa.open(
    input=True,
    channels=CHANNELS,
    rate=SAMPLERATE,
    format=pa.get_format_from_width(SAMPLE_WIDTH),
  )
  return audio  

def audio_read(audio, chunk=CHUNK):
  if isinstance(audio, wave.Wave_read):
    raw = audio.readframes(chunk)
  else:
    raw = audio.read(chunk)
  frames = numpy.frombuffer(raw, dtype=SAMPLE_TYPE).astype(float)
  frames /= SAMPLE_MAX
  frames.clip(-1,1)
  return frames

def get_peak_height(frames):
  return numpy.max(numpy.abs(numpy.fft.rfft(frames)))

def tobit(frames):
  maxfre = numpy.argmax(numpy.abs(numpy.fft.rfft(frames)))
  
  if (maxfre == one):
    return 1
  if maxfre == zero:
    return 0
  return -1

def read_message_from_file(audio):
  bits = bitarray()
  while True:
    frames = audio_read(audio)
    if len(frames):
      bits.append(tobit(frames))
    else:
      break
  return bits


# frames is an array of length 2 * BIT_WIDTH
def adjust_shift(frames, idx):
  r = idx / SHIFTS
  shift = math.floor(r * CHUNK)
  if get_peak_height(frames, shift) > get_peak_height(frames, 0):
    frames = frames[shift:]
    frames = numpy.concatenate((frames, audio_read(audio, shift)))
  return frames[CHUNK:]

def twoones(frames):
  return tobit(frames[CHUNK:]) == 1 and tobit(frames[:CHUNK]) == 1


def parse(message):
  best_shift = 0
  for i in range(SHIFTS):
    shift = i * CHUNK // SHIFTS
    if get_peak_height(message[best_shift:best_shift + CHUNK]) < get_peak_height(message[shift:shift + CHUNK]):
      best_shift = shift
  message = message[best_shift:best_shift - CHUNK]

  prev = 0
  curr = 0
  good = False
  bits = bitarray()
  for frame in [message[i:i + CHUNK] for i in range(0, len(message), CHUNK)]:
    bit = tobit(frame)
    if bit == -1:
      return bits
    if good:
      bits.append(bit)
    else:
      curr = bit
      if prev == 1 and curr == 1:
        good = True
      prev = curr
  return bits

def sync(prevframes):
  prev = 0
  curr = 0
  idx = 1
  while prev != 1 or curr != 1:
    prev = curr
    frames = audio_read()
    if idx < SHIFTS:
      prevframes = adjust_shift(numpy.concatenate((prevframes, frames)), idx)
      curr = tobit(prevframes)
      idx += 1
    else:
      curr = tobit(frames)
    if (curr == -1):
      return
  return
    

def read_message_from_mic(audio):
  print("Starting to listen...")
  bits = bitarray()
  while True:
    frames = audio_read(audio)
    if tobit(frames) != -1:
      print("Preamble has started!")
      sync(frames)
      break

  print("Message has started!")
  while True:
    frames = audio_read(audio)
    bit = tobit(frames)
    if bit == -1:
      break
    bits.append(bit)

  # message = numpy.concatenate((message, audio_read(audio)))
  return decode(bits)

def audio_close(audio):
  if isinstance(audio, wave.Wave_read):
    audio.close()
  else:
    audio.stop_stream()
    audio.close()

if len(sys.argv) > 1:
  audio = wave.open(sys.argv[1], 'rb')  
  bits = read_message_from_file(audio)
  decode(cutpreamble(bits))
else:
  audio = mic_open()
  bits = read_message_from_mic(audio)
  decode(bits)
audio_close(audio)