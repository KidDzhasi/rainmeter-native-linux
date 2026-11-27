#!/usr/bin/env python3
"""
Generate 10 intensive, hardware-accelerated Trad Desktop suites and .rmskin packages
modeled after the 10 reference designs, complete with 20-band real-time PipeWire/PulseAudio
spectrum visualizers, MPRIS2 media controls, live Open-Meteo/met.no weather, radial Roundline
gauges, and multi-shape vector HUDs.
"""

import os
import zipfile

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITES_DIR = os.path.join(REPO_DIR, "suites")
COMMUNITY_DIR = os.path.join(REPO_DIR, "community")


def make_audio_measures(bands=20, attack=28, decay=155, sensitivity=44):
    lines = [
        "[MeasureAudio]",
        "Measure=Plugin",
        "Plugin=AudioLevel",
        "FFTSize=1024",
        f"Bands={bands}",
        f"FFTAttack={attack}",
        f"FFTDecay={decay}",
        f"Sensitivity={sensitivity}",
        "",
    ]
    for b in range(bands):
        lines.extend(
            [
                f"[MeasureBand{b}]",
                "Measure=Plugin",
                "Plugin=AudioLevel",
                "Parent=MeasureAudio",
                "Type=Band",
                f"BandIdx={b}",
                "",
            ]
        )
    return "\n".join(lines)


def make_common_measures():
    return """[Variables]
@include=../../widgets/Theme.inc
@include2=../../widgets/Weather.inc
@include3=../../widgets/Notes.inc
AccentColor=0,210,255,255
TextColor=240,246,255,255
SubTextColor=175,190,215,240
TrackColor=32,38,52,220

[MeasureTime]
Measure=Time
Format=%H:%M

[MeasureTime12]
Measure=Time
Format=%I:%M %p

[MeasureTime12Short]
Measure=Time
Format=%I:%M

[MeasureHour]
Measure=Time
Format=%H

[MeasureHour12]
Measure=Time
Format=%I

[MeasureMinute]
Measure=Time
Format=%M

[MeasureSecond]
Measure=Time
Format=%S
MaxValue=60

[MeasureAMPM]
Measure=Time
Format=%p

[MeasureWeekday]
Measure=Time
Format=%A

[MeasureWeekdayShort]
Measure=Time
Format=%a

[MeasureDay]
Measure=Time
Format=%d

[MeasureMonth]
Measure=Time
Format=%B

[MeasureMonthShort]
Measure=Time
Format=%b

[MeasureMonthUpper]
Measure=Time
Format=%b

[MeasureDateSlash]
Measure=Time
Format=%d/%m/%Y

[MeasureYear]
Measure=Time
Format=%Y

[MeasureCPU]
Measure=CPU

[MeasureRAM]
Measure=PhysicalMemory

[MeasureSWAP]
Measure=SwapMemory

[MeasureTemp]
Measure=Plugin
Plugin=CoreTemp

[MeasureRoot]
Measure=FreeDiskSpace
Drive=/

[MeasureHome]
Measure=FreeDiskSpace
Drive=/home

[MeasureNetIn]
Measure=NetIn

[MeasureNetOut]
Measure=NetOut

[MeasureNetInKB]
Measure=Calc
Formula=MeasureNetIn / 1024

[MeasureNetOutKB]
Measure=Calc
Formula=MeasureNetOut / 1024

[MeasureBattery]
Measure=Battery

[MeasureWeatherTemp]
Measure=Weather
Type=Temperature

[MeasureWeatherUnit]
Measure=Weather
Type=TempUnit

[MeasureWeatherCond]
Measure=Weather
Type=Condition

[MeasureWeatherHigh]
Measure=Weather
Type=High

[MeasureWeatherLow]
Measure=Weather
Type=Low

[MeasureWeatherFeels]
Measure=Weather
Type=FeelsLike

[MeasureWeatherHum]
Measure=Weather
Type=Humidity

[MeasureWeatherRain]
Measure=Weather
Type=RainChance

[MeasureWeatherWind]
Measure=Weather
Type=WindSpeed

[MeasureWeatherSpeedUnit]
Measure=Weather
Type=SpeedUnit

[MeasureWeatherDir]
Measure=Weather
Type=WindDirection

[MeasureTrack]
Measure=Plugin
Plugin=NowPlaying
PlayerType=Title

[MeasureArtist]
Measure=Plugin
Plugin=NowPlaying
PlayerType=Artist

[MeasureAlbum]
Measure=Plugin
Plugin=NowPlaying
PlayerType=Album

[MeasureCover]
Measure=Plugin
Plugin=NowPlaying
PlayerType=Cover

[MeasurePlayIcon]
Measure=Plugin
Plugin=NowPlaying
PlayerType=StateButton

[MeasureIsPlaying]
Measure=Plugin
Plugin=NowPlaying
PlayerType=IsPlaying

[MeasureIsPaused]
Measure=Plugin
Plugin=NowPlaying
PlayerType=IsPaused

[MeasureProgress]
Measure=Plugin
Plugin=NowPlaying
PlayerType=Progress
MaxValue=100

[MeasurePosition]
Measure=Plugin
Plugin=NowPlaying
PlayerType=Position

[MeasureDuration]
Measure=Plugin
Plugin=NowPlaying
PlayerType=Duration
"""


# =============================================================================
# 1. MidnightDeerSuite (Photo 1: Midnight Bento Cards + Waveform + Moon Halo + Dock)
# =============================================================================
def build_midnight_deer():
    wave_bars = []
    # 16 symmetric center-out waveform bars inside the dark album square (x=104..186, center_y=414)
    for i in range(16):
        bx = 109 + i * 5
        wave_bars.append(
            f"""[MeterWaveBar{i}]
Meter=Bar
MeasureName=MeasureBand{i}
X={bx}
Y=390
W=3
H=48
BarOrientation=Vertical
BarColor=230,236,248,240
SolidColor=30,38,58,120
"""
        )
    return f"""[Rainmeter]
Update=33
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=1366
SkinHeight=768
AutoFit=1

[Metadata]
Name=MidnightDeerSuite
Author=Trad Desktop
Information=Midnight Navy Bento Suite with Symmetric Waveform Visualizer, Lunar Centerpiece, Telemetry Cards & Bottom Dock

{make_common_measures()}
{make_audio_measures(20, 26, 150, 45)}

; --- CENTER LUNAR HALO & MINIMALIST DEER SILHOUETTE ---
[MeterLunarHalo]
Meter=Shape
X=0
Y=0
Shape=Ellipse 683,395,210,210 | Fill Color 24,52,96,42 | StrokeWidth 0
Shape2=Ellipse 683,395,172,172 | Fill Color 38,78,136,58 | StrokeWidth 0
Shape3=Ellipse 683,395,136,136 | Fill Color 65,118,185,78 | StrokeWidth 0
Shape4=Ellipse 683,395,104,104 | Fill Color 228,238,255,235 | StrokeWidth 2 | Stroke Color 255,255,255,180
Shape5=Ellipse 683,545,270,58 | Fill Color 7,17,38,245 | StrokeWidth 1.5 | Stroke Color 55,105,175,120
; Stylized deer silhouette on lunar hill
Shape6=Polygon 640,492, 646,455, 672,448, 686,420, 694,424, 686,458, 678,492, 673,492, 675,468, 650,468, 645,492 | Fill Color 10,22,46,255 | StrokeWidth 0
Shape7=Line 690,422,704,402 | StrokeWidth 2.5 | Stroke Color 10,22,46,255
Shape8=Line 690,422,680,400 | StrokeWidth 2.5 | Stroke Color 10,22,46,255
Shape9=Line 697,412,708,410 | StrokeWidth 2 | Stroke Color 10,22,46,255
Shape10=Line 684,409,673,407 | StrokeWidth 2 | Stroke Color 10,22,46,255

; --- LEFT BENTO CARDS ---
[MeterLeftBento]
Meter=Shape
X=0
Y=0
; Time & Date Card
Shape=Rectangle 98,262,186,96,16 | Fill Color 34,44,72,225 | StrokeWidth 1.5 | Stroke Color 72,92,138,140
; Weather Card
Shape2=Rectangle 296,262,84,96,16 | Fill Color 34,44,72,225 | StrokeWidth 1.5 | Stroke Color 72,92,138,140
; Waveform Dark Box
Shape3=Rectangle 98,370,88,88,14 | Fill Color 16,20,30,240 | StrokeWidth 1.5 | Stroke Color 65,85,125,140
; Now Playing Card
Shape4=Rectangle 198,370,182,88,14 | Fill Color 34,44,72,225 | StrokeWidth 1.5 | Stroke Color 72,92,138,140
; Media Transport Pill
Shape5=Rectangle 98,472,164,40,18 | Fill Color 34,44,72,225 | StrokeWidth 1.5 | Stroke Color 72,92,138,140
; Storage / Trash Pill
Shape6=Rectangle 274,472,106,40,18 | Fill Color 34,44,72,225 | StrokeWidth 1.5 | Stroke Color 72,92,138,140
; Weather Cloud Icon
Shape7=Ellipse 332,296,12,10 | Fill Color 242,246,255,245 | StrokeWidth 0
Shape8=Ellipse 344,299,10,8 | Fill Color 242,246,255,245 | StrokeWidth 0
Shape9=Ellipse 322,300,9,7 | Fill Color 242,246,255,245 | StrokeWidth 0
Shape10=Rectangle 322,299,24,8,4 | Fill Color 242,246,255,245 | StrokeWidth 0

[MeterDayShort]
Meter=String
MeasureName=MeasureWeekdayShort
X=116
Y=282
W=160
H=32
FontFace=Serif
FontSize=18
FontColor=245,248,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterTime12]
Meter=String
MeasureName=MeasureTime12
X=268
Y=286
StringAlign=Right
FontFace=Sans
FontSize=14
FontColor=245,248,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterMonthName]
Meter=String
MeasureName=MeasureMonthShort
X=116
Y=324
W=160
H=24
FontFace=Sans
FontSize=11
FontColor=165,180,210,235
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterFullDate]
Meter=String
MeasureName=MeasureDateSlash
X=268
Y=325
StringAlign=Right
FontFace=Sans
FontSize=10
FontColor=165,180,210,235
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterWeatherTempVal]
Meter=String
MeasureName=MeasureWeatherTemp
MeasureName2=MeasureWeatherUnit
X=338
Y=272
W=84
H=86
StringAlign=Center
FontFace=Sans
FontSize=13
FontColor=235,242,255,255
Text="#CRLF##CRLF#%1%2"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

{"".join(wave_bars)}

[MeterListeningHdr]
Meter=String
X=212
Y=384
W=160
H=20
FontFace=Serif
FontSize=10
FontColor=220,230,250,240
Text="You're Listening :"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterNowTrack]
Meter=String
MeasureName=MeasureTrack
X=212
Y=408
W=156
H=18
ClipString=1
FontFace=Sans
FontSize=10
FontColor=255,255,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterNowArtist]
Meter=String
MeasureName=MeasureArtist
X=212
Y=430
W=156
H=16
ClipString=1
FontFace=Sans
FontSize=8
FontColor=148,165,198,235
Text="BY : %1"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterBtnPrev]
Meter=Shape
X=114
Y=479
W=26
H=26
Shape=Rectangle 4,6,2.5,14,1 | Fill Color 240,246,255,255 | StrokeWidth 0
Shape2=Polygon 8,13, 20,6, 20,20 | Fill Color 240,246,255,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Previous"]

[MeterBtnPlay]
Meter=Shape
X=167
Y=479
W=26
H=26
Hidden=[MeasureIsPlaying]
Shape=Polygon 20,13, 8,6, 8,20 | Fill Color 240,246,255,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterBtnPause]
Meter=Shape
X=167
Y=479
W=26
H=26
Hidden=[MeasureIsPaused]
Shape=Rectangle 7,6,3.5,14,1 | Fill Color 240,246,255,255 | StrokeWidth 0
Shape2=Rectangle 15,6,3.5,14,1 | Fill Color 240,246,255,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterBtnNext]
Meter=Shape
X=221
Y=479
W=26
H=26
Shape=Polygon 18,13, 6,6, 6,20 | Fill Color 240,246,255,255 | StrokeWidth 0
Shape2=Rectangle 19.5,6,2.5,14,1 | Fill Color 240,246,255,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Next"]

[MeterDiskPillText]
Meter=String
MeasureName=MeasureRoot
X=327
Y=483
W=106
H=32
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=235,242,255,245
Text="Disk %1%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

; --- RIGHT BENTO CARDS (STICKY NOTES ART CARD + TELEMETRY + POWER PILL) ---
[MeterRightBento]
Meter=Shape
X=0
Y=0
; White Art & Sticky Note Card
Shape=Rectangle 994,262,122,250,16 | Fill Color 238,241,246,245 | StrokeWidth 1.5 | Stroke Color 180,195,220,180
; Stylized minimal anime/character silhouette accents at bottom of art card
Shape2=Ellipse 1030,442,16,16 | Fill Color 28,34,48,245 | StrokeWidth 0
Shape3=Rectangle 1018,460,24,50,6 | Fill Color 28,34,48,245 | StrokeWidth 0
Shape4=Ellipse 1078,446,15,15 | Fill Color 28,34,48,245 | StrokeWidth 0
Shape5=Rectangle 1066,463,24,47,6 | Fill Color 28,34,48,245 | StrokeWidth 0
; Right System Card
Shape6=Rectangle 1128,262,142,196,16 | Fill Color 34,44,72,225 | StrokeWidth 1.5 | Stroke Color 72,92,138,140
; Bottom Right Action Pill
Shape7=Rectangle 1128,472,142,40,18 | Fill Color 34,44,72,225 | StrokeWidth 1.5 | Stroke Color 72,92,138,140

[MeterArtCardNoteHdr]
Meter=String
X=1055
Y=276
W=112
H=20
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=28,34,48,245
Text="#NoteTitle#"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterArtCardNoteBody]
Meter=String
X=1004
Y=302
W=102
H=120
ClipString=2
FontFace=Sans
FontSize=8
FontColor=45,55,75,235
Text="#NoteBody#"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterRootHdr]
Meter=String
MeasureName=MeasureRoot
X=1144
Y=282
FontFace=Sans
FontSize=10
FontColor=240,246,255,255
Text="ROOT : %1%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "/"]

[MeterRootBar]
Meter=Bar
MeasureName=MeasureRoot
X=1144
Y=306
W=110
H=6
BarOrientation=Horizontal
BarColor=135,175,250,255
SolidColor=22,28,46,220

[MeterHomeHdr]
Meter=String
MeasureName=MeasureHome
X=1144
Y=332
FontFace=Sans
FontSize=10
FontColor=240,246,255,255
Text="HOME : %1%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

[MeterHomeBar]
Meter=Bar
MeasureName=MeasureHome
X=1144
Y=356
W=110
H=6
BarOrientation=Horizontal
BarColor=135,175,250,255
SolidColor=22,28,46,220

[MeterBattHdr]
Meter=String
MeasureName=MeasureRAM
X=1144
Y=384
FontFace=Sans
FontSize=10
FontColor=240,246,255,255
Text="RAM : %1%"
AntiAlias=1

[MeterBattBar]
Meter=Bar
MeasureName=MeasureRAM
X=1144
Y=408
W=110
H=6
BarOrientation=Horizontal
BarColor=135,175,250,255
SolidColor=22,28,46,220

[MeterQuickAct1]
Meter=String
X=1154
Y=484
W=42
H=28
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=235,242,255,245
Text="NOTE"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterQuickAct2]
Meter=String
X=1199
Y=484
W=42
H=28
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=235,242,255,245
Text="CFG"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

[MeterQuickAct3]
Meter=String
X=1244
Y=484
W=42
H=28
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=235,242,255,245
Text="RLD"
AntiAlias=1
LeftMouseUpAction=[!Refresh]

; --- BOTTOM CENTER FLOATING DOCK ---
[MeterBottomDock]
Meter=Shape
X=0
Y=0
Shape=Rectangle 478,614,410,72,22 | Fill Color 42,54,84,215 | StrokeWidth 1.5 | Stroke Color 92,115,165,145
Shape2=Rectangle 500,627,46,46,12 | Fill Color 125,142,175,145 | StrokeWidth 1 | Stroke Color 180,198,235,120
Shape3=Rectangle 562,627,46,46,12 | Fill Color 125,142,175,145 | StrokeWidth 1 | Stroke Color 180,198,235,120
Shape4=Rectangle 624,627,46,46,12 | Fill Color 125,142,175,145 | StrokeWidth 1 | Stroke Color 180,198,235,120
Shape5=Rectangle 686,627,46,46,12 | Fill Color 125,142,175,145 | StrokeWidth 1 | Stroke Color 180,198,235,120
Shape6=Rectangle 748,627,46,46,12 | Fill Color 125,142,175,145 | StrokeWidth 1 | Stroke Color 180,198,235,120
Shape7=Rectangle 810,627,46,46,12 | Fill Color 125,142,175,145 | StrokeWidth 1 | Stroke Color 180,198,235,120
; Vector icons inside the 6 dock buttons
; 1. PC Monitor icon
Shape8=Rectangle 513,639,20,14,2 | Fill Color 0,0,0,0 | StrokeWidth 2 | Stroke Color 24,32,52,255
Shape9=Line 518,657,528,657 | StrokeWidth 2 | Stroke Color 24,32,52,255
; 2. Settings Gear circle
Shape10=Ellipse 585,650,8,8 | Fill Color 0,0,0,0 | StrokeWidth 2.2 | Stroke Color 24,32,52,255
Shape11=Ellipse 585,650,3,3 | Fill Color 24,32,52,255 | StrokeWidth 0
; 3. Web Globe icon
Shape12=Ellipse 647,650,9,9 | Fill Color 0,0,0,0 | StrokeWidth 2 | Stroke Color 24,32,52,255
Shape13=Line 638,650,656,650 | StrokeWidth 1.5 | Stroke Color 24,32,52,255
; 4. Headphones / Audio icon
Shape14=Arc 709,650,9,-180,180 | Fill Color 0,0,0,0 | StrokeWidth 2 | Stroke Color 24,32,52,255
Shape15=Rectangle 699,649,4,8,2 | Fill Color 24,32,52,255 | StrokeWidth 0
Shape16=Rectangle 715,649,4,8,2 | Fill Color 24,32,52,255 | StrokeWidth 0
; 5. Sticky Notes / Chat icon
Shape17=Rectangle 761,640,20,18,4 | Fill Color 0,0,0,0 | StrokeWidth 2 | Stroke Color 24,32,52,255
Shape18=Line 765,646,777,646 | StrokeWidth 1.5 | Stroke Color 24,32,52,255
Shape19=Line 765,651,774,651 | StrokeWidth 1.5 | Stroke Color 24,32,52,255
; 6. Sliders / Weather icon
Shape20=Line 826,641,826,659 | StrokeWidth 2 | Stroke Color 24,32,52,255
Shape21=Line 833,641,833,659 | StrokeWidth 2 | Stroke Color 24,32,52,255
Shape22=Line 840,641,840,659 | StrokeWidth 2 | Stroke Color 24,32,52,255

[MeterDockIcon1]
Meter=String
X=500
Y=627
W=46
H=46
Text=" "
LeftMouseUpAction=["xdg-open" "~"]

[MeterDockIcon2]
Meter=String
X=562
Y=627
W=46
H=46
Text=" "
LeftMouseUpAction=[!OpenControlCenter]

[MeterDockIcon3]
Meter=String
X=624
Y=627
W=46
H=46
Text=" "
LeftMouseUpAction=["xdg-open" "https://github.com/KidDzhasi/Trad-Desktop"]

[MeterDockIcon4]
Meter=String
X=686
Y=627
W=46
H=46
Text=" "
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterDockIcon5]
Meter=String
X=748
Y=627
W=46
H=46
Text=" "
LeftMouseUpAction=[!NotesPopup]

[MeterDockIcon6]
Meter=String
X=810
Y=627
W=46
H=46
Text=" "
LeftMouseUpAction=[!WeatherPopup]
"""


