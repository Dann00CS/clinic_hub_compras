import sys
sys.path.append("")
from pathlib import Path
import os
import numpy as np
import pymupdf
from paddleocr import PaddleOCR
import cv2
from pdf2image import convert_from_path
import unidecode
from nltk.corpus import stopwords
from thefuzz import fuzz
import string

from utils import print_utils

def plaintext_extraction_from_pdf(pdf_file_fullpath):
    '''
    Extraccion texto de un pdf (Texto desde imágenes utilizando OCR)
    '''
    doc = pymupdf.open(pdf_file_fullpath)
    plain_text = ""
    for page in doc.pages():
        plain_text+=page.get_text().replace("\n", " ")
        
    return plain_text

def check_if_ProductoInteres_in_extractedText(extracted_text, equipamiento_productointeres_text):
    stop_words = set(stopwords.words("spanish")) 
    wordList = [unidecode.unidecode(word.lower()) for word in [w for w in extracted_text.split(" ") if w != ""] if unidecode.unidecode(word.lower()) not in stop_words and unidecode.unidecode(word.lower()) not in string.punctuation]
    wordsToSearch = [unidecode.unidecode(word.lower()) for word in equipamiento_productointeres_text.replace("/", " ").split(" ") if unidecode.unidecode(word.lower()) not in stop_words and unidecode.unidecode(word.lower()) not in string.punctuation]
    word_in_doc = False
    for w in wordList:
        stop=False
        for w_t in wordsToSearch:
            if fuzz.ratio(w,w_t) >= 85:
                print(f"{print_utils.strGreen('Palabra encontrada!')} {w} (similar a: {w_t}) -- (fuzz ratio: {fuzz.ratio(w,w_t)})")
                stop=True
                word_in_doc=True
            if stop: break
    return word_in_doc

def pymupdf_pixmap_to_numpy(pixmap):
    """ 
    Convertir pymupdf.Pixmap a un array (compatible como input para PaddleOCR)
    """
    img_array = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.h, pixmap.w, pixmap.n)
    
    # Convert grayscale or CMYK to RGB
    if pixmap.n == 4:  # CMYK or RGB + Alpha
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
    elif pixmap.n == 1:  # Grayscale
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
    
    return img_array

# def convert_PDFpages_into_images_and_extractText_byOCR(pdf_file_fullpath):
#     pdf_page_to_images = convert_from_path(pdf_file_fullpath, poppler_path=r"C:\Users\dsierra\OneDrive - Hospital Clínic de Barcelona\Proyectos IA - Daniel\ProyectoCompras_IA\poppler-24.08.0\Library\bin")
#     for image in pdf_page_to_images:
#         image 

