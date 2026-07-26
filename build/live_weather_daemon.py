import os, time, json, urllib.request, datetime
DASH_DIR = os.path.expanduser("~/.config/rainmeter-native/Skins/PopNative/CleanDash")
INI_FILE = os.path.join(DASH_DIR, "CleanDash.ini")
while True:
    try:
        # Bypassing IP-API by locking coordinates to Johannesburg
        lat, lon, city = -26.2041, 28.0473, "JOHANNESBURG"
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&hourly=temperature_2m&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=8"
        
        # Using a proper User-Agent so the weather API doesn't block the request
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        w = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        
        c, h, d = w['current'], w['hourly'], w['daily']
        h_idx = int(c['time'][-5:-3])
        c_desc = "Clear" if c['weather_code'] <= 1 else ("Cloudy" if c['weather_code'] <= 3 else "Rain")
        
        hr_t = [f"{(h_idx+i)%24:02d}:00" for i in range(1, 6)]
        hr_v = [f"{int(h['temperature_2m'][h_idx+i])}°" for i in range(1, 6)]
        dy_n = [["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][datetime.datetime.strptime(dt, "%Y-%m-%d").weekday()] for dt in d['time'][1:8]]
        dy_v = [f"{int(d['temperature_2m_max'][i])}°" for i in range(1, 8)]
    except Exception as e:
        city = "OFFLINE"; c_desc = "ERR"
        c = {'temperature_2m': 0, 'relative_humidity_2m': 0, 'wind_speed_10m': 0}
        hr_t, hr_v, dy_n, dy_v = ["-"]*5, ["-"]*5, ["-"]*7, ["-"]*7
    ini = "[Rainmeter]\nUpdate=1000\n@Monitor=0\n"
    for m in ["Time", "Day", "Date", "Month"]:
        ini += f"[Measure{m}]\nMeasure=Time\nFormat=" + {"Time":"%H:%M:%S", "Day":"%A", "Date":"%d %B %Y", "Month":"%B %Y"}[m] + "\n"
    ini += "[MeasureCPU]\nMeasure=CPU\n[MeasureRAM]\nMeasure=PhysicalMemory\n"
    
    def text_meter(name, x, y, size, font, color, text, align="Left", extra=""):
        return f"[{name}]\nMeter=String\nX={x}\nY={y}\nFontSize={size}\nFontFace={font}\nFontColor={color}\nStringAlign={align}\nAntiAlias=1\n{extra}\nText={text}\n"
    def bar_meter(name, x, y, measure, color):
        return f"[{name}]\nMeter=Bar\nMeasureName={measure}\nX={x}\nY={y}\nW=280\nH=12\nSolidColor=0,0,0,0\nBarColor={color}\nBarOrientation=Horizontal\nCornerRadius=6\n"
    
    ini += text_meter("A_HTime", 780, 65, 26, "Orbitron", "255,255,255,255", "%1", "Center", "MeasureName=MeasureTime")
    ini += text_meter("A_HDay", 780, 110, 16, "Rajdhani", "255,90,80,255", "%1", "Center", "MeasureName=MeasureDay")
    ini += text_meter("A_HDate", 780, 140, 12, "Rajdhani", "255,255,255,255", "%1", "Center", "MeasureName=MeasureDate")
    
    ini += text_meter("A_WTitle", 270, 185, 12, "Rajdhani", "255,90,80,255", "LIVE WEATHER")
    ini += text_meter("A_WLoc", 270, 205, 11, "Rajdhani", "255,255,255,255", f"{city} (LIVE)")
    ini += text_meter("A_WTemp", 270, 255, 44, "Orbitron", "255,255,255,255", f"{int(c['temperature_2m'])}°C")
    ini += text_meter("A_WDesc", 270, 325, 14, "Rajdhani", "255,255,255,255", c_desc)
    ini += text_meter("A_WDet", 270, 370, 11, "Rajdhani", "100,220,255,255", f"{int(c['relative_humidity_2m'])}% HUMIDITY   |   {int(c['wind_speed_10m'])} KM/H WIND")
    ini += text_meter("WH_Label", 270, 400, 10, "Rajdhani", "255,90,80,255", "HOURLY FORECAST")
    for i in range(5):
        ini += text_meter(f"WH_T{i}", 274 + i*68, 415, 10, "Rajdhani", "100,220,255,255", hr_t[i], "Center")
        ini += text_meter(f"WH_V{i}", 274 + i*68, 435, 11, "Rajdhani", "255,255,255,255", hr_v[i], "Center")
        
    ini += text_meter("WD_Label", 270, 460, 10, "Rajdhani", "255,90,80,255", "7-DAY FORECAST")
    for i in range(7):
        ini += text_meter(f"WD_T{i}", 266 + i*48, 475, 10, "Rajdhani", "100,220,255,255", dy_n[i], "Center")
        ini += text_meter(f"WD_V{i}", 266 + i*48, 495, 11, "Rajdhani", "120,255,150,255", dy_v[i], "Center")
        
    ini += text_meter("A_CalH", 640, 215, 13, "Rajdhani", "120,255,150,255", "JULY 2026")
    ini += text_meter("A_CalS", 640, 240, 11, "Rajdhani", "255,255,255,255", "SUNDAY 26")
    
    cal_days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    cal_grid = [
        ["--", "--", "--", "1", "2", "3", "4"],
        ["5", "6", "7", "8", "9", "10", "11"],
        ["12", "13", "14", "15", "16", "17", "18"],
        ["19", "20", "21", "22", "23", "24", "25"],
        ["[26]", "27", "28", "29", "30", "31", "--"]
    ]
    for col in range(7):
        ini += text_meter(f"Cal_DH_{col}", 645 + col*45, 285, 11, "Rajdhani", "100,220,255,255", cal_days[col], "Center")
        for row in range(5):
            val = cal_grid[row][col]
            color = "255,255,100,255" if val == "[26]" else ("100,100,100,255" if val == "--" else "255,255,255,255")
            ini += text_meter(f"Cal_C_{row}_{col}", 645 + col*45, 320 + row*35, 11, "Rajdhani", color, val, "Center")
            
    ini += text_meter("A_CalC", 640, 525, 11, "Rajdhani", "120,255,150,255", "165 Days until birthday")
    
    ini += text_meter("A_SysT", 1010, 185, 12, "Rajdhani", "100,220,255,255", "SYSTEM MONITOR")
    ini += text_meter("A_SysS", 1010, 205, 11, "Rajdhani", "255,255,255,255", "POP!_OS LINUX")
    ini += text_meter("A_CPU_T", 1010, 255, 13, "Orbitron", "255,255,255,255", "CPU USAGE: %1%", extra="MeasureName=MeasureCPU")
    ini += bar_meter("A_CPU_B", 1010, 290, "MeasureCPU", "255,90,80,255")
    ini += text_meter("A_RAM_T", 1010, 340, 13, "Orbitron", "255,255,255,255", "RAM USAGE: %1%", extra="MeasureName=MeasureRAM")
    ini += bar_meter("A_RAM_B", 1010, 375, "MeasureRAM", "120,255,150,255")
    ini += text_meter("A_SysU", 1010, 440, 11, "Rajdhani", "255,255,255,255", "KERNEL: 6.x NATIVE | UPTIME: ACTIVE & STABLE")
    def bg_card(name, x, y, color="15,15,15,130", h=420):
        return f"[{name}BG]\nMeter=Image\nX={x}\nY={y}\nW=340\nH={h}\nSolidColor={color}\nCornerRadius=15\n"
    def top_bar(name, x, y, color):
        return f"[{name}Top]\nMeter=Image\nX={x}\nY={y}\nW=340\nH=8\nSolidColor={color}\nCornerRadius=6\n"
        
    ini += bg_card("Z_Head", 610, 40, h=130) + top_bar("Z_Head", 610, 40, "255,90,80,255")
    ini += bg_card("Z_Weath", 240, 150) + top_bar("Z_Weath", 240, 150, "255,90,80,255")
    ini += bg_card("Z_Cal", 610, 190, h=380) + top_bar("Z_Cal", 610, 190, "120,255,150,255")
    ini += bg_card("Z_Sys", 980, 150) + top_bar("Z_Sys", 980, 150, "100,220,255,255")
    
    ini += f"[Z_CPUBG]\nMeter=Image\nX=1010\nY=290\nW=280\nH=12\nSolidColor=30,30,30,160\nCornerRadius=6\n"
    ini += f"[Z_RAMBG]\nMeter=Image\nX=1010\nY=375\nW=280\nH=12\nSolidColor=30,30,30,160\nCornerRadius=6\n"
    
    with open(INI_FILE, "w") as f: f.write(ini)
    os.system("killall -9 rainmeter-native 2>/dev/null && nohup ~/Documents/GitHub/rainmeter-native/build/rainmeter-native " + INI_FILE + " > /dev/null 2>&1 &")
    
    time.sleep(1800)
