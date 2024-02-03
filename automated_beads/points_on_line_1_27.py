# -*- coding: utf-8 -*-
"""points_on_line_1_27.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1A29pkGl9LRPtlLQb5AjfPwMubMf80m2O
"""

import matplotlib.pyplot as plt
import numpy as np


x = np.linspace(-5,5,50)

exp_y = -2 * x - 1


def slope(x, y_int=-1, slope = -2):
    return slope * x + y_int
q = np.genfromtxt("../Examples/q.txt")
#print(q)
tau = np.genfromtxt("../Examples/tau.txt")
plt.scatter(np.log(q), np.log(tau))
#plt.xscale("log")
#plt.yscale("log")

q_fit = np.genfromtxt("../Examples/q_fit.txt")
tau_fit = np.genfromtxt("../Examples/tau_fit.txt")

#plt.plot(x, slope(x), color = "g")

plt.plot(np.log(q_fit), np.log(tau_fit))
#plt.fill_between(x, exp_y, exp_y + .5, alpha = 0.2)
#plt.fill_between(x, exp_y, exp_y - .5, alpha = 0.2)
#plt.xlim(-2,2)
#plt.ylim(-5,3)
#plt.xscale("log")
#plt.yscale("log")
plt.show()

def find_closest_points(my_pt_x, my_pt_y, code_x, code_y, expected_slope=-2.0, tolerance = 5.0, y_int=-1):

    closest_points = []
    distance_store = []

    for i in range(len(my_pt_x)):
      #if point is within certain range of polyfit slope, try saving nearby points to a list
      # and calculate how well they fit
        distance = np.abs(my_pt_y[i] - code_y[i+ 1]) #(my_pt_x[i] * (expected_slope)))
        distance_store.append([distance, my_pt_x[i], my_pt_y[i]])
        print("distance is", distance)
    #print(distance_store)
    distance_store = np.array(distance_store).T
    distance_store[0] = distance_store[0]/max(distance_store[0])



    smallest_val = np.argmin(distance_store)

    return distance_store

def find_nearby_avg(dist_x_y):

    lowest_point = np.argmin(dist_x_y[0])
    thisdict = dict([(0, [lowest_point, lowest_point + 1, lowest_point + 2, lowest_point + 3]),
      (1, [lowest_point-1, lowest_point, lowest_point + 1, lowest_point + 2]),
      (2, [lowest_point-2, lowest_point-1, lowest_point, lowest_point + 1, lowest_point + 2]),
      (3, [lowest_point, lowest_point + 1, lowest_point + 2, lowest_point + 3, lowest_point + 4])])

    case_0 = np.average([dist_x_y[0][i] for i in thisdict[0]])
    case_1 = np.average([dist_x_y[0][i] for i in thisdict[1]])
    case_2 = np.average([dist_x_y[0][i] for i in thisdict[2]])
    case_3 = np.average([dist_x_y[0][i] for i in thisdict[3]])
    print([case_0, case_1, case_2, case_3])
    best_option = np.argmin([case_0, case_1, case_2, case_3])

    return thisdict[best_option]




#expected_slope = 2.1  # Replace with your expected slope
result = find_closest_points(q, tau, q_fit, tau_fit)

print(result[0])



plt.scatter(np.log(result[1]), np.log(result[2]))
#plt.xscale("log")
#plt.yscale("log")
plt.plot(np.log(q_fit), np.log(tau_fit), color = "g")
plt.fill_between(np.log(q_fit), np.log(tau_fit), np.log(tau_fit) + 0.3, alpha = 0.2)
plt.fill_between(np.log(q_fit), np.log(tau_fit), np.log(tau_fit) - 0.3, alpha = 0.2)
plt.xlim(-2,2)
plt.ylim(-5,3)
plt.show()

print(find_nearby_avg(result))

"""def main(calc_slope, my_pt_x, my_pt_y, code_x, code_y, expected_slope = -2, slope_tolerance = 0.5):

  # allowed tolerances for points
    tolerance_list = [1.0, 0.85, 0.5, 0.1]

    calc_slope = 0.0
    high_slope = expected_slope + slope_tolerance
    low_slope = expected_slope - slope_tolerance

    i = 0
    while calc_slope <=  high_slope and calc_slope >= low_slope:
    # first, run your script and return the slope value and points
    # calc_slope, my_pt_x, my_pt_y, code_x, code_y = ....
    #this should reassign calc_slope

    # then find closest points
        result = find_closest_points(my_pt_x, my_pt_y, code_x, code_y, tolerance = tolerance_list[i])

        try_points = result.T[2] # locations of points to try

        i = i + 1
    # break loop if you don't get the desired slope
        if i > 3:
            # save figures here
            print("did not satisfy condition")
            break

lowest_point = 0

test = [5, 6, 7, 8]

thisdict = dict([(0, [lowest_point, lowest_point + 1, lowest_point + 2, lowest_point + 2]), (1, [lowest_point-1, lowest_point, lowest_point + 1]), (2, [lowest_point-1, lowest_point, lowest_point + 1])])

# can we unpack this so we can just add options into the dictionary and automatically calculate the avg?
print([test[i] for i in thisdict[0]])

for i in thisdict[0]:
  print(test[i])
"""

