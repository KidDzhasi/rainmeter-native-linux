function Initialize()
   timerTime = tonumber(SKIN:GetVariable('CountUpTimerTime')) or 0
   skinClamp = SKIN:GetVariable('SkinClampOn')
   showYears = SKIN:GetVariable('ShowYears')
   showMonths = SKIN:GetVariable('ShowMonths')
   showDays = SKIN:GetVariable('ShowDays')
   showHours = SKIN:GetVariable('ShowHours')
   showMinutes = SKIN:GetVariable('ShowMinutes')
   showSeconds = SKIN:GetVariable('ShowSeconds')
   showDesktopOnZero = SKIN:GetVariable('ShowDesktopOnZero')
   shutdownOnZero    = SKIN:GetVariable('ShutdownOnZero')
   usePlayer         = SKIN:GetVariable('UsePlayer')
end

function ShowOrHide()
   return SKIN:GetVariable('HideCountdown')
end

function GetXPos()
	local w = tonumber(SKIN:GetMeter('Seconds'):GetW())
	return w/2
end

function SaveTime(_isToday)
	local totaltime = 0
	
	if _isToday then
		totaltime = 0 + os.time()
	else
	    tYear   = SKIN:GetVariable('Year')
	    tMonth  = SKIN:GetVariable('Month')
	    tDay    = SKIN:GetVariable('Day')
	    tHour   = SKIN:GetVariable('Hour')
	    tMinute = SKIN:GetVariable('Minute')
	    tSecond = SKIN:GetVariable('Second')
	    local timeTbl = {month=tMonth, day=tDay, year=tYear, hour=tHour, min=tMinute, sec=tSecond}
		totaltime = os.time(timeTbl)
	end
	
	SKIN:Bang('!WriteKeyValue','Variables', 'CountUpTimerTime', totaltime, "Options/options.inc")
	timerTime = totaltime
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
   nTime = os.time() - timerTime
   
   if nTime < 0 then
	   nTime = 0
   end

   local avgDaysInMonth = 30 
   
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
   end) -- fin pcall
   if not ok then
      SKIN:Bang('!Log', tostring(err), 'Error')
   end
end -- function Update