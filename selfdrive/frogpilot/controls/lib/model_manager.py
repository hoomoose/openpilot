import os
import shutil
import ssl
import stat
import urllib.request

from pathlib import Path

from openpilot.common.params import Params

params = Params()

DEFAULT_MODEL = "duck-amigo"
DEFAULT_MODEL_NAME = "Duck Amigo (Default)"

VERSION = 'v1'

DOWNLOAD_URL = "https://github.com/FrogAi/FrogPilot-Resources/releases/download"
REPOSITORY_URL = f"https://raw.githubusercontent.com/FrogAi/FrogPilot-Resources/master"
MODELS_PATH = '/data/models'

def delete_deprecated_models():
  available_models = params.get("AvailableModels", encoding='utf-8')
  if available_models is None:
    return

  available_models = available_models.split(',')

  current_model = params.get("Model", encoding='utf-8')
  if current_model not in available_models:
    params.put("Model", DEFAULT_MODEL)
    params.put("ModelName", DEFAULT_MODEL_NAME)

  for f in os.listdir(MODELS_PATH):
    if f.endswith('.thneed') and f.split('.')[0] not in available_models:
      os.remove(os.path.join(MODELS_PATH, f))

def download_model():
  selected_model = params.get("Model", encoding='utf-8')
  model_file_path = os.path.join(MODELS_PATH, f"{selected_model}.thneed")

  if not os.path.exists(model_file_path):
    download_url = f"{DOWNLOAD_URL}/{selected_model}/{selected_model}.thneed"
    print(f"Attempting to download from URL: {download_url}")

    try:
      with urllib.request.urlopen(download_url) as f, open(model_file_path, 'wb') as output:
        output.write(f.read())
        os.fsync(output.fileno())
      current_permissions = stat.S_IMODE(os.lstat(model_file_path).st_mode)
      os.chmod(model_file_path, current_permissions | stat.S_IEXEC)

    except urllib.error.HTTPError as e:
      print(f"Failed to download the file. HTTP Error: {e.code} - {e.reason}")

def populate_models():
  model_names_url = f"{REPOSITORY_URL}/model_names_{VERSION}.txt"

  try:
    with urllib.request.urlopen(model_names_url) as response:
      output = response.read().decode('utf-8')

    params.put("AvailableModels", ','.join([line.split(' - ')[0] for line in output.split('\n') if ' - ' in line]))
    params.put("AvailableModelsNames", ','.join([line.split(' - ')[1] for line in output.split('\n') if ' - ' in line]))

  except urllib.error.URLError as e:
    if isinstance(e.reason, ssl.SSLError) and e.reason.reason == "CERTIFICATE_VERIFY_FAILED":
      print("SSL Certificate verification failed. Handling the error or taking alternative actions.")
    else:
      print(f"Failed to open URL. Error: {e.reason}")