# =============================================================================
# 2. MaterialPillSuite (Photo 2: 4-Color Left Bar + Stacked Clock + Colorful Pills)
# =============================================================================
def build_material_pill_suite():
    return f"""[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=1366
SkinHeight=768
AutoFit=1

[Metadata]
Name=MaterialPillSuite
Author=Trad Desktop
Information=Minimalist Stacked Clock, 4-Color Side Ribbon & Colorful Material Telemetry Toggle Pills

{make_common_measures()}

; --- LEFT 4-COLOR RIBBON & FLOATING ACTION SQUARES ---
[MeterLeftRibbon]
Meter=Shape
X=0
Y=0
Shape=Rectangle 0,0,16,192,0 | Fill Color 30,115,215,255 | StrokeWidth 0
Shape2=Rectangle 0,192,16,192,0 | Fill Color 229,57,53,255 | StrokeWidth 0
Shape3=Rectangle 0,384,16,192,0 | Fill Color 251,192,45,255 | StrokeWidth 0
Shape4=Rectangle 0,576,16,192,0 | Fill Color 67,160,71,255 | StrokeWidth 0
; 4 Floating Icon Badges
Shape5=Rectangle 44,120,34,34,6 | Fill Color 30,115,215,245 | StrokeWidth 0
Shape6=Rectangle 44,280,34,34,6 | Fill Color 229,57,53,245 | StrokeWidth 0
Shape7=Rectangle 44,440,34,34,6 | Fill Color 251,192,45,245 | StrokeWidth 0
Shape8=Rectangle 44,600,34,34,6 | Fill Color 67,160,71,245 | StrokeWidth 0
; Vector icons inside the 4 floating badges
Shape9=Rectangle 52,128,18,12,2 | Fill Color 0,0,0,0 | StrokeWidth 2 | Stroke Color 255,255,255,255
Shape10=Line 56,144,66,144 | StrokeWidth 2 | Stroke Color 255,255,255,255
Shape11=Rectangle 52,289,18,15,2 | Fill Color 0,0,0,0 | StrokeWidth 2 | Stroke Color 255,255,255,255
Shape12=Line 55,294,67,294 | StrokeWidth 1.5 | Stroke Color 255,255,255,255
; Beamed double music note icon (♫) inside yellow badge
Shape13=Ellipse 56,462,3.5,2.8 | Fill Color 255,255,255,255 | StrokeWidth 0
Shape14=Ellipse 65,460,3.5,2.8 | Fill Color 255,255,255,255 | StrokeWidth 0
Shape15=Line 59,462,59,449 | StrokeWidth 2 | Stroke Color 255,255,255,255
Shape16=Line 68,460,68,447 | StrokeWidth 2 | Stroke Color 255,255,255,255
Shape17=Line 59,449,68,447 | StrokeWidth 2.5 | Stroke Color 255,255,255,255
; Globe icon inside green badge
Shape18=Ellipse 61,617,9,9 | Fill Color 0,0,0,0 | StrokeWidth 2 | Stroke Color 255,255,255,255
Shape19=Line 52,617,70,617 | StrokeWidth 1.5 | Stroke Color 255,255,255,255
Shape20=Line 61,608,61,626 | StrokeWidth 1.5 | Stroke Color 255,255,255,255

[MeterSideBtn1]
Meter=String
X=44
Y=120
W=34
H=34
Text=" "
LeftMouseUpAction=[!OpenControlCenter]

[MeterSideBtn2]
Meter=String
X=44
Y=280
W=34
H=34
Text=" "
LeftMouseUpAction=["xdg-open" "~"]

[MeterSideBtn3]
Meter=String
X=44
Y=440
W=34
H=34
Text=" "
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterSideBtn4]
Meter=String
X=44
Y=600
W=34
H=34
Text=" "
LeftMouseUpAction=[!WeatherPopup]

; --- CENTER-LEFT STACKED CLOCK & SYSTEM/USER ---
[MeterClockHour]
Meter=String
MeasureName=MeasureHour
X=480
Y=170
StringAlign=Center
FontFace=Sans
FontSize=24
FontColor=240,245,255,255
Text="%1"
AntiAlias=1

[MeterClockArrow]
Meter=String
X=480
Y=242
StringAlign=Center
FontFace=Sans
FontSize=26
FontColor=229,57,53,255
Text=">"
AntiAlias=1

[MeterClockMin]
Meter=String
MeasureName=MeasureMinute
X=480
Y=320
StringAlign=Center
FontFace=Sans
FontSize=24
FontColor=240,245,255,255
Text="%1"
AntiAlias=1

[MeterSysLabel]
Meter=String
X=425
Y=420
FontFace=Sans
FontSize=10
FontColor=190,200,220,240
Text="SYSTEM"
AntiAlias=1

[MeterSysVal]
Meter=String
X=455
Y=454
FontFace=Sans
FontSize=11
FontColor=229,57,53,255
Text="TradDesktopLinux"
AntiAlias=1

[MeterUserLabel]
Meter=String
X=425
Y=495
FontFace=Sans
FontSize=10
FontColor=190,200,220,240
Text="USER"
AntiAlias=1

[MeterUserVal]
Meter=String
MeasureName=MeasureWeatherTemp
MeasureName2=MeasureWeatherUnit
X=455
Y=528
W=260
H=24
FontFace=Sans
FontSize=11
FontColor=229,57,53,255
Text="#WeatherLocation# (%1%2)"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterNotesQuickLink]
Meter=String
X=425
Y=570
W=280
H=38
FontFace=Sans
FontSize=10
FontColor=190,200,220,240
Text="NOTES: #NoteLine1#"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

; --- RIGHT 2-COLUMN MATERIAL CAPSULE PILLS ---
[MeterPills]
Meter=Shape
X=0
Y=0
; Row 1: Pink Disk Home Pill & Green Date Pill
Shape=Rectangle 846,232,96,36,18 | Fill LinearGradient 0 | 236,64,122,245 | 171,71,188,245 | StrokeWidth 0
Shape2=Ellipse 924,250,15,15 | Fill Color 255,255,255,65 | StrokeWidth 1.5 | Stroke Color 255,255,255,180
Shape3=Rectangle 956,232,92,36,18 | Fill LinearGradient 0 | 46,125,50,245 | 102,187,106,245 | StrokeWidth 0
Shape4=Ellipse 1030,250,15,15 | Fill Color 255,255,255,65 | StrokeWidth 1.5 | Stroke Color 255,255,255,180

; Row 2: Purple CPU Pill & Amber RAM Pill
Shape5=Rectangle 792,278,150,36,18 | Fill LinearGradient 0 | 142,36,170,245 | 94,53,177,245 | StrokeWidth 0
Shape6=Ellipse 902,296,15,15 | Fill Color 255,255,255,65 | StrokeWidth 1.5 | Stroke Color 255,255,255,180
Shape7=Rectangle 956,278,150,36,18 | Fill LinearGradient 0 | 255,160,0,245 | 255,193,7,245 | StrokeWidth 0
Shape8=Ellipse 974,296,15,15 | Fill Color 255,255,255,65 | StrokeWidth 1.5 | Stroke Color 255,255,255,180

; Row 3: Cyan Disk Root Pill & Red Year Pill
Shape9=Rectangle 780,324,162,36,18 | Fill LinearGradient 0 | 41,182,246,245 | 2,136,209,245 | StrokeWidth 0
Shape10=Ellipse 924,342,15,15 | Fill Color 255,255,255,65 | StrokeWidth 1.5 | Stroke Color 255,255,255,180
Shape11=Rectangle 956,324,74,36,18 | Fill Color 229,57,53,245 | StrokeWidth 0

; Row 4: Net In & Net Out Silver Toggle Pills
Shape12=Rectangle 824,370,118,36,18 | Fill Color 220,224,232,235 | StrokeWidth 1 | Stroke Color 255,255,255,180
Shape13=Ellipse 868,388,15,15 | Fill Color 255,255,255,255 | StrokeWidth 0
Shape14=Rectangle 956,370,118,36,18 | Fill Color 220,224,232,235 | StrokeWidth 1 | Stroke Color 255,255,255,180
Shape15=Ellipse 974,388,15,15 | Fill Color 255,255,255,255 | StrokeWidth 0

; Row 5: Download & Upload Labels Pill
Shape16=Rectangle 786,416,156,36,18 | Fill Color 210,215,224,225 | StrokeWidth 0
Shape17=Ellipse 916,434,15,15 | Fill Color 255,255,255,255 | StrokeWidth 0
Shape18=Rectangle 956,416,142,36,18 | Fill Color 210,215,224,225 | StrokeWidth 0
Shape19=Ellipse 996,434,15,15 | Fill Color 255,255,255,255 | StrokeWidth 0

; Row 6: Power / Battery Pill
Shape20=Rectangle 846,462,96,36,18 | Fill Color 220,224,232,235 | StrokeWidth 0
Shape21=Ellipse 882,480,15,15 | Fill Color 255,255,255,255 | StrokeWidth 0
Shape22=Rectangle 956,462,118,36,18 | Fill Color 220,224,232,235 | StrokeWidth 0
Shape23=Ellipse 974,480,15,15 | Fill Color 255,255,255,255 | StrokeWidth 0

[MeterPillHomeLbl]
Meter=String
X=876
Y=242
W=96
H=32
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="Home"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

[MeterPillHomeVal]
Meter=String
MeasureName=MeasureHome
X=924
Y=242
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

[MeterPillMonthLbl]
Meter=String
MeasureName=MeasureMonthShort
X=988
Y=242
W=92
H=32
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterPillDayVal]
Meter=String
MeasureName=MeasureDay
X=1030
Y=242
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterPillCpuLbl]
Meter=String
X=840
Y=288
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=255,255,255,255
Text="Cpu"
AntiAlias=1

[MeterPillCpuVal]
Meter=String
MeasureName=MeasureCPU
X=902
Y=288
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="%1"
AntiAlias=1

[MeterPillRamVal]
Meter=String
MeasureName=MeasureRAM
X=974
Y=288
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="%1"
AntiAlias=1

[MeterPillRamLbl]
Meter=String
X=1036
Y=288
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=255,255,255,255
Text="Ram"
AntiAlias=1

[MeterPillRootLbl]
Meter=String
X=845
Y=334
W=140
H=32
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=255,255,255,255
Text="Disk /"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "/"]

[MeterPillRootVal]
Meter=String
MeasureName=MeasureRoot
X=924
Y=334
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "/"]

[MeterPillYearVal]
Meter=String
MeasureName=MeasureYear
X=993
Y=334
W=74
H=32
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=255,255,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterPillNetInVal]
Meter=String
MeasureName=MeasureNetInKB
X=904
Y=380
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=30,36,48,255
Text="%1 KB/s"
AntiAlias=1

[MeterPillNetOutVal]
Meter=String
MeasureName=MeasureNetOutKB
X=1025
Y=380
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=30,36,48,255
Text="%1 KB/s"
AntiAlias=1

[MeterPillDownLbl]
Meter=String
X=852
Y=426
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=30,36,48,255
Text="Download"
AntiAlias=1

[MeterPillUpLbl]
Meter=String
X=1046
Y=426
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=30,36,48,255
Text="Upload"
AntiAlias=1

[MeterPillBattVal]
Meter=String
X=918
Y=472
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=30,36,48,255
Text="100"
AntiAlias=1

[MeterPillAcLbl]
Meter=String
X=1028
Y=472
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=30,36,48,255
Text="AC Line"
AntiAlias=1
"""