def text_extraction_from_images_from_pdf(pdf_file_fullpath, equipamiento_productointeres_text):
    dims_duple_NoTextImages_l = [] # Listado de tuples de dimension (width, length) de imagenes donde no se ha extraido texto
    pix_d = {}
    
    doc = pymupdf.open(pdf_file_fullpath)
    for i_page, page in enumerate(doc.pages()):     
        pix_d[f"{i_page}"] = {}
        for image_index, img in enumerate(page.get_images(), start=1): 
            xref = img[0]
            pix = pymupdf.Pixmap(doc, xref)
            
            if not pix.colorspace == None:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix) # Hacer distincion en esta condicion entre RGB/GRAY/CMYK
            else: # En ocasiones la imagen se trata de una "mask" (typically used for transparecy of black-and-white overlays) y no tiene si quiera atributo colorspace --> throw error
                base_image = doc.extract_image(xref)
                if base_image["colorspace"]==1:
                    pix = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.Pixmap(base_image["image"]))
                else:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.Pixmap(base_image["image"]))
                    
            pix_d[f"{i_page}"][f"{image_index}"] = pix
            
            ###### ----------------------------------- Guardado de imagenes (Individual case) ----------------------------------
            # if fol == "11_19" and fil == "Documento_SeccionResumenLicitacion_0.pdf":
            #     pix.save(os.path.join("data", "01", "pdf_docs", fol, page_name)) 
            ###### -------------------------------------------------------------------------------------------------------------
    
    already_inText = False   
    extractedTextFromImages_wholeDoc = " -------------------------------- Inicio de Documento (Texto extraido de imágenes) ------------------------------------- \n"
    for i_page in pix_d.keys():   
        if already_inText: continue 
        extractedText_wholeDoc = ""
        if len(pix_d[i_page])>=10:
            # ------------------------------------------- Caso con muchas imágenes por página (Posiblemente se trate de una página escaneada) --> Transformacion de página en imagen
            print(f"{print_utils.strYellow('Posible página escaneada! (Num images>=10)')} page: {i_page}")
            print("Convirtiendo la página a imagen... ")
            try:
                images = convert_from_path(pdf_file_fullpath, poppler_path=os.path.join("poppler-24.08.0", "Library", "bin"))
                png_filename = f'{Path(pdf_file_fullpath).with_suffix("")}_PAGE{i_page}.png'
                images[int(i_page)].save(png_filename , format="PNG")
                image_doc = pymupdf.open(png_filename)
                pix = image_doc[0].get_pixmap()
                pix_d[f"{i_page}"] = {}
                pix_d[f"{i_page}"][f"0_PageToImg"] = pix
                os.remove(png_filename)
            except Exception as e:
                print(f"Error convirtiendo la pagina {i_page} a imagen")
                print(e)
        
        # ------------------------------------------- Imagenes en los metadatos del documento
        extractText_ByPage = ""
        for pix_image_index, pix_v in pix_d[f"{i_page}"].items():
            extractedTextFromImages_wholeDoc += f"\n -- page_{i_page}-image_{pix_image_index}.png ({pix_v.width}, {pix_v.height}) -- \n"
            if already_inText: continue
            print(f"\n ---- Page: {i_page} -- # images: {len(pix_d[f'{i_page}'])}, ({pix_v.width}, {pix_v.height})")
            print(f"listado dimensiones a no comprobar: {dims_duple_NoTextImages_l}")
            if (pix_v.width>=100 or pix_v.height>=100) and ((pix_v.width, pix_v.height) not in dims_duple_NoTextImages_l):
                img = pymupdf_pixmap_to_numpy(pix_v) # Convertimos Pixmap --> Numpy Array
                print("Se inicia OCR... ")
                ocr = PaddleOCR(use_angle_cls=True, lang="es") # Inicializamos clase PaddleOCR
                result = ocr.ocr(img, cls=True, ) # Output original de Object Character Recognition desde libreria PaddleOCR
                if not result[0] == None:
                    found_words_l = [line[1][0] for line in result[0]] # Obtenemos listado de únicamente el texto identificado
                    for w in found_words_l:
                        extractText_ByPage+=f" {w}" # Concatenamos el texto de una imagen
                        extractedText_wholeDoc+=f" {w}" # Concatenamos todo el texto identificado (De todas las imagenes)
                        
                    if len(found_words_l)==0:
                        print(f"page_{i_page}-image_{pix_image_index}.png: Sin coincidencias!")
                        dims_duple_NoTextImages_l.append((pix_v.width, pix_v.height))
                    else:
                        print(f"page_{i_page}-image_{pix_image_index}.png: {found_words_l}")
                        if not check_if_ProductoInteres_in_extractedText(extractText_ByPage, equipamiento_productointeres_text) and pix.width<1000 and pix.height<1000: # En caso de no haber encontrado coincidencias, tambien guardamos las dimensiones para no volver a leer una imagen con esas dimensiones
                            # Se incluye tambien las coindiciones de que width y height sean mayor a 1000 para evitar que guardelas dimensiones de imagenes que son una pagina entera. (Ya que en este caso, son imagenes diferentes)
                            dims_duple_NoTextImages_l.append((pix_v.width, pix_v.height))
                else:
                    print("Sin palabras!")
                    dims_duple_NoTextImages_l.append((pix_v.width, pix_v.height))
                
                inText = check_if_ProductoInteres_in_extractedText(extractedText_wholeDoc, equipamiento_productointeres_text)
                if inText: already_inText=True
            
        extractedTextFromImages_wholeDoc+=extractedText_wholeDoc
        extractedTextFromImages_wholeDoc+=f"\n\n-------------------------------- Fin Página {i_page} ------------------------------------- \n"
        
    return already_inText, extractedTextFromImages_wholeDoc