#!/usr/bin/python3 

from datetime import datetime
from oligo import Iber

###############PREQUISITES###########################
user_i_de = "i-de_user_here"
passw_i_de = "i-de_passwd_here"

#####################################################


connection = Iber()
connection.login(user_i_de, passw_i_de)
connection.get_PS_info()
connection.get_power_peaks()
connection.comparator()

#x = connection.measurement()['consumption']
#x = connection.get_invoice(5)
#x = connection.get_hourly_consumption(datetime.strptime("15-06-2024","%d-%m-%Y"),datetime.strptime("02-07-2024","%d-%m-%Y"))
