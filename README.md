# Python modem

## Usage

### Transmitter
- To write an encoded message to `{filename.wav}`, type `python3 ./transmitter.py {filename.wav}` in the command line from the `modem` directory. Then input the message you wish to encode.
- To play the encoded message from your device's speakers, type `python3 ./transmitter.py` and then input the message you wish to enode. 
### Encoder
- To decode a message from `{filename.wav}`, type `python3 ./receiver.py {filename.wav}`.
- To decode a message coming from the device's microphone, type `python3 ./receiver.py` and then play the encoded message.

## Settings
By default, 880Hz represents a 1 and 440Hz represents a 0. The constant `FRAMERATE` governs the number of bits sent per second, with the equation tying these two values being `1/FRAMERATE = number of bits per second`. 