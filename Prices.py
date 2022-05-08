import sys
from math import factorial
from datetime import time

inf_price = 1_000_000  # for hard constraints


def set_dro_prices(sr_v, s_v, ward, mutual, ty):
    """
    calculates and updates all the  'dro' date_room_order constraints with cost
    :param ty: the type of variable updated : surgery request variable type/ surgeon variable type/ none if init sol
    :param mutual: boolean true if it is init solution or any other case of mutual sr_v and s_v update
     false any other case - i.e.single variable was updated
    :param sr_v: surgery request variable of a specific date room order
    :param s_v: surgery variable that matches the sr_v
    :param ward: a ward object
    :return cost of dro constraints
    """
    dro_cost = 0
    if mutual or isinstance(sr_v, ty):  # if the init_sol cost is calculated or sr_v was updated
        dro_cost += _set_surgeon_patient_price(sr_v, s_v, ward)
        dro_cost += _set_all_diff_price(sr_v)
    else:  # only s_v was updated
        dro_cost += _set_surgeon_patient_price(sr_v, s_v, ward)
    return dro_cost


def set_dr_prices(var_list, ward, mutual, ty):
    """
    calculates and updated all the dr date room constraints wit cost
    :param ty: the type of variable updated : surgery request variable type/ surgeon variable type/ none if init sol
    :param mutual: boolean true if it is init solution false any other case - i.e. variable was updated
    :param var_list: list of variables tuple : (sr_v,s_v) with same indexes. sr_v surgery request variable,
    s-v surgeon variable - the list will be of the tuples concerning a certain day and room
    :param ward: ward object
    """
    dr_cost = 0
    if mutual or isinstance(var_list[0][0], ty):
        sr_v_list = [t[0] for t in var_list]
        dr_cost += _set_total_duration_price(sr_v_list, ward)
    return dr_cost


def set_d_prices(d_dict, s_v, ty, next=False):
    """
    calculates and updated all the d date constraints wit cost
    :param ty: the type of variable updated : surgery request variable type/ surgeon variable type/ none if init sol
    or tuple update
    :param d_dict: dictionary of format key - room value - list of tuples [(sr_v,sr),(sr_v,sr)...]
    rooms concerning a certain ward in a certain day
    :param s_v: surgoen variable or None if sent from init_day and not value update
    """
    ty1 = ty
    d_cost = 0
    s_v_list = []  # list of all the surgeon variables in a certain day
    for lt in list(d_dict.values()):  # lt list of tuples
        for t in lt:
            s_v_list.append(t[1])

    if s_v is None:  # for calculating init day cost
        surgeon_set = set(s_v.value for s_v in s_v_list)  # set of the different surgeons assigned to surgery this day
        for surgeon in surgeon_set:
            if surgeon is not None:
                surgeon_v_list = _s_v_list_by_surgeon(s_v_list,
                                                      surgeon)  # list of surgeon variables of a certain surgeon in a day
                if len(surgeon_v_list) > 0:
                    d_cost += set_overlapping_prices(surgeon_v_list, None)
    else:  # when costs need to be updated by a single change
        if s_v.value is not None or s_v.prior_value is not None:
            # - we want to check overlapping also when sr_v is updated because times change
            if isinstance(s_v, ty) or ty == type(None):  # surgeon variable was updated or tuple was updated
                # checks current value
                if s_v.value is not None:
                    surgeon_v_list = _s_v_list_by_surgeon(s_v_list, s_v.value)
                    # list of surgeon variables of a certain surgeon in a day
                    d_cost += set_overlapping_prices(surgeon_v_list, s_v)
                # checks prior value
                if s_v.prior_value is not None and next:
                    surgeon_v_list = _s_v_list_by_surgeon(s_v_list, s_v.prior_value)
                    if len(surgeon_v_list) > 0:
                        d_cost += set_overlapping_prices(surgeon_v_list, None)
            else:  # surgery request variable updated - times changed need to check overlapping for the rest of the
                # surgeries in the day because their time changed - wand to check also before change and after change
                room_num = s_v.room.num
                for j in range(s_v.order, len(d_dict[room_num]) + 1):
                    s_v = d_dict[room_num][j - 1][1]  # s_v
                    if s_v.value is None:
                        break
                    surgeon_v_list = _s_v_list_by_surgeon(s_v_list, s_v.value)
                    d_cost += set_overlapping_prices(surgeon_v_list, s_v)
    return d_cost


def _s_v_list_by_surgeon(s_v_list, surgeon):
    """
    formats a list of surgeon variables of a certain surgeon in a day
    :param s_v_list: list of surgeon variables
    :param surgeon: surgeon object
    :return: list of surgeon variables of a specific surgeon
    """
    surgeon_v_list = []
    for s_v in s_v_list:
        if s_v.value == surgeon:
            surgeon_v_list.append(s_v)
    return surgeon_v_list


def _set_surgeon_patient_price(sr_v, s_v, ward):
    """
    calculates the binary cost of the surgeon_patient_skill  concerning the current surgery request value,
    inserts to constraint price table - the cost is normalized between 0 to 1 - hence duplicated by 100
    if the surgeon does not have the appropiate skill then price is inf (10,000)
    :param sr_v: surgery request variable object
    :param s_v: surgeon variable object
    :param ward: ward object
    :return:
    """
    cost = 0
    if sr_v.value is not None and s_v.value is not None:
        if sr_v.value.surgery_type not in s_v.value.surgical_grades:
            cost += inf_price
    sr_v.constraints['dro']['surgeon_patient'].prices[sr_v.get_constraint_dro_key()] = cost
    return cost


