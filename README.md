# 🧩 IRIS Toscana Payment Automation Script with Automatic CAPTCHA Solving

This script automates the payment process on the **IRIS Toscana** test platform using **Playwright** for web navigation and **GPT-4 Vision** for automatic CAPTCHA solving.  
All navigation results are saved in a timestamped folder and automatically compressed at the end of execution.

## Main Features

- ✅ Automated navigation of the IRIS Toscana test portal
- 🤖 Automatic CAPTCHA solving via GPT-4o Vision
- 🖐️ Manual fallback in case the automatic CAPTCHA solver fails
- 📦 Automatic download of payment documents
- 🗂️ Automatic organization of downloaded files into structured directories and ZIP compression

## Requirements

- Python 3.9+
- Virtual environment recommended
- Playwright installed and browsers configured (`playwright install`)
- Valid OpenAI API key (GPT-4o model)

### Required Python packages

```bash
pip install playwright python-dotenv openai pillow
playwright install
```

## Configuration

1. **Create a `.env` file** in the project directory and add your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key
```

2. **Adjust script parameters** (optional):
   
   Inside the script, you can configure:
   
   ```python
   HEADLESS_MODE = False  # Set to True to run in headless mode
   NAVIGATION_COUNT = 3   # Number of navigation iterations
   ```

## Usage

Simply run the script:

```bash
python your_script_name.py
```

The script will:
1. Open the IRIS Toscana test payment portal.
2. Fill out the payment form with randomized or default data.
3. Attempt to automatically solve the CAPTCHA using GPT-4o Vision.
4. If automatic solving fails, prompt you for manual CAPTCHA entry.
5. Download the payment document and save it in an automatically created timestamped directory.
6. Compress the results into a ZIP archive.

## Output

- ✅ **Downloaded files** saved in a dedicated folder.
- 🗂️ **ZIP archive** with all navigation results for easy sharing or storage.
- 📝 **Console logs** for detailed execution flow.

## Notes

- This script is intended for **testing** purposes on the IRIS Toscana **test environment** only.
- Make sure to comply with any legal and ethical guidelines when using automated navigation and AI-based CAPTCHA solving.
