import datetime
import os
import time

import cereal.messaging as messaging

from cereal import car, log
from openpilot.common.params import Params
from openpilot.common.realtime import DT_MDL, Priority, config_realtime_process
from openpilot.common.time import system_time_valid
from openpilot.system.hardware import HARDWARE

from openpilot.selfdrive.frogpilot.controls.frogpilot_plannerd import FrogPilotPlannerd
from openpilot.selfdrive.frogpilot.controls.lib.frogpilot_functions import FrogPilotFunctions
from openpilot.selfdrive.frogpilot.controls.lib.theme_manager import ThemeManager

ETHERNET = log.DeviceState.NetworkType.ethernet
WIFI = log.DeviceState.NetworkType.wifi

def automatic_update_check(params):
  update_available = params.get_bool("UpdateAvailable")
  update_state = params.get("UpdaterState", encoding='utf8')

  if update_available:
    HARDWARE.reboot()
  elif update_state == "idle":
    os.system("pkill -SIGUSR1 -f selfdrive.updated.updated")

def frogpilot_thread():
  config_realtime_process(5, Priority.CTRL_LOW)

  params = Params()
  params_memory = Params("/dev/shm/params")

  frogpilot_functions = FrogPilotFunctions()
  theme_manager = ThemeManager()

  CP = None

  automatic_updates = params.get_bool("AutomaticUpdates")
  first_run = True
  time_validated = system_time_valid()

  pm = messaging.PubMaster(['frogpilotPlan'])
  sm = messaging.SubMaster(['carState', 'controlsState', 'deviceState', 'frogpilotCarControl', 'frogpilotNavigation',
                            'frogpilotPlan', 'liveLocationKalman', 'longitudinalPlan', 'modelV2', 'radarState'],
                             poll='modelV2', ignore_avg_freq=['radarState'])

  while True:
    sm.update()

    deviceState = sm['deviceState']
    started = deviceState.started

    if started:
      if CP is None:
        with car.CarParams.from_bytes(params.get("CarParams", block=True)) as msg:
          CP = msg

          frogpilot_plannerd = FrogPilotPlannerd(CP)
          frogpilot_plannerd.update_frogpilot_params()

      if sm.updated['modelV2']:
        frogpilot_plannerd.update(sm['carState'], sm['controlsState'], sm['frogpilotCarControl'], sm['frogpilotNavigation'],
                                  sm['liveLocationKalman'], sm['modelV2'], sm['radarState'])

        frogpilot_plannerd.publish(sm, pm)

    if params_memory.get_bool("FrogPilotTogglesUpdated"):
      automatic_updates = params.get_bool("AutomaticUpdates")
      frogpilot_functions.backup_toggles()

      if started:
        frogpilot_plannerd.update_frogpilot_params()

    if not time_validated:
      time_validated = system_time_valid()
      if not time_validated:
        continue

    if datetime.datetime.now().second == 0 or first_run:
      screen_off = deviceState.screenBrightnessPercent == 0
      wifi_connection = deviceState.networkType in (ETHERNET, WIFI)

      check_update = screen_off and wifi_connection and not started

      if check_update:
        if automatic_updates:
          automatic_update_check(params)

      theme_manager.update_holiday()
      first_run = False

    time.sleep(DT_MDL)

def main():
  frogpilot_thread()

if __name__ == "__main__":
  main()
