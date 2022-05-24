from Hospital import Hospital
from R_in_Surgery import SurgeryVariable_SurgeryRequest
from S_in_Surgery import SurgeryVariable_Surgeon
from Constraint import Constraint
from copy import deepcopy
import random
import math
from datetime import time
import pandas as pd
# from Prices import set_d_prices, set_dr_prices, set_dro_prices
import Prices
import numpy as np
import matplotlib.pyplot as plt
import decimal
# from pylab import plot, title, xlabel, ylabel, savefig, legend, array

random.seed(4)
inf_price = 1_000  # for hard constraints


def init_variables2(hospital):
    # s_v - surgeon variable
    # sr_v -surgery request variable
    variables = {}  # format: {w1:{d1:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)]...},
    # d2:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)...]}}, w2:{d1:{r1:[(sr_v,sr),(sr_v,sr)...],.... }
    d_dict = {}  # key - room num - list of tuples [(sr_v,sr),(sr_v,sr)...]
    w_dict = {}
    v = []  # the list of tuples (sr_v,s_v) the tuple represents the same surgery

    sr_constraints, s_constraints = init_constraints()

    for ward in hospital.wards:
        w_dict.clear()
        room_allocation = ward.room_allocation
        for d in room_allocation:  # key of room_allocation is the different dates
            d_dict.clear()
            for room in room_allocation[d]:  # set of rooms that the ward received in the current date
                v.clear()
                for i in range(1, ward.max_slots):
                    v.append((SurgeryVariable_SurgeryRequest(room, day=d, order=i, sr_domain=ward.RTG,
                                                             constraints=sr_constraints),
                              SurgeryVariable_Surgeon(room, day=d, order=i, surgeon_domain=ward.ward_surgeons,
                                                      constraints=s_constraints)))
                d_dict[room.num] = v.copy()
            w_dict[d] = d_dict.copy()
        variables[ward] = w_dict.copy()

    return variables


def infinity():
    """
    :return: a generator from 0 to ing
    """
    i = 0
    while True:
        i += 1
        print(i)
        yield i


def sa_schedule(t, case=0):
    """
    generates a schedule for simulated annealing algo
    :param case: int resembles the solution space we want to work with
    {1 - all diff + surgeon patient, 2 - surgeon feasible , 3- None} default - 0  not taken into consideration when
    determining T0
    :param t: int current iteration
    :return: current temp
    """

    if case == 0:
        T0 = 162
        a = 0.005  # decrement factor
    if case == 1:
        T0 = inf_price * 2  # delta CMAX when passing from feasible to not feasible solution. total duration + overlapping
        a = 0.0005 * 10_000 * 2  # decrement factor
    if case == 2:
        T0 = inf_price * 3  # all dif, total duration, overlapping
        a = 0.0005 * 10_000 * 3  # decrement factor
    if case == 3:
        T0 = inf_price * 4
        a = 0.0005 * 10_000 * 4  # decrement factor
    return T0 - a * t


def sa_stopping_temp(case=0):
    """
    generates a stopping condition
    :param param: string - type of schedule Linear or Exponential
    :return: the stopping temperature
    """
    if case == 0:
        return 0.166
    if case == 1:
        # return 0.166 * 10_000 * 2
        return 0.166 * 100 * 2
    if case == 2:
        #return 0.166 * 10_000 * 3
        return 0.166 * 100 * 3
    if case == 3:
        #return 0.166 * 10_0000 * 4
        return 0.166 * 100 * 4


def set_init_value_day(v_dict, ward):
    """
     could receive d_dict of a specific ward and d - but just to be able to play with it for now..
    calculates the value of a day overall waiting time (wt) - over all costs of all the variables in the day. Calculates the value
    from zero with no prior value calculated, that means not the value after an update of a single variable
    Can't be preformed while determining init_sol because looks their are constraints that need the whole solution
    :param v_dict: v_dict: format: {w1:{d1:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)]...},
    d2:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)...]}}, w2:{d1:{r1:[(sr_v,sr),(sr_v,sr)...],.... }
    :param d: string of a date referring to the date the value will be calculated to
    :param ward: ward object
    :return: float the price of the day and the sumo of the wt of the day
    """
    init_cost = 0
    init_wt = 0  # wt - waiting time
    for d in v_dict[ward]:
        d_dict = v_dict[ward][d]
        init_cost += Prices.set_d_prices(d_dict, None, None)
        for room_num in d_dict:
            init_cost += Prices.set_dr_prices(d_dict[room_num], ward, True, None)
            for t in d_dict[room_num]:  # t- tuple (sr_v, s_v)
                sr_v = t[0]
                s_v = t[1]
                init_cost += Prices.set_dro_prices(sr_v, s_v, ward, True, None)
                if sr_v.value is not None:
                    init_wt += sr_v.value.calc_waiting_days(d)
                    sr_v.best_value = sr_v.value
                    s_v.best_value = s_v.value

    return init_wt + init_cost, init_wt