# =============================================================================
# 3. XeniumDashboard (Photo 3: Modular Dark HUD + 20-Band Blue Visualizer + Rings)
# =============================================================================
def build_xenium_dashboard():
    spec_bars = []
    # 20 vertical spectrum bars inside the bottom-center panel (x=320..692, y=268..356)
    for b in range(20):
        bx = 334 + b * 18
        spec_bars.append(
            f"""[MeterXeniumBar{b}]
Meter=Bar
MeasureName=MeasureBand{b}
X={bx}
Y=272
W=4
H=82
BarOrientation=Vertical
BarColor=#AccentColor#
SolidColor=85,95,112,180
"""
        )
    return f"""[Rainmeter]
Update=33
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=940
SkinHeight=460
AutoFit=1

[Metadata]
Name=XeniumDashboard
Author=Trad Desktop
Information=XENIUM Modular Desktop Command Center with 20-Band Spectrum Visualizer, Weather Forecast, Media Player & Circular Rings

{make_common_measures()}
{make_audio_measures(20, 26, 150, 44)}

; --- MODULAR DARK SLATE PANELS & ACCENT BARS ---
[MeterXeniumPanels]
Meter=Shape
X=0
Y=0
; 1. Left XENIUM Sidebar
Shape=Rectangle 10,10,148,388,2 | Fill Color 34,38,44,235 | StrokeWidth 1 | Stroke Color 70,80,95,160
Shape2=Line 10,46,158,46 | StrokeWidth 2 | Stroke Color #AccentColor#
; 2. Top-Center Weather Panel
Shape3=Rectangle 170,10,378,132,2 | Fill Color 34,38,44,235 | StrokeWidth 1 | Stroke Color 70,80,95,160
Shape4=Line 170,144,548,144 | StrokeWidth 2 | Stroke Color #AccentColor#
; 3. Mid-Center 4-Day Mini Forecast Strip
Shape5=Rectangle 170,146,378,94,2 | Fill Color 34,38,44,235 | StrokeWidth 1 | Stroke Color 70,80,95,160
Shape6=Line 264,154,264,232 | StrokeWidth 1 | Stroke Color 75,85,100,150
Shape7=Line 359,154,359,232 | StrokeWidth 1 | Stroke Color 75,85,100,150
Shape8=Line 454,154,454,232 | StrokeWidth 1 | Stroke Color 75,85,100,150
; 4. Bottom-Left Digital Clock Box
Shape9=Rectangle 170,252,138,146,2 | Fill Color 34,38,44,235 | StrokeWidth 1 | Stroke Color 70,80,95,160
Shape10=Line 282,252,282,398 | StrokeWidth 2 | Stroke Color #AccentColor#
; 5. Bottom-Center 20-Band Visualizer & Track Box
Shape11=Rectangle 318,252,396,146,2 | Fill Color 34,38,44,235 | StrokeWidth 1 | Stroke Color 70,80,95,160
Shape12=Line 318,364,714,364 | StrokeWidth 2 | Stroke Color #AccentColor#
; 6. Top-Right Media Art & Transport Box
Shape13=Rectangle 560,10,154,230,2 | Fill Color 34,38,44,235 | StrokeWidth 1 | Stroke Color 70,80,95,160
Shape14=Rectangle 568,18,138,176,2 | Fill LinearGradient 135 | 25,65,98,240 | 14,24,42,245 | StrokeWidth 1 | Stroke Color #AccentColor#
Shape15=Line 560,202,714,202 | StrokeWidth 2 | Stroke Color #AccentColor#
; Vector music note fallback emblem inside Media Art Box (shown behind cover art when no art is loaded)
Shape16=Ellipse 637,96,28,28 | Fill Color 16,24,38,200 | StrokeWidth 1.5 | Stroke Color #AccentColor#
Shape17=Ellipse 630,103,4.5,3.5 | Fill Color #AccentColor# | StrokeWidth 0
Shape18=Ellipse 644,100,4.5,3.5 | Fill Color #AccentColor# | StrokeWidth 0
Shape19=Line 634,103,634,86 | StrokeWidth 2.2 | Stroke Color #AccentColor#
Shape20=Line 648,100,648,83 | StrokeWidth 2.2 | Stroke Color #AccentColor#
Shape21=Line 634,86,648,83 | StrokeWidth 3 | Stroke Color #AccentColor#
; 7. Right SYSTEM Telemetry Sidebar
Shape22=Rectangle 726,10,204,388,2 | Fill Color 34,38,44,235 | StrokeWidth 1 | Stroke Color 70,80,95,160
Shape23=Line 726,46,930,46 | StrokeWidth 2 | Stroke Color #AccentColor#
; 8. Bottom Full-Width Quick Links Bar
Shape24=Rectangle 10,408,920,40,2 | Fill Color 34,38,44,235 | StrokeWidth 1 | Stroke Color 70,80,95,160
Shape25=Line 815,408,815,448 | StrokeWidth 2 | Stroke Color #AccentColor#
; Weather Sun Vector Icon in Top-Center Panel
Shape26=Ellipse 235,76,22,22 | Fill Color 0,0,0,0 | StrokeWidth 2 | Stroke Color 240,248,255,245
Shape27=Line 235,44,235,34 | StrokeWidth 2 | Stroke Color 240,248,255,245
Shape28=Line 235,108,235,118 | StrokeWidth 2 | Stroke Color 240,248,255,245
Shape29=Line 203,76,193,76 | StrokeWidth 2 | Stroke Color 240,248,255,245
Shape30=Line 267,76,277,76 | StrokeWidth 2 | Stroke Color 240,248,255,245
Shape31=Line 212,53,205,46 | StrokeWidth 2 | Stroke Color 240,248,255,245
Shape32=Line 258,99,265,106 | StrokeWidth 2 | Stroke Color 240,248,255,245
Shape33=Line 258,53,265,46 | StrokeWidth 2 | Stroke Color 240,248,255,245
Shape34=Line 212,99,205,106 | StrokeWidth 2 | Stroke Color 240,248,255,245

; --- LEFT SIDEBAR CONTENT ---
[MeterXeniumTitle]
Meter=String
X=24
Y=20
FontFace=Sans
FontSize=11
FontColor=240,246,255,255
Text="X E N I U M"
AntiAlias=1

[MeterXeniumOS]
Meter=String
X=24
Y=58
FontFace=Sans
FontSize=8
FontColor=0,195,255,255
Text="TRAD DESKTOP / LINUX"
AntiAlias=1

[MeterXeniumBuild]
Meter=String
X=24
Y=74
FontFace=Sans
FontSize=8
FontColor=0,195,255,235
Text="GNOME Wayland v1.2"
AntiAlias=1

[MeterNav1]
Meter=String
X=24
Y=112
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=230,236,245,245
Text=">  This PC"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "/"]

[MeterNav2]
Meter=String
X=24
Y=140
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=230,236,245,245
Text=">  Documents"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~/Documents"]

[MeterNav3]
Meter=String
X=24
Y=168
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=230,236,245,245
Text=">  Downloads"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~/Downloads"]

[MeterNav4]
Meter=String
X=24
Y=196
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=230,236,245,245
Text=">  Music"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~/Music"]

[MeterNav5]
Meter=String
X=24
Y=224
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=230,236,245,245
Text=">  Pictures"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~/Pictures"]

[MeterNav6]
Meter=String
X=24
Y=252
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=230,236,245,245
Text=">  Videos"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~/Videos"]

[MeterNavNotes]
Meter=String
X=24
Y=288
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=0,195,255,255
Text="*  Sticky Notes"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterNav7]
Meter=String
X=24
Y=324
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=230,236,245,245
Text="*  Control Center"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

[MeterNav8]
Meter=String
X=24
Y=352
W=126
H=24
FontFace=Sans
FontSize=9
FontColor=230,236,245,245
Text="*  Weather Studio"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

; --- TOP-CENTER WEATHER CONTENT ---
[MeterXenTemp]
Meter=String
MeasureName=MeasureWeatherTemp
MeasureName2=MeasureWeatherUnit
X=348
Y=32
W=120
H=48
StringAlign=Center
FontFace=Sans
FontSize=28
FontColor=255,255,255,255
Text="%1%2"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterXenCond]
Meter=String
MeasureName=MeasureWeatherCond
X=348
Y=88
W=140
H=24
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=220,230,245,245
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterXenFeels]
Meter=String
MeasureName=MeasureWeatherFeels
MeasureName2=MeasureWeatherUnit
X=420
Y=44
W=120
H=20
FontFace=Sans
FontSize=8
FontColor=200,212,230,240
Text="Feels Like:       %1%2"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterXenHum]
Meter=String
MeasureName=MeasureWeatherHum
X=420
Y=68
W=120
H=20
FontFace=Sans
FontSize=8
FontColor=200,212,230,240
Text="Humidity:         %1%"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterXenWind]
Meter=String
MeasureName=MeasureWeatherWind
MeasureName2=MeasureWeatherDir
MeasureName3=MeasureWeatherSpeedUnit
X=420
Y=92
W=124
H=20
FontFace=Sans
FontSize=8
FontColor=200,212,230,240
Text="Wind:     %2 %1 %3"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

; 4-Column Forecast Strip
[MeterFc1]
Meter=String
MeasureName=MeasureWeatherHigh
MeasureName2=MeasureWeatherLow
MeasureName3=MeasureWeatherUnit
X=217
Y=164
W=88
H=34
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=240,246,255,255
Text="%1%3 / %2%3"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterFc1Lbl]
Meter=String
X=217
Y=204
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=180,195,215,240
Text="Today"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterFc2]
Meter=String
MeasureName=MeasureWeatherHigh
MeasureName2=MeasureWeatherLow
MeasureName3=MeasureWeatherUnit
X=312
Y=164
W=88
H=34
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=240,246,255,255
Text="%1%3 / %2%3"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterFc2Lbl]
Meter=String
X=312
Y=204
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=180,195,215,240
Text="Tomorrow"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterFc3]
Meter=String
MeasureName=MeasureWeatherRain
X=406
Y=164
W=88
H=34
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=240,246,255,255
Text="Rain %1%"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterFc3Lbl]
Meter=String
X=406
Y=204
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=180,195,215,240
Text="Precipitation"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterFc4]
Meter=String
X=501
Y=164
W=88
H=34
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=0,195,255,255
Text="7-Day Forecast"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterFc4Lbl]
Meter=String
X=458
Y=204
W=86
H=18
ClipString=1
StringAlign=Left
FontFace=Sans
FontSize=8
FontColor=180,195,215,240
Text="#WeatherLocation#"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

; --- BOTTOM-LEFT CLOCK BOX ---
[MeterXenClock]
Meter=String
MeasureName=MeasureTime
X=226
Y=278
W=100
H=38
StringAlign=Center
FontFace=Sans
FontSize=24
FontColor=255,255,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterXenWeekday]
Meter=String
MeasureName=MeasureWeekday
X=226
Y=326
W=100
H=24
StringAlign=Center
FontFace=Sans
FontSize=11
FontColor=225,235,250,245
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterXenDate]
Meter=String
MeasureName=MeasureDay
MeasureName2=MeasureMonthShort
X=226
Y=356
W=100
H=24
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=185,200,220,240
Text="%1 %2"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterXenYearVert]
Meter=String
MeasureName=MeasureYear
X=295
Y=315
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=0,195,255,245
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

; --- LIVE SONG / VIDEO THUMBNAIL & 20-BAND SPECTRUM VISUALIZER ---
[MeterXeniumCoverArt]
Meter=Image
MeasureName=MeasureCover
X=568
Y=18
W=138
H=176
PreserveAspectRatio=2
SolidColor=0,0,0,0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterXenPrev]
Meter=Shape
X=590
Y=209
W=24
H=24
Shape=Rectangle 4,6,2.2,12,1 | Fill Color 240,246,255,255 | StrokeWidth 0
Shape2=Polygon 7.5,12, 18,6, 18,18 | Fill Color 240,246,255,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Previous"]

[MeterXenPlay]
Meter=Shape
X=625
Y=209
W=24
H=24
Hidden=[MeasureIsPlaying]
Shape=Polygon 18,12, 7,6, 7,18 | Fill Color #AccentColor# | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterXenPause]
Meter=Shape
X=625
Y=209
W=24
H=24
Hidden=[MeasureIsPaused]
Shape=Rectangle 7,6,3.2,12,1 | Fill Color #AccentColor# | StrokeWidth 0
Shape2=Rectangle 14,6,3.2,12,1 | Fill Color #AccentColor# | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterXenNext]
Meter=Shape
X=660
Y=209
W=24
H=24
Shape=Polygon 16.5,12, 6,6, 6,18 | Fill Color 240,246,255,255 | StrokeWidth 0
Shape2=Rectangle 18,6,2.2,12,1 | Fill Color 240,246,255,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Next"]

{"".join(spec_bars)}

[MeterXenTrackFooter]
Meter=String
MeasureName=MeasureTrack
MeasureName2=MeasureArtist
X=516
Y=374
W=376
H=18
ClipString=1
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=240,246,255,255
Text="%1 - %2"
AntiAlias=1

; --- RIGHT SYSTEM TELEMETRY SIDEBAR ---
[MeterSysHeader]
Meter=String
X=742
Y=20
FontFace=Sans
FontSize=11
FontColor=240,246,255,255
Text="S Y S T E M"
AntiAlias=1

[MeterSysCpuLbl]
Meter=String
MeasureName=MeasureCPU
X=742
Y=66
FontFace=Sans
FontSize=8
FontColor=230,238,250,245
Text="CPU                        %1%"
AntiAlias=1

[MeterSysCpuBar]
Meter=Bar
MeasureName=MeasureCPU
X=742
Y=84
W=172
H=4
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=75,85,100,190

[MeterSysTempLbl]
Meter=String
MeasureName=MeasureTemp
X=742
Y=106
FontFace=Sans
FontSize=8
FontColor=230,238,250,245
Text="TEMP                      %1°C"
AntiAlias=1

[MeterSysTempBar]
Meter=Bar
MeasureName=MeasureTemp
X=742
Y=124
W=172
H=4
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=75,85,100,190

[MeterSysRamLbl]
Meter=String
MeasureName=MeasureRAM
X=742
Y=146
FontFace=Sans
FontSize=8
FontColor=230,238,250,245
Text="RAM                        %1%"
AntiAlias=1

[MeterSysRamBar]
Meter=Bar
MeasureName=MeasureRAM
X=742
Y=164
W=172
H=4
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=75,85,100,190

[MeterSysRootLbl]
Meter=String
MeasureName=MeasureRoot
X=742
Y=186
FontFace=Sans
FontSize=8
FontColor=230,238,250,245
Text="ROOT /                    %1%"
AntiAlias=1

[MeterSysRootBar]
Meter=Bar
MeasureName=MeasureRoot
X=742
Y=204
W=172
H=4
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=75,85,100,190

[MeterSysHomeLbl]
Meter=String
MeasureName=MeasureHome
X=742
Y=226
FontFace=Sans
FontSize=8
FontColor=230,238,250,245
Text="HOME                      %1%"
AntiAlias=1

[MeterSysHomeBar]
Meter=Bar
MeasureName=MeasureHome
X=742
Y=244
W=172
H=4
BarOrientation=Horizontal
BarColor=#AccentColor#
SolidColor=75,85,100,190

; Bottom Dual Circular Ring Gauges in SYSTEM Sidebar
[MeterRingTrack1]
Meter=Roundline
X=744
Y=278
W=76
H=76
StartAngle=2.356
RotationAngle=4.712
LineStart=28
LineLength=35
Solid=1
LineColor=75,85,100,180

[MeterRingFill1]
Meter=Roundline
MeasureName=MeasureCPU
X=744
Y=278
W=76
H=76
StartAngle=2.356
RotationAngle=4.712
LineStart=28
LineLength=35
Solid=1
LineColor=#AccentColor#

[MeterRingVal1]
Meter=String
MeasureName=MeasureTemp
X=782
Y=308
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="%1°C"
AntiAlias=1

[MeterRingCap1]
Meter=String
X=782
Y=362
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=200,212,230,240
Text="CPU"
AntiAlias=1

[MeterRingTrack2]
Meter=Roundline
X=836
Y=278
W=76
H=76
StartAngle=2.356
RotationAngle=4.712
LineStart=28
LineLength=35
Solid=1
LineColor=75,85,100,180

[MeterRingFill2]
Meter=Roundline
MeasureName=MeasureRAM
X=836
Y=278
W=76
H=76
StartAngle=2.356
RotationAngle=4.712
LineStart=28
LineLength=35
Solid=1
LineColor=#AccentColor#

[MeterRingVal2]
Meter=String
MeasureName=MeasureRAM
X=874
Y=308
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=255,255,255,255
Text="%1%"
AntiAlias=1

[MeterRingCap2]
Meter=String
X=874
Y=362
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=200,212,230,240
Text="RAM"
AntiAlias=1

; --- BOTTOM QUICK LINKS BAR (INDIVIDUALLY CLICKABLE) ---
[MeterBottomLink1]
Meter=String
X=72
Y=421
W=86
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=225,235,248,240
Text="YouTube"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "https://www.youtube.com"]

[MeterBottomLink2]
Meter=String
X=172
Y=421
W=86
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=225,235,248,240
Text="GitHub"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "https://github.com/KidDzhasi/Trad-Desktop"]

[MeterBottomLink3]
Meter=String
X=278
Y=421
W=96
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=225,235,248,240
Text="DeviantArt"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "https://www.deviantart.com"]

[MeterBottomLink4]
Meter=String
X=394
Y=421
W=96
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=225,235,248,240
Text="Google Search"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "https://www.google.com"]

[MeterBottomLink5]
Meter=String
X=508
Y=421
W=96
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=0,195,255,255
Text="Sticky Notes"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterBottomLink6]
Meter=String
X=624
Y=421
W=106
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=225,235,248,240
Text="Weather Studio"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterBottomLink7]
Meter=String
X=746
Y=421
W=106
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=225,235,248,240
Text="Control Center"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

[MeterBottomIcons]
Meter=String
X=872
Y=421
W=96
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=0,195,255,255
Text="CAL  |  RLD"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]
"""


