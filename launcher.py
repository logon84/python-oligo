#!/usr/bin/python3 


from oligo import Iber

###############PREQUISITES###########################
user_i_de = "i-de_user_here"
passw_i_de = "i-de_passwd_here"
ree_token = "ree_token_here"

#####################################################


connection = Iber()
connection.login(user_i_de, passw_i_de)

#x = connection.watthourmeter()
#x = connection.get_invoices(5)
#x = connection.get_hourly_consumption("15-06-2020","02-07-2020")
#x = connection.get_invoice_consumption(1)
#x = connection.get_ree_20dha_data(ree_token,"15-06-2020","02-07-2020")
x = connection.calculate_invoice_20dha_PVPC(ree_token,0)

print(x)
