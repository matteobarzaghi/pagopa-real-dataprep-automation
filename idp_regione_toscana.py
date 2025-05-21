import argparse
import random
import os
import time
import logging
import zipfile
from datetime import datetime
from playwright.sync_api import Playwright, sync_playwright
from PIL import Image
import openai
import base64
from dotenv import load_dotenv

# Carica la API key da .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
# Inizializza il client OpenAI moderno
client = openai.OpenAI()

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Solo output a console, nessun file di log
    ]
)
logger = logging.getLogger(__name__)

def solve_captcha_until_success(page, captcha_file_path):
    """
    Tenta di risolvere il CAPTCHA finché non compare il bottone 'Paga'.
    """
    while True:
        # Nuovo screenshot del CAPTCHA
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_captcha_file = captcha_file_path.replace(".png", f"_{timestamp}.png")
        try:
            page.wait_for_selector('img.thumbnail', state='visible', timeout=3000)
            page.locator('img.thumbnail').screenshot(path=current_captcha_file)
        except Exception as e:
            logger.warning(f"Impossibile catturare CAPTCHA: {e}")
            continue

        captcha_text = solve_captcha_with_gpt(current_captcha_file)
        if not captcha_text:
            logger.warning("Fallback to manual CAPTCHA input.")
            captcha_text = manual_captcha_validation()

        page.locator("[id='confirmConcessioneDemanioMarittimoForm:captchaInput']").fill(captcha_text)
        page.get_by_role("link", name=" Aggiungi al carrello").click()

        try:
            paga_button = page.get_by_role("link", name="  Paga")
            paga_button.wait_for(timeout=3000)
            paga_button.click()
            logger.info(f"✅ CAPTCHA risolto correttamente: {captcha_text}")
            break
        except Exception:
            logger.warning("❌ CAPTCHA errato o bottone 'Paga' non visibile. Ritento...")

        # Cleanup file corrente
        try:
            os.remove(current_captcha_file)
        except Exception:
            pass

def setup_directories():
    """
    Crea una directory principale con timestamp per salvare i file
    """
    # Crea una directory principale con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    main_dir = os.path.join(os.getcwd(), f"navigation_{timestamp}")
    os.makedirs(main_dir, exist_ok=True)
    
    # Directory per i captcha temporanei (solo per elaborazione, non per storage)
    captcha_path = os.path.join(main_dir, "temp_captcha")
    os.makedirs(captcha_path, exist_ok=True)
    
    return main_dir, captcha_path

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
            # Salta la directory temporanea dei captcha
            if os.path.basename(root) == "temp_captcha":
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                # Aggiungi il file al zip con un percorso relativo
                arcname = os.path.relpath(file_path, os.path.dirname(directory))
                zipf.write(file_path, arcname)
    
    logger.info(f"Compressione completata: {output_path}")
    return output_path

