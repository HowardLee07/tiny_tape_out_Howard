## How it works

The analyzer records eight consecutive samples of four digital channels. It
samples its inputs on each rising edge of `clk`. An ARM rising edge observed
in the idle or ready state starts a capture. Beginning on the following
clock edge, a sampled low-to-high transition on CH0 triggers recording.
That transition is stored as sample 0. The following seven clock edges store
samples 1 through 7. DONE goes high once sample 7 has been stored.

ARM is edge-detected and ignored while waiting for a trigger or capturing.
When DONE is high, the sample at RD_ADDR appears on RD_DATA without another
clock edge. RD_DATA outputs zero while DONE is low. Samples remain available
until a new ARM edge is accepted or reset is sampled. Reset (`rst_n`) is active
low and synchronous. Its sampled ARM history starts at zero.

Use a source with signals stable around the sampling edge for deterministic
capture. An input transition between sampling edges can be missed.

## How to test

1. Hold ARM and CH0 low. Apply reset for at least one rising edge and release it.
2. Raise ARM for a clock edge while CH0 is low. Lower ARM with CH0 still low.
3. Drive the following four-bit words in order, one word per rising clock edge.
   CH0 is the least significant bit. The first word triggers capture.

   | Sample address | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | Expected word (hex) | 1 | 2 | 6 | 4 | F | 8 | A | 3 |

4. Check that DONE is high after the eighth word. Read addresses 0 to 7 and
   compare them with the table. No clock edge is needed to change the read address.

A microcontroller can drive the four channels, ARM, address, clock and reset,
and read the four sample outputs plus DONE. With manual drive, set the inputs
before pulsing the clock.