# =============================================================================
# 4. GreenRibbonSuite — Full 9-Panel Intensive Monolith Edition (Photo 4)
# =============================================================================
def build_green_ribbon_pro():
    return f"""[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=1120
SkinHeight=560
AutoFit=1

[Metadata]
Name=GreenRibbonSuite
Author=Trad Desktop
Information=9-Panel Charcoal Monolith Suite with Sweeping 3D Lime-Green & Cyan Ribbon Wave

{make_common_measures()}

; --- 9 CHARCOAL MONOLITH CARDS + SWEEPING LIME/CYAN 3D RIBBON ---
[MeterMonolithCards]
Meter=Shape
X=0
Y=0
; 1. Top-Left CPU Monolith
Shape=Rectangle 40,24,84,218,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 2. Bottom-Left Recycle/Disk Monolith
Shape2=Rectangle 40,278,84,234,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 3. Tall RAM & SWAP Monolith
Shape3=Rectangle 148,52,162,434,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 4. Tall GPU / Core Temp Monolith
Shape4=Rectangle 332,52,106,434,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 5. Top-Center Large Clock Card
Shape5=Rectangle 462,20,282,174,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 6. Mid-Center Date Card
Shape6=Rectangle 462,212,282,130,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 7. Bottom-Center Weather Card
Shape7=Rectangle 462,360,282,142,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 8. Narrow Vertical Bridge Pillar
Shape8=Rectangle 760,52,48,434,4 | Fill LinearGradient 135 | 20,22,28,245 | 10,12,16,250 | StrokeWidth 1 | Stroke Color 45,50,60,160
; 9a. Top-Right Media/Status Monolith
Shape9=Rectangle 832,14,88,162,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 9b. Mid-Right Drives Card
Shape10=Rectangle 832,208,88,108,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180
; 9c. Bottom-Right Network Monolith
Shape11=Rectangle 832,344,88,170,4 | Fill LinearGradient 135 | 22,25,30,245 | 12,14,18,250 | StrokeWidth 1 | Stroke Color 48,54,64,180

; --- SWEEPING LIME-GREEN & CYAN 3D RIBBON POLYGONS ACROSS PANELS ---
Shape12=Polygon 40,468, 124,412, 124,492, 40,512 | Fill LinearGradient 45 | 150,235,0,245 | 95,180,0,245 | StrokeWidth 0
Shape13=Polygon 148,415, 310,336, 310,378, 148,464 | Fill LinearGradient 35 | 145,235,0,245 | 0,205,225,215 | StrokeWidth 0
Shape14=Polygon 332,326, 438,266, 438,298, 332,360 | Fill LinearGradient 35 | 0,210,235,230 | 145,235,0,245 | StrokeWidth 0
Shape15=Polygon 462,282, 578,194, 542,194, 462,256 | Fill Color 145,235,0,240 | StrokeWidth 0
Shape16=Polygon 545,194, 668,26, 710,26, 582,194 | Fill LinearGradient 60 | 160,245,15,250 | 105,185,0,250 | StrokeWidth 0
Shape17=Polygon 668,26, 744,74, 744,114, 682,66 | Fill LinearGradient 15 | 125,210,0,245 | 82,145,0,245 | StrokeWidth 0
Shape18=Polygon 760,82, 808,108, 808,136, 760,112 | Fill Color 120,205,0,240 | StrokeWidth 0
Shape19=Polygon 832,88, 920,30, 920,86, 832,134 | Fill LinearGradient 45 | 0,210,235,235 | 150,235,0,245 | StrokeWidth 0
; Weather Moon & Cloud Vector Icon
Shape20=Ellipse 512,418,16,16 | Fill Color 235,240,248,245 | StrokeWidth 0
Shape21=Ellipse 520,413,13,13 | Fill Color 18,20,25,255 | StrokeWidth 0
Shape22=Rectangle 504,424,32,12,6 | Fill Color 185,192,205,240 | StrokeWidth 0
Shape23=Ellipse 724,482,5,5 | Fill Color 145,235,0,255 | StrokeWidth 0

; --- PANEL 1: CPU ---
[MeterGrCpuTitle]
Meter=String
X=82
Y=38
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=190,198,210,245
Text="Cpu"
AntiAlias=1

[MeterGrCpuBar]
Meter=Bar
MeasureName=MeasureCPU
X=78
Y=74
W=8
H=120
BarOrientation=Vertical
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrCpuVal]
Meter=String
MeasureName=MeasureCPU
X=82
Y=210
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=190,198,210,245
Text="%1%"
AntiAlias=1

; --- PANEL 2: STORAGE / RECYCLE ---
[MeterGrBinTitle]
Meter=String
X=82
Y=294
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=190,198,210,245
Text="Storage"
AntiAlias=1

[MeterGrBinBar]
Meter=Bar
MeasureName=MeasureRoot
X=78
Y=332
W=8
H=62
BarOrientation=Vertical
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrBinVal]
Meter=String
MeasureName=MeasureRoot
X=82
Y=406
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=190,198,210,245
Text="%1% Used"
AntiAlias=1

; --- PANEL 3: RAM & SWAP ---
[MeterGrRamTitle]
Meter=String
X=194
Y=104
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=190,198,210,245
Text="Ram"
AntiAlias=1

[MeterGrSwapTitle]
Meter=String
X=264
Y=104
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=190,198,210,245
Text="Swap"
AntiAlias=1

[MeterGrRamBar]
Meter=Bar
MeasureName=MeasureRAM
X=190
Y=142
W=8
H=155
BarOrientation=Vertical
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrSwapBar]
Meter=Bar
MeasureName=MeasureSWAP
X=260
Y=142
W=8
H=155
BarOrientation=Vertical
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrRamVal]
Meter=String
MeasureName=MeasureRAM
X=194
Y=310
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=190,198,210,245
Text="%1% Used"
AntiAlias=1

[MeterGrSwapVal]
Meter=String
MeasureName=MeasureSWAP
X=264
Y=310
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=190,198,210,245
Text="%1% Used"
AntiAlias=1

; --- PANEL 4: CORE TEMP / GPU ---
[MeterGrGpuTitle]
Meter=String
X=385
Y=74
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=190,198,210,245
Text="Core"
AntiAlias=1

[MeterGrGpuBar]
Meter=Bar
MeasureName=MeasureTemp
X=381
Y=116
W=8
H=130
BarOrientation=Vertical
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrGpuVal]
Meter=String
MeasureName=MeasureTemp
X=385
Y=262
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor=190,198,210,245
Text="%1°C"
AntiAlias=1

; --- PANEL 5: LARGE CLOCK ---
[MeterGrHour]
Meter=String
MeasureName=MeasureHour
X=480
Y=26
FontFace=Sans
FontSize=56
FontColor=215,220,228,255
Text="%1"
AntiAlias=1

[MeterGrSec]
Meter=String
MeasureName=MeasureSecond
MeasureName2=MeasureAMPM
X=484
Y=146
FontFace=Sans
FontSize=18
FontColor=215,220,228,245
Text="%1"
AntiAlias=1

[MeterGrAmPm]
Meter=String
MeasureName=MeasureAMPM
X=526
Y=158
FontFace=Sans
FontSize=9
FontColor=145,230,0,255
Text="%1"
AntiAlias=1

[MeterGrMin]
Meter=String
MeasureName=MeasureMinute
X=724
Y=118
StringAlign=Right
FontFace=Sans
FontSize=44
FontColor=145,230,0,255
Text="%1"
AntiAlias=1

; --- PANEL 6: DATE ---
[MeterGrDay]
Meter=String
MeasureName=MeasureDay
X=724
Y=224
W=240
H=32
StringAlign=Right
FontFace=Sans
FontSize=20
FontColor=220,225,232,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterGrMonth]
Meter=String
MeasureName=MeasureMonth
X=724
Y=258
W=240
H=34
StringAlign=Right
FontFace=Sans
FontSize=22
FontColor=145,230,0,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterGrYear]
Meter=String
MeasureName=MeasureYear
X=724
Y=298
W=240
H=32
StringAlign=Right
FontFace=Sans
FontSize=20
FontColor=220,225,232,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

; --- PANEL 7: WEATHER ---
[MeterGrWCond]
Meter=String
MeasureName=MeasureWeatherCond
X=478
Y=372
W=250
H=22
FontFace=Sans
FontSize=10
FontColor=215,220,228,255
Text="Currently - %1"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterGrWTemp]
Meter=String
MeasureName=MeasureWeatherTemp
MeasureName2=MeasureWeatherUnit
X=565
Y=396
W=140
H=42
FontFace=Sans
FontSize=28
FontColor=225,230,238,255
Text="%1%2"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterGrWHum]
Meter=String
MeasureName=MeasureWeatherHum
X=478
Y=446
W=240
H=18
FontFace=Sans
FontSize=8
FontColor=185,192,204,240
Text="Humidity: %1%"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterGrWRain]
Meter=String
MeasureName=MeasureWeatherRain
X=478
Y=462
W=240
H=18
FontFace=Sans
FontSize=8
FontColor=185,192,204,240
Text="Chance of rain: %1%"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterGrWWind]
Meter=String
MeasureName=MeasureWeatherWind
MeasureName2=MeasureWeatherDir
MeasureName3=MeasureWeatherSpeedUnit
X=478
Y=478
W=250
H=18
FontFace=Sans
FontSize=8
FontColor=185,192,204,240
Text="Wind: %1 %3 - %2 (#WeatherLocation#)"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

; --- PANEL 9A, 9B, 9C: MEDIA/NOTES, DRIVES & NET ---
[MeterGrMediaLbl]
Meter=String
X=876
Y=134
W=80
H=24
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=190,198,210,245
Text="Notes"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterGrMediaBar]
Meter=Bar
MeasureName=MeasureProgress
X=854
Y=154
W=44
H=6
BarOrientation=Horizontal
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrDrive1Lbl]
Meter=String
MeasureName=MeasureRoot
X=876
Y=220
W=80
H=22
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=190,198,210,245
Text="/ - %1%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "/"]

[MeterGrDrive1Bar]
Meter=Bar
MeasureName=MeasureRoot
X=850
Y=240
W=52
H=6
BarOrientation=Horizontal
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrDrive2Lbl]
Meter=String
MeasureName=MeasureHome
X=876
Y=266
W=80
H=22
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=190,198,210,245
Text="Home - %1%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

[MeterGrDrive2Bar]
Meter=Bar
MeasureName=MeasureHome
X=850
Y=286
W=52
H=6
BarOrientation=Horizontal
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrNetTitle]
Meter=String
X=876
Y=356
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=190,198,210,245
Text="Net"
AntiAlias=1

[MeterGrNetInBar]
Meter=Bar
MeasureName=MeasureNetIn
X=854
Y=384
W=6
H=96
BarOrientation=Vertical
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrNetOutBar]
Meter=Bar
MeasureName=MeasureNetOut
X=892
Y=384
W=6
H=96
BarOrientation=Vertical
BarColor=145,230,0,255
SolidColor=32,36,44,220

[MeterGrNetInLbl]
Meter=String
X=857
Y=490
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=190,198,210,245
Text="In"
AntiAlias=1

[MeterGrNetOutLbl]
Meter=String
X=895
Y=490
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=190,198,210,245
Text="Out"
AntiAlias=1
"""