def calc_value(tu, current_wt, chosen_v):
    """
    calcs the total cost of the solution node
    :param chosen_v:
    :param current_wt:
    :param tu: tuple (sr_v, s_v)
    :return: float total cost
    """
    cost = 0
    wt = current_wt
    sr_v = tu[0]
    s_v = tu[1]
    constraints = sr_v.constraints
    for con_key in constraints:
        for cons in constraints[con_key]:
            cost += sum(constraints[con_key][cons].prices.values())

    cost += sum(s_v.constraints['d']['overlapping'].prices.values())  # s_v constraint which is not sr_v constraint
    if type(chosen_v) is SurgeryVariable_Surgeon:
        return current_wt + cost
    else:
        if sr_v.value is not None:
            if sr_v.prior_value is None:
                wt += sr_v.value.calc_waiting_days(sr_v.day)
            else:
                wt += sr_v.value.calc_waiting_days(sr_v.day) - \
                      sr_v.prior_value.calc_waiting_days(sr_v.day)
        return wt + cost


def simulated_annealing(v_dict, ward, init_sol_param, case, genetic):
    """
    performs SA on a single day
    could receive d_dict of a specific ward and d - but just to be able to play with it for now...
    :param genetic: boolean - if sa is used for init population in genetic algorithm , if so list of all the schedules
    is returned
    :param v_dict: format: {w1:{d1:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)]...},
    d2:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)...]}}, w2:{d1:{r1:[(sr_v,sr),(sr_v,sr)...],.... }
    :param d: the date which the solution will be generated to
    :param ward: ward object whom the rooms concern
   :param case: int resembles the solution space we want to work with
    {1 - all diff + surgeon patient, 2 - surgeon feasible , 3- None}
    :param init_sol_param: function that determines the parameter which according to it the initial state will be
    generated
    """
    if genetic:
        g = []
    global t
    plot_list = []
    num_surgeries = init_solution(v_dict, init_sol_param, ward, 1)
    # dictionary {key- room num : value - current number of surgeries}
    current_value, current_u = set_init_value_day(v_dict, ward)  # float the value of the day -
    # total wt + total cost    plot_list.append([0, current_value])
    best_value = current_value
    best_schedule = deepcopy(v_dict)
    if genetic:
        g.append((deepcopy(v_dict), current_value, deepcopy(num_surgeries)))  # tuple of schedule and its value
    num_changes = 0
    for t in infinity():
        # plot_list.append([t, plot_value])
        print(t)
        if t > 50 :
            return g
        T = sa_schedule(t)
        st = sa_stopping_temp()
        if T <= st:  # and best_value < 100_000:  # none hard constraints are broken
            if genetic:
                return g
            else:
                return best_value, t, num_changes, plot_list, best_schedule
        else:
            chosen_v, delta_E, tu = select_successor(v_dict, ward, num_surgeries, case)
            if delta_E < 0:
                num_changes += 1
                current_value = calc_value(tu, current_u, chosen_v)
                plot_list.append([t, current_value])
                if genetic:
                    g.append((deepcopy(v_dict), current_value, deepcopy(num_surgeries)))
                if current_value < best_value:
                    best_value = current_value
                    best_schedule = deepcopy(v_dict)
                    '''if isinstance(chosen_v, tuple):  # when a new surgery was added to the room both sr_v and s_v are
                        # updated
                        chosen_v[0].best_value = chosen_v[0].value
                        chosen_v[1].best_value = chosen_v[1].value
                    else:
                        chosen_v.best_value = chosen_v.value'''
            else:
                p = decimal.Decimal(math.exp(-delta_E / T))
                rnd = random.uniform(0, 1)
                if rnd < p:  # change but only to feasible solutions
                    current_value = calc_value(tu, current_u, chosen_v)
                    plot_list.append([t, current_value])
                    if genetic:
                        g.append((deepcopy(v_dict), current_value, deepcopy(num_surgeries)))
                    num_changes += 1
                else:  # don't change
                    return_to_prior_value(chosen_v, v_dict, tu, ward, num_surgeries)


