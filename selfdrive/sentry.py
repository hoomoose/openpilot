"""Install exception handler for process crash."""
import os
import requests
import sentry_sdk
import time
import traceback

from datetime import datetime
from enum import Enum
from sentry_sdk.integrations.threading import ThreadingIntegration

from openpilot.common.params import Params
from openpilot.system.hardware import HARDWARE, PC
from openpilot.common.swaglog import cloudlog
from openpilot.system.version import get_commit, get_short_branch, get_origin, get_version, is_comma_remote

CRASHES_DIR = '/data/community/crashes/'

class SentryProject(Enum):
  # python project
  SELFDRIVE = "https://5ad1714d27324c74a30f9c538bff3b8d@o4505034923769856.ingest.sentry.io/4505034930651136"
  # native project
  SELFDRIVE_NATIVE = "https://5ad1714d27324c74a30f9c538bff3b8d@o4505034923769856.ingest.sentry.io/4505034930651136"


def is_connected_to_internet(timeout=5):
  try:
    requests.get("https://sentry.io", timeout=timeout)
    return True
  except Exception:
    return False


def bind_user() -> None:
  sentry_sdk.set_user({"id": HARDWARE.get_serial()})


def report_tombstone(fn: str, message: str, contents: str) -> None:
  frogpilot = "FrogAi" in get_origin()
  if not frogpilot or PC:
    return False

  no_internet = 0
  while True:
    if is_connected_to_internet():
      cloudlog.error({'tombstone': message})

      with sentry_sdk.configure_scope() as scope:
        bind_user()
        scope.set_extra("tombstone_fn", fn)
        scope.set_extra("tombstone", contents)
        sentry_sdk.capture_message(message=message)
        sentry_sdk.flush()
      break
    else:
      if no_internet > 5:
        break
      no_internet += 1
      time.sleep(600)


def capture_fingerprint(candidate):
  no_internet = 0
  while True:
    if is_connected_to_internet():
      bind_user()
      sentry_sdk.capture_message("Fingerprinted %s" % candidate, level='log')
      sentry_sdk.flush()
      break
    else:
      if no_internet > 5:
        break
      no_internet += 1
      time.sleep(600)


def capture_exception(*args, **kwargs) -> None:
  save_exception(traceback.format_exc())
  cloudlog.error("crash", exc_info=kwargs.get('exc_info', 1))

  try:
    bind_user()
    sentry_sdk.capture_exception(*args, **kwargs)
    sentry_sdk.flush()  # https://github.com/getsentry/sentry-python/issues/291
  except Exception:
    cloudlog.exception("sentry exception")


def save_exception(exc_text: str) -> None:
  if not os.path.exists(CRASHES_DIR):
    os.makedirs(CRASHES_DIR)

  files = [
    os.path.join(CRASHES_DIR, datetime.now().strftime('%Y-%m-%d--%H-%M-%S.log')),
    os.path.join(CRASHES_DIR, 'error.txt')
  ]

  for file in files:
    with open(file, 'w') as f:
      if file.endswith("error.txt"):
        lines = exc_text.splitlines()[-10:]
        f.write("\n".join(lines))
      else:
        f.write(exc_text)

  print('Logged current crash to {}'.format(files))


def set_tag(key: str, value: str) -> None:
  sentry_sdk.set_tag(key, value)


def init(project: SentryProject) -> bool:
  params = Params()
  installed = params.get("InstallDate", encoding='utf-8')
  updated = params.get("Updated", encoding='utf-8')

  short_branch = get_short_branch()

  if short_branch == "FrogPilot-Development":
    env = "Development"
  elif short_branch in {"FrogPilot-Staging", "FrogPilot-Testing"}:
    env = "Staging"
  elif short_branch == "FrogPilot":
    env = "Release"
  else:
    env = short_branch

  integrations = []
  if project == SentryProject.SELFDRIVE:
    integrations.append(ThreadingIntegration(propagate_hub=True))

  sentry_sdk.init(project.value,
                  default_integrations=False,
                  release=get_version(),
                  integrations=integrations,
                  traces_sample_rate=1.0,
                  max_value_length=8192,
                  environment=env)

  sentry_sdk.set_user({"id": HARDWARE.get_serial()})
  sentry_sdk.set_tag("branch", short_branch)
  sentry_sdk.set_tag("commit", get_commit())
  sentry_sdk.set_tag("updated", updated)
  sentry_sdk.set_tag("installed", installed)

  if project == SentryProject.SELFDRIVE:
    sentry_sdk.Hub.current.start_session()

  return True
