from requests import Session
from datetime import datetime
from io import StringIO
from dateutil.relativedelta import relativedelta
import calendar
from decimal import Decimal
import aiohttp
import asyncio

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

class ResponseException(Exception):
    pass


class LoginException(Exception):
    pass


class SessionException(Exception):
    pass


class NoResponseException(Exception):
    pass


class SelectContractException(Exception):
    pass


class Iber:

    __domain = "https://www.i-de.es"
    __login_url = __domain + "/consumidores/rest/loginNew/login"
    __wattmeter_url = __domain + "/consumidores/rest/escenarioNew/obtenerMedicionOnline/24"
    __icp_status_url = __domain + "/consumidores/rest/rearmeICP/consultarEstado"
    __contracts_url = __domain + "/consumidores/rest/cto/listaCtos/"
    __contract_detail_url = __domain + "/consumidores/rest/detalleCto/detalle/"
    __contract_selection_url = __domain + "/consumidores/rest/cto/seleccion/"
    __ps_info_url = __domain + "/consumidores/rest/infoPS/datos/"
    __power_peak_dates_url = __domain + "/consumidores/rest/consumoNew/obtenerLimitesFechasPotencia/"
    __power_peak_url = __domain + "/consumidores/rest/consumoNew/obtenerPotenciasMaximas/{0}"
    today = datetime.now()
    twoyearsago =  today - relativedelta(years=2)
    __invoice_list_url = __domain + "/consumidores/rest/consumoNew/obtenerDatosFacturasConsumo/fechaInicio/{0}/fechaFinal/{1}".format(twoyearsago.strftime("%d-%m-%Y%H:%M:%S"),today.strftime("%d-%m-%Y%H:%M:%S"))
    __consumption_max_date_url = __domain + "/consumidores/rest/consumoNew/obtenerLimiteFechasConsumo"
    __consumption_between_dates_csv_url = __domain + "/consumidores/rest/consumoNew/exportarACSVPeriodoConsumo/fechaInicio/{0}00:00:00/fechaFinal/{1}00:00:00/tipo/horaria/"
    __consumption_by_invoice_csv_url = __domain + "/consumidores/rest/consumoNew/exportarACSV/factura/{0}/fechaInicio/{1}00:00:00/fechaFinal/{2}23:59:59/modo/R"
    __headers_i_de = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
        'accept': "application/json; charset=utf-8",
        'content-type': "application/json; charset=utf-8",
        'cache-control': "no-cache"
    }

    __ree_api_url = "https://api.esios.ree.es/indicators/{0}?start_date=\"{1}\"T00:00:00&end_date=\"{2}\"T23:00:00"
    __headers_ree = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
        'accept': "application/json; application/vnd.esios-api-v1+json",
        'content-type': "application/json",
        'Host': "api.esios.ree.es",
        'Authorization': "Token token=",
        'Cookie': ""
    }
    

    def __init__(self):
        """Iber class __init__ method."""
        self.__session = None

    def login(self, user, password):
        """Creates session with your credentials"""
        self.__session = Session()
        login_data = "[\"{}\",\"{}\",null,\"Linux -\",\"PC\",\"Chrome 77.0.3865.90\",\"0\",\"\",\"s\"]".format(user, password)
        response = self.__session.request("POST", self.__login_url, data=login_data, headers=self.__headers_i_de)
        if response.status_code != 200:
            self.__session = None
            raise ResponseException("Response error, code: {}".format(response.status_code))
        json_response = response.json()
        if json_response["success"] != "true":
            self.__session = None
            raise LoginException("Login error, bad login")

    def __check_session(self):
        if not self.__session:
            raise SessionException("Session required, use login() method to obtain a session")

    def wattmeter(self):
        """Returns your current power consumption."""
        self.__check_session()
        response = self.__session.request("GET", self.__wattmeter_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        return str(json_response['valMagnitud']/1000)+"kw"

    def icpstatus(self):
        """Returns the status of your ICP."""
        self.__check_session()
        response = self.__session.request("POST", self.__icp_status_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["icp"] == "trueConectado":
            return True
        else:
            return False

    def contracts(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contracts_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["success"]:
            return json_response["contratos"]

    def contract(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contract_detail_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        return response.json()

    def contractselect(self, id):
        self.__check_session()
        response = self.__session.request("GET", self.__contract_selection_url + id, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if not json_response["success"]:
            raise SelectContractException

    def get_invoice(self,index):
        """Returns invoice data."""
        self.__check_session()
        response = self.__session.request("GET", self.__invoice_list_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        return json_response['facturas'][index]

    def get_last_day_with_recorded_data(self):
        """Returns hour consumption between dates."""
        self.__check_session()
        response = self.__session.request("GET", self.__consumption_max_date_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        max_date = datetime.strptime(json_response['fechaMaxima'], '%d-%m-%Y%H:%M:%S')
        return max_date

    def get_hourly_consumption(self,start_date,end_date):
        """Returns hour consumption between dates.This DOES NOT return E consumptions"""
        self.__check_session()
        max_date = self.get_last_day_with_recorded_data()
        if end_date > max_date:
            end_date = max_date
        response = self.__session.request("GET", self.__consumption_between_dates_csv_url.format(start_date.strftime('%d-%m-%Y'),end_date.strftime('%d-%m-%Y')), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        consumption_kwh = []
        csvdata = StringIO(response.text)
        next(csvdata)
        last_date = start_date
        for line in csvdata:
            #spaguetti.run
            current_date = datetime.strptime(line.split(";")[1], '%Y/%m/%d %H:%M')
            if not(current_date == last_date + relativedelta(hours=1)) and not(current_date == last_date) and not(current_date.month == 3 and current_date.day in range (25,32) and current_date.isoweekday() == 7 and current_date.hour == 3):
                 #NOT(current hour is consecutive to previous) and NOT(october hour change 0-1-2-2-3-4) and NOT(march hour change 0-1-3-4)
                 #value missing detected, fill with 0's
                 counter = 0
                 while current_date > (last_date + relativedelta(hours=1)):
                       consumption_kwh.append(0)
                       last_date = last_date + relativedelta(hours=1)
                       counter = counter + 1
                 print("----------------ATENCION: FALTAN ALGUNOS VALORES DE CONSUMO EN ESTA SIMULACION-----------------(" + str(counter) + ")")
            consumption_kwh.append(int(line.split(";")[3])/1000)
            last_date = current_date
        return start_date, end_date, consumption_kwh

    def get_hourly_consumption_by_invoice(self,invoice_number,start_date,end_date):
        """Returns hour consumption by invoice.This DOES return R and E consumptions, so it's better for costs comparison"""
        self.__check_session()
        response = self.__session.request("GET", self.__consumption_by_invoice_csv_url.format(invoice_number,start_date.strftime('%d-%m-%Y'),end_date.strftime('%d-%m-%Y')), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        consumption_kwh = []
        real_reads = []
        csvdata = StringIO(response.text)
        next(csvdata)
        for line in csvdata:
            consumption_kwh.append(float(line.split(";")[3].replace(',','.')))
            real_reads.append(int("R" in line.split(";")[4]))
        return start_date, end_date, consumption_kwh, real_reads

    def get_consumption(self,index):
        """Returns consumptions. Index 0 means current consumption not yet invoiced. Bigger indexes returns consumption by every already created invoice"""
        self.__check_session()
        real_reads = []
        if index == 0: #get current cost
            last_invoice = self.get_invoice(0) #get last invoice
            start_date = datetime.strptime(last_invoice['fechaHasta'], '%d/%m/%Y') + relativedelta(days=1) #get last day used in the last invoice to use next day as starting day for current cost
            end_date = self.today
            start_date, end_date, consumption_kwh = self.get_hourly_consumption(start_date,end_date)
            real_reads= [1 for i in range(len(consumption_kwh))]
        else:
            invoice = self.get_invoice(index-1)
            start_date = datetime.strptime(invoice['fechaDesde'], '%d/%m/%Y')
            end_date = datetime.strptime(invoice['fechaHasta'], '%d/%m/%Y')
            start_date, end_date, consumption_kwh, real_reads = self.get_hourly_consumption_by_invoice(invoice['numero'],start_date,end_date)
        return start_date, end_date, consumption_kwh, real_reads

    async def get(self,url,headers):
        """async request.GET to speedup REE data fetch"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                     raise ResponseException
                if not response.text:
                     raise NoResponseException
                return await response.json()

    def get_ree_data(self,token,start_date,end_date):
        """Returns energy prices from REE"""
        IDenergy20 = '10254'
        IDenergy20DHA = '10255'

        energy20 = []
        energy20DHA = []
        peak_mask = []

        url_0 = self.__ree_api_url.format(IDenergy20,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))
        url_1 = self.__ree_api_url.format(IDenergy20DHA,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))
        self.__headers_ree['Authorization'] = "Token token=" + token

        loop = asyncio.get_event_loop()
        parallel_http_get = [self.get(url_0, self.__headers_ree),self.get(url_1, self.__headers_ree)]
        results = loop.run_until_complete(asyncio.gather(*parallel_http_get))

        for i in range(len(results[0]['indicator']['values'])):
            energy20.append(self.roundup(float(results[0]['indicator']['values'][i]['value'])/1000, 6))
            energy20DHA.append(self.roundup(float(results[1]['indicator']['values'][i]['value'])/1000, 6))
            summer_flag = int("+02:00" in results[0]['indicator']['values'][i]['datetime'])
            is_it_peak_hour = int(results[0]['indicator']['values'][i]['datetime'][11:13]) in range(12+summer_flag,22+summer_flag)
            peak_mask.append(is_it_peak_hour)
        return energy20, energy20DHA, peak_mask

    def roundup(self, num, ndecimals):
        return float(round(Decimal(str(num)),ndecimals))

    def day_type_splitter(self, start_date, end_date):
        days_365 = 0
        days_366 = 0
        if calendar.isleap(start_date.year) and calendar.isleap(end_date.year):
            days_366 = (end_date - start_date).days+1
        elif not calendar.isleap(start_date.year) and not calendar.isleap(end_date.year):
            days_365 = (end_date - start_date).days+1
        elif not calendar.isleap(start_date.year) and calendar.isleap(end_date.year):
            days_365 = 366 - start_date.timetuple().tm_yday
            days_366 = (end_date - start_date).days+1 - days_365
        elif calendar.isleap(start_date.year) and not calendar.isleap(end_date.year):
            days_366 = 367 - start_date.timetuple().tm_yday
            days_365 = (end_date - start_date).days+1 - days_366
        return days_365, days_366

    def calculate_invoice_PVPC(self, token, index, simulate_pot):
        """Returns cost of same consumptions on pvpc . Index 0 means current consumption not yet invoiced. Bigger indexes returns costs of every already created invoice"""
        start_date, end_date, consumption_kwh, real_reads = self.get_consumption(index)
        energy20, energy20DHA, peak_mask = self.get_ree_data(token,start_date,end_date)
        days_365, days_366 = self.day_type_splitter(start_date,end_date)

        p1 = []
        p2 = []
        energy_real_read = 0
        for i in range(len(consumption_kwh)):
            p1.append(int(peak_mask[i]) * consumption_kwh[i])
            p2.append(int(not(peak_mask[i])) * consumption_kwh[i])
            energy_real_read = energy_real_read + real_reads[i]*consumption_kwh[i]

        PERC_REAL_KWH = self.roundup(energy_real_read*100/sum(consumption_kwh),2)
        PERC_ESTIM_KWH = self.roundup((sum(consumption_kwh)-energy_real_read)*100/sum(consumption_kwh),2)
        PERC_REAL_H = self.roundup(sum(real_reads)*100/len(real_reads),2)
        PERC_ESTIM_H = self.roundup((len(real_reads)-sum(real_reads))*100/len(real_reads),2)
        try:
            AVERAGE_KWH_H_REAL = self.roundup(energy_real_read/sum(real_reads),2)
        except:
            AVERAGE_KWH_H_REAL = 0
        try:
            AVERAGE_KWH_H_ESTIM = self.roundup((sum(consumption_kwh)-energy_real_read)/(len(real_reads)-sum(real_reads)),2)
        except:
             AVERAGE_KWH_H_ESTIM = 0

        if simulate_pot>0:
            pot = simulate_pot
        else:
            pot = (self.contract()['potMaxima'])/1000

        average_price_energy20 = 0
        average_price_energy20DHA_peak = 0
        average_price_energy20DHA_low = 0

        for i in range(len(consumption_kwh)):
            average_price_energy20 = average_price_energy20 + self.roundup((consumption_kwh[i]*energy20[i])/sum(consumption_kwh),6)
            average_price_energy20DHA_peak = average_price_energy20DHA_peak + self.roundup((p1[i]*energy20DHA[i])/sum(p1),6)
            average_price_energy20DHA_low = average_price_energy20DHA_low + self.roundup((p2[i]*energy20DHA[i])/sum(p2),6)

        power_cost = self.roundup(pot * days_365 * 38.043426/365, 2) + self.roundup(pot * days_365 * 3.113/365, 2) + self.roundup(pot * days_366 * 38.043426/366,2) + self.roundup(pot * days_366 * 3.113/366,2)
        energy_cost_20 = self.roundup(average_price_energy20*(self.roundup(sum(consumption_kwh),1)),2) + self.roundup(0.044027*(self.roundup(sum(consumption_kwh),1)),2)
        energy_cost_20DHA = self.roundup(average_price_energy20DHA_peak*(self.roundup(sum(p1),1)),2) + self.roundup(0.062012*(self.roundup(sum(p1),1)),2) + self.roundup(average_price_energy20DHA_low*(self.roundup(sum(p2),1)),2) + self.roundup(0.002215*(self.roundup(sum(p2),1)),2)
        energy_and_power_cost_20 = energy_cost_20 + power_cost
        energy_and_power_cost_20DHA = energy_cost_20DHA + power_cost
        energy_tax_20 = self.roundup(energy_and_power_cost_20*0.0511269632,2)
        energy_tax_20DHA = self.roundup(energy_and_power_cost_20DHA*0.0511269632,2)
        equipment_cost = self.roundup(days_365 * (0.81*12/365) + days_366 * (0.81*12/366),2)
        total_20 =  energy_and_power_cost_20 + energy_tax_20 + equipment_cost
        total_20DHA =  energy_and_power_cost_20DHA + energy_tax_20DHA + equipment_cost
        VAT_20 = self.roundup(total_20*0.21,2)
        VAT_20DHA = self.roundup(total_20DHA*0.21,2)
        total_plus_vat_20 = self.roundup(total_20 + VAT_20,2)
        total_plus_vat_20DHA = self.roundup(total_20DHA + VAT_20DHA,2)
#####################_____OTHER_COMPARISON (fill values)_____###############################
        name_other = "SOM ENERGIA 2.0DHA"
        power_cost_other = self.roundup(pot * days_365 * 38.043426/365, 2) + self.roundup(pot * days_366 * 38.043426/366, 2)
        energy_cost_other = self.roundup(sum(p1) * 0.147 + sum(p2) * 0.075,2)
        social_bonus_other = 0.02 * (days_365 + days_366)

#        name_other = "IBERDROLA 2.0DHA"
#        power_cost_other = self.roundup(pot * days_365 * 45/365, 2) + self.roundup(pot * days_366 * 45/366, 2)
#        energy_cost_other = self.roundup(sum(p1) * 0.134579 + sum(p2) * 0.067519,2)
#        social_bonus_other = 0.02 * (days_365 + days_366)

        energy_and_power_cost_other = energy_cost_other + power_cost_other
        energy_tax_other = self.roundup((energy_and_power_cost_other + social_bonus_other)*0.0511269632,2)
        equipment_cost_other = self.roundup(days_365 * (0.81*12/365) + days_366 * (0.81*12/366),2)
        total_other = energy_and_power_cost_other + energy_tax_other + equipment_cost_other + social_bonus_other
        VAT_other = self.roundup(total_other*0.21,2)
        total_plus_vat_other = self.roundup(total_other + VAT_other,2)
############################################################################################
        if index == 0:
            print("[CONSUMO ACTUAL]")
        elif index > 0:
            print("[FACTURA " + str(index) + "]")
        print("\nDESDE: {0}\nHASTA: {1}\nDIAS: {2}\nPOTENCIA: {3}KW\nCONSUMO PUNTA P1: {4:.2f}kwh   || Lectura Real: {5:.2f}%/h  {6:.2f}%/kwh  {7:.2f}kwh/h\nCONSUMO VALLE P2: {8:.2f}kwh  || Lectura Estimada: {9:.2f}%/h  {10:.2f}%/kwh  {11:.2f}kwh/h \n".format(start_date.strftime('%d-%m-%Y'),end_date.strftime('%d-%m-%Y'),str(days_365 + days_366),str(pot),sum(p1),PERC_REAL_H,PERC_REAL_KWH,AVERAGE_KWH_H_REAL,sum(p2),PERC_ESTIM_H,PERC_ESTIM_KWH,AVERAGE_KWH_H_ESTIM))
        print('{:<30} {:<30} {:<30}'.format("PVPC 2.0A precio", "PVPC 2.0DHA precio", name_other + " precio"))
        print("-----------------------------------------------------------------------------------------")
        print('{:<30} {:<30} {:<30}'.format("Coste potencia: {0:.2f}€".format(power_cost), "Coste potencia: {0:.2f}€".format(power_cost), "Coste potencia: {0:.2f}€".format(power_cost_other)))
        print('{:<30} {:<30} {:<30}'.format("Coste energía: {0:.2f}€".format(energy_cost_20), "Coste energía: {0:.2f}€".format(energy_cost_20DHA), "Coste energía: {0:.2f}€".format(energy_cost_other)))
        print('{:<30} {:<30} {:<30}'.format("Impuesto eléctrico: {0:.2f}€".format(energy_tax_20), "Impuesto eléctrico: {0:.2f}€".format(energy_tax_20DHA), "Impuesto eléctrico: {0:.2f}€".format(energy_tax_other)))
        print('{:<30} {:<30} {:<30}'.format("Bono social: 0.00€", "Bono social: 0.00€", "Bono social: {0:.2f}€".format(social_bonus_other)))
        print('{:<30} {:<30} {:<30}'.format("Equipos de medida: {0:.2f}€".format(equipment_cost), "Equipos de medida: {0:.2f}€".format(equipment_cost), "Equipos de medida: {0:.2f}€".format(equipment_cost_other)))
        print('{:<30} {:<30} {:<30}'.format("IVA: {0:.2f}€".format(VAT_20), "IVA: {0:.2f}€".format(VAT_20DHA), "IVA: {0:.2f}€".format(VAT_other)))
        print('{:<30} {:<30} {:<30}'.format("TOTAL: {0:.2f}€".format(total_plus_vat_20), "TOTAL: {0:.2f}€".format(total_plus_vat_20DHA), "TOTAL: {0:.2f}€\n\n".format(total_plus_vat_other)))
        return [total_plus_vat_20, total_plus_vat_20DHA, total_plus_vat_other]

    def get_PS_info(self):
        self.__check_session()
        response = self.__session.request("GET", self.__ps_info_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["modoFacturacion"] == "   ":
              modo_f = "1"
        else:
              modo_f = json_response["modoFacturacion"]
        print("\n[INFORMACIÓN DEL CONTRATO]" + "\n\n\t\tComercializadora: " + json_response["des_EPS_COM_VIG"] + "\n\t\tDirección suministro: " + str(json_response["ps_DIREC"]) + "\n\t\tTarifa: " + json_response["cod_TARIFA_TF_Descripcion"] + "\n\t\tPotencia: " + json_response["val_POT_P1"] + "W\n\t\tModo: " + modo_f + "\n\t\tTensión: " + json_response["val_TENSION_PTO_SUMIN"] + "V\n")
        return

    def get_power_peaks_max_date(self):
        self.__check_session()
        response = self.__session.request("GET", self.__power_peak_dates_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        max_date = datetime.strptime(json_response['fecMax'], '%d-%m-%Y%H:%M:%S')
        return max_date

    def get_power_peaks(self,year):
        self.__check_session()
        max_date = self.get_power_peaks_max_date()
        end_date = datetime.strptime("31-12-"+year+"23:59:59", '%d-%m-%Y%H:%M:%S')
        if end_date > max_date:
            end_date = max_date
        response = self.__session.request("GET", self.__power_peak_url.format(end_date.strftime('%d-%m-%Y%H:%M:%S')), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        monthly_max_power = ["NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA"]
        print("[POTENCIAS MAXIMAS DEL AÑO " + end_date.strftime('%Y') + "]\n")
        for i in range(len(json_response["potMaxMens"])):
              monthly_max_power[int(json_response["potMaxMens"][i]["name"][3:5])-1] = str(json_response["potMaxMens"][i]["y"]) + "w"
        for i in range(len(monthly_max_power)):
              print("\t\t{:02d}".format(i+1) + "/"+end_date.strftime('%Y') + ": " + monthly_max_power[i])
        print("\n")               
        return

    def continuous_calc(self,ree_token):
        simulate_pot = input("Introduza la potencia con la que desea simular el cálculo, o pulse ENTER si desea simular con la potencia actualmente contratada:")
        if len(simulate_pot) == 0:
            simulate_pot = 0
        else:
            simulate_pot = float(simulate_pot)
        totals = [0,0,0]
        for i in range(0,27,1):
            x = self.calculate_invoice_PVPC(ree_token,i,simulate_pot)
            for z in range(0,3):
                 totals[z] = totals[z] + x[z]
            min_cost = min(totals)
            if totals.index(min_cost) == 0:
                 print("ACUMULADO: La tarifa PVPC 2.0A habría supuesto un ahorro de {0:.2f}€ frente a PVPC 2.0DHA y de {1:.2f}€ frente a la tarifa de mercado libre. [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[1]-totals[0],totals[2]-totals[0], totals[0], totals[1], totals[2]))
            elif totals.index(min_cost) == 1:
                 print("ACUMULADO: La tarifa PVPC 2.0DHA habría supuesto un ahorro de {0:.2f}€ frente a PVPC 2.0A y de {1:.2f}€ frente a la tarifa de mercado libre. [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[0]-totals[1],totals[2]-totals[1], totals[0], totals[1], totals[2]))
            elif totals.index(min_cost) == 2:
                 print("ACUMULADO: La tarifa de mercado libre habría supuesto un ahorro de {0:.2f}€ frente a PVPC 2.0A y de {1:.2f}€ frente a PVPV 2.0DHA. [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[0]-totals[2],totals[1]-totals[2], totals[0], totals[1], totals[2]))
            print("\n##########  PULSE CUALQUIER TECLA PARA CONTINUAR O ESPACIO PARA ABANDONAR  ###########", end="")
            input_char = getch()
            print("\n")
            if input_char == " ".encode() or input_char == " ":
                 break
        return
