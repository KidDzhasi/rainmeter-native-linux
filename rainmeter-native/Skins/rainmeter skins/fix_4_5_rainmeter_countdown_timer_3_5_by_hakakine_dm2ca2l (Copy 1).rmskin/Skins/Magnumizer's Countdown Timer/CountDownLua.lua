function Initialize()
   tYear   = SKIN:GetVariable('Year')
   tMonth  = SKIN:GetVariable('Month')
   tDay    = SKIN:GetVariable('Day')
   tHour   = SKIN:GetVariable('Hour')
   tMinute = SKIN:GetVariable('Minute')
   tSecond = SKIN:GetVariable('Second')
   numberTime = SKIN:GetVariable('nTime')
   timerTime = tonumber(SKIN:GetVariable('CurrentTimerTime')) or 0
   counterSetTime = tonumber(SKIN:GetVariable('CurrentTimerTimeSet')) or 0
   skinClamp = SKIN:GetVariable('SkinClampOn')
   customMessageOn = SKIN:GetVariable('EndMessageOn')
   showYears = SKIN:GetVariable('ShowYears')
   showMonths = SKIN:GetVariable('ShowMonths')
   showDays = SKIN:GetVariable('ShowDays')
   showHours = SKIN:GetVariable('ShowHours')
   showMinutes = SKIN:GetVariable('ShowMinutes')
   showSeconds = SKIN:GetVariable('ShowSeconds')
   showDesktopOnZero = SKIN:GetVariable('ShowDesktopOnZero')
   shutdownOnZero = SKIN:GetVariable('ShutdownOnZero')
   customMessage = SKIN:GetVariable('CustomMessage')
   usePlayer = SKIN:GetVariable('UsePlayer')
   loop = SKIN:GetVariable('Loop')
end

function ShowOrHide()
   return SKIN:GetVariable('HideCountdown')
end

function CountFromDate()
   return SKIN:GetVariable('DateSet')
end

function GetXPos()
	local x = tonumber(SKIN:GetVariable('EndMessageXPos'))
	local w = tonumber(SKIN:GetMeter('GhostEndMessage'):GetW())
	w = w/2
	if x < w then
    return w
	else
	return x
	end
end

function SaveTime(_years, _months, _days, _hours, _minutes, _seconds)
	local yearsec = _years * 365 * 24 * 60 * 60
	local monthsec = _months * (365/12) * 24 * 60 * 60
	local daysec = _days * 24 * 60 * 60
	local hoursec = _hours * 60 * 60
	local minutesec = _minutes * 60
	local totalsec = yearsec + monthsec + daysec + hoursec + minutesec + _seconds
	local totaltime = totalsec + os.time()
	
	SKIN:Bang('!WriteKeyValue','Variables', 'CurrentTimerTime', totaltime, "Options/options.inc")
	SKIN:Bang('!WriteKeyValue','Variables', 'CurrentTimerTimeSet', totalsec, "Options/options.inc")
	timerTime = totaltime
	counterSetTime = totalsec
end

function RoundUpYear(nt)
	local yrs = nt / 60 / 60 / 24 / 30 / 12
	
	if yrs <= 1 and yrs >= 0.6 then
	return 1
	else
	return math.floor(yrs)
	end
end

function GetDays(X)
	if (X > 0) then
		return math.floor(X / 60 / 60 / 24) % 31
	else
		return 0
	end
end

