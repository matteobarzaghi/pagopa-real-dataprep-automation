import random
import os
from playwright.sync_api import Playwright, sync_playwright, expect
from PIL import Image

def manual_captcha_validation():
    """
    Function to manually validate captcha during testing
    """
    # Show the original captcha image without preprocessing
    img = Image.open('captcha.png')
    img.show()
    
    # Ask for manual input
    print("The captcha image has been opened.")
    captcha_text = input("Please enter the captcha text you see: ")
    return captcha_text


def run(playwright: Playwright) -> None:
        # Create a specific download directory
    download_path = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_path, exist_ok=True)

    browser = playwright.chromium.launch(headless=False) #TODO: Headeless mode equals true does not capture the image
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://iristest.rete.toscana.it/public/")
    page.get_by_role("link", name="  Paga").nth(3).click()
    page.get_by_role("link", name=" Paga il tributo").click()
    page.get_by_label("Ente concessionario").select_option("15")
    page.get_by_role("textbox", name="Codice Fiscale / P.IVA").click()
    page.get_by_role("textbox", name="Codice Fiscale / P.IVA").press("ControlOrMeta+V")
    amount = round(random.randint(10, 50))
    page.locator('input#concessioneDemanioMarittimoForm\\:importo').fill(str(amount))
    page.locator('input#concessioneDemanioMarittimoForm\\:cfSoggettoPassivo').fill("01386030488")
    page.get_by_role("textbox", name="Denominazione").click()
    page.get_by_role("textbox", name="Denominazione").fill("REGIONE TOSCANA")
    page.get_by_role("checkbox", name="Dichiaro di aver letto l'").check()
    page.get_by_role("link", name=" Continua").click()

    # Screenshot del CAPTCHA
    page.locator('img.thumbnail').screenshot(path="captcha.png")

    # Call the function to get the captcha text
    captcha_text = manual_captcha_validation()
    print(f"Captcha entered: {captcha_text}")

    # Inserisce il captcha letto
    page.locator("[id=\"confirmConcessioneDemanioMarittimoForm\\:captchaInput\"]").click()
    #page.locator("[id=\"confirmConcessioneDemanioMarittimoForm\\:captchaInput\"]").press("CapsLock")
    page.locator("[id=\"confirmConcessioneDemanioMarittimoForm\\:captchaInput\"]").fill(captcha_text)

    page.get_by_role("link", name=" Aggiungi al carrello").click()
    page.get_by_role("link", name="  Paga").click()
    page.locator("#cfInput").click()
    page.locator("#cfInput").fill("brzmtt91s22f205t")
    page.locator("input[name=\"email\"]").click()
    page.locator("input[name=\"email\"]").fill("matteo@mail.com")
    page.locator("input[name=\"emailConfirm\"]").click()
    page.locator("input[name=\"emailConfirm\"]").fill("matteo@mail.com")
    page.get_by_role("link", name="Pagamento mediante avviso").click()

    print(f"Waiting for download to start...")
    
    with page.expect_download() as download_info:
        page.get_by_role("link", name="  Scarica documento").click()
    
    download = download_info.value
    print(f"Download started: {download.suggested_filename}")
    
    # Save the file to our download directory with its suggested filename
    download_file_path = os.path.join(download_path, download.suggested_filename)
    download.save_as(download_file_path)
    
    print(f"File downloaded successfully to: {download_file_path}")

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)