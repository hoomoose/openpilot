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

                 # MPH = [0., 18,  36,  63,  94]
A_CRUISE_MIN_BP_CUSTOM = [0., 8., 16., 28., 42.]
                 # MPH = [0., 6.71, 13.4, 17.9, 24.6, 33.6, 44.7, 55.9, 67.1, 123]
A_CRUISE_MAX_BP_CUSTOM = [0.,    3,   6.,   8.,  11.,  15.,  20.,  25.,  30., 55.]

A_CRUISE_MIN_VALS_ECO = [-0.001, -0.010, -0.25, -0.5, -0.5]
A_CRUISE_MAX_VALS_ECO = [3.0, 2.5, 2.25, 1.75, 1.25, .75, .50, .35, .25, .05]

A_CRUISE_MIN_VALS_SPORT = [-0.50, -0.55, -0.60, -0.75, -1.0]
A_CRUISE_MAX_VALS_SPORT = [4.0, 3.75, 3.5, 3.0, 1.75, 1.25, 1.0, .75, .5, .25]

def get_min_accel_eco(v_ego):
  return interp(v_ego, A_CRUISE_MIN_BP_CUSTOM, A_CRUISE_MIN_VALS_ECO)

def get_max_accel_eco(v_ego):
  return interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_ECO)

def get_min_accel_sport(v_ego):
  return interp(v_ego, A_CRUISE_MIN_BP_CUSTOM, A_CRUISE_MIN_VALS_SPORT)

def get_max_accel_sport(v_ego):
  return interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_SPORT)

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

    if self.acceleration_profile == 1:
      self.max_accel = get_max_accel_eco(v_ego)
    elif self.acceleration_profile in (2, 3):
      self.max_accel = get_max_accel_sport(v_ego)
    elif not controlsState.experimentalMode:
      self.max_accel = get_max_accel(v_ego)
    else:
      self.max_accel = ACCEL_MAX

    if self.deceleration_profile == 1:
      self.min_accel = get_min_accel_eco(v_ego)
    elif self.deceleration_profile == 2:
      self.min_accel = get_min_accel_sport(v_ego)
    elif not controlsState.experimentalMode:
      self.min_accel = A_CRUISE_MIN
    else:
      self.min_accel = ACCEL_MIN

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

    frogpilotPlan.minAcceleration = self.min_accel
    frogpilotPlan.maxAcceleration = self.max_accel
    frogpilotPlan.tFollow = float(self.t_follow)
    frogpilotPlan.vCruise = float(self.v_cruise)

    pm.send('frogpilotPlan', frogpilot_plan_send)

  def update_frogpilot_params(self):
    self.is_metric = self.params.get_bool("IsMetric")

    custom_alerts = self.params.get_bool("CustomAlerts")

    custom_ui = self.params.get_bool("CustomUI")

    longitudinal_tune = self.params.get_bool("LongitudinalTune")
    self.acceleration_profile = self.params.get_int("AccelerationProfile") if longitudinal_tune else 0
    self.deceleration_profile = self.params.get_int("DecelerationProfile") if longitudinal_tune else 0
