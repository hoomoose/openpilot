# PFEIFER - MAPD - Modified by FrogAi for FrogPilot to automatically update
import os
import stat
import subprocess
import urllib.request

from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper

VERSION = 'v1'

MAPD_PATH = '/data/media/0/osm/mapd'
VERSION_PATH = '/data/media/0/osm/mapd_version'

def fetch_version():
  version_file_url = f"https://raw.githubusercontent.com/FrogAi/FrogPilot-Resources/master/mapd_version_{VERSION}.txt"

  with urllib.request.urlopen(version_file_url) as f:
    return f.read().decode('utf-8').strip()

def download():
  version = fetch_version()
  url = f"https://github.com/pfeiferj/openpilot-mapd/releases/download/{version}/mapd"
  mapd_dir = os.path.dirname(MAPD_PATH)

  if not os.path.exists(mapd_dir):
    os.makedirs(mapd_dir)

  with urllib.request.urlopen(url) as f:
    with open(MAPD_PATH, 'wb') as output:
      output.write(f.read())
      os.fsync(output)
      current_permissions = stat.S_IMODE(os.lstat(MAPD_PATH).st_mode) # <-- preserve permissions
      os.chmod(MAPD_PATH, current_permissions | stat.S_IEXEC) # <-- preserve permissions

    with open(VERSION_PATH, 'w') as output:
      output.write(version)
      os.fsync(output)

def mapd_thread(sm=None, pm=None):
  rk = Ratekeeper(0.05, print_delay_threshold=None)

  params = Params()
  params_memory = Params("/dev/shm/params")

  automatic_updates = params.get_bool("AutomaticUpdates")

  while True:
    if params_memory.get_bool("FrogPilotTogglesUpdated"):
      automatic_updates = params.get_bool("AutomaticUpdates")

    try:
      if not os.path.exists(MAPD_PATH):
        download()
        continue

      if not os.path.exists(VERSION_PATH):
        download()
        continue

      with open(VERSION_PATH) as f:
        content = f.read()
        if content != fetch_version() and (automatic_updates or params_memory.get_bool("ManualUpdateInitiated")):
          download()
          continue

      process = subprocess.Popen(MAPD_PATH)
      process.wait()
    except Exception as e:
      print(e)

    rk.keep_time()


def main(sm=None, pm=None):
  mapd_thread(sm, pm)

if __name__ == "__main__":
  main()
