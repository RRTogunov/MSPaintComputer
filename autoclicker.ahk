; #AutoHotkey v2
#Requires AutoHotkey v2.0

; MS Paint logic gate auto-clicker triggered by hotkey: CapsLock + `
CapsLock & `::{
	;;;;;;;; 100% circles ;;;;;;;;;;;;;;;;;;
	; initial parameters
	xpos_0  := 1842
	ypos_0 := 289
	dx_lead := 24
	dx_inst := 5
	dx_col := 50
	dy_row := 13
	dt := 20
	; init positions
	xpos_i := xpos_0
	ypos_i := ypos_0
	; get first colour
	col_i := PixelGetColor(xpos_i, ypos_i, "RGB")
	send("b")  ; get bucket tool ready

	; loop
	While (col_i != "0xED1C24")
	{
		Sleep(dt)
		send("i")  ; get eye-droslepper tool ready
		MouseClick(, xpos_i, ypos_i)  ; copy first colour
		MouseClick(, xpos_i + dx_lead, ypos_i)  ; paste colour
		Sleep(dt)
		send("i")
		MouseClick(, xpos_i + dx_inst, ypos_i)  ; copy second colour
		MouseClick(, xpos_i + dx_lead, ypos_i)  ; paste colour
		; update y position
		ypos_i := ypos_i + dy_row
		; check stop colour
		col_i := PixelGetColor(xpos_i, ypos_i, "RGB")
		; move to next column
		if (col_i = "0xFFAEC9")
		{
			xpos_i := xpos_i - dx_col  ; update x
			ypos_i := ypos_0  ; reset y
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