def return_to_prior_value(chosen_v, v_dict, tu, ward, num_surgeries):
    """
    returns the solution to the prior solution changes the values of the concerned variables back
    :param tu: tuple of (sr_v, s_v) of the chosen_v
    :param d_dict: dictionary format {d:{room_num : [(sr_v,s_v),(sr_v,s_v)...]}
    :param chosen_v: tuple/variable depends if there was a mutual change -in case of adding new surgery in the day

    """

    if isinstance(chosen_v, tuple):  # tuple (sr_v,s_v)
        sr_v = chosen_v[0]
        s_v = chosen_v[1]
        d_dict = v_dict[ward][sr_v.day]
        room_num = sr_v.room.num
        s_v_prior_update = chosen_v[1].value
        s_v.value = chosen_v[1].prior_value
        s_v.prior_value = s_v_prior_update
        # sr_v.value.assigned -= 1
        sr_v.value.assigned.remove(sr_v.get_constraint_dro_key())
        if len(sr_v.value.assigned) == 1:
            sr_v.constraints['dro']['all_diff'].prices[sr_v.value.assigned[0]] = 0
        if sr_v.prior_value is not None:
            # sr_v.prior_value.assigned += 1
            sr_v.prior_value.assigned.append(sr_v.get_constraint_dro_key())
            set_surgery_time(sr_v.start_time, sr_v, s_v)  # takes into account it is the last surgery in the day
        else:
            num_surgeries[sr_v.day][sr_v.room.num] -= 1
            nullify_surgery_time(sr_v, s_v)
        sr_v_prior_update = sr_v.value
        sr_v.value = sr_v.prior_value
        sr_v.prior_value = sr_v_prior_update
        price = calc_price_by_variable(tu, ward, d_dict, room_num, type(None), mutual=True, next=True)

    else:
        d_dict = v_dict[ward][chosen_v.day]
        if isinstance(chosen_v, SurgeryVariable_SurgeryRequest):
            # chosen_v.prior_value.assigned += 1
            chosen_v.prior_value.assigned.append(chosen_v.get_constraint_dro_key())
            # chosen_v.value.assigned -= 1
            chosen_v.value.assigned.remove(chosen_v.get_constraint_dro_key())
            if len(chosen_v.value.assigned) == 1:
                chosen_v.constraints['dro']['all_diff'].prices[chosen_v.value.assigned[0]] = 0
            prior_update = chosen_v.value
            chosen_v.value = chosen_v.prior_value
            chosen_v.prior_value = prior_update
            update_surgeries_time(d_dict, chosen_v.room.num, chosen_v.order - 1)
        else:
            prior_update = chosen_v.value
            chosen_v.value = chosen_v.prior_value
            chosen_v.prior_value = prior_update
        price = calc_price_by_variable(tu, ward, d_dict, chosen_v.room.num, type(chosen_v), mutual=False, next=True)


def nullify_surgery_time(sr_v, s_v):
    """
    sets a surgery start and end time to 00:00
    :param sr_v: surgery request variable
    :param s_v: surgeon varialbe
    """
    sr_v.start_time = time(hour=0, minute=0)
    sr_v.end_time = time(hour=0, minute=0)
    s_v.end_time = time(hour=0, minute=0)
    s_v.start_time = time(hour=0, minute=0)


def select_successor(v_dict, ward, num_surgeries, case):
    """
    selects a random variable and changes its value randomly from the domain , calculates the difference of the total
    solution price due to the change in the solution. \
    The difference is calculated by the subtraction of prior price from next price
    prior price - wt + cost of the specific variable that changed
    next price - wt + cost after the change
    :param v_dict: format: {w1:{d1:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)]...},
    d2:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)...]}}, w2:{d1:{r1:[(sr_v,sr),(sr_v,sr)...],.... }
    :param d: string date - from where the variable should be selected
    :param ward: ward object of the variable
    :param case: int resembles the solution space we want to work with
    {1 - all diff + surgeon patient, 2 - surgeon feasible , 3- None}
    :param num_surgeries:  dictionary {d : {key- room num : value - current number of surgeries}}
    :return: chosen variable/tuple and the difference in the total price of the solution, and the tuple chosen
    """
    d = random.choice(list(num_surgeries))
    d_dict = v_dict[ward][d]
    room_num = random.choice(list(d_dict))
    t = random.choice(d_dict[room_num])  # tuple (sr_v, s_v)
    chosen_v = random.choice(list(t))  # chosen variable
    num_surgeries_day = num_surgeries[d][room_num]
    delta_E = 0
    # if mutual update sr_v and s_v together
    if chosen_v.value is None:  # two options - 1: variable with no assignation 2: the domain is empty
        # if the value is none than we want to choose the next empty variable so the surgeries are in good order
        t = find_t_by_index(d_dict, chosen_v.room.num, num_surgeries_day + 1)
        delta, change = update_tuple_value(t, ward, d_dict, room_num, case)
        delta_E += delta
        if change:  # if the domain was of the chosen v was not empty
            num_surgeries[d][room_num] += 1
        return t, delta_E, t
    else:
        delta_E += update_variable_value(chosen_v, t, ward, d_dict, room_num, case)
        return chosen_v, delta_E, t


