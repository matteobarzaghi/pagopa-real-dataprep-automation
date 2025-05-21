import random
import os
import time
import logging
import zipfile
from datetime import datetime
from playwright.sync_api import Playwright, sync_playwright, expect
from PIL import Image

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Solo output a console, nessun file di log
    ]
)
logger = logging.getLogger(__name__)

def setup_directories():
    """
    Crea una directory principale con timestamp per salvare i file
    """
    # Crea una directory principale con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    main_dir = os.path.join(os.getcwd(), f"navigation_{timestamp}")
    os.makedirs(main_dir, exist_ok=True)
    
    return main_dir

def compress_directory(directory, output_filename=None):
    """
    Comprime la directory specificata in un file zip
    
    Args:
        directory: Il percorso della directory da comprimere
        output_filename: Nome del file zip di output (opzionale)
    
    Returns:
        Il percorso del file zip creato
    """
    if output_filename is None:
        output_filename = f"{os.path.basename(directory)}.zip"
    
    output_path = os.path.join(os.path.dirname(directory), output_filename)
    
    logger.info(f"Compressione della directory {directory} in {output_path}")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                # Aggiungi il file al zip con un percorso relativo
                arcname = os.path.relpath(file_path, os.path.dirname(directory))
                zipf.write(file_path, arcname)
    
    logger.info(f"Compressione completata: {output_path}")
    return output_path

def manual_captcha_validation():
    """
    Funzione per validare manualmente il captcha durante il test
    """
    try:
        # Chiedi input manuale direttamente
        captcha_text = input("Inserisci il testo del captcha che vedi nel browser: ")
        logger.info(f"Captcha inserito: {captcha_text}")
        return captcha_text
    except Exception as e:
        logger.error(f"Errore durante la validazione del captcha: {str(e)}")
        return ""

