"use strict";

var meaningchars = 0
var vm

window.stdin = ""

// https://github.com/michaelko/simpleterm
// Released under the terms of the WTFPL

function Terminal(host, width, height, addons) {
    this.w = width
    this.h = height
    this.parent = window.document.getElementById(host)
    this.y_base = 0
    this.x = 0
    this.y = 0
    this.cursorstate = 0
    this.colors = ["#000", "#e00", "#0e0", "#ee0", "#00e", "#e0e", "#0ee", "#eee"]
    this.def_attr = 7 << 3
    this.cur_att = this.def_attr
    this.buffer = ""
    // See: http://www.mediaevent.de/javascript/Extras-Javascript-Keycodes.html
    this.complete = false

    this.is_termjs = 1

    this.table = {
        8: "\x7f",
        9: "\t",
        13: "\r",
        10: "\n",
        27: "\x1b",
        33: "\x1b[5~",
        34: "\x1b[6~",
        35: "\x1bOF",
        36: "\x1bOH",
        37: "\x1b[D",
        38: "\x1b[A",
        39: "\x1b[C",
        40: "\x1b[B",
        45: "\x1b[2~",
        46: "\x1b[3~",
        112: '\x1bOP',
        113: '\x1bOQ',
        114: '\x1bOR',
        115: '\x1bOS',
        116: '\x1b[15~',
        117: '\x1b[17~',
        118: '\x1b[18~',
        119: '\x1b[19~',
        120: '\x1b[20~',
        121: '\x1b[21~',
        122: '\x1b[23~',
        123: '\x1b[24~',
    }
}


Terminal.prototype.open = function () {
    var y
    var rows = ['<table class="terminal-table">']

    this.lines = new Array()
    this.newline = new Array()

    for (y = 0; y < this.w; y++)
         this.newline[y] = 32 | (this.def_attr << 16)

    for (y = 0; y < this.h+1; y++)
        this.lines[y] = this.newline.slice()

    for (y = 0; y < this.h; y++)
        rows.push('<tr><td class="term" id="tline' + y + '"></td></tr>')

    this.applyStyles()
    rows.push('</table>')
    this.parent.innerHTML = rows.join('')
    this.refresh(0, this.h - 1)
    this.parent.addEventListener('keydown', this.keyDownHandler.bind(this))
    this.parent.addEventListener('keypress', this.keyPressHandler.bind(this))
    const that = this
    setInterval(function () {
        that.cursor_timer_cb()
    }, 500)
}

Terminal.prototype.refresh = function (y1, y2) {
    var y, html, c, x, cursor_x, mode, lastmode, ay
    for (y = y1; y <= y2; y++) {
        ay = (y + this.y_base) % this.h
        html = ""
        cursor_x = (y == this.y && this.cursor_state ) ?  this.x : NaN
        lastmode = this.def_attr
        for (x = 0; x < this.w; x++) {
            mode = this.lines[ay][x] >> 16
            c = this.lines[ay][x] & 0xffff
            if(cursor_x == x)
            	html += '<span class="termReverse">'
            if(cursor_x == x-1)
            	html += '</span>'
            if (mode != lastmode) {
                if (lastmode != this.def_attr)
                    html += '</span>'
                if (mode != this.def_attr)
                    html += '<span style="color:' + this.colors[(mode >> 3) & 7] + ';background-color:' + this.colors[mode & 7] + ';">'
            }
            var ttable={
            	32: "&nbsp;",
            	38: "&amp;",
            	60: "&lt;",
            	62: "&gt;",
            }
            html += (ttable[c] || (c<32 ? "&nbsp;" : String.fromCharCode(c)))
            lastmode = mode
        }
        if (lastmode != this.def_attr) {
            html += '</span>'
        }
       	document.getElementById("tline" + y).innerHTML = html
    }
}
Terminal.prototype.cursor_timer_cb = function () {
    this.cursor_state ^= 1
    this.refresh(this.y, this.y)
}
Terminal.prototype.show_cursor = function () {
    if (!this.cursor_state) {
        this.cursor_state = 1
        this.refresh(this.y, this.y)
    }
}