def update_tuple_value(t, ward, d_dict, room_num, case, genetic_value=False):
    """
    chooses new values for a tuple of variables which had none values and calculates the sum in the sol_value
    wt + cost
    :param t: tuple (sr_v,s_v)
    :param ward: ward objcect
    :param d_dict: dictionary format {room_num : [(sr_v,s_v),(sr_v,s_v)...]
    :param room_num: int
    :param case: int resembles the solution space we want to work with
    {1 - all diff + surgeon patient, 2 - surgeon feasible , 3- None}
    :return: delta E the difference of the total price of solution
    """
    print('Finished 3 check')
    if t is None:
        print('Finished 3')
    sr_v = t[0]
    if (sr_v == None):
        print("uv is none")
    s_v = t[1]
    change = False
    if genetic_value == False:
        if len(sr_v.domain) > 0 and len(s_v.domain) > 0:
            change = True
        if change:
            if case == 1:
                r_sr_domain = reduct_sr_domain(sr_v.domain)
                if r_sr_domain != False:
                    chosen_sr_v_value = random.choice(list(r_sr_domain))
                else:
                    change = False
                    return 0, change
            else:
                chosen_sr_v_value = random.choice(list(sr_v.domain))
            if case == 2 or case == 1:
                r_s_domain = reduct_s_domain(s_v.domain, chosen_sr_v_value.surgery_type)
                if r_s_domain != False:
                    chosen_s_v_value = random.choice(list(r_s_domain))
                else:
                    change = False
                    return 0, change
            else:
                chosen_s_v_value = random.choice(list(s_v.domain))
    if genetic_value != False or change:
        sr_v.prior_value = sr_v.value
        s_v.prior_value = s_v.value
    if genetic_value == False and change:
        prior_price = calc_price_by_variable(t, ward, d_dict, room_num, type(None), mutual=True)
        sr_v.value = chosen_sr_v_value
    else:
        sr_v.value = genetic_value[0]
    if sr_v.prior_value is not None and (change or genetic_value != False):
        sr_v.prior_value.assigned.remove(sr_v.get_constraint_dro_key())
        if len(sr_v.prior_value.assigned) == 1:
            sr_v.constraints['dro']['all_diff'].prices[sr_v.prior_value.assigned[0]] = 0
    sr_v.value.assigned.append(sr_v.get_constraint_dro_key())
    if genetic_value == False and change:
        s_v.value = chosen_s_v_value
    else:
        s_v.value = genetic_value[1]
    if sr_v.order > 1 and (change or genetic_value != False):
        prev_t = find_t_by_index(d_dict, room_num=sr_v.room.num, order=sr_v.order - 1)
        start_time = prev_t[0].end_time
    else:
        start_time = ward.start_d_hour
    if change or genetic_value != False:
        set_surgery_time(start_time, sr_v, s_v)  # relates to the surgery as a new surgery in the schedule
        next_price = calc_price_by_variable(t, ward, d_dict, room_num, type(None), mutual=True, next=True)
    if genetic_value == False and change:
        return next_price - prior_price, change
    if genetic_value == False and not change:
        return 0, change


def update_variable_value(chosen_v, t, ward, d_dict, room_num, case, genetic_value=False):
    """
    chooses new value for variable from domain and calculates the difference in the sol_value wt + cost
    :param chosen_v: chosen variable to change value
    :param t: tuple (sr_v,s_v)
    :param ward: ward object
    :param d_dict: dictionary format {room_num : [(sr_v,s_v),(sr_v,s_v)...]
    :param num_surgeries_day: int number of  current surgeries in the day
    :param room_num: int
    :param case: int resembles the solution space we want to work with
    {1 - all diff + surgeon patient, 2 - surgeon feasible , 3- None}
    :return: delta E the difference of the total price of solution
    """
    print(' Finished 2 check')
    if (t == None):
        print("Finished 2")
    if genetic_value == False:
        if len(chosen_v.domain) > 0:
            i = t.index(chosen_v)
            if i == 1:  # surgeon variable
                if case == 1 or case == 2:
                    r_s_domain = reduct_s_domain(chosen_v.domain, t[0].value.surgery_type)
                    if r_s_domain != False:
                        chosen_value = random.choice(list(r_s_domain))
                    else:
                        return 0
                else:
                    chosen_value = random.choice(list(chosen_v.domain))
            else:  # surgery request variable
                if case == 1:
                    r_sr_domain = reduct_sr_domain(chosen_v.domain)
                    if r_sr_domain != False:
                        chosen_value = random.choice(list(r_sr_domain))
                    else:
                        return 0
                else:
                    chosen_value = random.choice(list(chosen_v.domain))  # value of the variable
            chosen_v.prior_value = chosen_v.value
            prior_price = calc_price_by_variable(t, ward, d_dict, room_num, type(chosen_v), mutual=False)
            chosen_v.value = chosen_value
    else:
        i = t.index(chosen_v)
        chosen_v.prior_value = chosen_v.value
        chosen_v.value = genetic_value
    if genetic_value != False or len(chosen_v.domain) > 0:
        if i == 0:  # if chosen_v is an sr_v
            chosen_v.value.assigned.append(chosen_v.get_constraint_dro_key())
            chosen_v.prior_value.assigned.remove(chosen_v.get_constraint_dro_key())
            if len(chosen_v.prior_value.assigned) == 1:
                chosen_v.constraints['dro']['all_diff'].prices[chosen_v.prior_value.assigned[0]] = 0
            update_surgeries_time(d_dict, chosen_v.room.num, chosen_v.order - 1)
        next_price = calc_price_by_variable(t, ward, d_dict, room_num, type(chosen_v), mutual=False, next=True)
    if genetic_value == False:
        if len(chosen_v.domain) > 0:
            return next_price - prior_price
        else:
            return 0


