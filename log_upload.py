import requests
import re
from cabrillo.parser import parse_log_text
from time import sleep
import sys
from pathlib import Path

def submit_form_and_extract_field():
    # 1. Target URL
    url = "https://txqp.contesting.com/txqpsubmitlog.php"  # Replace with your target URL

    # 2. Custom Headers (as required by your target site)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    filename = "RG5A.LOG"
    
    dir_path = Path(__file__).parent.resolve()
    filenames = [p.name for p in dir_path.iterdir() if (p.is_file() and p.name[-3:].upper() == "LOG")]
    
    # Use a Session to handle cookies automatically across requests
    with requests.Session() as session:
        session.headers.update(headers)
        
        try:
            # Step 1. Initial GET request (required to obtain cookies/CSRF tokens)
            print("Sending GET request...")
            get_response = session.get(url, timeout=10)
            get_response.raise_for_status()
        except Exception as e:
            print(f"ERROR: NO response to GET request, exception {e}")
            return

        try:           
            for filename in filenames:
                # Step 2: get and modify log contents from file
                with open(filename, "r", encoding="utf-8") as file:
                    content = file.read()
                # Perform replace
                updated_content = content.replace("2025-09-20", "2026-09-19")
                final_content = updated_content.replace("2025-09-21", "2026-09-20")

                # Step 3: modify the form content based on the parsed values from the log file
                print(f"creating form_data for {filename}")
                form_data = create_form_data(final_content, filename)
                if form_data == None:
                    continue

                # Step 4: HTTP POST Request with Form Data
                print("Sending POST request...")
                form_data["logdata"] = final_content
                files = { "logfile": ("", b"")}
                response = requests.post(url, data=form_data, files=files)            
                response.raise_for_status()
                print(response.status_code)

                # Step 5: Extract Content from Response and write back to file
                # use regex to find the <pre></pre>tag
                # BUT first make sure it was processed correctly
                match = re.search(r"<p><strong>Whoops!</strong>(.*?)</p>", response.text, re.DOTALL)
                if match:
                    # was not processed successfully
                    print(f"ERROR: {filename} failed because {match.group(1)}")
                    print_form_data(form_data)
                    sleep(3)
                    continue
                match = re.search(r"<pre>(.*?)</pre>", response.text, re.DOTALL)
                if match:
                    new_log = match.group(1).replace("\r", "").replace("\n\n", "\n")
                    # print(f"Extracted Field Value: {new_log}")
                    with open(filename, "w", encoding="utf-8") as file:
                        file.write(new_log)
                else:
                    print("ERROR: result field not found in response.")
                    continue

                # wait until next POST to not overload Bruce's website
                sleep(3)

        except FileNotFoundError:
            print(f"Error: Local file '{filename}' was not found.")
        except requests.exceptions.RequestException as e:
            print(f"ERROR: HTTP Request failed: {e}")
            
    print("done")


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

def create_form_data(content, filename):
    # print(f"CONTENT\n{content}")
    # create form data based on the parsed log file text
    convert = {
        "category_operator": {
            "fd_key": "catop",
            "SINGLE-OP": "SO",
            "MULTI-OP": "MO",
            "CHECKLOG": "CHK",
            "DEFAULT": "SO"
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
    try:
        cab = parse_log_text(content, ignore_unknown_key=False, check_categories=False,
            ignore_order=True, check_mode=False)
    except Exception as e:
        print(f"ERROR: cabillo parser failed to process {filename}")
        return None
    if not cab:
        return None
    for key in convert:
        value = getattr(cab, key, "None")
        if value != None:
            if isinstance(convert[key], str):
                form_data[convert[key]] = value
            else:
                key_list = list(convert[key].keys()) # list of possible values
                if value in key_list:
                    form_data[convert[key]["fd_key"]] = convert[key][value]
                else:
                    form_data[convert[key]["fd_key"]] = convert[key]["DEFAULT"]
        elif not isinstance(convert[key], str):
            form_data[convert[key]["fd_key"]] = convert[key]["DEFAULT"]

    # check the location and if not in states and provinces, 
    # then if in counties, put "TX"
    # if not in counties, and the de_exch of the first QSO is not a county
    # then put "DX"
    if cab.location not in (["DX"] + list(states) + list(provinces)):
        if cab.location in list(counties):
            form_data['location'] = "TX"
        elif len(cab.qso) > 0 and cab.qso[0].de_exch[1] in list(counties):
            form_data['location'] = "TX"
        else:
            match = re.search(r"TX", cab.location.upper(), re.DOTALL)
            if match:
                form_data['location'] = "TX"
            else:
                form_data['location'] = "DX"

    print_form_data(form_data)
    return form_data

def print_form_data(form_data):
    form_data_keys = list(form_data.keys())
    del form_data_keys[-1]
    print(f"form_data:")
    for k in form_data_keys:
        print(f"{k}: {form_data[k]}")




if __name__ == "__main__":
    submit_form_and_extract_field()