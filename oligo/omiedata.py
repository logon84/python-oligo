import requests
from calendar import monthrange

def get_iva(year,month):
    if year >= 2025:
        return 0.21
    else:
        values =[]

        #get previous month data to calculate actual month vat
        month = month - 1
        if month <= 0:
            year = year - 1
            month = 12
        max_day = monthrange(year,month)[1]
        month = '{:02d}'.format(month)
        url = "https://www.omie.es/sites/default/files/dados/AGNO_{0}/MES_{1}/TXT/INT_MERCADO_DIARIO_MIN_MAX_1_01_{1}_{0}_{2}_{1}_{0}.TXT"
        data = requests.get(url.format(year,month,max_day))
        for n in range(3,len(data.text.split("\r\n")) - 2):
            values.append(float(data.text.split("\r\n")[n].split(";")[2].replace(",",".")))
        average = sum(values)/len(values)
        vat = 0.1 if average > 45 else 0.21 
        return vat
        
