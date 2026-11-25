## How it works

TinyScope-32 captures four digital inputs on rising clock edges. A rising ARM
sample in idle or after DONE latches the trigger mask from UIO[7:4] and value
from UIO[3:0]. The following rising edge writes the first sample. Hold all
sampled inputs stable around the active edge. Reset is synchronous, active low,
and aborts an acquisition or invalidates a frozen record.

Each mask bit selects a channel to compare with its corresponding value bit.
After 16 writes, READY_TO_TRIGGER goes high. The next sampled transition from
a nonmatching word to a matching word triggers. A match held through prefill
must first clear and return. A zero mask disables triggering for that capture;
use reset to abort. With mask 1, value 1 selects a CH0 rising edge and value 0
selects a falling edge. Changes to the configuration pins after ARM have no
effect on the active capture.

The circular buffer retains the last 16 samples before the trigger. The
trigger sample and 15 subsequent samples complete the record. DONE then
goes high and the buffer freezes. While DONE is high, drive the five-bit
logical read address on {UIO[1:0], UI[7:5]}. The oldest word is at address
0, the trigger at 16 and the newest word at 31. Outputs UO[3:0] update
asynchronously with the read address and are zero before DONE. UO[4] is DONE,
UO[5] is READY_TO_TRIGGER and all UIO pins are inputs. ARM edges during
acquisition are ignored. To re-arm after DONE, ensure ARM has been sampled
low and then raise it with the desired configuration on UIO.

## How to test

1. Clock once with reset low and ARM low, then release reset. Set UIO to
   0x51 and raise ARM for one rising edge. This selects CH2=0 and CH0=1.
2. Lower ARM. Drive the word 0x4 for 16 rising edges. READY_TO_TRIGGER
   goes high after the sixteenth. Drive 0xB on the next edge to trigger.
3. Drive the words 0x0 through 0xE in order on the next 15 rising edges.
   DONE goes high on the last one.
4. Read addresses 0 through 31. Expect sixteen copies of 0x4, then 0xB at
   address 16, then 0x0 through 0xE. Read address 31 with UIO[1:0]=3 and
   UI[7:5]=7. UO[5:0] should then be 0x1E.
