import datetime, Surgery_Type


class Surgeon(object):

    def __init__(self, s_id, surgical_grades, surgical_shifts):
        self.s_id = s_id
        self.surgical_grades = surgical_grades  # set(surgery_types)
        self.surgical_shifts = surgical_shifts  # set(shifts -string/date)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.s_id == other.s_id

    def get_surgery_types_id(self):
        st_id_set = set()
        for st in self.surgical_grades:
            st_id_set.add(st.st_id)
        return st_id_set


    def __hash__(self):
        return self.s_id
