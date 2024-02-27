#!/usr/bin/env python3
import subprocess
import sys
import time

from panda import Panda
from openpilot.system.hardware import HARDWARE

unlockCommand = [0x40, 0x05, 0x30, 0x11, 0x00, 0x40, 0x00, 0x00]
lockCommand = [0x40, 0x05, 0x30, 0x11, 0x00, 0x80, 0x00, 0x00]
p = Panda()

def main():
  subprocess.run(['pkill', '-f', 'openpilot'], check=True)

  p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

  # args
  if len(sys.argv) != 2:
    sys.exit('usage:\n\nroot@localhost:/data/openpilot$ pkill -f openpilot\n\nroot@localhost:/data/openpilot$ doors.py --lock\n\nroot@localhost:/data/openpilot$ doors.py --unlock\n\nroot@localhost:/data/openpilot$ reboot')

  if sys.argv[1]  == '--lock' or sys.argv[1]  == '-l':
    p.can_send(0x750, bytes(unlockCommand), 0)
    time.sleep(0.2)
    p.can_send(0x750, bytes(lockCommand), 0)

  if sys.argv[1] == '--unlock' or sys.argv[1] == '-u':
    p.can_send(0x750, bytes(lockCommand), 0)
    time.sleep(0.2)
    p.can_send(0x750, bytes(unlockCommand), 0)

  time.sleep(0.2)
  p.set_safety_mode(Panda.SAFETY_TOYOTA)
  p.send_heartbeat()
  print('\n\n\nrelay ON again\nkthxbay\n')

  HARDWARE.reboot()

main()