def reduct_sr_domain(sr_domain):
    """
    reduction of domain that all diff constraint is satisfied
    :param sr_domain: set of surgery requests
    :return: set of surgery requests
    """
    legit_domain = set()
    for sr in sr_domain:
        if len(sr.assigned) < 1:
            legit_domain.add(sr)
    if len(legit_domain) > 0:
        return legit_domain
    else:
        return False


def update_surgeries_time(d_dict, room_num, order):
    """
    updates all the surgery times from a specific surgery in the day and on - the surgery value in this order has been
    change so all the surgeries time after it also changed
    :param d_dict: dictionary format {room_num : [(sr_v,s_v),(sr_v,s_v)...]
    :param room_num: int room number that needs the times updated
    :param order: int index of the order of the surgery in the day - thaat from it the times need to be updated
    """
    prior_end_time = d_dict[room_num][order][0].start_time
    for j in range(order, len(d_dict[room_num])):  # update the times of all the surgeries
        # after the updated surgery variable because the times changed
        sr_v = d_dict[room_num][j][0]  # sr_v
        s_v = d_dict[room_num][j][1]  # s_v
        if sr_v.value is None:
            break
        else:
            set_surgery_time(prior_end_time, sr_v, s_v)
            prior_end_time = sr_v.end_time


def calc_price_by_variable(t, ward, d_dict, room_num, ty, mutual, next=False):
    """

    :param t: t: tuple (sr_v,s_v)
    :param ward: ward object
    :param d_dict: dictionary format {room_num : [(sr_v,s_v),(sr_v,s_v)...]
    :param room_num: int
    :param ty: type
    :param mutual: boolean - if both variables in the tuple have been updated
    :return: new wt + new cost
    """
    cost = 0
    wt = 0
    sr_v = t[0]
    s_v = t[1]
    cost += Prices.set_dro_prices(sr_v, s_v, ward, mutual, ty)
    cost += Prices.set_dr_prices(d_dict[room_num], ward, mutual, ty)
    cost += Prices.set_d_prices(d_dict, s_v, ty, next=next)
    if isinstance(sr_v, ty) or mutual:
        if sr_v.value is not None:  # in the case prior value was None and the calculation of prior price
            wt += sr_v.value.calc_waiting_days(sr_v.day)
    return wt + cost


def find_t_by_index(d_dict, room_num, order):
    """
    finds a tuple of variables by the order argument and the type of the variable
    :param d_dict: key - room num - list of tuples [(sr_v,sr),(sr_v,sr)...]
    :param room_num: index of room
    :param order: int the order of the variable/surgery in the day
    :param ty: the type of the variable surgery request or surgeon
    :return: tuple (sr_v,s_v) of the index in the input
    """
    for t in d_dict[room_num]:
        if t[0].order == order:
            return t


def by_waiting_time(sr):
    """
    support function for a key in sorted
    :param sr:A surgery request
    :return: the entrance date of the sr - so the domain can be sorted by it
    """
    return sr.entrance_date


def calc_end_time(start_time, duration_min):
    """
    help function to calculate time objects
    :param start_time: time object including hour and minutes
    :param duration_min: duration of a process in minutes
    :return: time object of the time after the duration process
    """
    end_time_min = start_time.hour * 60 + start_time.minute + duration_min
    hour = int(end_time_min / 60)
    minute = end_time_min % 60
    if hour > 23:
        hour = 23
        minute = 59
    end_time = time(hour=hour, minute=minute)
    return end_time


def set_surgery_time(start_time, sr_v, s_v):
    """
    sets the start time and end time of a surgery - calculates and manipulates time to define end time.
    :param start_time: time object -
    :param duration_min: the duration of the surgery in minutes - int
    :param sr_v: surgery request variable object
    :param s_v: surgeon object
    """
    sr_v.start_time = start_time
    s_v.start_time = start_time
    duration_min = sr_v.value.duration
    end_time = calc_end_time(start_time, duration_min)
    sr_v.end_time = end_time
    s_v.end_time = end_time


