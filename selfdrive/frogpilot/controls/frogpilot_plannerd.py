import numpy as np

import cereal.messaging as messaging

from openpilot.common.conversions import Conversions as CV
from openpilot.common.numpy_fast import interp
from openpilot.common.params import Params

from openpilot.selfdrive.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.selfdrive.controls.lib.drive_helpers import V_CRUISE_MAX
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import COMFORT_BRAKE, STOP_DISTANCE, get_safe_obstacle_distance, get_stopped_equivalence_factor, get_T_FOLLOW
from openpilot.selfdrive.controls.lib.longitudinal_planner import A_CRUISE_MIN, get_max_accel

from openpilot.selfdrive.frogpilot.controls.lib.frogpilot_functions import CITY_SPEED_LIMIT, CRUISING_SPEED, calculate_lane_width, calculate_road_curvature

class FrogPilotPlannerd:
  def __init__(self, CP):
    self.CP = CP

    self.params = Params()
    self.params_memory = Params("/dev/shm/params")

    self.t_follow = 0

  def update(self, carState, controlsState, frogpilotCarControl, frogpilotNavigation, liveLocationKalman, modelData, radarState):
    v_cruise_kph = min(controlsState.vCruise, V_CRUISE_MAX)
    v_cruise = v_cruise_kph * CV.KPH_TO_MS
    v_ego = max(carState.vEgo, 0)
    v_lead = radarState.leadOne.vLead

    road_curvature = calculate_road_curvature(modelData, v_ego)

    stop_distance = STOP_DISTANCE

    self.t_follow = self.update_t_follow(controlsState, frogpilotCarControl, radarState, v_ego, v_lead)

    if self.CP.openpilotLongitudinalControl:
      self.v_cruise = self.update_v_cruise(carState, controlsState, controlsState.enabled, liveLocationKalman, modelData, road_curvature, v_cruise, v_ego)
    else:
      self.v_cruise = v_cruise

  def update_t_follow(self, controlsState, frogpilotCarControl, radarState, v_ego, v_lead):
    t_follow = get_T_FOLLOW(controlsState.personality)

    lead_distance = radarState.leadOne.dRel

    return t_follow

  def update_v_cruise(self, carState, controlsState, enabled, liveLocationKalman, modelData, road_curvature, v_cruise, v_ego):
    gps_check = liveLocationKalman.gpsOK and liveLocationKalman.inputsOK

    v_ego_cluster = max(carState.vEgoCluster, v_ego)
    v_ego_diff = v_ego_cluster - v_ego

    v_cruise_cluster = max(controlsState.vCruiseCluster, controlsState.vCruise) * CV.KPH_TO_MS
    v_cruise_diff = v_cruise_cluster - v_cruise

    targets = []
    filtered_targets = [target - v_ego_diff if target > CRUISING_SPEED else v_cruise for target in targets]

    return min(filtered_targets)

  def publish(self, sm, pm):
    frogpilot_plan_send = messaging.new_message('frogpilotPlan')
    frogpilot_plan_send.valid = sm.all_checks(service_list=['carState', 'controlsState'])
    frogpilotPlan = frogpilot_plan_send.frogpilotPlan

    frogpilotPlan.tFollow = float(self.t_follow)
    frogpilotPlan.vCruise = float(self.v_cruise)

    pm.send('frogpilotPlan', frogpilot_plan_send)

  def update_frogpilot_params(self):
    self.is_metric = self.params.get_bool("IsMetric")

    custom_alerts = self.params.get_bool("CustomAlerts")

    custom_ui = self.params.get_bool("CustomUI")

    longitudinal_tune = self.params.get_bool("LongitudinalTune")
