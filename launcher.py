#!/usr/bin/python3 

from datetime import datetime
from oligo import Iber
import os


try:
    # Win32
    from msvcrt import getch
except ImportError:
    # UNIX
    def getch():
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

###############PREQUISITES###########################
user_i_de = "i-de_user_here"
passw_i_de = "i-de_passwd_here"
ree_token = "ree_token_here"

#####################################################


connection = Iber()
connection.login(user_i_de, passw_i_de)
connection.get_PS_info()
connection.get_power_peaks("2020")

#x = connection.watthourmeter()
#x = connection.get_invoice(5)
#x = connection.get_hourly_consumption(datetime.strptime("15-06-2020","%d-%m-%Y"),datetime.strptime("02-07-2020","%d-%m-%Y"))
#x = connection.get_invoice_consumption(1)
#x = connection.get_ree_data(ree_token,datetime.strptime("15-06-2020","%d-%m-%Y"),datetime.strptime("02-07-2020","%d-%m-%Y"))

simulate_pot = input("Introduza la potencia con la que desea simular el cálculo, o pulse ENTER si desea simular con la potencia actualmente contratada:")
if len(simulate_pot) == 0:
   simulate_pot = 0
else:
   simulate_pot = float(simulate_pot)

totals = [0,0,0]
for i in range(0,30,1):
    x = connection.calculate_invoice_PVPC(ree_token,i,simulate_pot)
    for z in range(0,3):
          totals[z] = totals[z] + x[z]
    min_cost = min(totals)
    if totals.index(min_cost) == 0:
        print("ACUMULADO: La tarifa PVPC 2.0A habría supuesto un ahorro de {0:.2f}€ frente a PVPC 2.0DHA y de {1:.2f}€ frente a la tarifa de mercado libre. [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[1]-totals[0],totals[2]-totals[0], totals[0], totals[1], totals[2]))
    elif totals.index(min_cost) == 1:
        print("ACUMULADO: La tarifa PVPC 2.0DHA habría supuesto un ahorro de {0:.2f}€ frente a PVPC 2.0A y de {1:.2f}€ frente a la tarifa de mercado libre. [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[0]-totals[1],totals[2]-totals[1], totals[0], totals[1], totals[2]))
    elif totals.index(min_cost) == 2:
        print("ACUMULADO: La tarifa de mercado libre habría supuesto un ahorro de {0:.2f}€ frente a PVPC 2.0A y de {1:.2f}€ frente a PVPV 2.0DHA. [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[0]-totals[3],totals[2]-totals[3], totals[0], totals[1], totals[2]))
    print("\n##########  PULSE CUALQUIER TECLA PARA CONTINUAR O ESPACIO PARA ABANDONAR  ###########", end="")
    input_char = getch()
    print("\n")
    if input_char == " ":
        break