def init_solution(v_dict, parameter, ward, case):
    """
     could receive d_dict of a specific ward and d - but just to be able to play with it for now..
    generates an initial solution - the solution is determined by the parameter. updates d-dict variables assigning each
    variable a certain value from its domain
    :param d: a certain date that the solution will be generated to
    :param v_dict:  format: {w1:{d1:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)]...},
    d2:{r1:[(sr_v,sr),(sr_v,sr)...], r2:[(sr_v,sr),(sr_v,sr)...]}}, w2:{d1:{r1:[(sr_v,sr),(sr_v,sr)...],.... }
    :param ward: ward object - to whom the room concern
    :param case: int resembles the solution space we want to work with
    {1 - all diff + surgeon patient, 2 - surgeon feasible , 3- None}
    :param parameter: the parameter that according to it the solution is generated - it will be the name of a function
    that serves as a key for the sort comparison
    :return num_surgeries - dictionary {key- room num : value - current number of surgeries}
    """
    # general heuristic for now all_diff constraint and total duration constraints are kept. i.e the same sr values will
    # not be assigned to different variables (to avoid all the variables to receive the same value) and the total
    # duration of a certain room will not exceed the max duration.

    num_surgeries = {}
    r_num_surgeries = {}
    for d in v_dict[ward]:
        r_num_surgeries.clear()
        d_dict = v_dict[ward][d]  # a dictionary -key - room value - list of [(sr_v,s_v),(sr_v,s_v)..]
        # dictionary of variables - representing room allocation of a single day for a certain ward.
        for room_num in d_dict:
            room_duration = 0
            prior_end_time = ward.start_d_hour
            for t, i in zip(d_dict[room_num], range(len(d_dict[room_num]))):  # t - tuple
                sr_v = t[0]
                s_v = t[1]
                if case == 1:
                    legit_sr_domain = reduct_sr_domain(sr_v.domain)
                    if legit_sr_domain != False:
                        sorted_domain = sorted(legit_sr_domain, key=parameter)  # returns a list
                    else:
                        sorted_domain = sorted(sr_v.domain, key=parameter)
                else:
                    sorted_domain = sorted(sr_v.domain, key=parameter)
                if len(sorted_domain) > 0:
                    for sr in sorted_domain:  # sr - surgery request
                        if room_duration + sr.duration <= ward.d_duration:
                            sr_v.value = sr
                            # sr.assigned = sr.assigned + 1
                            sr.assigned.append(sr_v.get_constraint_dro_key())
                            set_surgery_time(start_time=prior_end_time, sr_v=sr_v, s_v=s_v)
                            prior_end_time = sr_v.end_time
                            if len(s_v.domain) > 0:
                                if case == 1 or case == 2:
                                    legit_s_domain = reduct_s_domain(s_v.domain, sr_v.value.surgery_type)
                                    if legit_s_domain != False:
                                        s_v.value = random.choice(tuple(legit_s_domain))
                                    else:
                                        s_v.value = random.choice(tuple(s_v.domain))
                                else:
                                    s_v.value = random.choice(tuple(s_v.domain))
                            room_duration = room_duration + sr.duration
                            break  # assigned from domain no need to continue looking for value
                if sr_v.value is None:
                    r_num_surgeries[room_num] = sr_v.order - 1
                    break
                if i == (len(d_dict[room_num]) - 1):
                    r_num_surgeries[room_num] = sr_v.order
        num_surgeries[d] = r_num_surgeries.copy()

    return num_surgeries


def reduct_s_domain(s_domain, st):
    """
    reduces the domain to only values of surgeons which have the skill to operate this surgery type
    :param domain: set of surgeons
    :param st: surgery type
    :return: set of surgeons
    """
    legit_domain = set()
    for s in s_domain:
        if st in s.surgical_grades:
            legit_domain.add(s)
    if len(legit_domain) > 0:
        return legit_domain
    else:
        return False


def init_constraints():
    """
    initializes the different constraint objects (each one holding an empty dictionary of prices) and gathers them into
    dictionary
    :return: two dictionaries of constraints one for every type of variable surgery_request_variable and surgeon
    variable for modularity the main key is d_r_o / d_r / d (date, room , order) then each key holds a dictionary of all
    the constraints that suits this key - the key is the name of the constraint and the value is the constraint object
    """
    # hard constraints
    surgeon_patient_constraint = Constraint({})  # binary key - date_room_order
    all_diff_constraint = Constraint({})  # binary key - date_room_order (if len(assigned) of sr>1 than inf)
    surgeon_overlapping_constraint = Constraint({})
    # binary key - date (pass through all the the surgeon variables of this date of a specific ward)
    total_duration_constraint = Constraint({})  # global key date_room

    sr_constraints = {'dro': {'surgeon_patient': surgeon_patient_constraint, 'all_diff': all_diff_constraint},
                      'dr': {'total_duration': total_duration_constraint}}
    s_constraints = {'dro': {'surgeon_patient': surgeon_patient_constraint},
                     'd': {'overlapping': surgeon_overlapping_constraint}}

    return sr_constraints, s_constraints


def calc_wt_of_schedule(schedule):
    wd = 0
    for ward in schedule:
        for day in schedule[ward]:
            for room in schedule[ward][day]:
                for t in schedule[ward][day][room]:
                    if t[0].value is not None:
                        wd += t[0].value.calc_waiting_days(day)
    return wd


