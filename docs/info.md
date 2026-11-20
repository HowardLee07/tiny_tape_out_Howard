## How it works

TinyScope-16 samples four digital inputs on each rising edge of `clk`. A
sampled rising edge on ARM in idle or after DONE starts a new capture. At
that edge, the analyzer saves TRIGGER_FALLING (0 for rising, 1 for falling).
The first sample is taken on the following clock edge.

The analyzer continuously writes samples to a 16-entry circular buffer.
After the first eight writes, READY_TO_TRIGGER goes high. A CH0 transition of
the configured polarity can trigger starting at the ninth sample edge.
Transitions during prefill are ignored. The trigger edge is sampled along
with the other three channels. Seven more clock edges complete the capture,
which freezes the buffer and asserts DONE.

| Logical read address | Contents |
| --- | --- |
| 0–7 | Eight samples before the trigger, oldest first |
| 8 | Trigger sample |
| 9–15 | Seven samples after the trigger |

At the trigger, the analyzer saves the physical address of the oldest
sample. Readout adds the logical address to this saved address modulo 16.
Changing RD_ADDR updates the four RD_CH outputs without a clock edge while
DONE is high. RD_CH is zero while DONE is low.

ARM edges are ignored while waiting for a trigger or collecting post-trigger
samples. Hold ARM low for a clock edge before raising it for another capture.
Reset is synchronous and active low. It aborts an acquisition and invalidates
the previous record when sampled. Keep input values stable around the
sampling edges for deterministic capture.

## How to test

1. Hold ARM, CH0 and TRIGGER_FALLING low. Apply reset for one rising clock
   edge and then release it.
2. Raise ARM for one clock edge. Lower ARM and drive the following words,
   one per rising clock edge. CH0 is the least significant bit.

   | Sample phase | Read address | Input words in hex |
   | --- | --- | --- |
   | Before trigger | 0–7 | 0, 2, 4, 6, 8, A, C, E |
   | Trigger | 8 | F |
   | After trigger | 9–15 | A, 3, 1, 8, 5, C, 2 |

3. Check that READY_TO_TRIGGER goes high after the eighth word and returns
   low on the ninth word, which triggers the capture. DONE goes high after
   the sixteenth word.
4. Read all sixteen addresses and compare them with the table. Drive
   RD_ADDR[2:0] on UI[7:5] and RD_ADDR[3] on UIO[0]. The sample appears on
   UO[3:0], with DONE on UO[4] and READY_TO_TRIGGER on UO[5].
5. For falling-edge mode, set TRIGGER_FALLING on UIO[1] high before ARM and
   invert CH0 in each word in the table (XOR each word with 1).
