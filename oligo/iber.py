from requests import Session
from datetime import datetime
from io import StringIO
from dateutil.relativedelta import relativedelta
from . import vat
import calendar
from decimal import Decimal
import aiohttp
import asyncio
import sys
import unidecode
import glob
from pathlib import Path
import traceback



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

class NoIDEdataException(Exception):
    pass

class SelectContractException(Exception):
    pass


class Iber:

    __domain = "https://www.i-de.es"
    __login_url = __domain + "/consumidores/rest/loginNew/login"
    __2fa_url = __domain + "/consumidores/rest/usuarioNew/activarUsuarioCaducado/"
    __watthourmeter_url = __domain + "/consumidores/rest/escenarioNew/obtenerMedicionOnline/24"
    __icp_status_url = __domain + "/consumidores/rest/rearmeICP/consultarEstado"
    __contracts_url = __domain + "/consumidores/rest/cto/listaCtos/"
    __contract_detail_url = __domain + "/consumidores/rest/detalleCto/detalle/"
    __contract_selection_url = __domain + "/consumidores/rest/cto/seleccion/"
    __ps_info_url = __domain + "/consumidores/rest/infoPS/datos/"
    __ps_info_url_2 = __domain + "/consumidores/rest/detalleCto/opcionFE/"
    __power_peak_dates_url = __domain + "/consumidores/rest/consumoNew/obtenerLimitesFechasPotencia/"
    __power_peak_url = __domain + "/consumidores/rest/consumoNew/obtenerPotenciasMaximasRangoV2/01-{0}00:00:00/01-{1}00:00:00"
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

    __ree_api_url = "https://api.esios.ree.es/indicators/{0}?start_date={1}T00:00:00&end_date={2}T23:00:00"
    __headers_ree = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
        'accept': "application/json; application/vnd.esios-api-v1+json",
        'content-type': "application/json",
        'Host': "api.esios.ree.es",
        'Cookie': ""
    }

    COMPANY_DB = {
        #e_high, e_mid, e_low, p_high, p_low, social_bonus
        "PVPC 2.0TD":[0, 0, 0, 0.090411 ,0.046575, 0.012742],
        "Plenitude (<5 kW)":[0.099092,0.099092,0.099092,0.073806,0.073806, 0],
        "ENERGYA VM":[0.099125,0.099125,0.099125,0.093150,0.046576, 0],
        "Visalia":[0.108995,0.108995,0.108995,0.060273,0.060273, 0.006282],
        "Imagina":[0.113000,0.113000,0.113000,0.087000,0.044000, 0.012742],
        "Gana Energía":[0.113600,0.113600,0.113600,0.127406,0.049264,0.012742],
        "Nufri CN023":[0.115332,0.115332,0.115332,0.084193,0.032596, 0.012742],
        "Octopus Relax":[0.118000,0.118000,0.118000,0.095000,0.027000, 0.01],
        "TE A tu aire siempre":[0.119000,0.119000,0.119000, 0.071904, 0.071904, 0.012742],
        "Naturgy por uso":[0.119166,0.119166,0.119166,0.108163,0.033392, 0.0104],
        "Iberdrola Online":[0.124900,0.124900,0.124900,0.095890,0.046548, 0.012742],
        "Endesa One":[0.126000,0.126000,0.126000,0.112138,0.040267, 0.012742],
        "Repsol":[0.129900,0.129900,0.129900,0.068219,0.068219, 0.012742],
        "Naturgy Tarifa Compromiso":[0.140515 ,0.140515 ,0.140515 ,0.053005 ,0.044744, 0.012742],
        "Endesa Libre":[0.147500,0.147500,0.147500,0.112138,0.040267, 0.012742],
        "Nufri CN023 3P":[0.176079,0.106312,0.074711,0.084193,0.032596, 0.012742],
        "Iberdrola Online 3P":[0.172576,0.119892,0.087904,0.086301,0.013014, 0.012742],
        "Naturgy noche luz 3P":[0.185461,0.116414,0.082334,0.108163,0.033392, 0.0104],
        "Imagina 3P":[0.188000,0.114000,0.079000,0.099000,0.020000, 0.012742],
        "TE A tu aire programa tu ahorro 3P":[0.188041,0.116220,0.080428,0.071918,0.071890, 0.012742],
        "Octopus 3P":[0.192000,0.117000,0.080000,0.095000,0.027000, 0.01],
        "Endesa One 3P":[0.193860,0.117310,0.085834,0.112138,0.040267, 0.012742],
        "ENERGYA VM 3P":[0.195500,0.122400,0.092650,0.082192,0.002739, 0]}
    

    def __init__(self):
        """Iber class __init__ method."""
        self.__session = None

    def login(self, user, password):
        """Creates session with your credentials"""
        self.__session = Session()
        login_data = "[\"{}\",\"{}\",null,\"Linux -\",\"PC\",\"Chrome 77.0.3865.90\",\"0\",\"\",\"s\", null, null, \"{}\"]"
        response = self.__session.request("POST", self.__login_url, data=login_data.format(user, password, None), headers=self.__headers_i_de)
        if response.status_code != 200:
            self.__session = None
            raise ResponseException("Response error, code: {}".format(response.status_code))
        json_response = response.json()
        if json_response["success"] == "false":
            self.__session = None
            raise LoginException("Login error, bad login")
        elif json_response["success"] == "userExpired":
            if "Has superado el número máximo de intentos" in json_response["message"]:
                self.__session = None
                raise LoginException("Login retries limit reached. Try again tomorrow")
            elif "Usuario caducado por inactividad en el sistema" in json_response["message"]:
                pin_counter = 0
                while json_response["success"] != "true":
                    pin_counter = pin_counter + 1
                    if pin_counter > 3:
                        self.__session = None
                        raise LoginException("Max wrong pin limit reached")
                    pin = input("Enter received PIN: ")
                    __2fa_data = {"codigo":pin, "usuario": user}
                    response = self.__session.request("POST", self.__2fa_url, json=__2fa_data, headers=self.__headers_i_de)
                    json_response = response.json()
                #pin accepted. use cookie ("num") to login again
                response = self.__session.request("POST", self.__login_url, data=login_data.format(user, password, json_response["num"]), headers=self.__headers_i_de)
                if response.status_code != 200:
                    self.__session = None
                    raise ResponseException("Response error, code: {}".format(response.status_code))
                json_response = response.json()
        if json_response["success"] == "true":
            print("LOGIN OK")
        

    def __check_session(self):
        if not self.__session:
            raise SessionException("Session required, use login() method to obtain a session")

    def measurement(self):
        """Returns a measurement from the powermeter."""
        self.__check_session()
        json_response = "{}"
        retry = 0
        while retry < 4 and str(json_response) == "{}":
            retry = retry + 1
            if retry > 1:
                print("Retrying....")
            response = self.__session.request("GET", self.__watthourmeter_url, headers=self.__headers_i_de)
            if response.status_code != 200:
                raise ResponseException(response.status_code)
            if not response.text:
                raise NoResponseException
            json_response = response.json()
        if 'codSolicitudTGT' in json_response.keys():
            return {
                "id": json_response['codSolicitudTGT'],
                "meter": json_response["valLecturaContador"],
                "consumption": json_response['valMagnitud'] + "w",
                "icp": json_response['valInterruptor']
                }
        else:
            return "Couldn't get proper read"

    def current_kilowatt_hour_counter_read(self):
        """Returns the current read of the electricity meter."""
        return self.measurement()["meter"]

    def current_power_consumption(self):
        """Returns your current power consumption."""
        return self.measurement()['consumption']

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

    def contract_list(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contracts_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["success"]:
            return json_response["contratos"]

    def contract_details(self):
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
        if len(json_response['facturas']) == 0:
            raise NoIDEdataException
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
        kwh = []
        csvdata = StringIO(response.text)
        next(csvdata)
        last_date = start_date
        for line in csvdata:
            #spaguetti.run!!
            if int(line.split(";")[2]) == 25:
                #OCTOBER HOUR FIX
                current_date = datetime.strptime(line.split(";")[1] + " " + "23" + ":00", '%d/%m/%Y %H:%M')
            else:
                current_date = datetime.strptime(line.split(";")[1] + " " + str(int(line.split(";")[2]) - 1) + ":00", '%d/%m/%Y %H:%M')
                if not(current_date == last_date + relativedelta(hours=1)) and not(current_date == last_date):
                    #NOT(current hour is consecutive to previous)
                    #value missing detected, fill with 0's
                    counter = 0
                    while current_date > (last_date + relativedelta(hours=1)):
                        kwh.append(0)
                        last_date = last_date + relativedelta(hours=1)
                        counter = counter + 1
                    print("----------------ATENCION: FALTAN ALGUNOS VALORES DE CONSUMO EN ESTA SIMULACION-----------------(" + str(counter) + ")")
            kwh.append(float(line.split(";")[3].replace(',','.')))
            last_date = current_date
            if current_date.month == 3 and current_date.day in range (25,32) and current_date.isoweekday() == 7 and current_date.hour == 22:
                #MARCH HOUR FIX
                last_date = last_date + relativedelta(hours=1)
        return [kwh, [1 for i in range(len(kwh))]]

    def get_hourly_consumption_by_invoice(self,invoice_number,start_date,end_date):
        """Returns hour consumption by invoice.This DOES return R and E consumptions, so it's better for costs comparison"""
        self.__check_session()
        response = self.__session.request("GET", self.__consumption_by_invoice_csv_url.format(invoice_number,start_date.strftime('%d-%m-%Y'),end_date.strftime('%d-%m-%Y')), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        kwh = []
        real_reads_mask = []
        csvdata = StringIO(response.text)
        next(csvdata)
        for line in csvdata:
            kwh.append(float(line.split(";")[3].replace(',','.')))
            real_reads_mask.append(int("R" in line.split(";")[4]))
        return [kwh, real_reads_mask]

    def get_consumption_details(self,index):
        """Returns detailed consumptions. Index 0 means current consumption not yet invoiced. Bigger indexes returns consumption by every already created invoice"""
        self.__check_session()
        real_reads = []
        if index == 0: #get current cost
            last_invoice = self.get_invoice(0) #get last invoice
            start_date = datetime.strptime(last_invoice['fechaHasta'], '%d/%m/%Y') + relativedelta(days=1) #get last day used in the last invoice to use next day as starting day for current cost
            end_date = self.get_last_day_with_recorded_data()
            if end_date <= datetime.strptime(last_invoice['fechaHasta'], '%d/%m/%Y'):
            #no hourly consumption since last invoice
                end_date = start_date
                return start_date, end_date, 0, 0, 0, [0, 0, 0, 0, 0, 0]			
            else:
                energy_reads = self.get_hourly_consumption(start_date,end_date)
        else:
            invoice = self.get_invoice(index-1)
            start_date = datetime.strptime(invoice['fechaDesde'], '%d/%m/%Y')
            end_date = datetime.strptime(invoice['fechaHasta'], '%d/%m/%Y')
            energy_reads = self.get_hourly_consumption_by_invoice(invoice['numero'],start_date,end_date)

        period_mask = self.get_ree_data(start_date,end_date, "period_mask")
        p1 = []
        p2 = []
        p3 = []
        energy_real_reads = []
        consumption_kwh = energy_reads[0]
        real_reads_mask = energy_reads[1]
        for i in range(len(consumption_kwh)):
            p1.append(int(period_mask[i] == 1) * consumption_kwh[i])
            p2.append(int(period_mask[i] == 2) * consumption_kwh[i])
            p3.append(int(period_mask[i] == 3) * consumption_kwh[i])
            energy_real_reads.append(real_reads_mask[i]*consumption_kwh[i])
        PERC_REAL_KWH = self.roundup(sum(energy_real_reads)*100/sum(consumption_kwh),2)
        PERC_ESTIM_KWH = 100 - PERC_REAL_KWH
        PERC_REAL_H = self.roundup(sum(real_reads_mask)*100/len(real_reads_mask),2)
        PERC_ESTIM_H = 100 - PERC_REAL_H
        try:
            AVERAGE_KWH_H_REAL = self.roundup(sum(energy_real_reads)/sum(real_reads_mask),2)
        except:
            AVERAGE_KWH_H_REAL = 0
        try:
            AVERAGE_KWH_H_ESTIM = self.roundup((sum(consumption_kwh)-sum(energy_real_reads))/(len(real_reads_mask)-sum(real_reads_mask)),2)
        except:
             AVERAGE_KWH_H_ESTIM = 0
        energy_calcs = [PERC_REAL_H, PERC_REAL_KWH, AVERAGE_KWH_H_REAL, PERC_ESTIM_H, PERC_ESTIM_KWH, AVERAGE_KWH_H_ESTIM]		
        return start_date, end_date, p1, p2, p3, energy_calcs

    async def get(self,url,headers):
        """async request.GET to speedup REE data fetch"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                     raise ResponseException
                if not response.text:
                     raise NoResponseException
                return await response.json()

    def get_ree_data(self,start_date,end_date, data_type):
        """Returns energy prices/period_mask from REE"""
        IDenergy20TD = '1001'
        IDhourtype = '1002'
        ID20TDzone = 'Península'
        data = []
        
        p = Path(__file__).with_name('ree_token.txt')
        with p.open('r') as f:
            token=f.read().replace("\n", "")
        self.__headers_ree['x-api-key'] = token

        if data_type == "energy_price":
            url_0 = self.__ree_api_url.format(IDenergy20TD,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))
        elif data_type == "period_mask":
            url_0 = self.__ree_api_url.format(IDhourtype,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))

        parallel_http_get = [self.get(url_0, self.__headers_ree)]
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(asyncio.gather(*parallel_http_get))
        for i in range(len(results[0]['indicator']['values'])):
            if unidecode.unidecode(results[0]['indicator']['values'][i]['geo_name']) == unidecode.unidecode(ID20TDzone):
                if data_type == "period_mask":
                    data.append(int(results[0]['indicator']['values'][i]['value']))
                elif data_type == "energy_price":
                    data.append(self.roundup(float(results[0]['indicator']['values'][i]['value'])/1000, 6))
        return data

    def roundup(self, num, ndecimals):
        return float(round(Decimal(str(num)),ndecimals))

    def day_leap_splitter(self, start_date, end_date):
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
    
    def calculate_invoice(self, start_date, end_date, pot, p1, p2, p3, vat_value, company_name):
        """Returns cost of invoice for a determined company."""
        days_365, days_366 = self.day_leap_splitter(start_date,end_date)
        et_value = 0.0511269632

        if company_name == "PVPC 2.0TD":
            energy_20td_price = self.get_ree_data(start_date,end_date, "energy_price")
            avg_price_energy_20td_price_peak = 0
            avg_price_energy_20td_price_low = 0
            avg_price_energy_20td_price_superlow = 0

            for i in range(len(energy_20td_price)):
                avg_price_energy_20td_price_peak += self.roundup((p1[i]*energy_20td_price[i])/sum(p1),6)
                avg_price_energy_20td_price_low += self.roundup((p2[i]*energy_20td_price[i])/sum(p2),6)
                avg_price_energy_20td_price_superlow +=  self.roundup((p3[i]*energy_20td_price[i])/sum(p3),6)

            pot_toll= [22.958932, 0.442165]
            pot_tax = [3.971618, 0.255423]
            power_toll_tax_cost_low = self.roundup(pot * ((end_date - start_date).days + 1) * pot_toll[1]/(365 + int(calendar.isleap(start_date.year))), 2) + self.roundup(pot * ((end_date - start_date).days + 1) * pot_tax[1]/(365 + int(calendar.isleap(start_date.year))), 2)
            power_toll_tax_cost_peak = self.roundup(pot * ((end_date - start_date).days + 1) * pot_toll[0]/(365 + int(calendar.isleap(start_date.year))), 2) + self.roundup(pot * ((end_date - start_date).days + 1) * pot_tax[0]/(365 + int(calendar.isleap(start_date.year))), 2)
            power_margin = self.roundup(pot * days_365 * 3.113/365, 2) + self.roundup(pot * days_366 * 3.113/366, 2)

            power_cost = self.roundup(power_margin + power_toll_tax_cost_peak + power_toll_tax_cost_low,2)
            energy_cost_20TD_peak = self.roundup(avg_price_energy_20td_price_peak*(self.roundup(sum(p1),2)),2)
            energy_cost_20TD_low = self.roundup(avg_price_energy_20td_price_low*(self.roundup(sum(p2),2)),2)
            energy_cost_20TD_superlow = self.roundup(avg_price_energy_20td_price_superlow*(self.roundup(sum(p3),2)),2)
            energy_cost = self.roundup(energy_cost_20TD_peak + energy_cost_20TD_low + energy_cost_20TD_superlow, 2)
        else:

            power_cost = self.roundup(pot * days_365 * self.COMPANY_DB[company_name][4], 2) + self.roundup(pot * days_365 * self.COMPANY_DB[company_name][3], 2)
            power_cost += self.roundup(pot * days_366 * self.COMPANY_DB[company_name][4], 2) + self.roundup(pot * days_366 * self.COMPANY_DB[company_name][3], 2)
            power_cost = self.roundup(power_cost, 2)
            energy_cost = self.roundup(self.roundup(sum(p1),0) * self.COMPANY_DB[company_name][0] + self.roundup(sum(p2),0) * self.COMPANY_DB[company_name][1] + self.roundup(sum(p3),0) * self.COMPANY_DB[company_name][2],2)

        energy_and_power_cost = energy_cost + power_cost
        social_bonus =  self.roundup(self.COMPANY_DB[company_name][5] * (days_365 + days_366),2)
        energy_tax = self.roundup((energy_and_power_cost + social_bonus)*et_value,2)
        equipment_cost = self.roundup(days_365 * (0.81*12/365) + days_366 * (0.81*12/366),2)
        total = energy_and_power_cost + energy_tax + equipment_cost + social_bonus
        VAT = self.roundup(total*vat_value,2)
        total_plus_vat = self.roundup(total + VAT,2)

        company_calcs = [company_name, power_cost, energy_cost, energy_tax, social_bonus, equipment_cost, vat_value, VAT, total_plus_vat]
        return company_calcs

    def print_3comparison(self, header, company1, company2, company3):
        #header = [type_consumptions, start_date, end_date, pot, p1, p2, p3, PERC_REAL_H, PERC_REAL_KWH, AVERAGE_KWH_H_REAL, PERC_ESTIM_H, PERC_ESTIM_KWH, AVERAGE_KWH_H_ESTIM]
        #companyX = [name, pot_cost, energy_cost, elec_tax, social_bonus, equip_cost, vat%, vat, total]
        if header[0] == 0:
            print("[CONSUMO ACTUAL]")
        else:
            print("[FACTURA {}]".format(header[0]))
        print("\nPERIODO: {0} - {1}\nDIAS: {2}\nPOTENCIA: {3}KW\nCONSUMOS: TOTAL = {4:.2f}kwh || PUNTA_P1 = {5:.2f}kwh VALLE_P2 = {6:.2f}kwh SUPERVALLE_P3 = {7:.2f}kwh\nLECTURA REAL: {8:.2f}%/h  {9:.2f}%/kwh  {10:.2f}kwh/h\nLECTURA ESTIMADA: {11:.2f}%/h  {12:.2f}%/kwh  {13:.2f}kwh/h \n".format(header[1].strftime('%d-%m-%Y'),header[2].strftime('%d-%m-%Y'),(header[2]-header[1]).days + 1,header[3],sum(header[4])+sum(header[5])+sum(header[6]),sum(header[4]),sum(header[5]),sum(header[6]),header[7],header[8],header[9],header[10],header[11], header[12]))
        print('{:<30} {:<30} {:<30}'.format(company1[0],company2[0], company3[0]))
        print("-----------------------------------------------------------------------------------------")
        print('{:<30} {:<30} {:<30}'.format("Coste potencia: {0:.2f}€".format(company1[1]), "Coste potencia: {0:.2f}€".format(company2[1]), "Coste potencia: {0:.2f}€".format(company3[1])))
        print('{:<30} {:<30} {:<30}'.format("Coste energía: {0:.2f}€".format(company1[2]), "Coste energía: {0:.2f}€".format(company2[2]), "Coste energía: {0:.2f}€".format(company3[2])))
        print('{:<30} {:<30} {:<30}'.format("Impuesto eléctrico: {0:.2f}€".format(company1[3]), "Impuesto eléctrico: {0:.2f}€".format(company2[3]), "Impuesto eléctrico: {0:.2f}€".format(company3[3])))
        print('{:<30} {:<30} {:<30}'.format("Bono social: {0:.2f}€".format(company1[4]), "Bono social: {0:.2f}€".format(company2[4]), "Bono social: {0:.2f}€".format(company3[4])))
        print('{:<30} {:<30} {:<30}'.format("Equipos de medida: {0:.2f}€".format(company1[5]), "Equipos de medida: {0:.2f}€".format(company2[5]), "Equipos de medida: {0:.2f}€".format(company3[5])))
        print('{:<30} {:<30} {:<30}'.format("IVA ({0}%): {1:.2f}€".format(100*company1[6],company1[7]), "IVA ({0}%): {1:.2f}€".format(100*company2[6],company2[7]), "IVA ({0}%): {1:.2f}€".format(100*company3[6],company3[7])))
        print('{:<30} {:<30} {:<30}'.format("TOTAL: {0:.2f}€".format(company1[8]), "TOTAL: {0:.2f}€".format(company2[8]), "TOTAL: {0:.2f}€\n\n".format(company3[8])))
        return "Done"

    def get_PS_info(self):
        self.__check_session()
        response = self.__session.request("GET", self.__ps_info_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        
        self.__check_session()
        response2 = self.__session.request("GET", self.__ps_info_url_2, headers=self.__headers_i_de)
        if response2.status_code != 200:
            raise ResponseException
        if not response2.text:
            raise NoResponseException
        json_response2 = response2.json()

        print("\n[INFORMACIÓN DEL CONTRATO]" + "\n\n\t\tComercializadora: " + json_response["des_EPS_COM_VIG"] + "\n\t\tDirección suministro: " + str(json_response["ps_DIREC"]) + "\n\t\tTarifa: " + json_response2["detalle"]["desTarifIbdla"] + "\n\t\tPotencia: " + json_response["val_POT_P1"] + "W" + "\n\t\tTensión: " + json_response["val_TENSION_PTO_SUMIN"] + "V\n")
        return

    def get_power_peaks_max_date(self):
        self.__check_session()
        response = self.__session.request("GET", self.__power_peak_dates_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response['resultado'] == 'correcto':
            max_date = datetime.strptime(json_response['fecMax'], '%d-%m-%Y%H:%M:%S')
        elif json_response['resultado'] == 'ER_1B':
            max_date = "ERROR"
        return max_date

    def get_power_peaks(self):
        self.__check_session()
        max_date = self.get_power_peaks_max_date()
        if max_date != "ERROR":
            max_date_month = max_date.month
            max_date_year = max_date.year
            ayearago_month = max_date.month
            ayearago_year = max_date.year - 1
            response = self.__session.request("GET", self.__power_peak_url.format(str(ayearago_month)+"-"+str(ayearago_year),str(max_date_month)+"-"+str(max_date_year)), headers=self.__headers_i_de)
            if response.status_code != 200:
                raise ResponseException
            if not response.text:
                raise NoResponseException
            json_response = response.json()
            print("[POTENCIAS MAXIMAS PERIODO " + str(ayearago_month)+"-"+str(ayearago_year) + " A " + str(max_date_month)+"-"+str(max_date_year) + "]\n")
            print("\t   VALLE,PUNTA\n")
            try:
                for i in range(len(json_response["potMaxMens"])):
                    title = json_response["potMaxMens"][i][0]["name"][3:11] + " "
                    pot_low = str(json_response["potMaxMens"][i][0]["y"]) + "w, "
                    pot_low = " -------, " if "None" in pot_low else pot_low
                    pot_high = str(json_response["potMaxMens"][i][1]["y"]) + "w"
                    pot_high = "-------" if "None" in pot_high else pot_high
                    print(title + pot_low + pot_high)
                print("\n")
            except:
                print("No power data available\n\n")   
        else:
            print("No power data available\n\n")			
        return

    def comparator(self):
        pot = input("Introduza la potencia con la que desea simular el cálculo, o pulse ENTER si desea simular con la potencia actualmente contratada:")
        if pot.upper() in ["*", "*".encode()]:
            print(self.measurement())
            exit = getch()
        else:
            pot = (self.contract_details()['potMaxima'])/1000 if len(pot) == 0 else float(pot)
            totals = [0,0,0]
            prices1 = []
            prices2 = []
            prices3 = []
            mode = 0
            for i in range(0,13):
                try:
                    prices1.append(0)
                    prices2.append(0)
                    prices3.append(0)
                    start_date, end_date, p1, p2, p3, energy_calcs = self.get_consumption_details(i)
                    if start_date != end_date:
                        vat_value = vat.get_iva(end_date.year,end_date.month)
                        input_char = "M"
                        highlight = ["PVPC 2.0TD", "Nufri CN023 3P", "Iberdrola Online 3P"]
                        while input_char.upper() in ["M", "M".encode()]:
                            if mode == 0: #comparison of 3 with pretty print
                                c1 = self.calculate_invoice(start_date, end_date, pot, p1, p2, p3, vat_value, highlight[0])
                                c2 = self.calculate_invoice(start_date, end_date, pot, p1, p2, p3, vat_value, highlight[1])
                                c3 = self.calculate_invoice(start_date, end_date, pot, p1, p2, p3, vat_value, highlight[2])
                                header = [i, start_date, end_date, pot, p1, p2, p3] + energy_calcs
                                self.print_3comparison(header, c1, c2, c3)

                                prices1[len(prices1)-1] = c1[8]
                                prices2[len(prices2)-1] = c2[8]
                                prices3[len(prices3)-1] = c3[8]
                                totals[0] = sum(prices1)
                                totals[1] = sum(prices2)
                                totals[2] = sum(prices3)
                                min_cost_index = totals.index(min(totals))
                                print("ACUMULADO: La tarifa {0} habría supuesto un ahorro de {1:.2f}€ frente a la tarifa {2} y de {3:.2f}€ frente a la tarifa {4}. [{5:.2f}€, {6:.2f}€, {7:.2f}€]".format(min_cost_index + 1, totals[(min_cost_index + 1) % 3]-totals[min_cost_index], (min_cost_index + 1)%3 + 1, totals[(min_cost_index + 2) % 3]-totals[min_cost_index], (min_cost_index + 2)%3 + 1, totals[0], totals[1], totals[2]))
                            else: #all comparison
                                output = []
                                print("    PERIODO: {} - {}".format(start_date.strftime('%d-%m-%Y'),end_date.strftime('%d-%m-%Y')))
                                for c in self.COMPANY_DB.keys():
                                    res = self.calculate_invoice(start_date, end_date, pot, p1, p2, p3, vat_value, c)
                                    if len(output) == 0:
                                        output.append(res)
                                    else:
                                        for index in range(len(output)):
                                            if res[8] >= output[index][8]:
                                                output.insert(index, res)
                                                break
                                            elif index == len(output) - 1:
                                                output.append(res)
                                for company in output:
                                    if company[0] in highlight:
                                        print("->  " + str(company) + " <-")
                                    else:
                                        print("    " + str(company))
                            print("\n##########  PULSE (M)CAMBIAR MODO. (ESPACIO)CERRAR. (OTRA TECLA)CONTINUAR  ###########", end="")
                            input_char = getch()
                            print("\n")
                            if input_char.upper() in ["M", "M".encode()]:
                                mode = not(mode)
                        if input_char in [" ", " ".encode()]:
                            break
                except Exception:
                    traceback.print_exc()
                    break
        return