def genetic_algorithm(pm, size_population, case, max_generation):
    generation_values = []
    population = genetic_initialize_population(size_population, case)  # list of tuples (schedule, value)
    num_generation = 0
    best_chrom = min(population, key=lambda chrom: chrom[1])
    while True:
        new_population = []
        generation_values.append([min(population, key=lambda chrom: chrom[1])[1],
                                  sum(chrom[1] for chrom in population) / len(population)])
        for i in range(len(population)):
            parents = genetic_random_selection(population)  # returns list of schedules
            child, child_num_surgeries = genetic_reproduce(parents, case)
            if random.uniform(0, 1) < pm:
                child, child_num_surgeries = genetic_mutate(child, child_num_surgeries, case)
            child_value = genetic_calc_value(child)
            new_population.append((child, child_value, child_num_surgeries))
        genetic_selection_probability(new_population)
        population = deepcopy(new_population)
        best_of_generation = min(population, key=lambda chrom: chrom[1])
        if best_of_generation[1] < best_chrom[1]:
            best_chrom = deepcopy(best_of_generation)
        if num_generation > max_generation:
            return generation_values, best_chrom
        else:
            num_generation += 1

def genetic_initialize_population(size, case):
    """
    initializes a populcation of chromosomes when each chromozome is a sechedule i.e v_dict
    :param size: the size of the population
    :return: population - list of tuples (schedule, value, num_surgeries) and the ward that was initialized
    """
    population = []
    Soroka = Hospital(1, "Soroka")
    var_dict = init_variables2(Soroka)
    w = Soroka.find_ward(w_id=1)
    sa_schedules = simulated_annealing(var_dict, w, by_waiting_time, case=case, genetic=True)
    print('schedules' , sa_schedules)
    print('type', type(sa_schedules))
    print(' ')
    print(len(sa_schedules) , size)
    sample_index = len(sa_schedules) // size
    for i in range(len(sa_schedules)):
        print(i , sample_index)
        if i % sample_index == 0:
            population.append(sa_schedules[i])
    genetic_selection_probability(population)
    return population


def genetic_selection_probability(population):
    """
    for every schedule in population Cumulative distribution values are assigned.
    first the density probability is assigned and from there the cumulative one.
    the range of p is added to each tuple of chrom in the population
    the probability is defined for a min problem
    :param population: list of tuples (schedule, value)
    :return: void - updates population to be list of tuples (schedule, value, p_begin, p_end)
    """
    max_value = max(population, key=lambda item: item[1])[1]
    sum_value = sum(chrom[1] for chrom in population)
    sum_v = 0
    list_v = []
    for chrom in population:  # chrom = tuple
        v = (max_value + 1 - chrom[1]) / sum_value
        sum_v += v
        list_v.append(v)

    p_prior = 0
    for i in range(len(population)):
        p = list_v[i] / sum_v
        population[i] = population[i] + (p_prior, p_prior + p,)
        p_prior += p


def genetic_random_selection(population):
    """
    select parents from population
    :param population: list of tuples (schedule, value, p_begin, p_end)
    :return: list of  tuples (parent schedules, parents num of surgeries)
    """
    parents = []
    for i in range(2):
        p = random.uniform(0, 1)
        for chrom in population:
            if chrom[3] < p < chrom[4]:
                parents.append((chrom[0], chrom[2]))
                break
    return parents


def genetic_reproduce(parents, case):
    """
    generated child schedule from two parents - compares the schedules for every variable in schedule i.e. surgery request
    or surgeon that are not identical in both schedules child chooses randomly one of the parents variables
    :param parents: list of schedules
    :param case: selection method
    :return: child variable
    """
    parent_a = parents[0][0]
    parent_b = parents[1][0]
    child = deepcopy(parent_a)
    child_num_surgeries = deepcopy(parents[0][1])

    for ward_a, ward_b, ward_c in zip(parent_a, parent_b, child):
        for day in parent_a[ward_a]:
            for room_num in parent_a[ward_a][day]:
                for order in range(len(parent_a[ward_a][day][room_num])):
                    variable_a = parent_a[ward_a][day][room_num][order]
                    variable_b = parent_b[ward_b][day][room_num][order]
                    variable_c = child[ward_c][day][room_num][order]
                    if variable_a[0].value != variable_b[0].value:  # surgery request in surgery request variable
                        if variable_b[0].value is not None:
                            p = random.uniform(0, 1)
                            if p < 0.5:
                                if variable_a[0].value is None:
                                    srv_value = genetic_find_child_value(variable_b[0].value, variable_c[0])
                                    sr_value = genetic_find_child_value(variable_b[1].value, variable_c[1])
                                    update_tuple_value(child[ward_c][day][room_num][order], ward_c, child[ward_c][day],
                                                       room_num, case, (srv_value, sr_value))
                                    child_num_surgeries[day][room_num] += 1
                                    continue
                                else:
                                    srv_value = genetic_find_child_value(variable_b[0].value, variable_c[0])
                                    update_variable_value(child[ward_c][day][room_num][order][0], variable_c, ward_c,
                                                          child[ward_c][day], room_num, case, srv_value)
                        else:
                            continue
                    if variable_a[0].value is not None:
                        if variable_a[1].value != variable_b[1].value:
                            p = random.uniform(0, 1)
                            if p < 0.5:
                                sr_value = genetic_find_child_value(variable_b[1].value, variable_c[1])
                                update_variable_value(child[ward_c][day][room_num][order][1], variable_c, ward_c,
                                                      child[ward_c][day], room_num, case, sr_value)
                            if (variable_a[0].value is None or variable_b[0].value is None):
                                print("is none")

    return child, child_num_surgeries


