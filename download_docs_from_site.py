import os
from pathlib import Path
import time
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import print_utils

import pandas as pd
import re
import shutil
from unidecode import unidecode
import unicodedata
import zipfile

import pdfplumber
from bs4 import BeautifulSoup
import requests
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 
from selenium.common.exceptions import NoSuchElementException
from urllib3.exceptions import ReadTimeoutError

def remove_accents(text):
    """Normalize text to remove accents"""
    return ''.join(
        char for char in unicodedata.normalize('NFD', text)
        if unicodedata.category(char) != 'Mn'
    )

def download_pdf_file_ByURL(r, url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        if response.headers.get("Content-Type") == "application/pdf":
            with open(save_path, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=1024): # check
                    pdf_file.write(chunk)
        elif response.headers.get("Content-Type") == "application/zip":
            save_path = f'{Path(save_path).with_suffix("")}.zip'
            with open(save_path, "wb") as zip_file:
                for chunk in response.iter_content(chunk_size=1024): # check
                    zip_file.write(chunk)
            extract_to = f'{Path(save_path).with_suffix("")}_ZIP' 
            print(f"entra! {save_path}, {extract_to}")
            with zipfile.ZipFile(save_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            print("entra2")
            for file_name in os.listdir(extract_to):
                source_path = os.path.join(extract_to, file_name)
                destination_path = os.path.join(f"{extract_to}_{file_name}")

                # Move file or folder
                shutil.move(source_path, destination_path)
            
            os.removedirs(extract_to)
            os.remove(save_path)
        print(f"Archivo descargado correctamente: {save_path}")
        # else:
        #     print(save_path, os.path.exists(save_path))
        return {"isError": False, "exception_message": "", "error_message": ""}
    
    except requests.exceptions.RequestException as e:
        return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error en la descarga!: Expediente({r['Expedient']}) Link({r['Link']})"}
        
def save_docAdj_JuntaAndalucia(r, folder_path):
    '''
    Funcion que obtiene el documento de Adjudicación mediante WebScrapping (BS4) en la siguiente web.
    sitename: 'contrataciondelestado.es'
    '''
    try:
        if not os.path.exists(os.path.join(folder_path, "Documento_Adjudicación.pdf")):
            pdf_content_01 = BeautifulSoup(requests.get(r["Link"]).text, features="html.parser") 
            
            for div in pdf_content_01.findAll("a"): 
                try: 
                    if div.has_attr("href") \
                        and (re.search("adjudicacion", unidecode(div.text.replace("\n", "")).lower()) \
                                or re.search("formalizacion", unidecode(div.text.replace("\n", "")).lower()) \
                                    or re.search("resolucion", unidecode(div.text.replace("\n", "")).lower()) \
                                        or re.search("acta", unidecode(div.text.replace("\n", "")).lower()) \
                                            or re.search("info", unidecode(div.text.replace("\n", "")).lower()) \
                                                or re.search("informacion", unidecode(div.text.replace("\n", "")).lower()) \
                                                    or re.search("sobre", unidecode(div.text.replace("\n", "")).lower()) \
                                                        or re.search("sobres", unidecode(div.text.replace("\n", "")).lower()) \
                                                            or re.search("contrato", unidecode(div.text.replace("\n", "")).lower())
                            ):
                                # and not (re.search("rectificacion", unidecode(div.text.replace("\n", "")).lower(), re.IGNORECASE) or re.search("errores", unidecode(div.text.replace("\n", "")).lower(), re.IGNORECASE)):
                        print(div.text.replace("\n", ""), div["href"])   
                
                        # ----------------------------- Obtenemos el enlace del primer documento y guardamos el pdf de dicho enlace
                        if not os.path.isdir(folder_path):
                            os.mkdir(folder_path)
                        if not os.path.isfile(os.path.join(folder_path, "Documento_Adjudicación.pdf")):
                            o = download_pdf_file_ByURL(r, div["href"], os.path.join(folder_path, "Documento_Adjudicación.pdf"))
                            if o["isError"]: return o
                            
                except Exception as e:
                    return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error al identificar boton de descarga del documento de Adjudicación: Expediente({r['Expedient']}) Link({r['Link']})"}
        else:
            print(print_utils.strBlue(f"Ya existe archivo con mismo nombre: {os.path.join(list(Path(folder_path).parts)[-1], 'Documento_Adjudicación.pdf')}"))        
        return {"isError": False, "exception_message": "", "error_message": ""}
            
    except Exception as e:
        return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error al cargar el contenido de la web o no se ha encontrado el recurso deseado (BS4): Expediente({r['Expedient']}) Link({r['Link']})"}
        
def save_docAdj_contrataciondelestado(r, folder_path):
    '''
    Funcion que obtiene el documento de Adjudicación mediante WebScrapping (BS4) en la siguiente web.
    sitename: 'contrataciondelestado.es'
    '''
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)
    try: 
        pdf_content_01 = BeautifulSoup(requests.get(r["Link"]).text, features="html.parser") # Obtenemos el código fuente dal enlace del excel
        
        keywords = ["adjudicacion", "formalizacion", "resolucion", "acta", "info", "informacion", "sobre", "sobres", "SOBRES", "contrato"] # Listado de palabras para buscar. El documento PDFs correspondiente es descargado en caso de encontrar en su nombre alguna de ellas
        
        # Listado de href de los documentos de la sección "Resumen Licitación"
        filtered_divs_ResumenLicitacion = [div for div in pdf_content_01.findAll("div", class_="padding0punto1") if any(word in remove_accents(div.text.strip()).lower() for word in keywords)] 
        filtered_href_ResumenLicitacion = [div.parent.parent.find(string="Pdf").parent["href"] for div in filtered_divs_ResumenLicitacion] 
        print(f"Numero de PDFs (Sección Resumen Licitación): {len(filtered_href_ResumenLicitacion)}")
        
        # Listado de href de los documentos de la sección "Otros documentos"
        if not pdf_content_01.find("table", class_="ancho100") is None:
            filtered_ids_divs_OtrosDocs = [div for div in pdf_content_01.find("table", class_="ancho100").findAll("span", class_="outputText") if any(word in remove_accents(div.text.strip()).lower() for word in keywords)] 
            filtered_names_OtrosDocs = [div.text.replace(" ", "_").replace("/", "_") for div in filtered_ids_divs_OtrosDocs] 
            filtered_href_OtrosDocs = [pdf_content_01.find_all("a", id=div.get("id").replace("textStipo1PadreGen", "linkVerDocPadreGen"))[-1]["href"] for div in filtered_ids_divs_OtrosDocs] 
            print(f"Numero de PDFs (Sección Otros Documentos): {len(filtered_href_OtrosDocs)}")
        else:
            filtered_ids_divs_OtrosDocs, filtered_names_OtrosDocs, filtered_href_OtrosDocs = [], [], []
        
        # --------------------------------------------------------------- Seccion "Resumen Licitacion" ---------------------------------------------------------------
        for i, href_resumen_lic in enumerate(filtered_href_ResumenLicitacion):
            try:
                if not os.path.exists(os.path.join(folder_path, f"Documento_SeccionResumenLicitacion_{i}.pdf")):
                    
                    # ----------------------------- Obtenemos el enlace del primer documento y guardamos el pdf de dicho enlace
                    # if not os.path.isfile(os.path.join(folder_path, f"Documento_SeccionResumenLicitacion_{i}.pdf")): # WARNING: Comento esto ya que en ocasiones hay archivos con exactamente mismo nombre y queremos que tambien los descargue
                    o = download_pdf_file_ByURL(r, href_resumen_lic, os.path.join(folder_path, f"Documento_SeccionResumenLicitacion_{i}.pdf"))
                    if o["isError"]: 
                        o["error_message"] = f"Error en la descarga de Documento: Documento_SeccionResumenLicitacion_{i}.pdf (Seccion Resumen Licitación)"
                        return o

                    # ----------------------------- Obtenemos el enlace del segundo documento y guardamos el pdf de dicho enlace
                    try:
                        with pdfplumber.open(os.path.join(folder_path, f"Documento_SeccionResumenLicitacion_{i}.pdf")) as pdf:
                            pdf_href_02 = None
                            for page in pdf.pages:
                                words_df = pd.DataFrame(page.extract_words())
                                if not "text" in words_df.columns.tolist(): continue
                                if words_df[words_df["text"]=="Documento"].shape[0]>0:
                                    for ind in words_df[words_df["text"]=="Documento"].index:
                                        if words_df["text"].loc[ind] == "Documento" and words_df["text"].loc[ind+1] == "de" and words_df["text"].loc[ind+2] == "Acta":
                                            annots_df = pd.DataFrame(page.annots)
                                            if annots_df[annots_df["x0"]==words_df["x0"].loc[ind]].shape[0]>0 and pdf_href_02 == None:
                                                pdf_href_02 = annots_df[annots_df["x0"]==words_df["x0"].loc[ind]]["uri"].iloc[-1]

                        if not pdf_href_02 == None:                
                            if not os.path.isfile(os.path.join(folder_path, f"Documento_SeccionResumenLicitacion_{i}_EnlaceInterior_ActaResolución.pdf")): 
                                o = download_pdf_file_ByURL(r, pdf_href_02, os.path.join(folder_path, f"Documento_SeccionResumenLicitacion_{i}_EnlaceInterior_ActaResolución.pdf"))
                                if o["isError"]: 
                                    o["error_message"] = f"Error en la descarga de Documento: Documento_SeccionResumenLicitacion_{i}_EnlaceInterior_ActaResolución.pdf (Seccion Resumen Licitación)"
                                    # return o # WARNING: En ocasiones puede haber error en la descarga del pdf dentro del primer pdf, comentando esta linea, se evita que se pare todo el proceso
                    
                    except Exception as e:
                        print({"isError": True, "exception_message": e.__str__(), "error_message": f"Error al identificar boton de descarga 'Acta de Adjudicación' dentro de documento: Documento_SeccionResumenLicitacion_{i}.pdf"})
                else:
                    nm = f"Documento_SeccionResumenLicitacion_{i}.pdf"
                    print(print_utils.strBlue(f"Ya existe archivo con mismo nombre: {os.path.join(list(Path(folder_path).parts)[-1], nm)}"))    
                    
            except Exception as e:
                return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error en la obtención de Documento: Documento_SeccionResumenLicitacion_{i}.pdf (Seccion Resumen Licitación)"}
        
        # --------------------------------------------------------------- Seccion "Otros Documentos" ---------------------------------------------------------------
        if len(filtered_href_OtrosDocs):
            for i, href_resumen_lic in enumerate(filtered_href_OtrosDocs): # En los documentos PDFs de la Seccion "Otros Documentos" NO buscamos enlaces de "Actas de Resolución".
                print(filtered_names_OtrosDocs[i])
                try:
                    doc_name = filtered_names_OtrosDocs[i]
                    okName = False
                    i = 2
                    while okName == False:
                        if os.path.exists(os.path.join(folder_path, f"Documento_SeccionOtrosDocs_{doc_name}.pdf")):
                            doc_name = f"{doc_name.split('_0')[0]}_0{i}"
                            i+=1
                        else: okName = True
                    # if not os.path.exists(os.path.join(folder_path, f"Documento_SeccionOtrosDocs_{doc_name}.pdf")): # WARNING: Comento esto ya que en ocasiones hay archivos con exactamente mismo nombre y queremos que tambien los descargue
                        
                        # ----------------------------- Obtenemos el enlace del primer documento y guardamos el pdf de dicho enlace
                        # if not os.path.isfile(os.path.join(folder_path, f"Documento_SeccionOtrosDocs_{filtered_names_OtrosDocs[i]}.pdf")): # WARNING: Comento esto ya que en ocasiones hay archivos con exactamente mismo nombre y queremos que tambien los descargue
                    o = download_pdf_file_ByURL(r, href_resumen_lic, os.path.join(folder_path, f"Documento_SeccionOtrosDocs_{doc_name}.pdf"))
                    if o["isError"]: 
                        o["error_message"] = f"Error en la descarga de Documento: Documento_SeccionOtrosDocs_{doc_name}.pdf (Seccion Otros Documentos)"
                        return o
                    # else:
                    #     nm = f"Documento_SeccionOtrosDocs_{filtered_names_OtrosDocs[i]}.pdf"
                    #     print(print_utils.strBlue(f"Ya existe archivo con mismo nombre: {os.path.join(list(Path(folder_path).parts)[-1], nm)}"))    
                    
                except Exception as e:
                    return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error en la obtención de Documento: Documento_SeccionOtrosDocs_{filtered_names_OtrosDocs[i]}.pdf (Seccion Otros Documentos)"}           
        
        return {"isError": False, "exception_message": "", "error_message": ""}
    
    except Exception as e:
        return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error al cargar el contenido de la web o no se ha encontrado el recurso deseado (BS4): Expediente({r['Expedient']}) Link({r['Link']})"}
    
def save_docAdj_ContratosPublicosComunidadMadrid(r, folder_path):
    '''
    Funcion que obtiene el documento de Adjudicación mediante WebScrapping (BS4) en la siguiente web.
    sitename: 'contratos-publicos.comunidad.madrid'
    '''
    try:
        pdf_content_01 = BeautifulSoup(requests.get(r["Link"]).text, features="html.parser")
        keywords = ["adjudicaci[oó]n", "formalizaci[oó]n", "resoluci[oó]n", "acta", "info", "informaci[oó]n", "sobre", "sobres", "contrato"]
        pattern = re.compile(rf"({'|'.join(keywords)})", re.IGNORECASE)
        # pattern = re.compile(rf"(?=.*resoluci[oó]n)|(?=.*adjudicaci[oó]n)", re.IGNORECASE)
        divs = pdf_content_01.find_all("div", text=pattern)
        filtered_divs = []
        for div in divs:
            if len(div.parent.find_all("a"))>0: 
                filtered_divs.append(div)
                
        pdf_names_l = [div.text.strip().split("(")[0].strip() for div in filtered_divs]
        pdf_href_l = [div.parent.find_all("a")[0]["href"] for div in filtered_divs]
        
        for pdf_href, pdf_name in zip(pdf_href_l, pdf_names_l):
            try:
                # ----------------------------- Obtenemos el enlace del primer documento y guardamos el pdf de dicho enlace
                if not os.path.isdir(folder_path):
                    os.mkdir(folder_path)
                if not os.path.isfile(os.path.join(folder_path, f"{pdf_name}.pdf")):
                    o = download_pdf_file_ByURL(r, "https://contratos-publicos.comunidad.madrid/"+pdf_href, os.path.join(folder_path, f"{pdf_name}.pdf"))
                    if o["isError"]: return o
                else:
                    nm = f"{pdf_name}.pdf"
                    print(print_utils.strBlue(f"Ya existe archivo con mismo nombre: {os.path.join(list(Path(folder_path).parts)[-1], nm)}"))   
                
            except Exception as e:
                return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error en la obtención del documento de Adjudicación: Expediente({r['Expedient']}) Link({r['Link']})"}
        
        return {"isError": False, "exception_message": "", "error_message": ""} 
    
    except Exception as e:
        return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error al cargar el contenido de la web o no se ha encontrado el recurso deseado (BS4): Expediente({r['Expedient']}) Link({r['Link']})"}
    
def save_docAdj_ContratacionPublicaCAT(r, folder_path, driver_path):
    '''
    Funcion que obtiene el documento de Adjudicación mediante WebScrapping (Selenium) en la siguiente web.
    sitename: 'contractaciopublica.cat'
    '''
    options = Options()
    # options.add_argument("--disable-blink-features=AutomationControlled")  # Bypass bot detection
    options.add_argument("--start-minimized")
    options.add_experimental_option("prefs", {
        "download.default_directory": os.path.join(os.getcwd(), folder_path),  # Download folder path
        "download.prompt_for_download": False,   
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    # options.add_argument("--headless")  # Run in headless mode (no UI)
    # driver_path = 'C:\\Users\\dsierra\\.wdm\\drivers\\chromedriver\\win64\\133.0.6943.126\\chromedriver-win32/chromedriver.exe' # driver_path = ChromeDriverManager().install()
    service = Service(driver_path)  
    driver = webdriver.Chrome(service=service, options=options)

    url = r["Link"]
    try:
        driver.get(url)
    except TimeoutError or ReadTimeoutError: 
        print(f"{print_utils.strYellow('Tiempo de espera en la carga de la web excedido.')} url: {url}")
        return {"isError": True, "exception_message": "", "error_message": ""}
        
    
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)
    try:
        try: 
            modal = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.ID, "ppms_cm_reject-all")))
            time.sleep(4) 
            modal.click()
        except: 
            pass # Caso en el que no haya modal de cookies (En ocasiones no sale)
        
        try: 
            e = driver.find_element(By.XPATH, "//a[contains(text(), 'Adjudicació')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", e)
            
            element = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Adjudicació')]")))
            element.click()
            time.sleep(4)
        except NoSuchElementException:
            driver.quit()
            os.removedirs(folder_path) # Caso en el link es correcto pero si no tiene Adjudicacion es porque es un suministro o fungible (eliminamos la carpeta para que luego no hagamos busqueda en contrataciondelestado.es de este expediente)
            return {"isError": True, "exception_message": NoSuchElementException, "error_message": f"{print_utils.strYellow('Sin sección Adjudicació en el enlace (Selenium)')}: Expediente({r['Expedient']}) Link({r['Link']})')"}
        
        buttons = driver.find_elements(By.XPATH, "//a[contains(translate(text(), '.PDF', '.pdf'), '.pdf')]")
        pdf_button_element = driver.find_elements(By.XPATH, "//button[contains(translate(text(), '.PDF', '.pdf'), '.pdf')]")
        buttons.extend(pdf_button_element)
        if len(buttons)==0: 
            return {"isError": True, "exception_message": e.__str__(), "error_message": f"Sin documentos PDF para descargar (Selenium): Expediente({r['Expedient']}) Link({r['Link']})"}
        driver.execute_script("arguments[0].scrollIntoView(true);", buttons[-1])
        time.sleep(2)

        for button in buttons:
            if button.get_attribute("innerText").endswith("pdf") or button.get_attribute("innerText").endswith("PDF"):
                try: 
                    # if re.search("resolucio", unidecode(button.get_attribute("innerText")).lower(), re.IGNORECASE) and \
                    #         re.search("adjudicacio", unidecode(button.get_attribute("innerText")).lower(), re.IGNORECASE): #WARNING: Hemos decidido descargar todos los archivos
                    pre_num_files = len(os.listdir(folder_path))
                    button.click() 
                    print(f"Botón/Enlace de Descarga {button.get_attribute('innerText')} pulsado. Descarga iniciada...")
                    time.sleep(1)
                    wait = True
                    while wait:
                        if len(os.listdir(folder_path))==pre_num_files+1:
                            wait=False 
                        time.sleep(1)  
                    print(f"Documento descargado: {os.path.join(folder_path, button.get_attribute('innerText'))}")   
                        
                except Exception as e:
                    print(f"Error con selenium al clickar el botón!: DocName({button.get_attribute('innerText')}) Expediente({r['Expedient']}) Link({r['Link']})")
            
        driver.quit() 
        return {"isError": False, "exception_message": "", "error_message": ""}
        
    except Exception as e:
        driver.quit() 
        return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error al cargar el contenido de la web o no se ha encontrado el recurso deseado (Selenium): Expediente({r['Expedient']}) Link({r['Link']})"}

