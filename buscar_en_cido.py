def buscar_en_cido(expedient, folder_path, driver_path):
    '''
    Busca el PDF d'adjudicació per un expedient a CIDO si no es troba a contractaciopublica.cat
    '''
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(service=ChromeService(driver_path), options=options)
    wait = WebDriverWait(driver, 10)

    website='https://cido.diba.cat/contractacio?filtreParaulaClau%5Bkeyword%5D=&ordenacio=TITOL&ordre=DESC&showAs=GRID&filtreProximitat%5Bpoblacio%5D=&filtreProximitat%5Bkm%5D=&filtreProximitat%5Blatitud%5D=&filtreProximitat%5Blongitud%5D=&filtreDataPublicacio%5Bde%5D=&filtreDataPublicacio%5BfinsA%5D=&filtreTipusImport%5Bimport%5D%5BimportInici%5D=&filtreTipusImport%5Bimport%5D%5BimportFinal%5D=&opcions-menu=&_token=UZSGcuGsH78zqT_2k7zBvMVxm0AMyQ0a2ly7ZZKo6jc'
    url_base = "https://cido.diba.cat"

    try:
        driver.get(website)

        # Acceptar cookies si apareixen
        try:
            accept_cookies = wait.until(EC.element_to_be_clickable((By.ID, "gdpr-cookie-accept")))
            accept_cookies.click()
        except:
            pass

        search_input = wait.until(EC.presence_of_element_located((By.ID, "filtreParaulaClau_keyword")))
        search_input.clear()
        search_input.send_keys(expedient)

        search_button = wait.until(EC.element_to_be_clickable((By.ID, "filtreParaulaClau_submit")))
        search_button.click()

        # Esperar resultats
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".panel-title a")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        panels = soup.find_all("div", class_="panel-resultat")

        for i, panel in enumerate(panels):
            try:
                title_tag = panel.find("h2", class_="panel-title").find("a")
                enllac = url_base + title_tag['href']
                driver.execute_script("window.open(arguments[0]);", enllac)
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(1)

                detail_soup = BeautifulSoup(driver.page_source, 'html.parser')

                # Buscar link d’adjudicació
                tables = detail_soup.find_all("table")
                if len(tables) > 1:
                    rows = tables[1].find_all("tr")
                    for row in rows:
                        cols = row.find_all("td")
                        if cols and "Adjudicació" in cols[3].text:
                            link = row.find("a", href=True)
                            if link:
                                print("🔁 (CIDO) Enllaç a Adjudicació trobat:", link['href'])
                                driver.get(link['href'])  # Anem directament al PDF o pàgina
                                time.sleep(2)
                                # Assumim que el PDF es descarrega directament
                                driver.quit()
                                return {"isError": False, "exception_message": "", "error_message": ""}
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                print(f"❌ Error amb resultat CIDO [{i+1}]: {e}")
    except Exception as e:
        print(f"❌ Error buscant a CIDO: {e}")
    finally:
        driver.quit()

    return {"isError": True, "exception_message": "", "error_message": "No s’ha trobat adjudicació a CIDO"}

    
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
            print("⚠️ No s'ha trobat la secció Adjudicació a contractaciopublica.cat. Provant CIDO...")

            driver.quit()  # 🔒 Tancar el driver antic que ha fallat

            fallback_result = buscar_en_cido(r["Expedient"], folder_path, driver_path)

            if fallback_result["isError"]:
                return fallback_result

            # Crear un nou driver per continuar
            options = Options()
            options.add_experimental_option("prefs", {
                "download.default_directory": os.path.join(os.getcwd(), folder_path),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            })
            # Aquí pots posar headless si vols
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=options)

            url = fallback_result["alt_url"]
            print(f"🔁 Navegant a la nova URL d'adjudicació trobada a CIDO: {url}")
            driver.get(url)
            time.sleep(2)
           


            #return buscar_en_cido(r["Expedient"], folder_path, driver_path)

            #return {"isError": True, "exception_message": NoSuchElementException, "error_message": f"{print_utils.strYellow('Sin sección Adjudicació en el enlace (Selenium)')}: Expediente({r['Expedient']}) Link({r['Link']})')"}
        
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