'''def _set_all_diff_price(sr_v):
    """
    Hard constraint if the surgery request of this variable is already assigned to a different variable cost is inf i.e
    inf_price * number of possible constraints broken nCk - how many groups of 2 can be made from a group of assigned
    :param sr_v: surgery request variable object
    """
    if sr_v.value is not None:
        if sr_v.value.assigned > 1:
            sr_v.constraints['dro']['all_diff'].prices[sr_v.get_constraint_dro_key()] = \
                factorial(sr_v.value.assigned) / factorial(2) / factorial(sr_v.value.assigned - 2) * inf_price
            # nCk number of binary constraints broken
            return factorial(sr_v.value.assigned) / factorial(2) / factorial(sr_v.value.assigned - 2) * inf_price
        else:
            sr_v.constraints['dro']['all_diff'].prices[sr_v.get_constraint_dro_key()] = 0
            return 0
    else:
        sr_v.constraints['dro']['all_diff'].prices[sr_v.get_constraint_dro_key()] = 0
        return 0
'''


def _set_all_diff_price(sr_v):
    """
    Hard constraint if the surgery request of this variable is already assigned to a different variable cost is inf i.e
    inf_price * number of possible constraints broken nCk - how many groups of 2 can be made from a group of assigned
    param sr_v: surgery request variable object
    """
    cost = 0
    if sr_v.value is not None:
        if len(sr_v.value.assigned) > 1:
            for key in sr_v.value.assigned:
                sr_v.constraints['dro']['all_diff'].prices[key] = inf_price
                cost += inf_price
            return cost
        else:
            sr_v.constraints['dro']['all_diff'].prices[sr_v.get_constraint_dro_key()] = 0
            return 0
    else:
        sr_v.constraints['dro']['all_diff'].prices[sr_v.get_constraint_dro_key()] = 0
        return 0


def _set_total_duration_price(sr_v_list, ward):
    """
    Hard Constraint - gives a price of inf_price to a room which the total duration of it is larger than the wards day
    surgical duration
    :param sr_v_list: list of surgery request variable objects - all the variables in a certain day and room
    :param ward: ward object
    """

    td = 0  # total duration
    max_surgery_time = ward.d_duration
    for sr_v in sr_v_list:
        if sr_v.value is None:
            break
        else:
            td += sr_v.value.duration
        if td > max_surgery_time:
            sr_v.constraints['dr']['total_duration'].prices[sr_v.get_constraint_dr_key()] = inf_price
            return inf_price
        else:
            sr_v.constraints['dr']['total_duration'].prices[sr_v.get_constraint_dr_key()] = 0
    return 0


def set_overlapping_prices(surgeon_v_list, s_v):
    '''

    :param surgeon_v_list: list of surgeon variables of a certain surgeon in a day
    :param s_v: surgeon variable
    :return: price
    '''
    if s_v is None:  # for initial day and prior value
        s_id = surgeon_v_list[0].value.s_id
        for i in range(len(surgeon_v_list) - 1):
            for j in range(i + 1, len(surgeon_v_list)):
                if surgeon_v_list[i].room != surgeon_v_list[j].room:
                    overlapping = check_overlapping(surgeon_v_list[i], surgeon_v_list[j])
                    if overlapping:
                        surgeon_v_list[i].constraints['d']['overlapping'].prices[
                            surgeon_v_list[i].get_constraint_d_key(s_id)] = inf_price
                        return inf_price
        surgeon_v_list[0].constraints['d']['overlapping'].prices[surgeon_v_list[0].get_constraint_d_key(s_id)] = 0
    else:
        for v in surgeon_v_list:
            if v != s_v and v.room != s_v.room:
                overlapping = check_overlapping(v, s_v)  # boolean
                if overlapping:
                    s_v.constraints['d']['overlapping'].prices[s_v.get_constraint_d_key(s_v.value.s_id)] = inf_price
                    return inf_price
        surgeon_v_list.remove(s_v)
        for i in range(len(surgeon_v_list)):
            for j in range(i + 1, len(surgeon_v_list)):
                if surgeon_v_list[i].room != surgeon_v_list[j].room:
                    overlapping = check_overlapping(surgeon_v_list[i], surgeon_v_list[j])
                    if overlapping:
                        s_v.constraints['d']['overlapping'].prices[s_v.get_constraint_d_key(s_v.value.s_id)] = inf_price
                        return 0
        s_v.constraints['d']['overlapping'].prices[s_v.get_constraint_d_key(s_v.value.s_id)] = 0
    return 0


def check_overlapping(s_v1, s_v2):
    # import SSP_initialization

    if s_v1.start_time <= s_v2.start_time:
        first_v = s_v1
        second_v = s_v2
    else:
        first_v = s_v2
        second_v = s_v1

    if second_v.start_time <= calc_end_time(start_time=first_v.end_time, duration_min=30):
        return True
    else:
        return False


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