# =============================================================================
# 5. CyberYellowHUD (Photo 5: Tactical Yellow Arc Dials + Wireframe HUD + 20-Band Scope)
# =============================================================================
def build_cyber_yellow_hud():
    scope_bars = []
    for b in range(20):
        bx = 442 + b * 11
        scope_bars.append(
            f"""[MeterYellowScope{b}]
Meter=Bar
MeasureName=MeasureBand{b}
X={bx}
Y=524
W=7
H=38
BarOrientation=Vertical
BarColor=245,232,20,240
SolidColor=55,58,24,140
"""
        )
    return f"""[Rainmeter]
Update=33
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=1220
SkinHeight=660
AutoFit=1

[Metadata]
Name=CyberYellowHUD
Author=Trad Desktop
Information=Tactical Cyber-Yellow Sci-Fi HUD with 5 Radial Arc Dials, Radar Clock, Wireframe Music/Weather & 20-Band Spectrum Scope

{make_common_measures()}
{make_audio_measures(20, 25, 145, 45)}

; --- TACTICAL YELLOW WIREFRAME BOXES & RADIAL DIAL BACKDROPS ---
[MeterYellowWireframe]
Meter=Shape
X=0
Y=0
; Top-Center Radar Clock Outer & Inner Rings
Shape=Ellipse 474,182,76,76 | Fill Color 18,24,28,140 | StrokeWidth 2 | Stroke Color 245,232,20,235
Shape2=Ellipse 474,182,66,66 | Fill Color 0,0,0,0 | StrokeWidth 1 | Stroke Color 245,232,20,140
; 5 Left Radial Gauge Outer Rings
Shape3=Ellipse 185,255,44,44 | Fill Color 18,24,28,130 | StrokeWidth 1.5 | Stroke Color 245,232,20,190
Shape4=Ellipse 298,255,56,56 | Fill Color 18,24,28,130 | StrokeWidth 1.5 | Stroke Color 245,232,20,190
Shape5=Ellipse 254,342,52,52 | Fill Color 18,24,28,130 | StrokeWidth 1.5 | Stroke Color 245,232,20,190
Shape6=Ellipse 130,368,58,58 | Fill Color 18,24,28,130 | StrokeWidth 1.5 | Stroke Color 20,24,28,230
Shape7=Ellipse 425,392,66,66 | Fill Color 18,24,28,140 | StrokeWidth 2 | Stroke Color 245,232,20,220
Shape8=Ellipse 538,318,54,54 | Fill Color 18,24,28,130 | StrokeWidth 1.5 | Stroke Color 245,232,20,190
; Top-Right Calendar Wireframe Box
Shape9=Rectangle 810,126,204,108,0 | Fill Color 16,22,26,175 | StrokeWidth 1.5 | Stroke Color 245,232,20,220
Shape10=Line 810,146,1014,146 | StrokeWidth 1 | Stroke Color 245,232,20,150
; Mid-Right Music Player Wireframe Box
Shape11=Rectangle 690,262,216,104,0 | Fill Color 16,22,26,180 | StrokeWidth 1.5 | Stroke Color 245,232,20,220
Shape12=Rectangle 842,272,56,84,0 | Fill Color 28,32,20,230 | StrokeWidth 1 | Stroke Color 245,232,20,160
; Vector beamed music note emblem inside Album Art box (shown when no cover art is present)
Shape13=Ellipse 864,322,4.5,3.5 | Fill Color 245,232,20,225 | StrokeWidth 0
Shape14=Ellipse 876,319,4.5,3.5 | Fill Color 245,232,20,225 | StrokeWidth 0
Shape15=Line 868,322,868,303 | StrokeWidth 2 | Stroke Color 245,232,20,225
Shape16=Line 880,319,880,300 | StrokeWidth 2 | Stroke Color 245,232,20,225
Shape17=Line 868,303,880,300 | StrokeWidth 3 | Stroke Color 245,232,20,225
; Mid-Center Weather Wireframe Box
Shape18=Rectangle 578,392,204,82,0 | Fill Color 16,22,26,180 | StrokeWidth 1.5 | Stroke Color 245,232,20,220
; Right Quick Action Icon Strip Box
Shape19=Rectangle 892,400,198,32,0 | Fill Color 16,22,26,180 | StrokeWidth 1.5 | Stroke Color 245,232,20,220
; Bottom-Center 20-Band Spectrum & Disk I/O Box
Shape20=Rectangle 430,490,236,80,0 | Fill Color 16,22,26,185 | StrokeWidth 1.5 | Stroke Color 245,232,20,220
Shape21=Line 430,520,666,520 | StrokeWidth 1 | Stroke Color 245,232,20,160
; Bottom-Right Network & Security Status Box
Shape22=Rectangle 896,478,202,88,0 | Fill Color 16,22,26,185 | StrokeWidth 1.5 | Stroke Color 245,232,20,220

; --- 6 RADIAL ROUNDLINE GAUGES (CLOCK + CPU + SWAP + NET + BATTERY + RAM) ---
[MeterYClockRing]
Meter=Roundline
MeasureName=MeasureSecond
X=398
Y=106
W=152
H=152
StartAngle=4.712
RotationAngle=6.283
LineStart=56
LineLength=66
Solid=1
LineColor=245,232,20,245

[MeterYClockText]
Meter=String
MeasureName=MeasureTime
X=474
Y=166
StringAlign=Center
FontFace=Sans
FontSize=20
FontColor=245,232,20,255
Text="%1"
AntiAlias=1

[MeterYClockSub]
Meter=String
MeasureName=MeasureSecond
X=474
Y=196
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor=245,232,20,200
Text="SEC %1"
AntiAlias=1

; Dial 1: CPU %
[MeterYCpuRing]
Meter=Roundline
MeasureName=MeasureCPU
X=141
Y=211
W=88
H=88
StartAngle=2.356
RotationAngle=4.712
LineStart=33
LineLength=40
Solid=1
LineColor=245,232,20,245

[MeterYCpuText]
Meter=String
MeasureName=MeasureCPU
X=185
Y=244
StringAlign=Center
FontFace=Sans
FontSize=11
FontColor=245,232,20,255
Text="%1%"
AntiAlias=1

[MeterYCpuLbl]
Meter=String
X=185
Y=264
StringAlign=Center
FontFace=Sans
FontSize=7
FontColor=245,232,20,190
Text="CPU"
AntiAlias=1

; Dial 2: SWAP / TEMP
[MeterYTempRing]
Meter=Roundline
MeasureName=MeasureTemp
X=242
Y=199
W=112
H=112
StartAngle=4.712
RotationAngle=4.712
LineStart=42
LineLength=50
Solid=1
LineColor=245,232,20,245

[MeterYTempText]
Meter=String
MeasureName=MeasureTemp
X=298
Y=242
StringAlign=Center
FontFace=Sans
FontSize=13
FontColor=245,232,20,255
Text="%1°C"
AntiAlias=1

[MeterYTempLbl]
Meter=String
X=298
Y=264
StringAlign=Center
FontFace=Sans
FontSize=7
FontColor=245,232,20,190
Text="CORE TEMP"
AntiAlias=1

; Dial 3: ROOT DISK %
[MeterYDiskRing]
Meter=Roundline
MeasureName=MeasureRoot
X=202
Y=290
W=104
H=104
StartAngle=1.571
RotationAngle=4.712
LineStart=39
LineLength=47
Solid=1
LineColor=245,232,20,245

[MeterYDiskText]
Meter=String
MeasureName=MeasureRoot
X=254
Y=330
StringAlign=Center
FontFace=Sans
FontSize=12
FontColor=245,232,20,255
Text="%1%"
AntiAlias=1

[MeterYDiskLbl]
Meter=String
X=254
Y=350
StringAlign=Center
FontFace=Sans
FontSize=7
FontColor=245,232,20,190
Text="DISK /"
AntiAlias=1

; Dial 4: HOME DISK % (Dark Accent Dial)
[MeterYHomeRing]
Meter=Roundline
MeasureName=MeasureHome
X=72
Y=310
W=116
H=116
StartAngle=2.356
RotationAngle=4.712
LineStart=44
LineLength=52
Solid=1
LineColor=245,232,20,220

[MeterYHomeText]
Meter=String
MeasureName=MeasureHome
X=130
Y=356
StringAlign=Center
FontFace=Sans
FontSize=14
FontColor=245,232,20,255
Text="%1%"
AntiAlias=1

[MeterYHomeLbl]
Meter=String
X=130
Y=378
StringAlign=Center
FontFace=Sans
FontSize=7
FontColor=245,232,20,190
Text="HOME"
AntiAlias=1

; Dial 5: BATTERY 100%
[MeterYBattRing]
Meter=Roundline
MeasureName=MeasureBattery
X=359
Y=326
W=132
H=132
StartAngle=1.571
RotationAngle=5.2
LineStart=49
LineLength=60
Solid=1
LineColor=245,232,20,255

[MeterYBattText]
Meter=String
X=425
Y=376
StringAlign=Center
FontFace=Sans
FontSize=14
FontColor=245,232,20,255
Text="100%"
AntiAlias=1

[MeterYBattLbl]
Meter=String
X=425
Y=398
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,210
Text="Battery"
AntiAlias=1

; Dial 6: RAM %
[MeterYRamRing]
Meter=Roundline
MeasureName=MeasureRAM
X=484
Y=264
W=108
H=108
StartAngle=4.712
RotationAngle=4.712
LineStart=40
LineLength=48
Solid=1
LineColor=245,232,20,245

[MeterYRamText]
Meter=String
MeasureName=MeasureRAM
X=538
Y=306
StringAlign=Center
FontFace=Sans
FontSize=13
FontColor=245,232,20,255
Text="%1%"
AntiAlias=1

[MeterYRamLbl]
Meter=String
X=538
Y=326
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,200
Text="RAM"
AntiAlias=1

; --- TOP-RIGHT CALENDAR BOX (CLICKABLE) ---
[MeterYCalHdr]
Meter=String
MeasureName=MeasureMonth
MeasureName2=MeasureYear
X=912
Y=130
W=200
H=20
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="%1 %2"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterYCalDays]
Meter=String
X=912
Y=152
W=200
H=18
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,235
Text="M     T     W     T     F     S     S"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterYCalRow1]
Meter=String
X=912
Y=170
W=200
H=18
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=220,228,235,230
Text=" 1     2     3     4     5     6     7"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterYCalRow2]
Meter=String
X=912
Y=186
W=200
H=18
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=220,228,235,230
Text=" 8     9    10    11    12    13    14"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterYCalRow3]
Meter=String
X=912
Y=202
W=200
H=18
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="15    16    17    18    19    20    21"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterYCalRow4]
Meter=String
X=912
Y=218
W=200
H=18
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=220,228,235,230
Text="22    23    24    25    26    27    28"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

; --- MID-RIGHT MUSIC PLAYER WIREFRAME BOX ---
[MeterYTrack]
Meter=String
MeasureName=MeasureTrack
X=700
Y=270
W=136
H=14
ClipString=1
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="Track: %1"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterYArtist]
Meter=String
MeasureName=MeasureArtist
X=700
Y=286
W=136
H=14
ClipString=1
FontFace=Sans
FontSize=8
FontColor=245,232,20,220
Text="Artist: %1"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterYAlbum]
Meter=String
MeasureName=MeasureAlbum
X=700
Y=302
W=136
H=14
ClipString=1
FontFace=Sans
FontSize=8
FontColor=245,232,20,190
Text="Album: %1"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterYPrev]
Meter=Shape
X=704
Y=318
W=22
H=22
Shape=Rectangle 3,5,2,11,1 | Fill Color 245,232,20,255 | StrokeWidth 0
Shape2=Polygon 6.5,10.5, 16,5, 16,16 | Fill Color 245,232,20,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Previous"]

[MeterYPlay]
Meter=Shape
X=736
Y=318
W=22
H=22
Hidden=[MeasureIsPlaying]
Shape=Polygon 16,10.5, 6,5, 6,16 | Fill Color 245,232,20,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterYPause]
Meter=Shape
X=736
Y=318
W=22
H=22
Hidden=[MeasureIsPaused]
Shape=Rectangle 6,5,3,11,1 | Fill Color 245,232,20,255 | StrokeWidth 0
Shape2=Rectangle 12.5,5,3,11,1 | Fill Color 245,232,20,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterYNext]
Meter=Shape
X=768
Y=318
W=22
H=22
Shape=Polygon 15.5,10.5, 6,5, 6,16 | Fill Color 245,232,20,255 | StrokeWidth 0
Shape2=Rectangle 17,5,2,11,1 | Fill Color 245,232,20,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Next"]

[MeterYProgBar]
Meter=Bar
MeasureName=MeasureProgress
X=700
Y=344
W=136
H=8
BarOrientation=Horizontal
BarColor=245,232,20,255
SolidColor=55,58,24,180

[MeterYArtIcon]
Meter=Image
MeasureName=MeasureCover
X=842
Y=272
W=56
H=84
PreserveAspectRatio=2
SolidColor=0,0,0,0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

; --- MID-CENTER WEATHER BOX ---
[MeterYWDate]
Meter=String
MeasureName=MeasureTime12
MeasureName2=MeasureWeekdayShort
X=588
Y=398
W=188
H=18
FontFace=Sans
FontSize=8
FontColor=245,232,20,245
Text="%1  •  %2  •  #WeatherLocation#"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterYWTemp]
Meter=String
MeasureName=MeasureWeatherTemp
MeasureName2=MeasureWeatherHigh
MeasureName3=MeasureWeatherLow
MeasureName4=MeasureWeatherUnit
X=588
Y=416
W=188
H=18
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="Temp: %1%4   High: %2%4   Low: %3%4"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterYWCond]
Meter=String
MeasureName=MeasureWeatherCond
X=588
Y=434
W=188
H=18
FontFace=Sans
FontSize=8
FontColor=245,232,20,235
Text="Current: %1"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterYWHumBar]
Meter=Bar
MeasureName=MeasureWeatherHum
X=588
Y=454
W=184
H=8
BarOrientation=Horizontal
BarColor=245,232,20,245
SolidColor=55,58,24,180

; --- RIGHT QUICK ACTION BAR (INDIVIDUALLY CLICKABLE) ---
[MeterYAct1]
Meter=String
X=912
Y=409
W=36
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="FILES"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

[MeterYAct2]
Meter=String
X=950
Y=409
W=36
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="NOTES"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterYAct3]
Meter=String
X=990
Y=409
W=36
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="WEB"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "https://github.com/KidDzhasi/Trad-Desktop"]

[MeterYAct4]
Meter=String
X=1028
Y=409
W=36
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="WTHR"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterYAct5]
Meter=String
X=1068
Y=409
W=36
H=24
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor=245,232,20,255
Text="CTRL"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

; --- BOTTOM-CENTER 20-BAND SPECTRUM & STORAGE BOX ---
[MeterYScopeHdr]
Meter=String
MeasureName=MeasureRoot
MeasureName2=MeasureHome
X=440
Y=496
FontFace=Sans
FontSize=8
FontColor=245,232,20,245
Text="ROOT: %1%   HOME: %2%   AUDIO SPECTRUM (20-BAND)"
AntiAlias=1

{"".join(scope_bars)}

; --- BOTTOM-RIGHT NETWORK & SECURITY BOX ---
[MeterYNet1]
Meter=String
MeasureName=MeasureNetInKB
MeasureName2=MeasureNetOutKB
X=906
Y=486
FontFace=Sans
FontSize=8
FontColor=245,232,20,245
Text="NET IN: %1 KB/s   OUT: %2 KB/s"
AntiAlias=1

[MeterYNet2]
Meter=String
X=906
Y=502
FontFace=Sans
FontSize=8
FontColor=245,232,20,225
Text="Auth: WPA2-Personal  •  Status: ONLINE"
AntiAlias=1

[MeterYNet3]
Meter=String
X=906
Y=518
FontFace=Sans
FontSize=8
FontColor=245,232,20,225
Text="Source: AC Mains  •  Charge: 100%"
AntiAlias=1

[MeterYNetBar1]
Meter=Bar
MeasureName=MeasureCPU
X=906
Y=538
W=182
H=6
BarOrientation=Horizontal
BarColor=245,232,20,245
SolidColor=55,58,24,180

[MeterYNetBar2]
Meter=Bar
MeasureName=MeasureRAM
X=906
Y=550
W=182
H=6
BarOrientation=Horizontal
BarColor=245,232,20,245
SolidColor=55,58,24,180
"""


