from docycle import DocomoCycle
from line import Line
from parking import TYO_PARKING_LIST
import time
import os

# docomo cycle
user = os.environ['CYCLE_USER']
password = os.environ['CYCLE_PASS']
my_area_id = DocomoCycle.TYO_AREA_ID_LIST['chiyoda']
my_parking_id = TYO_PARKING_LIST['A1-01.Chiyoda City Office']
my_user_id = 'TYO'

# line
line_token = os.environ['LINE_TOKEN']


if __name__ == '__main__':
    threashold = 3
    dc = DocomoCycle(user, password, my_user_id, my_area_id)
    li = Line(line_token)

    while True:

        time.sleep(60 * 3)

        cycles = dc.get_cycle_list(my_parking_id)

        if cycles == None:
            li.send_message('nothing')
        elif len(cycles) < threashold:
            if dc.reserve_cycle(my_parking_id) != None:
                message = dc.reserve_info()

                li.send_message(message)
                exit()