def save_docAdj_ContratacionEuskadi_WebAntigua(driver, r, folder_path):
    print("Euskadi antigua!")
    try:
        tab9_e_l = driver.find_elements(By.XPATH, f"//a[contains(@href, 'adjudicacion')]")
        driver.execute_script("arguments[0].scrollIntoView(true);", tab9_e_l[-1])
        time.sleep(1)

        element = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, 'adjudicacion')]")))
        time.sleep(1) 
        element.click()

        buttons = driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'óÓAÁ', 'oOaa'), 'adjudicacion')]")
        time.sleep(1)
        original_window = driver.current_window_handle

        for button in buttons:
            try:
                file_name = button.get_attribute("innerText")
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                # if re.search("resolucion", unidecode(button.get_attribute("innerText")).lower(), re.IGNORECASE) and \
                #         re.search("adjudicacion", unidecode(button.get_attribute("innerText")).lower(), re.IGNORECASE):
                button.click() 
                download_button = driver.find_elements(By.XPATH, "//*[@onclick[contains(., 'descargar')]]")
                print(f"Botón/Enlace de Descarga {download_button[0].get_attribute('innerText')} pulsado. Descarga iniciada...")
                driver.execute_script("arguments[0].removeAttribute('target');", download_button[0])
                download_button[0].click()
                new_tab = [tab for tab in driver.window_handles if tab != original_window][0]
                driver.switch_to.window(new_tab)
                file_url = driver.current_url
                print("File URL:", file_url)
                o = download_pdf_file_ByURL(r, file_url, os.path.join(folder_path, f"{file_name}.pdf")) 
                if o["isError"]: 
                    return o
                else:
                    return {"isError": True, "exception_message": "", "error_message": f""}
            except Exception as e:
                print("wrong button (Caso euskadi web antigua TODO)")
                return {"isError": True, "exception_message": e.__str__(), "error_message": f""}
    except Exception as e:
        driver.quit() 
        return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error al cargar el contenido de la web o no se ha encontrado el recurso deseado (Selenium): Expediente({r['Expedient']}) Link({r['Link']})"}