# =============================================================================
# 6 & 7. ShieldOSHub (Photo 6) & ShieldOSDark (Photo 7)
# =============================================================================
def build_shield_os(dark_plate=False):
    suite_name = "ShieldOSDark" if dark_plate else "ShieldOSHub"
    plate_shapes = ""
    if dark_plate:
        plate_shapes = """Shape=Polygon 215,86, 405,86, 466,56, 634,56, 695,86, 885,86, 962,186, 972,282, 852,282, 852,398, 972,398, 962,494, 885,594, 695,594, 634,624, 466,624, 405,594, 215,594, 138,494, 128,398, 248,398, 248,282, 128,282, 138,186 | Fill Color 18,22,28,244 | StrokeWidth 2 | Stroke Color 95,112,135,215
"""
    fg_col = "238,245,255,250" if dark_plate else "64,74,88,250"
    ring_col = "220,232,246,238" if dark_plate else "78,90,104,235"
    sub_col = "168,186,210,240" if dark_plate else "84,96,112,235"
    pod_bg = "28,34,42,242" if dark_plate else "235,242,250,185"
    wing_bg = "22,27,35,238" if dark_plate else "230,238,248,175"
    core_bg = "20,25,33,246" if dark_plate else "238,244,252,195"

    vis_bars = []
    for b in range(10):
        bx = 528 + b * 5
        vis_bars.append(
            f"""[MeterShieldVis{b}]
Meter=Bar
MeasureName=MeasureBand{b}
X={bx}
Y=552
W=3
H=26
BarOrientation=Vertical
BarColor={fg_col}
SolidColor=110,122,138,85
"""
        )

    return f"""[Rainmeter]
Update=33
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=1100
SkinHeight=680
AutoFit=1

[Metadata]
Name={suite_name}
Author=Trad Desktop
Information=S.H.I.E.L.D. OS Rotary Sci-Fi Hub with Concentric Tech Rings, 12 Orbital Pods & Live Audio Spectrum

{make_common_measures()}
{make_audio_measures(12, 26, 150, 44)}

; --- BACKING PLATE, CONCENTRIC TECH RINGS & CALLOUT WINGS ---
[MeterShieldBase]
Meter=Shape
X=0
Y=0
{plate_shapes}
; 4 Rectangular Callout Wings (drawn FIRST so orbital circular pods sit cleanly on top without inner seam overlap)
Shape2=Rectangle 164,194,184,68,16 | Fill Color {wing_bg} | StrokeWidth 2 | Stroke Color {ring_col}
Shape3=Rectangle 164,418,184,68,16 | Fill Color {wing_bg} | StrokeWidth 2 | Stroke Color {ring_col}
Shape4=Rectangle 752,194,184,68,16 | Fill Color {wing_bg} | StrokeWidth 2 | Stroke Color {ring_col}
Shape5=Rectangle 752,418,184,68,16 | Fill Color {wing_bg} | StrokeWidth 2 | Stroke Color {ring_col}
; Central Concentric Rings (center = 550, 340)
Shape6=Ellipse 550,340,188,188 | Fill Color 0,0,0,0 | StrokeWidth 3 | Stroke Color {ring_col}
Shape7=Ellipse 550,340,170,170 | Fill Color 0,0,0,0 | StrokeWidth 6 | Stroke Color 120,132,148,140
Shape8=Ellipse 550,340,152,152 | Fill Color {core_bg} | StrokeWidth 3 | Stroke Color {ring_col}
Shape9=Arc 550,340,178,-140,100 | Fill Color 0,0,0,0 | StrokeWidth 7 | Stroke Color {fg_col}
Shape10=Arc 550,340,178,20,110 | Fill Color 0,0,0,0 | StrokeWidth 7 | Stroke Color {fg_col}
; 12 Orbital Circular Pods around the main ring
Shape11=Ellipse 550,108,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape12=Ellipse 432,146,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape13=Ellipse 668,146,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape14=Ellipse 348,228,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape15=Ellipse 316,340,36,36 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape16=Ellipse 348,452,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape17=Ellipse 432,534,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape18=Ellipse 550,566,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape19=Ellipse 668,534,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape20=Ellipse 752,228,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape21=Ellipse 784,340,36,36 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}
Shape22=Ellipse 752,452,38,38 | Fill Color {pod_bg} | StrokeWidth 2.5 | Stroke Color {ring_col}

; --- LIVE ROUNDLINE RINGS ON MAIN HUB ---
[MeterShieldMainRing]
Meter=Roundline
MeasureName=MeasureCPU
X=380
Y=170
W=340
H=340
StartAngle=4.712
RotationAngle=6.283
LineStart=156
LineLength=164
Solid=1
LineColor={fg_col}

; --- CENTER HUB: CLOCK & TERMINAL ---
[MeterShieldHour]
Meter=String
MeasureName=MeasureHour12
X=542
Y=252
StringAlign=Right
FontFace=Sans
FontSize=38
FontColor={fg_col}
Text="%1:"
AntiAlias=1

[MeterShieldMin]
Meter=String
MeasureName=MeasureMinute
X=548
Y=256
FontFace=Sans
FontSize=20
FontColor={fg_col}
Text="%1"
AntiAlias=1

[MeterShieldAmPm]
Meter=String
MeasureName=MeasureAMPM
X=548
Y=284
FontFace=Sans
FontSize=15
FontColor={fg_col}
Text="%1"
AntiAlias=1

[MeterShieldTabRss]
Meter=String
X=492
Y=322
W=48
H=22
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor={fg_col}
Text="RSS"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "https://news.ycombinator.com"]

[MeterShieldTabNotes]
Meter=String
X=550
Y=322
W=56
H=22
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor={fg_col}
Text="NOTES"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterShieldTabLinks]
Meter=String
X=608
Y=322
W=48
H=22
StringAlign=Center
FontFace=Sans
FontSize=10
FontColor={fg_col}
Text="LINKS"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "https://github.com/KidDzhasi/Trad-Desktop"]

[MeterShieldLine1]
Meter=String
X=550
Y=350
W=230
H=18
ClipString=1
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor={sub_col}
Text="NOTE: #NoteLine1#"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterShieldLine2]
Meter=String
MeasureName=MeasureWeatherCond
MeasureName2=MeasureWeatherTemp
MeasureName3=MeasureWeatherUnit
X=550
Y=370
W=230
H=18
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor={sub_col}
Text="#WeatherLocation#: %1 (%2%3)"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterShieldLine3]
Meter=String
X=550
Y=390
W=230
H=18
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor={sub_col}
Text="[Click to Edit Sticky Notes or Control Center]"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterShieldLine4]
Meter=String
MeasureName=MeasureCPU
MeasureName2=MeasureRAM
X=550
Y=410
W=230
H=18
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor={sub_col}
Text="CPU LOAD: %1%  •  RAM: %2%"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

; --- ORBITAL PODS & WINGS CONTENT ---
; Top Pod (Power/Reload)
[MeterPodTop]
Meter=String
X=550
Y=98
W=60
H=40
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor={fg_col}
Text="SYNC"
AntiAlias=1
LeftMouseUpAction=[!Refresh]

; Top-Left Media Pod (Vector Transport Icons)
[MeterPodMediaPrev]
Meter=Shape
X=404
Y=138
W=18
H=18
Shape=Rectangle 2,4,2,10,1 | Fill Color {fg_col} | StrokeWidth 0
Shape2=Polygon 5,9, 13,4, 13,14 | Fill Color {fg_col} | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Previous"]

[MeterPodMediaPlay]
Meter=Shape
X=423
Y=124
W=18
H=18
Hidden=[MeasureIsPlaying]
Shape=Polygon 14,9, 5,4, 5,14 | Fill Color {fg_col} | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterPodMediaPause]
Meter=Shape
X=423
Y=124
W=18
H=18
Hidden=[MeasureIsPaused]
Shape=Rectangle 5,4,2.8,10,1 | Fill Color {fg_col} | StrokeWidth 0
Shape2=Rectangle 10.5,4,2.8,10,1 | Fill Color {fg_col} | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterPodMediaNext]
Meter=Shape
X=442
Y=138
W=18
H=18
Shape=Polygon 13,9, 5,4, 5,14 | Fill Color {fg_col} | StrokeWidth 0
Shape2=Rectangle 14,4,2,10,1 | Fill Color {fg_col} | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Next"]

; Top-Right Apps Pod
[MeterPodApps]
Meter=String
X=668
Y=138
W=64
H=40
StringAlign=Center
FontFace=Sans
FontSize=9
FontColor={fg_col}
Text="STUDIO"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

; Upper-Left CPU/RAM Pod + Wing
[MeterPodCpuRam]
Meter=String
MeasureName=MeasureCPU
MeasureName2=MeasureRAM
X=348
Y=214
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="CPU %1%#CRLF#RAM %2%"
AntiAlias=1

[MeterWingCpu1]
Meter=String
MeasureName=MeasureCPU
X=246
Y=204
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="CORE LOAD: %1%"
AntiAlias=1

[MeterWingCpuBar]
Meter=Bar
MeasureName=MeasureCPU
X=186
Y=224
W=120
H=5
BarOrientation=Horizontal
BarColor={fg_col}
SolidColor=120,130,145,90

[MeterWingTemp]
Meter=String
MeasureName=MeasureTemp
X=246
Y=238
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={sub_col}
Text="THERMAL: %1°C"
AntiAlias=1

; Mid-Left Disk Pod
[MeterPodDisk]
Meter=String
MeasureName=MeasureRoot
X=316
Y=326
W=64
H=40
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="DISK /#CRLF#%1%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "/"]

; Lower-Left Network Pod + Wing
[MeterPodNet]
Meter=String
X=348
Y=442
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="WIFI#CRLF#NET"
AntiAlias=1

[MeterWingNetUp]
Meter=String
MeasureName=MeasureNetOutKB
X=182
Y=428
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="UP: %1 KB/s"
AntiAlias=1

[MeterWingNetDn]
Meter=String
MeasureName=MeasureNetInKB
X=182
Y=448
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="DN: %1 KB/s"
AntiAlias=1

[MeterWingNetSsid]
Meter=String
X=182
Y=466
FontFace=Sans
FontSize=7
FontColor={sub_col}
Text="NET: ONLINE"
AntiAlias=1

; Bottom-Left Weather Pod
[MeterPodWeather]
Meter=String
MeasureName=MeasureWeatherTemp
MeasureName2=MeasureWeatherUnit
MeasureName3=MeasureWeatherDir
X=432
Y=520
W=68
H=44
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="%1%2#CRLF#WIND %3"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

; Bottom-Center Audio Spectrum Pod
{"".join(vis_bars)}

; Bottom-Right Storage Home Pod
[MeterPodHome]
Meter=String
MeasureName=MeasureHome
X=668
Y=520
W=68
H=44
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="HOME#CRLF#%1%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

; Upper-Right Folders Pod + Wing
[MeterPodFolders]
Meter=String
X=752
Y=218
W=68
H=44
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="FILES#CRLF#OPEN"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

[MeterWingFolder1]
Meter=String
X=800
Y=202
W=126
H=18
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="> Trad Control Center"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

[MeterWingFolder2]
Meter=String
X=800
Y=220
W=126
H=18
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="> Sticky Notes Editor"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterWingFolder3]
Meter=String
X=800
Y=238
W=126
H=18
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="> Downloads Folder"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~/Downloads"]

; Mid-Right Power Pod
[MeterPodPower]
Meter=String
X=784
Y=326
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="100%#CRLF#AC"
AntiAlias=1

; Lower-Right Calendar Pod + Wing
[MeterPodCalDate]
Meter=String
MeasureName=MeasureWeekdayShort
MeasureName2=MeasureDay
X=752
Y=436
W=68
H=44
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="%1#CRLF#%2"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterWingCal]
Meter=String
MeasureName=MeasureMonth
MeasureName2=MeasureYear
X=860
Y=434
W=136
H=44
StringAlign=Center
FontFace=Sans
FontSize=8
FontColor={fg_col}
Text="%1 %2#CRLF#Su Mo Tu We Th Fr Sa"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]
"""


