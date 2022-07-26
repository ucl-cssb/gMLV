import sys
import os

sys.path.append('../../RED_master/')


import json
import math
from casadi import *
import numpy as np
import matplotlib.pyplot as plt
from RED.environments.OED_env import *
import tensorflow as tf
import time
from xdot import xdot

from simulate import simulate

def check_symmetric(a, rtol=1e-05, atol=1e-08):
    return numpy.allclose(a, a.T, rtol=rtol, atol=atol)


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


lb = params.copy()
lb[lb>0] *= 0.8
lb[lb<0] *= 1.2
ub = params.copy()
ub[ub>0] *= 1.2
ub[ub<0] *= 0.8

print(lb)
print(ub)

sys.exit()

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
print('trajectory solver initialised')
all_final_params = []
all_initial_params = []

us = np.load('working_dir/us.npy')
print(us.shape)

env.CI_solver = env.get_control_interval_solver(control_interval_time, dt, mode='sim')
trajectory_solver = env.get_sampled_trajectory_solver(N_control_intervals, control_interval_time, dt)




all_losses = []

for i in range(30):
    print()
    print('SAMPLE: ', i)
    initial_params = np.random.uniform(low=lb, high=ub)
    param_guesses = initial_params
    param_guesses = DM(param_guesses)
    env.param_guesses = param_guesses
    print('initial params: ', param_guesses)
    env.reset()

    env.us = us


    trajectory = trajectory_solver(y0, params,
                                       reshape(us, (n_controlled_inputs, N_control_intervals)))

    print(trajectory.shape)
    print(trajectory[0,:])

    #print(trajectory[:,0:2])
    # add noramlly distributed noise
    trajectory[0:len(y0),:] += np.random.normal(loc = 0, scale = np.sqrt(0.05*trajectory[0:len(y0),:]))
    #print(trajectory[:,0:2])
    #print(np.random.normal(loc = 0, scale = 0.05*trajectory[:,0:2]))

    param_solver = env.get_param_solver(trajectory_solver, trajectory, initial_Y = y0.T)
    print('param solver initialised')

    print(lb)
    print(ub)
    print(param_guesses)

    sol = param_solver(x0=param_guesses, lbx=lb, ubx=ub)
    print(sol)

    param_guesses = sol['x']

    #est_trajectory = trajectory_solver(env.initial_Y, param_guesses, env.us).T
    print('initial params: ', initial_params)
    print('inferrred params: ', param_guesses)
    print('actual params: ', env.actual_params)



    print(trajectory[-1,0])

    all_final_params.append(param_guesses.elements())
    all_losses.append(sol['f'].elements())

print(np.array(all_final_params))
all_final_params = np.array(all_final_params)
cov = np.cov(all_final_params.T)

q, r = qr(cov)

det_cov = np.prod(diag(r).elements())

logdet_cov = trace(log(r)).elements()[0]
print(cov)
print(check_symmetric(cov))
print('cov shape: ', cov.shape)

print(' det cov: ', det_cov)
print('eigen values: ', np.linalg.eig(cov)[0])
print('log det cov; ',logdet_cov)
print('losses:', all_losses)
np.save('./working_dir/all_final_params_opt.npy', all_final_params)
np.save('./working_dir/all_losses_opt.npy', np.array(all_losses))
