import requests
import re
from cabrillo.parser import parse_log_text

def submit_form_and_extract_field():
    # 1. Target URL
    url = "https://txqp.contesting.com/txqpsubmitlog.php"  # Replace with your target URL

    # 2. Custom Headers (as required by your target site)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    filename = "RG5A.LOG"
    
    # Use a Session to handle cookies automatically across requests
    with requests.Session() as session:
        session.headers.update(headers)

        try:
            # 1. Initial GET request (if required to obtain cookies/CSRF tokens)
            print("Sending GET request...")
            get_response = session.get(url, timeout=10)
            get_response.raise_for_status()

            # Step 2: get and modify log contents from file
            with open(filename, "r", encoding="utf-8") as file:
                content = file.read()
            # Perform replace
            updated_content = content.replace("2025-09-20", "2026-09-19")
            final_content = updated_content.replace("2025-09-21", "2026-09-20")

            # Step 3: modify the form content based on the parsed values from the log file
            form_data = create_form_data(final_content)

            # Step 4: HTTP POST Request with Form Data
            print("Sending POST request...")
            form_data["logdata"] = final_content
            files = { "logfile": ("", b"")}
            response = requests.post(url, data=form_data, files=files)            
            response.raise_for_status()
            print(response.status_code)

            # Step 5: Extract Content from Response and write back to file
            # use regex to find the <pre></pre>tag
            match = re.search(r"<pre>(.*?)</pre>", response.text, re.DOTALL)
            if match:
                new_log = match.group(1).replace("\r", "").replace("\n\n", "\n")
                print(f"Extracted Field Value: {new_log}")
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(new_log)
            else:
                print("Target field not found in response.")

        except FileNotFoundError:
            print(f"Error: Local file '{filename}' was not found.")
        except requests.exceptions.RequestException as e:
            print(f"HTTP Request failed: {e}")
    print("done")

def create_form_data(content):
    print(f"CONTENT\n{content}")
    # Reference files
    COUNTIES_FILE = 'counties.txt'
    STATES_FILE = 'states.txt'
    PROVINCES_FILE = 'provinces.txt'
    """Initialize with reference data files"""
    # Load counties, states, and provinces
    with open(COUNTIES_FILE, 'r') as f:
        counties = set(line.strip().upper() for line in f if line.strip())

    with open(STATES_FILE, 'r') as f:
        states = set(line.strip().upper() for line in f if line.strip())

    with open(PROVINCES_FILE, 'r') as f:
        provinces = set(line.strip().upper() for line in f if line.strip())
    
    # create form data based on the parsed log file text
    convert = {
        "category_operator": {
            "fd_key": "catop",
            "SINGLE-OP": "SO",
            "MULTI-OP": "MO",
            "CHECKLOG": "CHK",
            "DEFAULT": "SW"
        },
        "category_mode": {
            "fd_key": "catmode",
            "MIXED": "MIX",
            "SSB": "PH",
            "CW": "CW",
            "DEFAULT": "MIX"
        },
        "category_power": {
            "fd_key": "catpower",
            "HIGH": "HP",
            "LOW": "LP",
            "QRP": "QRP",
            "DEFAULT": "LP"
        },
        "category_station": {
            "fd_key": "catstation",
            "FIXED": "FIX",
            "MOBILE": "MOB",
            "DEFAULT": "FIX"
        },
        "club": "clubname1",
        "email": "emailadr",
        "location": "location"

    }
    form_data = {
            "appaction": "step2",
            "emailadr": "k5dx@tdxs.net",
            "location": "TX",       # first qso dx_exch
            "catop": "SO",          # SO, MO, CHK
            "catmode": "",          # MIX, CW, PH
            "catpower": "LP",       # LP, HP, QRP
            "catstation": "FIX",    # FIX, MOB
            "clubname1": "None",    
            "clubname2": "",
            "logdata": content
            # Add your key-value form fields here
        }
    # parse the log text and fill in the form_data object
    cab = parse_log_text(content, ignore_unknown_key=False, check_categories=False,
        ignore_order=True, check_mode=False)
    if not cab:
        return False
    for key in convert:
        value = getattr(cab, key, "")
        if len(value) > 0:
            if isinstance(convert[key], str):
                form_data[convert[key]] = value
            else:
                key_list = list(convert[key].keys()) # list of possible values
                if value in key_list:
                    form_data[convert[key]["fd_key"]] = convert[key][value]
                else:
                    form_data[convert[key]] = convert[key]["DEFAULT"]
        else:
            form_data[convert[key]["fd_key"]] = convert[key]["DEFAULT"]
    print(f"form_data:\n{form_data}")
    return form_data




if __name__ == "__main__":
    submit_form_and_extract_field()