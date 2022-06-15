import sys
import os



sys.path.append('../../RED_master/')

import math
from casadi import *
import numpy as np
import matplotlib.pyplot as plt
from RED.environments.OED_env import *

import tensorflow as tf
import time

from xdot import xdot
import json
def disablePrint():
    sys.stdout = open(os.devnull, 'w')

def enablePrint():
    sys.stdout = sys.__stdout__

SMALL_SIZE = 11
MEDIUM_SIZE = 14
BIGGER_SIZE = 17

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title



if __name__ == '__main__':
    y0 = np.array([1., 1., 1.])

    gMLV_params = json.load(open('gMLV_params.json'))
    M = np.array(gMLV_params['M'])
    E = np.array(gMLV_params['E'])
    gr = np.array(gMLV_params['gr'])
    y0 = np.array(gMLV_params['y0'])
    scale_factor = gMLV_params['scale_factor']
    eta = gMLV_params['eta']

    M *= -scale_factor
    E *= scale_factor
    gr *= scale_factor ** 2
    y0 *= scale_factor

    params = np.hstack((M.flatten(), gr.flatten(), E.flatten()))  # need to flatten for FIM calc
    print(params)

    params = DM(params)

    print(params.size())
    actual_params = params
    N_control_intervals = 10
    control_interval_time = 1  # AU
    num_inputs = -1
    input_bounds = [[0, 1], [0, 1], [0, 1]]
    n_observed_variables = 3
    n_controlled_inputs = 3
    dt = 0.01
    normaliser = -1

    save_path = './'

    args = y0, xdot, params, actual_params, n_observed_variables, n_controlled_inputs, num_inputs, input_bounds, dt, control_interval_time, normaliser
    env = OED_env(*args)

    # test simulation
    us = np.random.rand(3, N_control_intervals)
    # us = np.zeros((3,N_control_intervals))*scale_factor
    # us = np.array([[0,0,1]]*N_control_intervals).T*scale_factor


    def get_full_u_solver():
        us = SX.sym('us', N_control_intervals * n_controlled_inputs)
        env.CI_solver = env.get_control_interval_solver(control_interval_time, dt, mode='OED')
        trajectory_solver = env.get_sampled_trajectory_solver(N_control_intervals, control_interval_time, dt)
        est_trajectory = trajectory_solver(env.initial_Y, actual_params, reshape(us , (n_controlled_inputs, N_control_intervals)))

        print(est_trajectory.shape)
        FIM = env.get_FIM(est_trajectory)
        FIM += DM(np.ones(FIM.size()) * eta)
        print(FIM.shape)
        q, r = qr(FIM)

        obj = -trace(log(r))
        # obj = -log(det(FIM))
        nlp = {'x': us, 'f': obj}
        solver = env.gauss_newton(obj, nlp, us, limited_mem = True) # for some reason limited mem works better for the MPC
        # solver.print_options()
        # sys.exit()

        return solver


    u0 = [0.5] * n_controlled_inputs*N_control_intervals
    env.u0 = DM(u0)
    u_solver = get_full_u_solver()
    sol = u_solver(x0=u0, lbx = [0]*n_controlled_inputs*N_control_intervals, ubx = [1]*n_controlled_inputs*N_control_intervals)
    us = sol['x']
    print(sol)
    us = np.array(us.elements()).reshape(n_controlled_inputs,  N_control_intervals, order = 'F').T
    print('logdetFIM:', -sol['f'])
    print('us:')
    print(us)


    np.save('working_dir/us.npy', us)





