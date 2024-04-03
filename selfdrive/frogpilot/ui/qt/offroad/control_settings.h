#pragma once

#include <set>

#include "selfdrive/frogpilot/ui/qt/widgets/frogpilot_controls.h"
#include "selfdrive/ui/qt/offroad/settings.h"
#include "selfdrive/ui/ui.h"

class FrogPilotControlsPanel : public FrogPilotListWidget {
  Q_OBJECT

public:
  explicit FrogPilotControlsPanel(SettingsWindow *parent);

signals:
  void openParentToggle();
  void openSubParentToggle();

private:
  void hideEvent(QHideEvent *event);
  void hideSubToggles();
  void hideToggles();
  void updateCarToggles();
  void updateMetric();
  void updateState(const UIState &s);
  void updateToggles();

  ButtonControl *slcPriorityButton;

  FrogPilotButtonsToggleControl *modelSelector;

  FrogPilotDualParamControl *aggressiveProfile;
  FrogPilotDualParamControl *conditionalSpeedsImperial;
  FrogPilotDualParamControl *conditionalSpeedsMetric;
  FrogPilotDualParamControl *standardProfile;
  FrogPilotDualParamControl *relaxedProfile;

  std::set<QString> aolKeys = {"AlwaysOnLateralMain", "HideAOLStatusBar", "PauseAOLOnBrake"};
  std::set<QString> conditionalExperimentalKeys = {"CECurves", "CECurvesLead", "CENavigation", "CESignal", "CESlowerLead", "CEStopLights", "HideCEMStatusBar"};
  std::set<QString> deviceManagementKeys = {"DeviceShutdown", "LowVoltageShutdown", "MuteOverheated", "NoLogging", "NoUploads", "OfflineMode"};
  std::set<QString> experimentalModeActivationKeys = {"ExperimentalModeViaDistance", "ExperimentalModeViaLKAS", "ExperimentalModeViaScreen"};
  std::set<QString> laneChangeKeys = {"LaneChangeTime", "LaneDetection", "LaneDetectionWidth", "OneLaneChange"};
  std::set<QString> lateralTuneKeys = {"ForceAutoTune", "NNFF", "NNFFLite"};
  std::set<QString> longitudinalTuneKeys = {"AccelerationProfile", "AggressiveAcceleration", "DecelerationProfile", "SmoothBraking", "StoppingDistance"};
  std::set<QString> mtscKeys = {"DisableMTSCSmoothing", "MTSCAggressiveness", "MTSCCurvatureCheck", "MTSCLimit"};
  std::set<QString> qolKeys = {"CustomCruise", "DisableOnroadUploads", "HigherBitrate", "OnroadDistanceButton", "PauseLateralOnSignal", "PauseLateralSpeed", "ReverseCruise", "SetSpeedOffset"};
  std::set<QString> speedLimitControllerKeys = {"SLCControls", "SLCQOL", "SLCVisuals"};
  std::set<QString> speedLimitControllerControlsKeys = {"Offset1", "Offset2", "Offset3", "Offset4", "SLCFallback", "SLCOverride", "SLCPriority"};
  std::set<QString> speedLimitControllerQOLKeys = {"ForceMPHDashboard", "SLCConfirmation", "SetSpeedLimit"};
  std::set<QString> speedLimitControllerVisualsKeys = {"ShowSLCOffset", "UseVienna"};
  std::set<QString> visionTurnControlKeys = {};

  std::map<std::string, ParamControl*> toggles;

  Params params;
  Params paramsMemory{"/dev/shm/params"};

  bool hasCommaNNFFSupport;
  bool hasNNFFLog;
  bool hasOpenpilotLongitudinal;
  bool hasPCMCruise;
  bool isMetric;
  bool online;
  bool started;
};