def save_docAdj_ContratacionEuskadi(r, folder_path, driver_path):
    '''
    Funcion que obtiene el documento de Adjudicación mediante WebScrapping (Selenium) en la siguiente web.
    sitename: 'www.contratacion.euskadi.eus'
    '''
    options = Options()
    # options.add_argument("--disable-blink-features=AutomationControlled")  # Bypass bot detection
    options.add_argument("--start-minimized")
    options.add_experimental_option("prefs", {
        "download.default_directory": os.path.join(os.getcwd(), folder_path),  # Download folder path
        "download.prompt_for_download": False,   
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    # options.add_argument("--headless")  # Run in headless mode (no UI)
    # driver_path = 'C:\\Users\\dsierra\\.wdm\\drivers\\chromedriver\\win64\\133.0.6943.126\\chromedriver-win32/chromedriver.exe' # driver_path = ChromeDriverManager().install()
    service = Service(driver_path)  
    driver = webdriver.Chrome(service=service, options=options)

    url = r["Link"]
    try:
        driver.get(url)
    except TimeoutError: 
        print(f"{print_utils.strYellow('Tiempo de espera en la carga de la web excedido.')} url: {url}")
        return {"isError": True, "exception_message": "", "error_message": ""}
    
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)

    try:
        try:
            element = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '#tabs-9')]")))
            time.sleep(2) 
            element.click()
        except Exception as e:
            o = save_docAdj_ContratacionEuskadi_WebAntigua(driver, r, folder_path) # Web antigua
            return o
            
        buttons = driver.find_elements(By.XPATH, "//*[@onclick[contains(., 'descargarFichero')]]")
        driver.execute_script("arguments[0].scrollIntoView(true);", buttons[-1])
        time.sleep(2)
        
        for button in buttons:
            if button.get_attribute("innerText").endswith("pdf"):
                try:
                    # if re.search("resolucion", unidecode(button.get_attribute("innerText")), re.IGNORECASE) and \
                    #         re.search("adjudicacion", unidecode(button.get_attribute("innerText")), re.IGNORECASE): # WARNING: Se ha decidido la descarga de todos los documentos
                    pre_num_files = len(os.listdir(folder_path))
                    button.click() 
                    print(f"Botón/Enlace de Descarga {button.get_attribute('innerText')} pulsado. Descarga iniciada...")
                    wait = True
                    while wait:
                        if len(os.listdir(folder_path))==pre_num_files+1:
                            wait=False 
                        time.sleep(1)  
                    print(f"Documento descargado: {os.path.join(folder_path, button.get_attribute('innerText'))}") 
                                
                except Exception as e:
                    print(f"Error con selenium al clickar el botón!: DocName({button.get_attribute('innerText')}) Expediente({r['Expedient']}) Link({r['Link']})")
        
        driver.quit() 
        return {"isError": False, "exception_message": "", "error_message": ""}
        
    except Exception as e:
        if driver.page_source == '<html><head></head><body></body></html>':
            # os.remove(folder_name)
            driver.quit() 
            return {"isError": True, "exception_message": "404 Error", "error_message": f"Error al cargar el contenido de la web o no se ha encontrado el recurso deseado (Selenium): Expediente({r['Expedient']}) Link({r['Link']}) -- 404 ERROR!"}
        driver.quit() 
        return {"isError": True, "exception_message": e.__str__(), "error_message": f"Error al cargar el contenido de la web o no se ha encontrado el recurso deseado (Selenium): Expediente({r['Expedient']}) Link({r['Link']})"}
    