def run_navigation(playwright: Playwright, headless=False, navigation_count=1) -> None:
    """
    Esegue la navigazione sul sito
    
    Args:
        playwright: Istanza del Playwright
        headless: Modalità headless (default: False)
        navigation_count: Numero di volte per eseguire la navigazione (default: 1)
    """
    main_dir = setup_directories()
    
    logger.info(f"Avvio navigazione con parametri: headless={headless}, navigazioni={navigation_count}")
    logger.info(f"Directory principale creata: {main_dir}")
    
    # Configura il browser con i parametri corretti per la modalità headless
    browser_launch_options = {
        "headless": headless,
    }
    
    # Aggiungi parametri extra se siamo in modalità headless per assicurare la cattura del captcha
    if headless:
        browser_launch_options.update({
            "args": [
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--no-sandbox",
            ]
        })
    
    browser = playwright.chromium.launch(**browser_launch_options)
    
    successful_navigations = 0
    
    for iteration in range(1, navigation_count + 1):
        try:
            logger.info(f"Iniziando navigazione {iteration}/{navigation_count}")
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                accept_downloads=True
            )
            page = context.new_page()
            
            # Aggiungi un timestamp per tracciare meglio l'esecuzione
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Primo passo: Accedere al sito
            logger.info("Accesso al sito principale")
            page.goto("https://iristest.rete.toscana.it/public/")
            
            # Navigazione ai pagamenti
            logger.info("Navigazione alla sezione pagamenti")
            page.get_by_role("link", name="  Paga").nth(3).click()
            page.get_by_role("link", name=" Paga il tributo").click()
            
            # Compilazione form
            logger.info("Compilazione form di pagamento")
            page.get_by_label("Ente concessionario").select_option("15")
            
            # Utilizza il codice fiscale inviato dagli appunti o genera uno fittizio
            page.get_by_role("textbox", name="Codice Fiscale / P.IVA").click()
            try:
                page.get_by_role("textbox", name="Codice Fiscale / P.IVA").press("ControlOrMeta+V")
                logger.info("Codice fiscale incollato dagli appunti")
            except Exception:
                # Se l'incolla non funziona, usa un valore di default
                page.get_by_role("textbox", name="Codice Fiscale / P.IVA").fill("BRZMTT91S22F205T")
                logger.info("Utilizzato codice fiscale di default")
            
            # Genera un importo casuale tra 10 e 50 euro
            amount = random.randint(10, 50)
            logger.info(f"Importo selezionato: {amount} euro")
            page.locator('input#concessioneDemanioMarittimoForm\\:importo').fill(str(amount))
            
            page.locator('input#concessioneDemanioMarittimoForm\\:cfSoggettoPassivo').fill("01386030488")
            page.get_by_role("textbox", name="Denominazione").click()
            page.get_by_role("textbox", name="Denominazione").fill("REGIONE TOSCANA")
            
            # Accetta le condizioni
            page.get_by_role("checkbox", name="Dichiaro di aver letto l'").check()
            logger.info("Condizioni accettate")
            
            # Continua al prossimo step
            page.get_by_role("link", name=" Continua").click()
            logger.info("Passaggio alla pagina captcha")
            
            # Attendi che il captcha sia visibile
            page.wait_for_selector('img.thumbnail', state='visible')
            
            # Validazione del captcha - senza salvare l'immagine
            captcha_text = manual_captcha_validation()
            
            # Inserisce il captcha letto
            logger.info("Inserimento del captcha")
            page.locator("[id=\"confirmConcessioneDemanioMarittimoForm\\:captchaInput\"]").click()
            page.locator("[id=\"confirmConcessioneDemanioMarittimoForm\\:captchaInput\"]").fill(captcha_text)
            
            # Continua con il processo di pagamento
            logger.info("Aggiunta al carrello")
            page.get_by_role("link", name=" Aggiungi al carrello").click()
            page.get_by_role("link", name="  Paga").click()
            
            # Inserimento dati utente
            logger.info("Inserimento dati utente")
            page.locator("#cfInput").click()
            page.locator("#cfInput").fill("brzmtt91s22f205t")
            page.locator("input[name=\"email\"]").click()
            page.locator("input[name=\"email\"]").fill("matteo@mail.com")
            page.locator("input[name=\"emailConfirm\"]").click()
            page.locator("input[name=\"emailConfirm\"]").fill("matteo@mail.com")
            
            # Seleziona pagamento mediante avviso
            logger.info("Selezione metodo pagamento mediante avviso")
            page.get_by_role("link", name="Pagamento mediante avviso").click()
            
            # Scarica il documento
            logger.info("Avvio download del documento")
            with page.expect_download() as download_info:
                page.get_by_role("link", name="  Scarica documento").click()
                
            download = download_info.value
            timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{timestamp_file}_{download.suggested_filename}"
            download_file_path = os.path.join(main_dir, new_filename)
            
            # Salva il file con un nome univoco direttamente nella cartella principale
            download.save_as(download_file_path)
            logger.info(f"File scaricato con successo in: {download_file_path}")
            
            successful_navigations += 1
            
        except Exception as e:
            logger.error(f"Errore durante la navigazione {iteration}: {str(e)}")
        
        finally:
            # Chiudi il contesto dopo ogni navigazione
            try:
                context.close()
                logger.info(f"Navigazione {iteration} completata")
            except Exception as e:
                logger.error(f"Errore durante la chiusura del contesto: {str(e)}")
                
        # Aggiungi una pausa tra le navigazioni per evitare problemi
        if iteration < navigation_count:
            wait_time = random.uniform(2, 5)
            logger.info(f"Pausa di {wait_time:.2f} secondi prima della prossima navigazione")
            time.sleep(wait_time)
    
    # Chiudi il browser dopo tutte le navigazioni
    browser.close()
    logger.info(f"Navigazioni completate con successo: {successful_navigations}/{navigation_count}")
    
    # Comprimi la directory principale in un file zip
    zip_path = compress_directory(main_dir)
    logger.info(f"Directory compressa in: {zip_path}")
    
    return zip_path, main_dir

def main():
    """
    Funzione principale per l'esecuzione dello script
    """
    try:
        # Parametri configurabili
        HEADLESS_MODE = True  # Imposta a True per eseguire in modalità headless
        NAVIGATION_COUNT = 1   # Numero di volte per eseguire la navigazione
        
        logger.info(f"Avvio script con parametri: headless={HEADLESS_MODE}, navigazioni={NAVIGATION_COUNT}")
        
        with sync_playwright() as playwright:
            zip_path, main_dir = run_navigation(playwright, headless=HEADLESS_MODE, navigation_count=NAVIGATION_COUNT)
            
        logger.info(f"Script completato con successo. Risultati salvati in:")
        logger.info(f" - Directory: {main_dir}")
        logger.info(f" - File ZIP: {zip_path}")
        
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione dello script: {str(e)}")

if __name__ == "__main__":
    main()