# =============================================================================
# 8. DiagonalMinimalSuite (Photo 8: Angled Left Ribbon Blades + Black/White Stadium Pills)
# =============================================================================
def build_diagonal_minimal():
    blades = []
    labels = [
        ("Files", 'LeftMouseUpAction=["xdg-open" "~"]', ""),
        ("RAM %1%", "LeftMouseUpAction=[!OpenControlCenter]", "MeasureName=MeasureRAM"),
        ("%1 %2", "LeftMouseUpAction=[!CalendarPopup]", "MeasureName=MeasureDay\nMeasureName2=MeasureMonthShort"),
        ("CPU %1%", "LeftMouseUpAction=[!OpenControlCenter]", "MeasureName=MeasureCPU"),
        ("Browser", 'LeftMouseUpAction=["xdg-open" "https://github.com/KidDzhasi/Trad-Desktop"]', ""),
        ("Notes", "LeftMouseUpAction=[!NotesPopup]", ""),
        ("Weather", "LeftMouseUpAction=[!WeatherPopup]", ""),
        ("Studio", "LeftMouseUpAction=[!OpenControlCenter]", ""),
    ]
    shapes = []
    for i, (txt, action, meas) in enumerate(labels):
        y0 = 260 + i * 42
        y1 = y0 - 85
        shapes.append(
            f"Shape{i+1 if i>0 else ''}=Polygon 0,{y0}, 168,{y1}, 178,{y1+22}, 0,{y0+28} | Fill Color 12,14,18,245 | StrokeWidth 0"
        )
        blades.append(
            f"""[MeterBladeLbl{i}]
Meter=String
{meas}
X=118
Y={y1 + 26}
W=120
H=24
StringAlign=Center
Angle=-27
FontFace=Sans
FontSize=10
FontColor=245,248,255,255
Text="{txt}"
AntiAlias=1
{action}
"""
        )

    return f"""[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=1366
SkinHeight=768
AutoFit=1

[Metadata]
Name=DiagonalMinimalSuite
Author=Trad Desktop
Information=Minimalist Monochrome Diagonal Ribbon Blades with High-Contrast Black & White Stadium Clock/Date Pills

{make_common_measures()}

; --- LEFT ANGLED BLACK BLADES & RIGHT STADIUM PILLS ---
[MeterDiagShapes]
Meter=Shape
X=0
Y=0
{chr(10).join(shapes)}
; Top-Right Black Time Pill
Shape9=Rectangle 738,184,526,52,26 | Fill Color 10,12,16,248 | StrokeWidth 0
; Mid-Right White Date Pill
Shape10=Rectangle 738,284,526,52,26 | Fill Color 250,252,255,248 | StrokeWidth 1 | Stroke Color 200,208,220,180
Shape11=Ellipse 1218,296,4,4 | Fill Color 12,14,18,255 | StrokeWidth 0
Shape12=Ellipse 1232,296,4,4 | Fill Color 12,14,18,255 | StrokeWidth 0
Shape13=Ellipse 1246,296,4,4 | Fill Color 12,14,18,255 | StrokeWidth 0
; Now Playing Grey Pill
Shape14=Rectangle 970,384,294,24,6 | Fill Color 78,82,90,235 | StrokeWidth 0
; Bottom-Right Files & HDD Status Block
Shape15=Rectangle 1044,468,26,92,4 | Fill Color 10,12,16,248 | StrokeWidth 0
Shape16=Rectangle 1078,476,184,34,8 | Fill Color 82,86,94,235 | StrokeWidth 0
Shape17=Rectangle 1078,524,184,34,8 | Fill Color 82,86,94,235 | StrokeWidth 0

{"".join(blades)}

[MeterDiagTime]
Meter=String
MeasureName=MeasureTime12
MeasureName2=MeasureWeekday
X=764
Y=194
W=480
H=36
FontFace=Sans
FontSize=22
FontColor=250,252,255,255
Text="%1   %2"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterDiagDate]
Meter=String
MeasureName=MeasureDay
MeasureName2=MeasureMonth
MeasureName3=MeasureYear
X=764
Y=294
W=480
H=36
FontFace=Sans
FontSize=21
FontColor=14,16,22,255
Text="%1 %2 %3"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterDiagTrack]
Meter=String
MeasureName=MeasureTrack
X=980
Y=389
W=220
H=18
ClipString=1
FontFace=Sans
FontSize=9
FontColor=245,248,255,255
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterDiagPos]
Meter=String
MeasureName=MeasurePosition
X=1254
Y=389
StringAlign=Right
FontFace=Sans
FontSize=9
FontColor=245,248,255,255
Text="%1"
AntiAlias=1

[MeterDiagFiles]
Meter=String
MeasureName=MeasureWeatherTemp
MeasureName2=MeasureWeatherUnit
X=1092
Y=486
W=166
H=24
FontFace=Sans
FontSize=9
FontColor=245,248,255,255
Text="Files  |  Notes  |  %1%2"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterDiagHdd]
Meter=String
MeasureName=MeasureRoot
MeasureName2=MeasureHome
X=1092
Y=534
W=166
H=24
FontFace=Sans
FontSize=9
FontColor=245,248,255,255
Text="HDD  |  /: %1%  Home: %2%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]
"""


# =============================================================================
# 9. ArcticRingsCluster (Photo 9: 11 Frosted White & Azure Circular Ring Medallions)
# =============================================================================
def build_arctic_rings_cluster():
    pods = [
        # (name, cx, cy, r, measure, label_fmt, sub_text, font_size)
        ("Clock", 242, 232, 68, "MeasureSecond", "%1", "TIME", 20),
        ("Trash", 738, 224, 68, "MeasureRoot", "DISK", "STORAGE", 16),
        ("Wifi", 490, 272, 52, "MeasureBattery", "100", "ONLINE", 18),
        ("Up", 374, 326, 52, "MeasureNetOutKB", "%1", "UP KB/S", 14),
        ("Down", 606, 326, 52, "MeasureNetInKB", "%1", "DOWN KB/S", 14),
        ("Cpu", 490, 444, 82, "MeasureCPU", "%1", "CPU %", 34),
        ("Ram", 322, 444, 52, "MeasureRAM", "%1", "RAM", 18),
        ("Swap", 658, 444, 52, "MeasureSWAP", "%1", "SWAP", 18),
        ("DiskC", 374, 558, 52, "MeasureRoot", "%1", "DISK /", 18),
        ("DiskE", 606, 558, 52, "MeasureHome", "%1", "HOME", 18),
        ("Vol", 490, 602, 52, "MeasureWeatherTemp", "%1", "WEATHER", 14),
    ]
    shapes = [
        # Top Media Player Medallion (cx=490, cy=122, r=82)
        "Shape=Ellipse 490,122,82,82 | Fill LinearGradient 135 | 245,250,255,235 | 205,218,235,235 | StrokeWidth 3 | Stroke Color 255,255,255,245",
        "Shape2=Ellipse 490,122,68,68 | Fill Color 0,0,0,0 | StrokeWidth 8 | Stroke Color 30,136,215,150",
        "Shape3=Ellipse 490,122,56,56 | Fill Color 242,247,255,240 | StrokeWidth 2 | Stroke Color 55,155,225,180",
        "Shape4=Ellipse 490,122,28,28 | Fill Color 248,252,255,250 | StrokeWidth 2 | Stroke Color 55,155,225,210",
    ]
    idx = 5
    meters = []
    for name, cx, cy, r, meas, val_fmt, sub_txt, fsize in pods:
        shapes.append(
            f"Shape{idx}=Ellipse {cx},{cy},{r},{r} | Fill LinearGradient 135 | 245,250,255,235 | 205,218,235,235 | StrokeWidth 2.5 | Stroke Color 255,255,255,245"
        )
        shapes.append(
            f"Shape{idx+1}=Ellipse {cx},{cy},{r-9},{r-9} | Fill Color 0,0,0,0 | StrokeWidth 6 | Stroke Color 175,205,235,160"
        )
        idx += 2
        val_meas = "MeasureTime" if name == "Clock" else meas
        if name == "Vol":
            act = "LeftMouseUpAction=[!WeatherPopup]"
        elif name == "Clock":
            act = "LeftMouseUpAction=[!CalendarPopup]"
        elif name in ("Trash", "DiskC"):
            act = 'LeftMouseUpAction=["xdg-open" "/"]'
        elif name == "DiskE":
            act = 'LeftMouseUpAction=["xdg-open" "~"]'
        elif name == "Wifi":
            act = "LeftMouseUpAction=[!NotesPopup]"
        else:
            act = "LeftMouseUpAction=[!OpenControlCenter]"
        meters.append(
            f"""[MeterArcRing{name}]
Meter=Roundline
MeasureName={meas}
X={cx - r}
Y={cy - r}
W={r * 2}
H={r * 2}
StartAngle=4.712
RotationAngle=6.283
LineStart={r - 12}
LineLength={r - 6}
Solid=1
LineColor=18,132,215,245

[MeterArcVal{name}]
Meter=String
MeasureName={val_meas}
X={cx}
Y={cy - fsize // 2 - 4}
W={r * 2 - 16}
H={fsize + 18}
StringAlign=Center
FontFace=Sans
FontSize={fsize}
FontColor=72,82,96,245
Text="{val_fmt}"
AntiAlias=1
{act}

[MeterArcSub{name}]
Meter=String
X={cx}
Y={cy + r // 2 - 4}
StringAlign=Center
FontFace=Sans
FontSize=7
FontColor=90,102,118,240
Text="{sub_txt}"
AntiAlias=1
{act}
"""
        )

    return f"""[Rainmeter]
Update=1000
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=980
SkinHeight=680
AutoFit=1

[Metadata]
Name=ArcticRingsCluster
Author=Trad Desktop
Information=12 Frosted White & Azure Circular Ring Medallions for Media, Clock, CPU, RAM, Network, Disks & Weather

{make_common_measures()}

[MeterArcticMedallions]
Meter=Shape
X=0
Y=0
{chr(10).join(shapes)}

[MeterTopMediaRing]
Meter=Roundline
MeasureName=MeasureProgress
X=408
Y=40
W=164
H=164
StartAngle=4.712
RotationAngle=6.283
LineStart=64
LineLength=72
Solid=1
LineColor=14,128,215,255

[MeterTopPrev]
Meter=Shape
X=437
Y=111
W=22
H=22
Shape=Rectangle 3,5,2.2,12,1 | Fill Color 75,88,105,245 | StrokeWidth 0
Shape2=Polygon 6.5,11, 16,5, 16,17 | Fill Color 75,88,105,245 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Previous"]

[MeterTopPlay]
Meter=Shape
X=479
Y=111
W=22
H=22
Hidden=[MeasureIsPlaying]
Shape=Polygon 16,11, 6,5, 6,17 | Fill Color 18,132,215,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterTopPause]
Meter=Shape
X=479
Y=111
W=22
H=22
Hidden=[MeasureIsPaused]
Shape=Rectangle 6,5,3.2,12,1 | Fill Color 18,132,215,255 | StrokeWidth 0
Shape2=Rectangle 12.5,5,3.2,12,1 | Fill Color 18,132,215,255 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterTopNext]
Meter=Shape
X=521
Y=111
W=22
H=22
Shape=Polygon 15.5,11, 6,5, 6,17 | Fill Color 75,88,105,245 | StrokeWidth 0
Shape2=Rectangle 17,5,2.2,12,1 | Fill Color 75,88,105,245 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Next"]

{"".join(meters)}
"""