def genetic_find_child_value(value, variable):
    for v in variable.domain:
        if v == value:
            return v


def genetic_mutate(child, child_num_surgeries, case):
    for ward in child:
        chosen_v, delta_E, t = select_successor(child, ward, child_num_surgeries, case)

    return child, child_num_surgeries


def genetic_calc_value(child):
    cost = 0
    srv_constraints, sv_constraints = get_constraint_dictionary(child)
    for con_key in srv_constraints:
        for cons in srv_constraints[con_key]:
            cost += sum(srv_constraints[con_key][cons].prices.values())
    cost += sum(sv_constraints['d']['overlapping'].prices.values())  # s_v constraint which is not sr_v constraint

    wt = 0
    for ward in child:
        for day in child[ward]:
            for room_num in child[ward][day]:
                for order in range(len(child[ward][day][room_num])):
                    sr_v = child[ward][day][room_num][order][0]
                    if sr_v.value is not None:
                        wt += sr_v.value.calc_waiting_days(sr_v.day)

    return wt + cost


def get_constraint_dictionary(v_dict):
    for ward in v_dict:
        for day in v_dict[ward]:
            for room_num in v_dict[ward][day]:
                for order in range(len(v_dict[ward][day][room_num])):
                    srv_constraints = v_dict[ward][day][room_num][order][0].constraints
                    sv_constraints = v_dict[ward][day][room_num][order][1].constraints
                    return srv_constraints, sv_constraints


g_values, bc = genetic_algorithm(0.06, 1, 1, 200)
# g_values, bc = genetic_algorithm(0.06, 50, 1, 500)
for v in g_values:
    if v[0] > inf_price:
        v[0] = 5_000
generations = range(len(g_values))
xtick = np.arange(min(generations), max(generations), 25)
min_values, avg_values = zip(*g_values)

# values_with_colors_and_labels = ((min_values, 'green', 'min'), (avg_values, 'grey', 'avg'))
fig = plt.figure()
ax = fig.add_subplot()
plt.plot(generations, min_values,)
plt.title('SSP Genetic Best Values')
plt.xticks(xtick)
plt.xlabel('generation')
plt.ylabel('waiting time')

# savefig("genetic")
for i, v in enumerate(min_values):
    if i<2:
        ax.text(i, v - 50, "%d" % v, ha="center")
    if i>50 and i%25==0:
        ax.text(i, v - 50, "%d" % v, ha="center")
plt.show()

fig = plt.figure()
ax = fig.add_subplot()
plt.plot(generations, avg_values)
plt.title('SSP Genetic Average Values')
plt.xticks(xtick)
plt.xlabel('generation')
plt.ylabel('waiting time')
for i, v in enumerate(avg_values):
    if i>100 and i%25==0:
        ax.text(i, v - 50, "%d" % v, ha="center")
plt.show()


print('Finished 1')

'''# Simulated Annealing
Soroka = Hospital(1, "Soroka")
var_dict = init_variables2(Soroka)
w = Soroka.find_ward(w_id=1)
bv, t, nc, pl, bs = simulated_annealing(var_dict, w, by_waiting_time, case=1, genetic=False)
wd = calc_wt_of_schedule(bs)
print(wd)
print('t: ' + str(t) + ' num_change: ' + str(nc) + ' best_value: ' + str(bv))
print(pl)
print(pl[len(pl) - 1])
t1 = pl[0][0]
cv = pl[0][1]
pll = [[t1, "inf"]]

pl.sort(key=lambda x: x[1])

for li in pl:
    if li[1] > 1_000_000:
        li[1] = 4_100
    else:
        li[1] = round(li[1], 2)
# print(pl)
print('t: ' + str(t) + ' num_change: ' + str(nc) + ' best_value: ' + str(bv))

pl = np.array(pl)
x1, y1 = pl.T
i = np.array(['inf'])
y = np.setdiff1d(y1, i)
y = y.astype(np.float)


x1 = x1.astype(np.float)

plt.scatter(x1, y1)
plt.title('SSP Simulated-Annealing')
plt.xlabel('iteration')
plt.ylabel('waiting time')
xtick = np.arange(x1.min(), x1.max(), 2_500)
plt.xticks(xtick)

plt.show()

# receive surgeries and change the needed variables - their domain will only contain the specific surgeon and patient
# received from surgeries'''