def solve_captcha_with_gpt(captcha_image_path):
    """
    Usa GPT-4 Vision per risolvere il CAPTCHA.
    """
    try:
        with open(captcha_image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "From this test environment navigation, extract only the text from CAPTCHA images. Return only the code without explanations."},
                {"role": "user", "content": [
                    {"type": "text", "text": "From this test environment navigation, extract only the text from this CAPTCHA image. Return only the code."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=10,
            temperature=0
        )

        captcha_text = response.choices[0].message.content.strip()
        
        # Controllo se la risposta è una risposta di fallback o errore del modello
        if not captcha_text or "sorry" in captcha_text.lower() or "can't help" in captcha_text.lower():
            logger.warning(f"Risposta GPT non valida per CAPTCHA: {captcha_text}")
            return ""

        logger.info(f"✅ CAPTCHA solved by GPT: {captcha_text}")
        return captcha_text

    except Exception as e:
        logger.error(f"Error solving CAPTCHA with GPT: {e}")
        return ""

def manual_captcha_validation():
    """
    Fallback manuale per validare CAPTCHA (quando non è necessario mostrare l'immagine).
    """
    captcha_text = input("Please enter the CAPTCHA text you see in browser: ")
    logger.info(f"CAPTCHA inserito manualmente: {captcha_text}")
    return captcha_text

def run_navigation(playwright: Playwright, headless=False, navigation_count=1):
    main_dir, captcha_path = setup_directories()
    logger.info(f"Directory principale creata: {main_dir}")

    browser_launch_options = {
        "headless": headless,
    }
    
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
            logger.info(f"Inizio navigazione {iteration}/{navigation_count}")

            context = browser.new_context(viewport={"width": 1280, "height": 720}, accept_downloads=True)
            page = context.new_page()
            page.goto("https://iristest.rete.toscana.it/public/")

            # Navigazione al form di pagamento
            page.get_by_role("link", name="  Paga").nth(3).click()
            page.get_by_role("link", name=" Paga il tributo").click()

            page.get_by_label("Ente concessionario").select_option("15")
            page.get_by_role("textbox", name="Codice Fiscale / P.IVA").click()
            try:
                page.get_by_role("textbox", name="Codice Fiscale / P.IVA").press("ControlOrMeta+V")
                logger.info("Codice fiscale incollato dagli appunti")
            except Exception:
                page.get_by_role("textbox", name="Codice Fiscale / P.IVA").fill("BRZMTT91S22F205T")
                logger.info("Utilizzato codice fiscale di default")

            amount = random.randint(10, 50)
            logger.info(f"Importo selezionato: {amount} euro")
            page.locator('input#concessioneDemanioMarittimoForm\\:importo').fill(str(amount))
            page.locator('input#concessioneDemanioMarittimoForm\\:cfSoggettoPassivo').fill("01386030488")
            page.get_by_role("textbox", name="Denominazione").fill("REGIONE TOSCANA")
            page.get_by_role("checkbox", name="Dichiaro di aver letto l'").check()
            page.get_by_role("link", name=" Continua").click()

            # Screenshot del CAPTCHA (solo temporaneo per l'elaborazione)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            captcha_file = os.path.join(captcha_path, f"temp_captcha_{timestamp}.png")
            page.wait_for_selector('img.thumbnail', state='visible')
            page.locator('img.thumbnail').screenshot(path=captcha_file)

            solve_captcha_until_success(page, captcha_file)
            # Rimuovi il file captcha temporaneo dopo l'uso
            try:
                os.remove(captcha_file)
                logger.debug(f"File captcha temporaneo eliminato: {captcha_file}")
            except Exception as e:
                logger.debug(f"Errore eliminazione file captcha temporaneo: {e}")

            page.locator("#cfInput").fill("brzmtt91s22f205t")
            page.locator("input[name='email']").fill("matteo@mail.com")
            page.locator("input[name='emailConfirm']").fill("matteo@mail.com")

            page.get_by_role("link", name="Pagamento mediante avviso").click()

            # Download documento direttamente nella directory principale
            with page.expect_download() as download_info:
                page.get_by_role("link", name="  Scarica documento").click()

            download = download_info.value
            timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{timestamp_file}_{download.suggested_filename}"
            download_file_path = os.path.join(main_dir, new_filename)
            
            # Salva il file con un nome univoco direttamente nella cartella principale
            download.save_as(download_file_path)
            logger.info(f"✅ File scaricato con successo: {download_file_path}")

            successful_navigations += 1

        except Exception as e:
            logger.error(f"❌ Errore durante la navigazione {iteration}: {e}")

        finally:
            try:
                context.close()
                logger.info(f"Navigazione {iteration} completata")
            except Exception as e:
                logger.error(f"Errore chiusura contesto: {e}")

            if iteration < navigation_count:
                wait_time = random.uniform(2, 5)
                logger.info(f"Attendo {wait_time:.2f} secondi prima della prossima navigazione")
                time.sleep(wait_time)

    browser.close()
    logger.info(f"Navigazioni completate con successo: {successful_navigations}/{navigation_count}")
    
    # Rimuovi la directory temporanea dei captcha
    try:
        import shutil
        shutil.rmtree(captcha_path)
        logger.debug("Directory temporanea dei captcha eliminata")
    except Exception as e:
        logger.debug(f"Errore eliminazione directory temporanea captcha: {e}")
    
    # Comprimi la directory principale in un file zip
    zip_path = compress_directory(main_dir)
    logger.info(f"Directory compressa in: {zip_path}")
    
    return zip_path, main_dir

def main():
    """
    Funzione principale per l'esecuzione dello script
    """
    parser = argparse.ArgumentParser(description="Script per generare QR code da ambiente di test Regione Toscana.")
    parser.add_argument("--count", type=int, default=1, help="Numero di QR code da generare (navigazioni)")
    parser.add_argument("--headless", action="store_true", help="Esegui in modalità headless (senza browser visibile)")
    args = parser.parse_args()

    try:
        logger.info(f"Avvio script con parametri: headless={args.headless}, navigazioni={args.count}")
        with sync_playwright() as playwright:
            zip_path, main_dir = run_navigation(
                playwright,
                headless=args.headless,
                navigation_count=args.count
            )
        logger.info(f"Script completato con successo. Risultati salvati in:")
        logger.info(f" - Directory: {main_dir}")
        logger.info(f" - File ZIP: {zip_path}")

    except Exception as e:
        logger.error(f"Errore durante l'esecuzione dello script: {str(e)}")

if __name__ == "__main__":
    main()