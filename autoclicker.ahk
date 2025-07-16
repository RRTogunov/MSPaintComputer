; #AutoHotkey v2
#Requires AutoHotkey v2.0

; MS Paint logic gate auto-clicker triggered by hotkey: CapsLock + `
CapsLock & `::{
	; check if using classic MS paint
	classic_paint := WinActive("ahk_exe mspaint1.exe") > 0

	;;;;;;;; 100% circles ;;;;;;;;;;;;;;;;;;

    ; initial parameters
    xpos_0  := 1843 + classic_paint*6 ;1842
    ypos_0 := 289 - classic_paint*36


    dx_lead := 21 ; 24
    dx_inst := 2 ; 5
    dx_col := 50
    dy_row := 13
    dt := 15

    ; init positions
    xpos_i := xpos_0
    ypos_i := ypos_0

	; setup window
	WinMaximize "A"  ; maximise window
	sleep(10)
	if classic_paint {
		MouseClick(, 165, 53)
		MouseClick(, 137, 99)
		MouseClick(, 104, 51)
	} else {
		Send("^0")  ; zoom to 100%
	}
	sleep(10)
	MouseClick(, 1888 - classic_paint*12, 1057 + classic_paint*48, 5)  ; move to right
	MouseClick(, 1911, 204 - classic_paint*2, 5)  ; move to top
	sleep(10)

    ; get first colour
    col_i := PixelGetColor(xpos_i, ypos_i, "RGB")
	if classic_paint {
		MouseClick(, 313, 95)  ; get bucket tool ready
	} else {
		Send("p")  ; get bucket tool ready
		sleep(10)
		send("b")
		sleep(10)
		Send("i")
	}

    ; loop
   While (g_KeepRunning && col_i != "0xED1C24" && ypos_i < 1051) {
        Sleep(dt)
		if classic_paint {
			MouseClick(, 315, 131)  ; select eye dropper tool
		} else {
			Send("i")
		}
        MouseClick(, xpos_i, ypos_i)  ; copy first colour
		Sleep(5)
        MouseClick(, xpos_i + dx_lead, ypos_i)  ; paste colour
        Sleep(dt)
        if classic_paint {
			MouseClick(, 315, 131)  ; select eye dropper tool
		} else {
			Send("i")
		}
        MouseClick(, xpos_i + dx_inst, ypos_i)  ; copy second colour
		Sleep(5)
        MouseClick(, xpos_i + dx_lead, ypos_i)  ; paste colour

        ypos_i += dy_row
		;Send("i")
        col_i := PixelGetColor(xpos_i, ypos_i, "RGB")

        if (col_i = "0xFFAEC9") {
            xpos_i -= dx_col
            ypos_i := ypos_0
        }
    }
	;;;;;;;; 200% circles ;;;;;;;;;;;;;;;;;;
	;; initial parameters
	;xpos_i := 1760
	;ypos_i := 390
	;; get first colour
	;col_i := PixelGetColor(xpos_i, ypos_i, "RGB")
	;send("b")  ; get bucket tool ready
	;; loop
	;While (col_i != "0xED1C24")
	;{
	;	Sleep(30)
	;	send("i")  ; get eye-droslepper tool ready
	;	MouseClick(, xpos_i, ypos_i)  ; copy first colour
	;	MouseClick(, xpos_i + 50, ypos_i)  ; paste colour
	;	Sleep(30)
	;	send("i")
	;	MouseClick(, xpos_i + 10, ypos_i)  ; copy second colour
	;	MouseClick(, xpos_i + 50, ypos_i)  ; paste colour
	;	; update y position
	;	ypos_i := ypos_i + 26
	;	;~ ypos_i := ypos_i + 12		; check stop colour
	;	col_i := PixelGetColor(xpos_i, ypos_i, "RGB")
	;	; move to next column
	;	if (col_i = "0xFFAEC9")
	;	{
	;		xpos_i := xpos_i - 100  ; update x
	;		ypos_i := 390  ; reset y
	;	}
	;}
}

; Secondary hotkey - only active to stop the script
#HotIf g_KeepRunning
Esc::{
    global g_KeepRunning
    g_KeepRunning := false
    ToolTip("Stopping script...", 100, 100)
    SetTimer(() => ToolTip(), -2000)
}
#HotIf