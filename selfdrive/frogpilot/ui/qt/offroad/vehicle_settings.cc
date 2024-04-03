#include "selfdrive/frogpilot/ui/qt/offroad/vehicle_settings.h"

FrogPilotVehiclesPanel::FrogPilotVehiclesPanel(SettingsWindow *parent) : FrogPilotListWidget(parent) {
  disableOpenpilotLong = new ParamControl("DisableOpenpilotLongitudinal", tr("Disable openpilot Longitudinal Control"), tr("Disable openpilot longitudinal control and use stock ACC instead."), "", this);
  addItem(disableOpenpilotLong);

  QObject::connect(disableOpenpilotLong, &ToggleControl::toggleFlipped, [=]() {
    if (started) {
      if (FrogPilotConfirmationDialog::toggle(tr("Reboot required to take effect."), tr("Reboot Now"), this)) {
        Hardware::reboot();
      }
    }
  });

  std::vector<std::tuple<QString, QString, QString, QString>> vehicleToggles {
    {"LongitudinalTune", tr("Longitudinal Tune"), tr("Use a custom Toyota longitudinal tune.\n\nCydia = More focused on TSS-P vehicles but works for all Toyotas\n\nDragonPilot = Focused on TSS2 vehicles\n\nFrogPilot = Takes the best of both worlds with some personal tweaks focused around FrogsGoMoo's 2019 Lexus ES 350"), ""},
  };

  for (const auto &[param, title, desc, icon] : vehicleToggles) {
    ParamControl *toggle;

    if (param == "LongitudinalTune") {
      std::vector<std::pair<QString, QString>> tuneOptions{
        {"StockTune", tr("Stock")},
        {"CydiaTune", tr("Cydia")},
      };
      toggle = new FrogPilotButtonsParamControl(param, title, desc, icon, tuneOptions);

      QObject::connect(static_cast<FrogPilotButtonsParamControl*>(toggle), &FrogPilotButtonsParamControl::buttonClicked, [this]() {
        if (started) {
          if (FrogPilotConfirmationDialog::toggle(tr("Reboot required to take effect."), tr("Reboot Now"), this)) {
            Hardware::reboot();
          }
        }
      });

    } else {
      toggle = new ParamControl(param, title, desc, icon, this);
    }

    toggle->setVisible(false);
    addItem(toggle);
    toggles[param.toStdString()] = toggle;

    QObject::connect(toggle, &ToggleControl::toggleFlipped, [this]() {
      updateToggles();
    });

    QObject::connect(toggle, &AbstractControl::showDescriptionEvent, [this]() {
      update();
    });
  }

  std::set<QString> rebootKeys = {};
  for (const QString &key : rebootKeys) {
    QObject::connect(toggles[key.toStdString().c_str()], &ToggleControl::toggleFlipped, [this]() {
      if (started) {
        if (FrogPilotConfirmationDialog::toggle(tr("Reboot required to take effect."), tr("Reboot Now"), this)) {
          Hardware::reboot();
        }
      }
    });
  }

  QObject::connect(uiState(), &UIState::uiUpdate, this, &FrogPilotVehiclesPanel::updateState);

  updateCarToggles();
}

void FrogPilotVehiclesPanel::updateState(const UIState &s) {
  if (!isVisible()) return;

  started = s.scene.started;
}

void FrogPilotVehiclesPanel::showEvent(QShowEvent *event) {
  updateCarToggles();
}

void FrogPilotVehiclesPanel::updateToggles() {
  std::thread([this]() {
    paramsMemory.putBool("FrogPilotTogglesUpdated", true);
    std::this_thread::sleep_for(std::chrono::seconds(1));
    paramsMemory.putBool("FrogPilotTogglesUpdated", false);
  }).detach();
}

void FrogPilotVehiclesPanel::updateCarToggles() {
  auto carParams = params.get("CarParamsPersistent");
  if (!carParams.empty()) {
    AlignedBuffer aligned_buf;
    capnp::FlatArrayMessageReader cmsg(aligned_buf.align(carParams.data(), carParams.size()));
    cereal::CarParams::Reader CP = cmsg.getRoot<cereal::CarParams>();

    hasOpenpilotLongitudinal = CP.getOpenpilotLongitudinalControl();
  } else {
    hasOpenpilotLongitudinal = false;
  }

  hideToggles();
}

void FrogPilotVehiclesPanel::hideToggles() {
  disableOpenpilotLong->setVisible(hasOpenpilotLongitudinal);

  bool gm = carMake == "Buick" || carMake == "Cadillac" || carMake == "Chevrolet" || carMake == "GM" || carMake == "GMC";
  bool subaru = carMake == "Subaru";
  bool toyota = carMake == "Lexus" || carMake == "Toyota";

  std::set<QString> longitudinalKeys = {"LongitudinalTune"};

  for (auto &[key, toggle] : toggles) {
    if (toggle) {
      toggle->setVisible(false);

      if (!hasOpenpilotLongitudinal && longitudinalKeys.find(key.c_str()) != longitudinalKeys.end()) {
        continue;
      }

      if (gm) {
        toggle->setVisible(gmKeys.find(key.c_str()) != gmKeys.end());
      } else if (subaru) {
        toggle->setVisible(subaruKeys.find(key.c_str()) != subaruKeys.end());
      } else if (toyota) {
        toggle->setVisible(toyotaKeys.find(key.c_str()) != toyotaKeys.end());
      }
    }
  }

  update();
}
