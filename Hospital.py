from Ward import Ward
from Patient import Patient
from Room import Room
import pandas as pd
import xlrd

path = 'C:\\Users\\noamga\\Downloads\\Data-20200802T142933Z-001\\Data'
class Hospital(object):

    def __init__(self, h_id, name):
        self.h_id = h_id
        self.name = name
        self.rooms = self._init_rooms()
        self.patients = self._init_patients()
        self.wards = self._init_wards()

    def _init_wards(self):
        initWards = self._getWards_DB()  # list of <id. name> of the wards as in DB.
        wards = set()
        for ward in initWards:
            w_id = ward['id']
            name = ward['name']
            d_duration = ward['d_duration']
            max_slots = ward['max_slots']
            start_hour = ward['start_d_hour']
            # room allocation
            wards.add(Ward(name, w_id, self, d_duration, max_slots, start_hour))
        return wards

    def _init_rooms(self):
        '''
        recieves the rooms data from DB transform to objects
        :return: set of rooms
        '''
        init_rooms = self._getRoomsDB()
        rooms = set()
        for r in init_rooms:
            room_num = r
            surgery_types = init_rooms[r]
            rooms.add(Room(num=room_num, surgery_types=surgery_types))
        return rooms

    def _init_patients(self):
        init_patients = self._getPatients_DB()
        patients = set()
        for patient in init_patients:
            p_id = int(patient['patient_id'])
            birth_date = patient['date_of_birth']
            gender = patient['gender']
            patients.add(Patient(p_id, birth_date, gender))
        return patients

    def _getWards_DB(self):
        df = pd.read_excel(io='Ward.xlsx')
        wards = df.to_dict('records')
        return wards

    def _getRoomsDB(self):
        '''
        reads from excel file
        :return: dictionary {room num: set(surgery type id)}
        '''
        df = pd.read_excel(io='Room.xlsx')
        data = df.to_dict('records')
        rooms = {}
        for r in data:
            if r['id'] in rooms:
                rooms[r['id']].add(r['surgeryT_id'])
            else:
                rooms[r['id']] = {r['surgeryT_id']}
        return rooms

    def _getPatients_DB(self):
        df = pd.read_excel(io='Patient.xlsx')
        patients = df.to_dict('records')
        return patients

    def findPatientByID(self, p_id):
        for p in self.patients:
            if p.p_id == int(p_id):
                return p
        return None

    def findRoom(self, room_num):
        for r in self.rooms:
            if r.num == room_num:
                return r
        return None

    def find_ward(self, w_id):
        for w in self.wards:
            if w.w_id == w_id:
                return w