# =============================================================================
# 10. TypographyFillSuite (Photo 10: Refined Tech & Cyber Editorial HUD + Live Album/Video Cover)
# =============================================================================
def build_typography_fill():
    return f"""[Rainmeter]
Update=500
AccurateText=1
AnchorX=Center
AnchorY=Center
SkinWidth=1240
SkinHeight=680
AutoFit=1

[Metadata]
Name=TypographyFillSuite
Author=Trad Desktop
Information=Refined Cyber-Editorial Typographic HUD with Dual-Tone Clock, Tactical Weather Grid, Stacked Date, Sticky Notes & Live Video/Album Thumbnail

{make_common_measures()}

; --- REFINED CYBER-EDITORIAL HUD FRAMES, ACCENT LINES & MEDIA CARD ---
[MeterTypoShapes]
Meter=Shape
X=0
Y=0
; 1. Top-Left Weather Cyber HUD Panel
Shape=Rectangle 44,36,496,184,10 | Fill LinearGradient 135 | 16,22,34,195 | 10,14,22,215 | StrokeWidth 1.5 | Stroke Color #AccentColor#
Shape2=Line 44,142,540,142 | StrokeWidth 1 | Stroke Color 90,115,150,120
Shape3=Line 336,48,336,208 | StrokeWidth 1 | Stroke Color 90,115,150,120
; 2. Top-Right Stacked Date & Sticky Notes Cyber Card
Shape4=Rectangle 836,36,360,218,10 | Fill LinearGradient 135 | 16,22,34,195 | 10,14,22,215 | StrokeWidth 1.5 | Stroke Color #AccentColor#
Shape5=Line 836,196,1196,196 | StrokeWidth 1 | Stroke Color 90,115,150,130
Shape6=Line 992,48,992,188 | StrokeWidth 1 | Stroke Color 90,115,150,110
; 3. Center Dual-Tone Cyber Clock Frame
Shape7=Rectangle 44,244,764,252,14 | Fill LinearGradient 135 | 14,18,28,175 | 8,11,18,195 | StrokeWidth 1.5 | Stroke Color 95,120,160,135
Shape8=Line 64,244,220,244 | StrokeWidth 3 | Stroke Color 235,115,135,255
Shape9=Line 510,244,670,244 | StrokeWidth 3 | Stroke Color #AccentColor#
; 4. Bottom 5-Metric Cyber Telemetry Bar
Shape10=Rectangle 44,520,764,84,10 | Fill LinearGradient 135 | 16,22,34,205 | 10,14,22,225 | StrokeWidth 1.5 | Stroke Color #AccentColor#
Shape11=Line 197,534,197,590 | StrokeWidth 1 | Stroke Color 90,115,150,110
Shape12=Line 350,534,350,590 | StrokeWidth 1 | Stroke Color 90,115,150,110
Shape13=Line 502,534,502,590 | StrokeWidth 1 | Stroke Color 90,115,150,110
Shape14=Line 655,534,655,590 | StrokeWidth 1 | Stroke Color 90,115,150,110
; 5. Bottom-Right Media & Video Thumbnail Card
Shape15=Rectangle 836,276,360,328,10 | Fill LinearGradient 135 | 22,24,34,230 | 14,16,24,245 | StrokeWidth 1.5 | Stroke Color #AccentColor#
; Fallback vector music note emblem (shown when no cover art is active)
Shape16=Ellipse 1016,364,30,30 | Fill Color 26,32,46,210 | StrokeWidth 1.5 | Stroke Color #AccentColor#
Shape17=Ellipse 1009,371,4.5,3.5 | Fill Color #AccentColor# | StrokeWidth 0
Shape18=Ellipse 1023,368,4.5,3.5 | Fill Color #AccentColor# | StrokeWidth 0
Shape19=Line 1013,371,1013,353 | StrokeWidth 2.2 | Stroke Color #AccentColor#
Shape20=Line 1027,368,1027,350 | StrokeWidth 2.2 | Stroke Color #AccentColor#
Shape21=Line 1013,353,1027,350 | StrokeWidth 3 | Stroke Color #AccentColor#

; --- LIVE SONG / VIDEO THUMBNAIL (AUTO-FIT) + TRANSPORT OVERLAY ---
[MeterTypoCoverArt]
Meter=Image
MeasureName=MeasureCover
X=844
Y=284
W=344
H=174
PreserveAspectRatio=2
SolidColor=0,0,0,0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterTypoTransportOverlay]
Meter=Shape
X=0
Y=0
Shape=Rectangle 844,458,344,74,0 | Fill LinearGradient 0 | 128,54,78,225 | 64,32,58,235 | StrokeWidth 0
Shape2=Ellipse 946,495,20,20 | Fill Color 18,22,32,140 | StrokeWidth 1.5 | Stroke Color 235,195,125,235
Shape3=Ellipse 1016,495,24,24 | Fill Color 18,22,32,160 | StrokeWidth 1.8 | Stroke Color #AccentColor#
Shape4=Ellipse 1086,495,20,20 | Fill Color 18,22,32,140 | StrokeWidth 1.5 | Stroke Color 235,195,125,235

; --- TOP-LEFT WEATHER BLOCK (REFINED CYBER PROPORTIONS) ---
[MeterTypoHigh]
Meter=String
MeasureName=MeasureWeatherHigh
MeasureName2=MeasureWeatherUnit
X=64
Y=52
W=255
H=34
FontFace=Orbitron
FontSize=20
FontColor=235,125,142,250
Text="HIGH  %1%2"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterTypoLow]
Meter=String
MeasureName=MeasureWeatherLow
MeasureName2=MeasureWeatherUnit
X=64
Y=94
W=255
H=34
FontFace=Orbitron
FontSize=20
FontColor=135,185,235,250
Text="LOW   %1%2"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterTypoLoc]
Meter=String
X=64
Y=152
W=260
H=20
ClipString=1
FontFace=Rajdhani
FontSize=11
FontColor=175,190,212,240
Text="LOC // #WeatherLocation#"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterTypoCond]
Meter=String
MeasureName=MeasureWeatherCond
X=64
Y=176
W=260
H=24
ClipString=1
FontFace=Orbitron
FontSize=13
FontColor=#AccentColor#
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterTypoOut1]
Meter=String
MeasureName=MeasureWeekdayShort
X=356
Y=54
W=168
H=26
FontFace=Orbitron
FontSize=15
FontColor=230,238,250,245
Text="DAY // %1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterTypoOut1Sub]
Meter=String
MeasureName=MeasureWeatherTemp
MeasureName2=MeasureWeatherUnit
X=356
Y=88
W=168
H=22
FontFace=Share Tech Mono
FontSize=11
FontColor=#AccentColor#
Text="NOW: %1%2"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterTypoOut2]
Meter=String
X=356
Y=152
W=168
H=22
FontFace=Orbitron
FontSize=12
FontColor=145,185,235,245
Text="PRECIPITATION"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterTypoOut2Sub]
Meter=String
MeasureName=MeasureWeatherRain
MeasureName2=MeasureWeatherHum
X=356
Y=178
W=168
H=22
FontFace=Share Tech Mono
FontSize=10
FontColor=195,210,230,240
Text="RAIN %1%  •  HUM %2%"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

; --- TOP-RIGHT STACKED DATE & STICKY NOTES ---
[MeterTypoMonth]
Meter=String
MeasureName=MeasureMonthShort
X=914
Y=48
W=140
H=30
StringAlign=Center
FontFace=Orbitron
FontSize=18
FontColor=235,125,142,250
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterTypoDay]
Meter=String
MeasureName=MeasureDay
X=914
Y=80
W=140
H=64
StringAlign=Center
FontFace=Orbitron
FontSize=44
FontColor=#AccentColor#
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterTypoYear]
Meter=String
MeasureName=MeasureYear
X=914
Y=154
W=140
H=24
StringAlign=Center
FontFace=Share Tech Mono
FontSize=14
FontColor=225,195,115,245
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterTypoNoteHdr]
Meter=String
X=1094
Y=52
W=180
H=22
StringAlign=Center
FontFace=Orbitron
FontSize=9
FontColor=#AccentColor#
Text="#NoteTitle# [EDIT]"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterTypoNoteBody]
Meter=String
X=1008
Y=80
W=172
H=104
ClipString=2
FontFace=Sans
FontSize=9
FontColor=215,225,240,240
Text="#NoteBody#"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterTypoQuick1]
Meter=String
X=884
Y=214
W=76
H=24
StringAlign=Center
FontFace=Share Tech Mono
FontSize=9
FontColor=190,210,235,245
Text="[FILES]"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

[MeterTypoQuick2]
Meter=String
X=972
Y=214
W=76
H=24
StringAlign=Center
FontFace=Share Tech Mono
FontSize=9
FontColor=#AccentColor#
Text="[NOTES]"
AntiAlias=1
LeftMouseUpAction=[!NotesPopup]

[MeterTypoQuick3]
Meter=String
X=1060
Y=214
W=76
H=24
StringAlign=Center
FontFace=Share Tech Mono
FontSize=9
FontColor=190,210,235,245
Text="[WEATHER]"
AntiAlias=1
LeftMouseUpAction=[!WeatherPopup]

[MeterTypoQuick4]
Meter=String
X=1148
Y=214
W=76
H=24
StringAlign=Center
FontFace=Share Tech Mono
FontSize=9
FontColor=190,210,235,245
Text="[STUDIO]"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

; --- CENTER REFINED CYBER DUAL-TONE CLOCK ---
[MeterTypoHour]
Meter=String
MeasureName=MeasureHour12
X=215
Y=288
StringAlign=Center
FontFace=Orbitron
FontSize=92
FontColor=235,124,142,250
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterTypoAmPm]
Meter=String
MeasureName=MeasureAMPM
MeasureName2=MeasureSecond
X=426
Y=346
StringAlign=Center
FontFace=Share Tech Mono
FontSize=19
FontColor=185,200,222,245
Text="%1#CRLF#:%2"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

[MeterTypoMin]
Meter=String
MeasureName=MeasureMinute
X=635
Y=288
StringAlign=Center
FontFace=Orbitron
FontSize=92
FontColor=#AccentColor#
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CalendarPopup]

; --- BOTTOM 5-METRIC CYBER TELEMETRY BAR ---
[MeterTypoCpu]
Meter=String
MeasureName=MeasureCPU
X=120
Y=538
StringAlign=Center
FontFace=Share Tech Mono
FontSize=13
FontColor=235,132,148,250
Text="CPU#CRLF#%1%"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

[MeterTypoRam]
Meter=String
MeasureName=MeasureRAM
X=273
Y=538
StringAlign=Center
FontFace=Share Tech Mono
FontSize=13
FontColor=#AccentColor#
Text="RAM#CRLF#%1%"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

[MeterTypoTemp]
Meter=String
MeasureName=MeasureTemp
X=426
Y=538
StringAlign=Center
FontFace=Share Tech Mono
FontSize=13
FontColor=235,192,105,250
Text="TEMP#CRLF#%1°C"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

[MeterTypoDisk]
Meter=String
MeasureName=MeasureRoot
X=578
Y=538
StringAlign=Center
FontFace=Share Tech Mono
FontSize=13
FontColor=135,185,245,250
Text="DISK /#CRLF#%1%"
AntiAlias=1
LeftMouseUpAction=["xdg-open" "~"]

[MeterTypoBatt]
Meter=String
MeasureName=MeasureNetInKB
X=731
Y=538
StringAlign=Center
FontFace=Share Tech Mono
FontSize=13
FontColor=190,205,225,250
Text="NET IN#CRLF#%1 KB/s"
AntiAlias=1
LeftMouseUpAction=[!OpenControlCenter]

; --- BOTTOM-RIGHT MUSIC TRANSPORT (CRISP VECTOR ICONS) & TRACK METADATA ---
[MeterTypoPrev]
Meter=Shape
X=935
Y=484
W=22
H=22
Shape=Rectangle 3,5,2.2,12,1 | Fill Color 235,205,145,250 | StrokeWidth 0
Shape2=Polygon 6.5,11, 16,5, 16,17 | Fill Color 235,205,145,250 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Previous"]

[MeterTypoPlay]
Meter=Shape
X=1005
Y=484
W=22
H=22
Hidden=[MeasureIsPlaying]
Shape=Polygon 16,11, 6,5, 6,17 | Fill Color #AccentColor# | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterTypoPause]
Meter=Shape
X=1005
Y=484
W=22
H=22
Hidden=[MeasureIsPaused]
Shape=Rectangle 6,5,3.2,12,1 | Fill Color #AccentColor# | StrokeWidth 0
Shape2=Rectangle 12.5,5,3.2,12,1 | Fill Color #AccentColor# | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterTypoNext]
Meter=Shape
X=1075
Y=484
W=22
H=22
Shape=Polygon 15.5,11, 6,5, 6,17 | Fill Color 235,205,145,250 | StrokeWidth 0
Shape2=Rectangle 17,5,2.2,12,1 | Fill Color 235,205,145,250 | StrokeWidth 0
LeftMouseUpAction=[!CommandMeasure MeasureTrack "Next"]

[MeterTypoTrack]
Meter=String
MeasureName=MeasureTrack
X=852
Y=546
W=328
H=20
ClipString=1
FontFace=Sans
FontSize=11
FontColor=235,242,255,250
Text="%1"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]

[MeterTypoArtist]
Meter=String
MeasureName=MeasureArtist
MeasureName2=MeasurePosition
MeasureName3=MeasureDuration
X=852
Y=572
W=328
H=18
ClipString=1
FontFace=Share Tech Mono
FontSize=9
FontColor=#AccentColor#
Text="%1   •   %2 / %3"
AntiAlias=1
LeftMouseUpAction=[!CommandMeasure MeasureTrack "PlayPause"]
"""


SUITES_TO_BUILD = {
    "MidnightDeerSuite": build_midnight_deer,
    "MaterialPillSuite": build_material_pill_suite,
    "XeniumDashboard": build_xenium_dashboard,
    "GreenRibbonSuite": build_green_ribbon_pro,
    "CyberYellowHUD": build_cyber_yellow_hud,
    "ShieldOSHub": lambda: build_shield_os(dark_plate=False),
    "ShieldOSDark": lambda: build_shield_os(dark_plate=True),
    "DiagonalMinimalSuite": build_diagonal_minimal,
    "ArcticRingsCluster": build_arctic_rings_cluster,
    "TypographyFillSuite": build_typography_fill,
}


def main():
    os.makedirs(SUITES_DIR, exist_ok=True)
    os.makedirs(COMMUNITY_DIR, exist_ok=True)

    for name, builder in SUITES_TO_BUILD.items():
        ini_content = builder()
        suite_folder = os.path.join(SUITES_DIR, name)
        os.makedirs(suite_folder, exist_ok=True)
        ini_path = os.path.join(suite_folder, f"{name}.ini")
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(ini_content)

        # Also package an installable .rmskin in community/<name>.rmskin
        rmskin_path = os.path.join(COMMUNITY_DIR, f"{name}.rmskin")
        rmskin_ini = (
            "[rmskin]\n"
            f"Name={name}\n"
            "Author=Trad Desktop\n"
            "Version=1.2.0\n"
            f"LoadType=Skin\n"
            f"Load={name}/{name}.ini\n"
        )
        with zipfile.ZipFile(rmskin_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("RMSKIN.ini", rmskin_ini)
            zf.writestr(f"Skins/{name}/{name}.ini", ini_content)

        print(f"Generated suite: {ini_path} and package: {rmskin_path}")


if __name__ == "__main__":
    main()