function Update()
   local ok, err = pcall(function()
   local nTime = 0
   local timeTbl = {month=tMonth, day=tDay, year=tYear, hour=tHour, min=tMinute, sec=tSecond}
   local dateset = tonumber(CountFromDate())

    if (dateset == 0) then
		nTime = timerTime - os.time()
	else
		nTime = os.time(timeTbl) - os.time()   
	end
	
   local numbertime = tonumber(numberTime)
   local avgDaysInMonth = 30
   local endmessageon = tonumber(customMessageOn)
   local looping = tonumber(loop)
   
    if nTime < 0 then
		if (dateset == 0) and (looping == 1) then
			timerTime = counterSetTime + os.time()
			nTime = timerTime - os.time()
			SKIN:Bang('!WriteKeyValue','Variables', 'CurrentTimerTime', timerTime, "Options/options.inc")
		else
			if (numbertime == 1) then
				SKIN:Bang('!WriteKeyValue','Variables', 'nTime', '0')
				SKIN:Bang('!SetVariable', 'nTime', '0')
				numberTime = 0
			end
			if (endmessageon == 1) then
				SKIN:Bang('!SetOption', 'Years', 'Prefix', '')
				SKIN:Bang('!SetOption', 'Years', 'Text', '')
				SKIN:Bang('!SetOption', 'LineYears', 'Hidden', '1')
				SKIN:Bang('!SetOption', 'YearsDash', 'Text', '')
				SKIN:Bang('!SetOption', 'YearsLabel', 'Text', '')

				SKIN:Bang('!SetOption', 'Months', 'Prefix', '')
				SKIN:Bang('!SetOption', 'Months', 'Text', '')
				SKIN:Bang('!SetOption', 'LineMonths', 'Hidden', '1')
				SKIN:Bang('!SetOption', 'MonthsDash', 'Text', '')
				SKIN:Bang('!SetOption', 'MonthsLabel', 'Text', '')

				SKIN:Bang('!SetOption', 'Days', 'Prefix', '')
				SKIN:Bang('!SetOption', 'Days', 'Text', '')
				SKIN:Bang('!SetOption', 'LineDays', 'Hidden', '1')
				SKIN:Bang('!SetOption', 'DaysDash', 'Text', '')
				SKIN:Bang('!SetOption', 'DaysLabel', 'Text', '')
				
				SKIN:Bang('!SetOption', 'Hours', 'Text', '')
				SKIN:Bang('!SetOption', 'Hours', 'Prefix', '')
				SKIN:Bang('!SetOption', 'LineHours', 'Hidden', '1')
				SKIN:Bang('!SetOption', 'HoursDash', 'Text', '')
				SKIN:Bang('!SetOption', 'HoursLabel', 'Text', '')
				
				SKIN:Bang('!SetOption', 'Minutes', 'Text', '')
				SKIN:Bang('!SetOption', 'Minutes', 'Prefix', '')
				SKIN:Bang('!SetOption', 'LineMinutes', 'Hidden', '1')
				SKIN:Bang('!SetOption', 'MinutesDash', 'Text', '')
				SKIN:Bang('!SetOption', 'MinutesLabel', 'Text', '')
				
				SKIN:Bang('!SetOption', 'Seconds', 'Prefix', '')
				SKIN:Bang('!SetOption', 'Seconds', 'Text', '')
				SKIN:Bang('!SetOption', 'SecondsLabel', 'Text', '')
				SKIN:Bang('!SetOption', 'SecondsLabelCentered', 'Text', '')
				SKIN:Bang('!SetOption', 'EndMessage', 'Text', customMessage)
				SKIN:Bang('!SetOption', 'EndMessage', 'X', GetXPos())
				return
			else
				nTime = 0
				return
			end
		end
    end
   
   local years = math.floor(nTime / 60 / 60 / 24 / avgDaysInMonth / 12)
   local months = math.floor(nTime / 60 / 60 / 24 / avgDaysInMonth) % 12
   local days = tonumber(GetDays(nTime))
   local hours = math.floor(nTime / 60 / 60) % 24
   local minutes = math.floor(nTime / 60) % 60
   local seconds = math.floor(nTime) % 60
   
   local altminutes = math.floor(nTime / 60)
   local althours = math.floor(nTime / 60 / 60)
   local altdays =  math.floor(nTime / 60 / 60 / 24)
   local altmonths = math.floor(nTime / 60 / 60 / 24 / avgDaysInMonth)
   local altyears = RoundUpYear(nTime)
   
   local hidecountdown = tonumber(ShowOrHide())
   local skinclamp = tonumber(skinClamp)
   local showyears = tonumber(showYears)
   local showmonths = tonumber(showMonths)
   local showdays = tonumber(showDays)
   local showhours = tonumber(showHours)
   local showminutes = tonumber(showMinutes)
   local showseconds = tonumber(showSeconds)
   local showdesktoponzero = tonumber(showDesktopOnZero)
   local shutdownonzero = tonumber(shutdownOnZero)
   local useplayer = tonumber(usePlayer)

 
	if (altmonths <= 0) then
		days = altdays
	end

   if (hidecountdown == 0) then
   
   	if (showyears == 1) then
	
		if (showmonths == 0 and showdays == 0 and showhours == 0 and showminutes == 0 and showseconds == 0) then
		
			SKIN:Bang('!SetOption', 'Years', 'Prefix', '')
		
		else
		
			if (years < 10) then
			SKIN:Bang('!SetOption', 'Years', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Years', 'Prefix', '')
			end
			
		end
	
		if (altyears <= 0 and skinclamp == 1) then
		SKIN:Bang('!HideMeter', 'Years')
		SKIN:Bang('!SetOption', 'LineYears', 'Hidden', '1')
		SKIN:Bang('!SetOption', 'YearsDash', 'Text', '')
		SKIN:Bang('!SetOption', 'YearsLabel', 'Text', '')
		else
		SKIN:Bang('!ShowMeter', 'Years')
		
			if (showmonths == 0 and showdays == 0 and showhours == 0 and showminutes == 0 and showseconds == 0) then
		
			SKIN:Bang('!SetOption', 'Years', 'Text', altyears..'')
		
			else
			
			SKIN:Bang('!SetOption', 'Years', 'Text', years..'')
				
			end
		
			if (showmonths == 1 or showdays == 1 or showhours == 1 or showminutes == 1 or showseconds == 1) then
			SKIN:Bang('!SetOption', 'YearsDash', 'Text', '/')
			SKIN:Bang('!SetOption', 'LineYears', 'Hidden', '0')
			else
			SKIN:Bang('!SetOption', 'LineYears', 'Hidden', '1')
			SKIN:Bang('!SetOption', 'YearsDash', 'Text', '')
			end
			
		end
		
	else
	SKIN:Bang('!HideMeter', 'Years')
	SKIN:Bang('!SetOption', 'LineYears', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'YearsDash', 'Text', '')
	SKIN:Bang('!SetOption', 'YearsLabel', 'Text', '')
	end
	
	if (showmonths == 1) then

		if (altmonths <= 0 and skinclamp == 1) then
		SKIN:Bang('!HideMeter', 'Months')
		SKIN:Bang('!SetOption', 'LineMonths', 'Hidden', '1')
		SKIN:Bang('!SetOption', 'MonthsDash', 'Text', '')
		SKIN:Bang('!SetOption', 'MonthsLabel', 'Text', '')
		else
		SKIN:Bang('!ShowMeter', 'Months')
		
			if (showdays == 1 or showhours == 1 or showminutes == 1 or showseconds == 1) then
			SKIN:Bang('!SetOption', 'LineMonths', 'Hidden', '0')
			SKIN:Bang('!SetOption', 'MonthsDash', 'Text', '/')
			else
			SKIN:Bang('!SetOption', 'LineMonths', 'Hidden', '1')
			SKIN:Bang('!SetOption', 'MonthsDash', 'Text', '')
			end
			
			if (showyears == 0 and showdays == 0 and showhours == 0 and showminutes == 0 and showseconds == 0) then
			SKIN:Bang('!SetOption', 'Months', 'Prefix', '')
			end
			
		end
				
		if (showyears == 0) then
		SKIN:Bang('!SetOption', 'Months', 'Text', altmonths..'')
		
			if (altmonths < 10) then
			SKIN:Bang('!SetOption', 'Months', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Months', 'Prefix', '')
			end
		
		else
		SKIN:Bang('!SetOption', 'Months', 'Text', months..'')
		
			if (months < 10) then
			SKIN:Bang('!SetOption', 'Months', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Months', 'Prefix', '')
			end
		
		end
			
	else
	SKIN:Bang('!HideMeter', 'Months')
	SKIN:Bang('!SetOption', 'LineMonths', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'MonthsDash', 'Text', '')
	SKIN:Bang('!SetOption', 'MonthsLabel', 'Text', '')
	end
	
	
	if (showdays == 1) then

		if (altdays <= 0 and skinclamp == 1) then
		SKIN:Bang('!HideMeter', 'Days')
		SKIN:Bang('!SetOption', 'LineDays', 'Hidden', '1')
		SKIN:Bang('!SetOption', 'DaysDash', 'Text', '')
		SKIN:Bang('!SetOption', 'DaysLabel', 'Text', '')
		else
		SKIN:Bang('!ShowMeter', 'Days')
		
			if (showhours == 1 or showminutes == 1 or showseconds == 1) then
			SKIN:Bang('!SetOption', 'LineDays', 'Hidden', '0')
			SKIN:Bang('!SetOption', 'DaysDash', 'Text', '/')
			else
			SKIN:Bang('!SetOption', 'LineDays', 'Hidden', '1')
			SKIN:Bang('!SetOption', 'DaysDash', 'Text', '')
			end
			
			if (showyears == 0 and showmonths == 0 and showhours == 0 and showminutes == 0 and showseconds == 0) then
			SKIN:Bang('!SetOption', 'Days', 'Prefix', '')
			end
			
		end

		if (showyears == 0 and showmonths == 0) then
		SKIN:Bang('!SetOption', 'Days', 'Text', altdays..'')
		
			if (altdays < 10) then
			SKIN:Bang('!SetOption', 'Days', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Days', 'Prefix', '')
			end
		
		else
		SKIN:Bang('!SetOption', 'Days', 'Text', days..'')
		
			if (days < 10) then
			SKIN:Bang('!SetOption', 'Days', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Days', 'Prefix', '')
			end
		
		end
			
	else
	SKIN:Bang('!HideMeter', 'Days')
	SKIN:Bang('!SetOption', 'LineDays', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'DaysDash', 'Text', '')
	SKIN:Bang('!SetOption', 'DaysLabel', 'Text', '')
	end

		
	if (showhours == 1) then

		if (althours <= 0 and skinclamp == 1) then
		SKIN:Bang('!HideMeter', 'Hours')
		SKIN:Bang('!SetOption', 'LineHours', 'Hidden', '1')
		SKIN:Bang('!SetOption', 'HoursDash', 'Text', '')
		SKIN:Bang('!SetOption', 'HoursLabel', 'Text', '')
		else
		SKIN:Bang('!ShowMeter', 'Hours')
		
			if (showminutes == 1 or showseconds == 1) then
			SKIN:Bang('!SetOption', 'LineHours', 'Hidden', '0')
			SKIN:Bang('!SetOption', 'HoursDash', 'Text', ':')
			else
			SKIN:Bang('!SetOption', 'LineHours', 'Hidden', '1')
			SKIN:Bang('!SetOption', 'HoursDash', 'Text', '')
			end
			
			if (showyears == 0 and showmonths == 0 and showdays == 0 and showminutes == 0 and showseconds == 0) then
			SKIN:Bang('!SetOption', 'Hours', 'Prefix', '')
			end
			
		end
		
		if (showyears == 0 and showmonths == 0 and showdays == 0) then
		SKIN:Bang('!SetOption', 'Hours', 'Text', althours..'')
		
			if (althours < 10) then
			SKIN:Bang('!SetOption', 'Hours', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Hours', 'Prefix', '')
			end
			
		else
		SKIN:Bang('!SetOption', 'Hours', 'Text', hours..'')
		
			if (hours < 10) then
			SKIN:Bang('!SetOption', 'Hours', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Hours', 'Prefix', '')
			end
			
		end
			
	else
	SKIN:Bang('!HideMeter', 'Hours')
	SKIN:Bang('!SetOption', 'LineHours', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'HoursDash', 'Text', '')
	SKIN:Bang('!SetOption', 'HoursLabel', 'Text', '')
	end

			
	if (showminutes == 1) then

		if (altminutes <= 0 and skinclamp == 1) then
		SKIN:Bang('!HideMeter', 'Minutes')
		SKIN:Bang('!SetOption', 'LineMinutes', 'Hidden', '1')
		SKIN:Bang('!SetOption', 'MinutesDash', 'Text', '')
		SKIN:Bang('!SetOption', 'MinutesLabel', 'Text', '')
		else
		SKIN:Bang('!ShowMeter', 'Minutes')
		
			if (showseconds == 1) then
			SKIN:Bang('!SetOption', 'LineMinutes', 'Hidden', '0')
			SKIN:Bang('!SetOption', 'MinutesDash', 'Text', ':')
			else
			SKIN:Bang('!SetOption', 'LineMinutes', 'Hidden', '1')
			SKIN:Bang('!SetOption', 'MinutesDash', 'Text', '')
			end
			
			if (showyears == 0 and showmonths == 0 and showdays == 0 and showhours == 0 and showseconds == 0) then
			SKIN:Bang('!SetOption', 'Minutes', 'Prefix', '')
			end
			
		end
		
		if (showyears == 0 and showmonths == 0 and showdays == 0 and showhours == 0) then
		SKIN:Bang('!SetOption', 'Minutes', 'Text', altminutes..'')
		
			if (altminutes < 10) then
			SKIN:Bang('!SetOption', 'Minutes', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Minutes', 'Prefix', '')
			end
		
		else
		SKIN:Bang('!SetOption', 'Minutes', 'Text', minutes..'')
		
			if (minutes < 10) then
			SKIN:Bang('!SetOption', 'Minutes', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Minutes', 'Prefix', '')
			end
		
		end
			
	else
	SKIN:Bang('!HideMeter', 'Minutes')
	SKIN:Bang('!SetOption', 'LineMinutes', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'MinutesDash', 'Text', '')
	SKIN:Bang('!SetOption', 'MinutesLabel', 'Text', '')
	end

				
	if (showseconds == 1) then

		SKIN:Bang('!ShowMeter', 'Seconds')
		
		if (showyears == 0 and showmonths == 0 and showdays == 0 and showhours == 0 and showminutes == 0) then
		SKIN:Bang('!SetOption', 'Seconds', 'Text', nTime..'')
		SKIN:Bang('!SetOption', 'Seconds', 'Prefix', '')
		SKIN:Bang('!ShowMeter', 'SecondsLabelCentered')
		SKIN:Bang('!HideMeter', 'SecondsLabel')
		else
		SKIN:Bang('!SetOption', 'Seconds', 'Text', seconds..'')
		SKIN:Bang('!HideMeter', 'SecondsLabelCentered')
		SKIN:Bang('!ShowMeter', 'SecondsLabel')
		
			if (seconds < 10) then
			SKIN:Bang('!SetOption', 'Seconds', 'Prefix', '0')
			else
			SKIN:Bang('!SetOption', 'Seconds', 'Prefix', '')
			end
			
		end
			
	else
	SKIN:Bang('!HideMeter', 'Seconds')
	SKIN:Bang('!SetOption', 'SecondsLabel', 'Text', '')
	SKIN:Bang('!SetOption', 'SecondsLabelCentered', 'Text', '')
	end
	
   else
		SKIN:Bang('!HideMeter', 'Years')
		SKIN:Bang('!SetOption', 'LineYears', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'YearsDash', 'Text', '')
	SKIN:Bang('!SetOption', 'YearsLabel', 'Text', '')
		SKIN:Bang('!HideMeter', 'Months')
		SKIN:Bang('!SetOption', 'LineMonths', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'MonthsDash', 'Text', '')
	SKIN:Bang('!SetOption', 'MonthsLabel', 'Text', '')
		SKIN:Bang('!HideMeter', 'Days')
		SKIN:Bang('!SetOption', 'LineDays', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'DaysDash', 'Text', '')
	SKIN:Bang('!SetOption', 'DaysLabel', 'Text', '')
		SKIN:Bang('!HideMeter', 'Hours')
		SKIN:Bang('!SetOption', 'LineHours', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'HoursDash', 'Text', '')
	SKIN:Bang('!SetOption', 'HoursLabel', 'Text', '')
		SKIN:Bang('!HideMeter', 'Minutes')
		SKIN:Bang('!SetOption', 'LineMinutes', 'Hidden', '1')
	SKIN:Bang('!SetOption', 'MinutesDash', 'Text', '')
	SKIN:Bang('!SetOption', 'MinutesLabel', 'Text', '')
		SKIN:Bang('!HideMeter', 'Seconds')
	SKIN:Bang('!SetOption', 'SecondsLabel', 'Text', '')
	SKIN:Bang('!SetOption', 'SecondsLabelCentered', 'Text', '')
    end
		
	if (years <= 0) and (months <= 0) and (days <= 0) and (hours <= 0) and (minutes <= 0)  then
	
		if (seconds == 10) or (seconds == 8) or (seconds == 6) or (seconds == 4) or (seconds == 2) then
		SKIN:Bang('[Play "#L10SSound#"]')
		end	
		
		if (nTime <= 0) and (numbertime == 1) then

			if (dateset == 0) and (looping == 1) then
				timerTime = 1 + counterSetTime + os.time()
				SKIN:Bang('!WriteKeyValue','Variables', 'CurrentTimerTime', timerTime, "Options/options.inc")
			else
				SKIN:Bang('!WriteKeyValue','Variables', 'nTime', '0')
				SKIN:Bang('!SetVariable', 'nTime', '0')
				numberTime = 0
			end

			SKIN:Bang('[Play "#TZeroSound#"]')
			SKIN:Bang('"#URLinput#"')
			
			if (showdesktoponzero == 1) then
				SKIN:Bang('[Shell:::{3080F90D-D7AD-11D9-BD98-0000947B0257}]')
			end
			
			if (shutdownonzero == 1) then
				SKIN:Bang('[shutdown.exe /s /c "Countdown has reached zero. The computer is shutting down!"]')
			end
			
			if (useplayer == 1) then
				SKIN:Bang('"#Player#" #ExecFile#')
			else
				SKIN:Bang('"#ExecFile#"')
			end

		end
	end
   end) -- fin pcall
   if not ok then
      SKIN:Bang('!Log', tostring(err), 'Error')
   end
end -- function Update