Terminal.prototype.esc_done = function (j) {
    this.complete = true
    return j
}
Terminal.prototype.handle_esc = function (i, string) {
    // A Escape sequence. Trying to parse it, in case it is not complete abort
    // and safe the bytes in buffer
    // http://www-user.tu-chemnitz.de/~heha/hs_freeware/terminal/terminal.htm
    // http://www.termsys.demon.co.uk/vtansi.htm
    // https://espterm.github.io/docs/VT100%20escape%20codes.html

    this.complete = false
    var j=1

    const first = string[i+1]
    const second = string[i+2]

    if(first=='['){

        if(second == 'C'){
            this.x++;
            this.refresh(this.y, this.y)
            return this.esc_done(2)
        }

        if(second == 'K'){
            console.log('159: ESC [ K : erase to end of line (inclusive)')
            this.refresh(this.y, this.y)
            return this.esc_done(2)
        }

        if(second == 'M'){
            console.log('159: ESC [ M : Move/scroll window down one line')
            this.refresh(this.y, this.y)
            return this.esc_done(2)
        }

        if(second == 'A'){
            console.log('159: ESC [ A : arrow up')
            if (this.y>0) this.y--;
            this.refresh(this.y, this.y)
            return this.esc_done(2)
        }

        if(second == 'm'){
            this.cur_att = 7 << 3
            return this.esc_done(2)
        }

        if(second == '0' && string[i+3] == 'm'){
            this.cur_att = 7 << 3
            return this.esc_done(3)
        }

        if(string.slice(i+1).match(/^\[[0-9;]*m/)){
            var m=/^\[[0-9;]*m/.exec(string.slice(i+1))
            var numbers=m[0].match(/[0-9]*/g)

            for(var n=0;n<numbers.length;n++){
                var num=parseInt(numbers[n])
                if(isNaN(num))
                    continue

                if(num>29 && num <38){
                    // Foreground
                    this.cur_att &= 7
                    this.cur_att |= (num-30) << 3
                    this.complete = true
                }

                if(num>39 && num<48){
                    // Background
                    this.cur_att &= 7 << 3
                    this.cur_att |= num-40
                    this.complete = true
                }
            }
            return this.esc_done(m[0].length)
         }

         if(string.slice(i+1).match(/^\[[0-9]+,[0-9]+[Hf]/)){    // goto xy
            var pos= /^\[([0-9]+),([0-9]+)[Hf]/.exec(string.slice(i+1))
            this.x = parseInt(pos[1])
            this.y = parseInt(pos[2])
            return this.esc_done(1+pos[0].length)
         }

        if(string.slice(i+1).match(/^\[2J/)){     // clear screen
            for (y = 0; y < this.h+1; y++)
                this.lines[y] = this.newline.slice()
            this.y_base=0
            this.x=this.y=0
            this.refresh(0,this.h-1)
            return this.esc_done(3)
         }

         if(string.slice(i+1).match(/^\[0?J/)){     // clear screen from cursor down
            for (x = this.x  ; x < this.w  ; x++)
                this.lines[(this.y + this.y_base)%this.h][x] = 32 | this.def_attr << 16

            for (y = this.y+1; y < this.h+1; y++)
                this.lines[(y + this.y_base)%this.h] = this.newline.slice()

            this.refresh(0,this.h-1)
            return this.esc_done( (/^\[0?J/.exec(string.slice(i+1))).length+1 )
         }

         if(string.slice(i+1).match(/^\[6n/)){
            console.log("???:" + string.fromCharCode(33)+"["+this.x+";"+this.y+"R" )
            return this.esc_done(3)
         }
    } else if( typeof(string[i+1]) == "string"){
        // There is a charater after esc, but it's not '[', simply ignor the esc.
        this.buffer=string.slice(i+1)
        this.complete=true
    }
    return j
}

Terminal.prototype.write = function (string) {
	//alert(string)
	string=this.buffer+string
	this.buffer=""
//write:
	for(var i=0;i<string.length;i++){
		switch(string.charCodeAt(i)){

		    case 10:  // \n
                this.y++
                break

            case 13:  // \r
                this.x = 0
                break

            case 8:  // Backspace
                if (this.x > 0) {
                    this.x--
                }
                break

            case 9: // Vertical Tab
                const n = (this.x + 8) & ~7
                if (n <= this.w) {
                    this.x = n
                }
                break

            case 27:   // ^[
                const j = this.handle_esc(i, string)

                if(!this.complete){
                    //this.buffer = string.slice(i)
                    console.log('TODO:FIXME:['+string.slice(i)+"]")
                    i+=j
                    break
                } else {
                    i+=j
                }
                break

		    default: // Normal char. Just display.
                this.lines[(this.y + this.y_base)%this.h][this.x++]=string.charCodeAt(i) | this.cur_att << 16
		}

		if(this.x >= this.w){  // End of Line
			this.x=0
			this.y++
		}
		if (this.y >= this.h) {
            this.y_base++
            this.y--
            this.lines[(this.y + this.y_base) % this.h]=this.newline.slice()
            this.refresh(0, this.h-1)
        }
                // -1 because otherwise the cursor in the old position at a higher line might be still visible.
        this.refresh(Math.max(0,this.y-1), this.y)
	}
}

Terminal.prototype.keyDownHandler = function (event) {
    var key
    //console.log("keyDownHandler")
    key = this.table[event.keyCode]

    if (event.ctrlKey && event.keyCode >= 65 && event.keyCode <= 90) {
        key = String.fromCharCode(event.keyCode - 64)
    }
    if (event.altKey || event.metaKey) {
        key = "\x1b" + key
    }
    if (key) {
        if (event.stopPropagation) event.stopPropagation()
        if (event.preventDefault) event.preventDefault()
        this.show_cursor()
        this.key_rep_state = 1
        this.handler(key, event)
        return false
    } else {
        this.key_rep_state = 0
        return true
    }
}

Terminal.prototype.keyPressHandler = function (event) {
    if (event.stopPropagation) event.stopPropagation()
    if (event.preventDefault) event.preventDefault()
    if (
        !this.key_rep_state &&
        ( event.charCode != undefined ) &&
        ( event.charCode !=0 ) &&
        !event.altKey && !event.metaKey
    ) {
        this.show_cursor()
        this.handler(String.fromCharCode(event.charCode), event)
        return false
    } else {
        return true
    }
}

Terminal.prototype.applyStyles = function () {
  if (!Terminal.stylesApplied) {
    Terminal.stylesApplied = true
    var css = '.term { font-family: courier,fixed,swiss,monospace,sans-serif; font-size: 14px; color: #f0f0f0; background: #000000; }' +
      '.terminal-table { border-collapse: collapse; }' +
      '.termReverse { color: #000000; background: #00ff00; }'

    var head = document.head || document.getElementsByTagName('head')[0]
    var style = document.createElement('style')

    style.type = 'text/css'

    if (style.styleSheet){
      style.styleSheet.cssText = css
    } else {
      style.appendChild(document.createTextNode(css))
    }

    head.appendChild(style)
  }
}

Terminal.prototype.set_vm_handler = function (ref_vm, ref_handler, ref_helper) {
    vm = ref_vm
    this.handler = ref_handler || handlevt
    vm.vt.helper = ref_helper || helper

}

Terminal.stylesApplied = false


function ESC(data) {
    return String.fromCharCode(27)+data
}


// Ctrl+L is mandatory ! xterm.js 4.7.0+
function helper(term, kc, e) {
    var x,y
    var vtsix = false
    // xterm3/4 ?
    if (!term.is_termjs) {
        if (!term.buffer) {
            //xtermsixel
            vtsix = true
            x = 0+term._core.buffer.x
            y = 0+term._core.buffer.y + term._core.buffer.ybase

        } else {
            x = 0+term.buffer.active.cursorX
            y = 0+term.buffer.active.cursorY
        }

    // simpleterm
    } else {
        x = 0 + term.x
        y = 0 + term.y
    }
    //
    if (e.ctrlKey) {
        console.log('ctrl + '+ kc)
        if (kc == 76) {
            console.log("Cursor pos clrscr :",x,y)
            var cy = 0 + y
            if ( cy > 0) {
                var cx = 0 + x
                if (cy <= term.rows) {
                    term.write( ESC("[B") )
                    term.write( ESC("[J") )
                    term.write( ESC("[A") )
                }

                term.write( ESC("[A") )
                term.write( ESC("[K") )
                term.write( ESC("[1J"))

                for (var i=1;i<cy;i++) {
                    term.write( ESC("[A") )
                    term.write( ESC("[M") )
                }
                term.write( ESC("[M") )
                if (cx > 0) {
                    if (!vtsix)
                        term.write( ESC("["+cx+"C") )

                }
            }
            return false
        }
    }
    return true
}




function handlevt(vtchar, e) {

    const term = vm.vt.xterm

    function ESC(data) {
        return String.fromCharCode(27)+data
    }

    const keymapping = {
        'ArrowUp' : ESC("[A"),
        'ArrowDown' : ESC("[B"),
        'ArrowRight' : ESC("[C"),
        'ArrowLeft' : ESC("[D"),
        'Home' : ESC("[H"),
        'End' : ESC("[F"),
        'Delete' : ESC("[C" + String.fromCharCode(127)),
    }

    const printable = !e.altKey && !e.altGraphKey && !e.ctrlKey && !e.metaKey;
    const kc = e.keyCode

    // that helper handle ctrl+L for clearing screen while keeping cursor pos in the line
    if ( !vm.vt.helper(vm.vt.xterm, kc, e) )
        return;

    var key = e.key

    if (key.length>1) {
        if ( key in keymapping ) {
            meaningchars++
            window.stdin += keymapping[key]
            return
        } else {
            key = String.fromCharCode(kc)
        }
        console.log('key '+ e.key +" => [" + key + ']  was ['  + kc + ']' )
    }

    if (kc <=27) {

        console.log("KBD : "+kc+ " len= "+key.length+" mc="+  meaningchars)

        // do not complete tab for nothing to complete until two tabs
        if (kc==9) {
            if ( meaningchars == 0 ) {
                return
            }
        }

        // do not interpret empty lines
        if (kc==13) {
            if ( meaningchars == 0 ) {
                term.write("\r\n>>> ")
                return
            }
            window.stdin_flush = true
            meaningchars = 0
        }

    }

    const utf = unescape(encodeURIComponent(key))

    if (utf.substr(0,1) != key.substr(0,1) ) {
        console.log("utf-8:" + utf )
        window.stdin += utf
    } else {
        window.stdin += key
    }

    if ( (kc!=13) &&  (kc!=9) ) {
        meaningchars++
    }

    //local echo

    if (vm.stdin_echo) {
        term.write(key)
        if (kc == 13) term.write("\n")
    }
}





export { Terminal, helper, handlevt }
