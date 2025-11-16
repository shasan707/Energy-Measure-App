import tinytuya

# Tuya device configuration
DEVICE_ID  = "bf78adbade628ba872bhgl"
API_REGION = "eu"
API_KEY    = "7tqfnvegh54x3uf7hes7"
API_SECRET = "18f9489fc72f4d38aafcff1fac13f3ff"
#kwddafyt7htpgmhscsct
# Initialize the cloud connection
c = tinytuya.Cloud(
    apiRegion=API_REGION,
    apiKey=API_KEY,
    apiSecret=API_SECRET,
    apiDeviceID=DEVICE_ID
)

def get_device_status():
    # Fetch the device status from Tuya API
    raw = c.getstatus(DEVICE_ID)
    
    # Print the raw response to see the API response
    print("Raw Device Status:", raw)  # This will show the full raw response
    
    # Extract the result list from the response
    result_list = raw.get("result", [])
    
    # Print the result list to verify what data is inside
    print("Result List:", result_list)  # This will show the parsed result list
    
    # Map the data from the result list
    m = {item["code"]: item["value"] for item in result_list}
    
    # Print the mapped data to verify what values you're extracting
    print("Mapped Data:", m)  # This will show the final mapping of the data
    
    # Return the formatted data as a dictionary
    return {
        "switch": m.get("switch_1", False),
        "power": float(m.get("cur_power", 0)) / 10.0,
        "current": float(m.get("cur_current", 0)) / 1000.0,
        "voltage": float(m.get("cur_voltage", 0)) / 10.0,
    }

# def get_device_status():
#     raw = c.getstatus(DEVICE_ID)
#     result_list = raw.get("result", [])
#     m = {item["code"]: item["value"] for item in result_list}
#     return {
#         "switch": m.get("switch_1", False),
#         "power": float(m.get("cur_power", 0)) / 10.0,
#         "current": float(m.get("cur_current", 0)) / 1000.0,
#         "voltage": float(m.get("cur_voltage", 0)) / 10.0,
#     }

def turn_on():
    return c.sendcommand(DEVICE_ID, {"commands": [{"code": "switch_1", "value": True}]})

def turn_off():
    return c.sendcommand(DEVICE_ID, {"commands": [{"code": "switch_1", "value": False}]})