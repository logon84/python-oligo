#!/usr/bin/python3 

from datetime import datetime
from oligo import Iber

###############PREQUISITES###########################
user_i_de = "i-de_user_here"
passw_i_de = "i-de_passwd_here"
ree_token = "ree_token_here"

#####################################################


connection = Iber()
connection.login(user_i_de, passw_i_de)
connection.get_PS_info()
connection.get_power_peaks("2020")
#connection.get_anual_report(ree_token)

#x = connection.watthourmeter()
#x = connection.get_invoice(5)
#x = connection.get_hourly_consumption(datetime.strptime("15-06-2020","%d-%m-%Y"),datetime.strptime("02-07-2020","%d-%m-%Y"))
#x = connection.get_invoice_consumption(1)
#x = connection.get_ree_data(ree_token,datetime.strptime("15-06-2020","%d-%m-%Y"),datetime.strptime("02-07-2020","%d-%m-%Y"))

for i in range(3,-1,-1):
    x = connection.calculate_invoice_PVPC(ree_token,i)
    print(x)
    print("\n###################################\n")