def search_contratacionestado_byExpediente_and_save_docAdjudicacion(r, folder_path, driver_path):
    options = Options()
    # options.add_argument("--disable-blink-features=AutomationControlled")  # Bypass bot detection
    options.add_argument("--start-minimized")
    options.add_experimental_option("prefs", {
        "download.default_directory": os.path.join(os.getcwd(), folder_path),  # Download folder path
        "download.prompt_for_download": False,   
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    # options.add_argument("--headless")  # Run in headless mode (no UI)
    # driver_path = 'C:\\Users\\dsierra\\.wdm\\drivers\\chromedriver\\win64\\133.0.6943.126\\chromedriver-win32/chromedriver.exe' # driver_path = ChromeDriverManager().install()
    service = Service(driver_path)  
    driver = webdriver.Chrome(service=service, options=options)

    url = "https://contrataciondelestado.es/wps/portal/!ut/p/b1/jc7LDoIwEAXQb-ELZihtkWXlUYooqIDSDenCGAyPjfH7rcat6Oxucm7mgoaWer7PKQt8OIOezKO_mns_T2Z4Zc07GhdhmKQEV0cvQpJHdc1TGyWzoLWAeSFtsqbkRyURVZpEee0ylIT_18cvJ_BX_wR6mZAPWJr4Bgsbduk8XqC1zO9EE--FCjws1gf7KCu3VSmJi0ihgnYDox6SQN2oEY7zBI-gDGg!/dl4/d5/L2dBISEvZ0FBIS9nQSEh/pw/Z7_AVEQAI930OBRD02JPMTPG21004/act/id=0/p=javax.servlet.include.path_info=QCPjspQCPbusquedaQCPMainBusqueda.jsp/605288354672/-/"
    try:
        driver.get(url)
    except TimeoutError: 
        print(f"{print_utils.strYellow('Tiempo de espera en la carga de la web excedido.')} url: {url}")
        return {"isError": True, "exception_message": "", "error_message": ""}
    
    try:
        lic_b = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:linkFormularioBusqueda")))
        lic_b.click()                                                             

        input_e = driver.find_element(By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:text71ExpMAQ")
        input_e.clear()
        input_e.send_keys(r["Expedient"])

        search_b = driver.find_element(By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:button1")
        driver.execute_script("arguments[0].scrollIntoView(true);", search_b)
        search_b.click()

        avanzada_e = driver.find_element(By.CLASS_NAME, "capaAvanzada")
        driver.execute_script("arguments[0].scrollIntoView(true);", avanzada_e)

        enlace_b = driver.find_element(By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21004_:form1:enlaceExpediente_0")
        enlace_b.click()
        
        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21006_:form1:text_EnlaceLicAgr")))
        enlace_lic = driver.find_element(By.ID, "viewns_Z7_AVEQAI930OBRD02JPMTPG21006_:form1:link_EnlaceLicPLACE")
        enlace_lic.click()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "logo_img")))
        right_url = driver.current_url
        r["Link"] = right_url
        r["Link pdf adjudicacio"] = ""
        print(f"Nuevo link: {r['Link']}")
    
        # driver.quit() 
        return r, False
        # save_docAdjudicacion(r, folder_path, driver)
        
        # return {"isError": False, "exception_message": "", "error_message": ""}
        
    except Exception as e:
        print(e)
        # driver.quit() 
        return r, True

def save_docAdjudicacion(expediente, folder_path, driver_path):
    '''
    Función que, proporcionando el nombre de la página web, realiza una operación de WebScrapping hasta encontrar el documento de Adjudicación. 
    Una vez lo encuentra, permite guardarlo en una carpeta para su posterior lectura.
    La función distingue entre varias páginas web de consulta, realizando dicha operación de WebScrapping de distinta forma para cada una, dado que cada una está construida de forma diferente.
    '''
    #sitename = expediente["Link"].split("//")[1].split("/")[0]
    #afegit per Anna per no tenir l'error quan no tens link
    link = expediente["Link"]
    if isinstance(link, str) and "//" in link:
        sitename = link.split("//")[1].split("/")[0]
    else:
        sitename = None
    expedient_name_simplified = str(expediente["Expedient"]).replace("/", "_").replace("-", "_").replace(".", "_").replace(" ", "_").replace("(", "").replace(")", "")
    folder_name = os.path.join(folder_path, expedient_name_simplified)
    print("-"*50)
    print(expedient_name_simplified)
    error = {"isError": None, "exception_message": None, "error_message": None}
    match sitename:
        # ------------------------------------------------------------------------------------------------------- contratacion del estado  ------------------------------------------------------------------------------------------------
        case 'contrataciondelestado.es': # BS4
            error = save_docAdj_contrataciondelestado(expediente, folder_name)
            
        # ------------------------------------------------------------------------------------------------------- contratos publicos madrid ------------------------------------------------------------------------------------------------
        case 'contratos-publicos.comunidad.madrid': # BS4
            error = save_docAdj_ContratosPublicosComunidadMadrid(expediente, folder_name)
        
        # ------------------------------------------------------------------------------------------------------- contratacion publica gencat ------------------------------------------------------------------------------------------------
        case 'contractaciopublica.cat' | 'contractaciopublica.gencat.cat': # Selenium
            if os.path.exists(folder_name):
                if not len(os.listdir(folder_name))>0: # Este if solo existe en los casos de Selenium, ya que al tratarse de una "simulación" sobre el browser, cuando descarga archivos en una misma sesion, el propio Google Chrome les pone (1), (2), etc... al final del nombre del archivo
                    error = save_docAdj_ContratacionPublicaCAT(expediente, folder_name, driver_path)
                else: 
                    print(f"{print_utils.strBlue('Ya existen documentos en el directorio:')} ({folder_name})") 
                    error = {"isError": False, "exception_message": "", "error_message": ""}
            else:
                error = save_docAdj_ContratacionPublicaCAT(expediente, folder_name, driver_path)
                
        # ------------------------------------------------------------------------------------------------------- euskadi ------------------------------------------------------------------------------------------------
        case 'www.contratacion.euskadi.eus' | 'www.euskadi.eus': # Selenium
            if os.path.exists(folder_name):
                if not len(os.listdir(folder_name))>0: # Este if solo existe en los casos de Selenium, ya que al tratarse de una "simulación" sobre el browser, cuando descarga archivos en una misma sesion, el propio Google Chrome les pone (1), (2), etc... al final del nombre del archivo
                    error = save_docAdj_ContratacionEuskadi(expediente, folder_name, driver_path)
                else: 
                    print(f"{print_utils.strBlue('Ya existen documentos en el directorio:')} ({folder_name})") 
                    error = {"isError": False, "exception_message": "", "error_message": ""}
            else:
                error = save_docAdj_ContratacionEuskadi(expediente, folder_name, driver_path)
                
        # ------------------------------------------------------------------------------------------------------- junta de andalucia ------------------------------------------------------------------------------------------------
        case 'www.juntadeandalucia.es': # Selenium
            error = save_docAdj_JuntaAndalucia(expediente, folder_name)
            
        # ------------------------------------------------------------------------------------------------------- otros ------------------------------------------------------------------------------------------------
        case 'www.contratosdegalicia.gal':
            print(f"{print_utils.strYellow('Caso sin realizar: www.contratosdegalicia.gal')}")
            error = {"isError": False, "exception_message": "", "error_message": ""}
        
        case _:
            print(f"{print_utils.strRed('Caso sin estudiar!')}")
    return error
        