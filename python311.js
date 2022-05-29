"use strict";

window.__defineGetter__('__FILE__', function() {
  return (new Error).stack.split('/').slice(-1).join().split('?')[0].split(':')[0] +": "
})

const DBG=0


//register
if (typeof register === 'undefined' ) {

String.prototype.rsplit = function(sep, maxsplit) {
    var split = this.split(sep);
    return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
}

String.prototype.endswith = function(suffix) {
    return this.indexOf(suffix, this.length - suffix.length) !== -1;
}

String.prototype.startswith = function(prefix) {
    return this.indexOf(prefix, 0) !== -1;
}

function defined(e,o){
    if (typeof o === 'undefined' || o === null)
        o = window;
    try {
        e = o[e];
    } catch (x) { return false }

    if (typeof e === 'undefined' || e === null)
        return false;
    return true;
}

function register(fn,fn_dn){
    if (!defined(fn_dn) )
        fn_dn = fn.name;
    console.log('  |-- added ' + fn_dn );
    window[fn_dn]=fn;
}

register(register)
register(defined);

function repr(obj) {
    if(obj == null || typeof obj === 'string' || typeof obj === 'number') return String(obj);
    if(obj.length) return '[' + Array.prototype.map.call(obj, repr).join(', ') + ']';
    if(obj instanceof HTMLElement) return '<' + obj.nodeName.toLowerCase() + '>';
    if(obj instanceof Text) return '"' + obj.nodeValue + '"';
    if(obj.toString) return obj.toString();

    return JSON.stringify(obj);
}
register(repr)


// https://github.com/ljharb/is-callable/blob/master/index.js
var fnToStr = Function.prototype.toString;

var constructorRegex = /^\s*class\b/;
var isES6ClassFn = function isES6ClassFunction(value) {
    try {
        var fnStr = fnToStr.call(value);
        return constructorRegex.test(fnStr);
    } catch (e) {
        return false; // not a function
    }
};

var tryFunctionObject = function tryFunctionToStr(value) {
    try {
        if (isES6ClassFn(value)) { return false; }
        fnToStr.call(value);
        return true;
    } catch (e) {
        return false;
    }
};

var toStr = Object.prototype.toString;
var fnClass = '[object Function]';
var genClass = '[object GeneratorFunction]';
var hasToStringTag = typeof Symbol === 'function' && typeof Symbol.toStringTag === 'symbol';

function isCallable(value) {
    if (!value) { return false; }
    if (typeof value !== 'function' && typeof value !== 'object') { return false; }
    if (typeof value === 'function' && !value.prototype) { return true; }
    if (hasToStringTag) { return tryFunctionObject(value); }
    if (isES6ClassFn(value)) { return false; }
    var strClass = toStr.call(value);
    return strClass === fnClass || strClass === genClass;
};
register(isCallable)

//bad behaviour when  o.attr == None
function hasattr(o,e){
    try {
        e = o[e];
    } catch (x) { return false }

    if (typeof e === 'undefined' || e === null)
        return false;
    return true;
}

register(hasattr);


function setdefault(n,v,o){
    if (o == null)
        o = window;

    if (undef(n,o)){
        o[n]=v;
        console.log('  |-- ['+n+'] set to ['+ o[n]+']' );
        return true;
    }
    return false;
}

register(setdefault);


function dirname(path){
    return path.replace(/\\/g,'/').replace(/\/[^\/]*$/, '');
}
register(dirname);

function basename(path){
    return path.split('/').pop();
}
register(basename);

function _until(fn_solver){
    var argv = Array.from(arguments)
    argv.shift()

    return new Promise(resolve => {
        var start_time = Date.now();
        function solve() {
          if ( fn_solver.apply(null, argv ) ) {
            console.log("_until has reached", argv)
            resolve();
          } else if (Date.now() > start_time + 30000) {
            console.error('ERROR time out waiting for condition _until',argv);
            resolve();
          } else {
            window.setTimeout(solve, 50);
          }
        }
        solve();
    });
}
register(_until);

} // register




// fs tools =========================================================

async function _rcp(url, store) {
    var content
    try {
        content = await fetch(url)
    } catch (x) { return false }

    store = store || ( "/data/data/" + url )
    console.info(__FILE__,`rcp ${url} => ${store}`)
    if (content.ok) {
        const text= await content.text()
        await FS.writeFile( store, text);
        return true;
    } else {
        console.error(__FILE__,`can't rcp ${url} to ${store}`)
        return false;
    }
}
register(_rcp)


// events ===========================================================


function on_click(button_id, pycode, jsfunc) {
   const wdg = document.getElementById(button_id)
    if (wdg) {
        if (pycode) {
            wdg.addEventListener('click', (e) => {
                // #! turns echo off
                Module.PyRun_SimpleString("#!\n${pycode}")
            })
        }
        if (jsfunc)
            jsfunc()
        wdg.removeAttribute('disabled')
    } else
        console.error(__FILE__, `cannot bind code to id=${button_id}`)
}
register(on_click)




// READLINE ========================================================


var readline = { last_cx : -1 , index : 0, history : ["help()"] }


readline.complete = function (line) {
    if ( readline.history[ readline.history.length -1 ] != line )
        readline.history.push(line);
    readline.index = 0;
    python.PyRun_SimpleString(line + "\n")

}

window.readline = readline


// Xterm Sixel ======================================================

export class WasmTerminal {
    constructor(hostid, cols, rows) {
        this.input = ''
        this.resolveInput = null
        this.activeInput = true
        this.inputStartCursor = null

        this.xterm = new Terminal(
            {
                allowTransparency: true,
                scrollback: 10000,
                fontSize: 14,
                theme: { background: '#1a1c1f' },
                cols: (cols || 100), rows: (rows || 25)
            }
        );

        const imageAddon = new ImageAddon.ImageAddon("./xtermjsixel/xterm-addon-image-worker.js", {sixelSupport: true});

        this.xterm.loadAddon(imageAddon);
        console.warn(hostid,cols,rows)
        this.xterm.open(document.getElementById( 'terminal'))

        // hack to hide scrollbar inside box
        document.getElementsByClassName('xterm-viewport')[0].style.left="-15px"

        this.xterm.onKey((keyEvent) => {
            // Fix for iOS Keyboard Jumping on space
            if (keyEvent.key === " ") {
                keyEvent.domEvent.preventDefault();
            }

        });

        this.xterm.onData(this.handleTermData)
    }

    open(container) {
        this.xterm.open(container);
    }

    ESC() {
        for (var i=0; i < arguments.length; i++)
            this.xterm.write("\x1b"+arguments[i])
    }

    handleTermData = (data) => {

        const ord = data.charCodeAt(0);
        let ofs;

        const cx = this.xterm.buffer.active.cursorX

        // TODO: Handle ANSI escape sequences
        if (ord === 0x1b) {

            // Handle special characters
            switch ( data.charCodeAt(1) ) {
                case 0x5b:

                    const cursor = readline.history.length  + readline.index
                    var histo = ">>> "

                    switch ( data.charCodeAt(2) ) {

                        case 65:
                            //console.log("VT UP")
                            // memo cursor pos before entering histo
                            if (!readline.index) {
                                if (readline.last_cx < 0 ) {
                                    readline.last_cx = cx
                                    readline.buffer = this.input
                                }
                                // TODO: get current line content from XTERM
                            }

                            if ( cursor >0 ) {
                                readline.index--
                                histo = ">>> " +readline.history[cursor-1]
                                //console.log(__FILE__," histo-up  :", readline.index, cursor, histo)

                                this.ESC("[132D","[2K")
                                this.xterm.write(histo)
                                this.input = histo.substr(4)
                            }
                            break;

                        case 66:
                            //console.log("VT DOWN")
                            if ( readline.index < 0  ) {
                                readline.index++
                                histo = histo + readline.history[cursor]
                                this.ESC("[132D","[2K")
                                this.xterm.write(histo)
                                this.input = histo.substr(4)
                            } else {
                                // we are back
                                if (readline.last_cx >= 0) {
                                    histo = histo + readline.buffer
                                    readline.buffer = ""
                                    this.ESC("[2K")
                                    this.ESC("[132D")
                                    this.xterm.write(histo)
                                    this.input = histo.substr(4)
                                    this.ESC("[132D")
                                    this.ESC("["+readline.last_cx+"C")
                                    //console.log(__FILE__," histo-back", readline.index, cursor, histo)
                                    readline.last_cx = -1
                                }
                            }
                            break;

                        case 67:
                            //console.log("VT RIGHT")
                            break;

                        case 68:
                            //console.log("VT LEFT")
                            break;

                        default:
                            console.log(__FILE__,"VT arrow ? "+data.charCodeAt(2))
                    }
                    break
                default:

                    console.log(__FILE__,"VT ESC "+data.charCodeAt(1))
            }

        } else if (ord < 32 || ord === 0x7f) {
            switch (data) {
                case "\r": // ENTER
                case "\x0a": // CTRL+J
                case "\x0d": // CTRL+M
                    this.xterm.write('\r\n');
                    readline.complete(this.input)
                    this.input = '';
                    break;
                case "\x7F": // BACKSPACE
                case "\x08": // CTRL+H
                case "\x04": // CTRL+D
                    this.handleCursorErase(true);
                    break;

                case "\0x03": // CTRL+C

                    break

                // ^L for clearing VT but keep X pos.
                case "\x0c":
                    const cy = this.xterm.buffer.active.cursorY

                    if (cy < this.xterm.rows )
                        this.ESC("[B","[J","[A")

                    this.ESC("[A","[K","[1J")

                    for (var i=1;i<cy;i++) {
                        this.ESC("[A","[M")
                    }

                    this.ESC("[M")

                    if ( cx>0 )
                        this.ESC("["+cx+"C")
                    break;

            default:
                switch (ord) {
                    case 3:
                        readline.complete("raise KeyboardInterrupt")
                        break
                default :
                    console.log("vt:" + ord )
                }
            }
        } else {
            this.input += data;
            this.xterm.write(data)
        }
    }

    handleCursorErase() {
        // Don't delete past the start of input
        if (this.xterm.buffer.active.cursorX <= this.inputStartCursor) {
            return
        }
        this.input = this.input.slice(0, -1)
        this.xterm.write('\x1B[D')
        this.xterm.write('\x1B[P')
    }


    clear() {
        this.xterm.clear()
    }

    // direct write
    sixel(data) {
        this.xterm.write(data)
    }

    print(message) {
        const normInput = message.replace(/[\r\n]+/g, "\n").replace(/\n/g, "\r\n")
        this.xterm.write(normInput)
    }

}
register(WasmTerminal)

// Browser FS ====================================================
var VM


var prom = {}
var prom_count = 0
function* iterator(oprom) {
    const mark = prom_count++;
    var counter = 0;
    oprom.then( (value) => prom[mark] = value )
    while (!prom[mark]) {
        yield counter++;
    }
    yield prom[mark];
    delete prom[mark]
}
register(iterator)


async function mount_at(archive, path, relpath, hint) {
    const mark = prom_count++;

    var BFS = new BrowserFS.EmscriptenFS()
    relpath = relpath || '/'
    hint = hint || archive

    function apk_cb(e, apkfs){
        console.log(__FILE__, "mounting",archive,"onto", path)

        BrowserFS.FileSystem.InMemory.Create(
            function(e, memfs) {
                BrowserFS.FileSystem.OverlayFS.Create({"writable" :  memfs, "readable" : apkfs },
                    function(e, ovfs) {
                                BrowserFS.FileSystem.MountableFileSystem.Create({
                                    '/' : ovfs
                                    }, async function(e, mfs) {
                                        await BrowserFS.initialize(mfs);
                                        await VM.FS.mount(BFS, {root: relpath}, path );
                                        prom[mark] = true;
                                    })
                    }
                );
            }
        );
    }

    const response = await fetch(archive);
    const zipData = await response.arrayBuffer();
    await BrowserFS.FileSystem.ZipFS.Create(
        {"zipData" : VM.Buffer.from(zipData), "name": hint}, apk_cb)

/*
    fetch(archive).then(function(response) {
        return response.arrayBuffer();
    }).then(function(zipData) {
        BrowserFS.FileSystem.ZipFS.Create({"zipData" : VM.Buffer.from(zipData),"name":"apkfs"}, apk_cb)
    })
*/
    await _until(defined, ""+mark, prom)
    delete prom[mark]
    return `${hint} mounted`
}
register(mount_at)



async function fshandler(VM) {
    console.log(__FILE__,"fshandler Begin")
    await _until(defined,"FS", VM)
    await _until(defined,"python")
    try {
        VM.FS.mkdir("/data")
        VM.FS.mkdir("/data/data")
    } catch (x) {
        console.info("/data/data aleady there");
    }

    VM.Buffer = BrowserFS.BFSRequire('buffer').Buffer;


    if (VM.APK) {
        const assets = "/data/data/" + VM.APK + "/assets"
        try {
            VM.FS.mkdir("/data/data/" + VM.APK);
            VM.FS.mkdir(assets);
            console.log(VM.APK, "assets will be hosted at", assets )
        } catch(y) {
            if (VM.APK != 'org.python')
                console.warn(assets," already there ???");
        }


        if (VM.APK != "org.python")   {
            //                  BrowserFS.FileSystem.IndexedDB.Create({},
            //                      function(e, idbfs) {

            var BFS = new BrowserFS.EmscriptenFS()



            function apk_cb(e, apkfs){
                console.log(__FILE__,"APK", VM.APK,"maybe received")
                window.document.title = VM.APK
                BrowserFS.FileSystem.InMemory.Create(
                    function(e, memfs) {
                        BrowserFS.FileSystem.OverlayFS.Create({"writable" :  memfs, "readable" : apkfs },
                            function(e, ovfs) {
                                        BrowserFS.FileSystem.MountableFileSystem.Create({
                                            '/' : ovfs
                                            }, async function(e, mfs) {
                                                await BrowserFS.initialize(mfs);
                                                // BFS is now ready to use!
                                                await VM.FS.mount(BFS, {root: "/"}, "/data/data/" + VM.APK );
                                                await VM.FS.mkdir("/data/data/" + VM.APK + "/need-preload");
                                                console.log(VM.APK," Mounted !")
                                                VM.vfs = BFS
                                            })
                            }
                        );
                    }
                );
            }

            fetch(VM.APK + ".apk").then(function(response) {
                return response.arrayBuffer();
            }).then(function(zipData) {
                BrowserFS.FileSystem.ZipFS.Create({"zipData" : VM.Buffer.from(zipData),"name":"apkfs"}, apk_cb)
            })

            await _until(defined,"vfs", VM)
            if (!VM.vfs) {
                VM.motd = "FATAL: " + VM.APK+ ".apk could not be downloaded and mounted"
                console.error(VM.motd)
            }
        }
    } else {
        console.warn(__FILE__,"not mounting any VFS")
    }
}



// Python WASM ===================================================


const modularized = (typeof python311 != 'undefined')


function pythonvm(vterm, config) {
    var canvasid = "canvas"
    var autorun = null

    if (config){
        canvasid = config._sdl2
        autorun = config.archive
    }

    console.log(__FILE__, "canvas found at "+ canvasid)

    canvas.addEventListener("webglcontextlost", function(e) { alert('WebGL context lost. You will need to reload the page.'); e.preventDefault(); }, false);

    console.log(__FILE__, "terminal found at "+ vterm)

    const sixel_prefix = String.fromCharCode(27)+"Pq"


    const statusElement = document.getElementById('status') || {};
    const progressElement = document.getElementById('progress') || {};
    const spinnerElement = document.getElementById('spinner') || { style: {} } ;

    var buffer_stdout = ""
    var buffer_stderr = ""
    var flushed_stdout = false
    var flushed_stderr = false


    const text_codec = new TextDecoder()


    function b_utf8(s) {
        var ary = []
        for ( var i=0; i<s.length; i+=1 ) {
            ary.push( s.substr(i,1).charCodeAt(0) )
        }
        return text_codec.decode(  new Uint8Array(ary) )
    }

    register(b_utf8)

    function pre1(VM){

        function stdin() {
            return null
        }

        function stdout(code) {

            var flush = (code == 4)
            if (flush) {
                flushed_stdout = true
            } else {
                if (code == 10) {
                    if (flushed_stdout) {
                        flushed_stdout = false
                        return
                    }

                    buffer_stdout += "\r\n";
                    flush = true
                }
                flushed_stdout = false
            }

            if (buffer_stdout != "") {
                if (flush) {
                    if (buffer_stdout.startsWith(sixel_prefix)) {
                        console.info("[sixel image]");
                        VM.vt.sixel(buffer_stdout);
                    } else {
                        if (buffer_stdout.startsWith("Looks like you are rendering"))
                            return;

                        VM.vt.xterm.write( b_utf8(buffer_stdout) )
                    }
                    buffer_stdout = ""
                    return
                }
            }
            if (!flush)
                buffer_stdout += String.fromCharCode(code);
        }


        function stderr(code) {
            var flush = (code == 4)
            if (flush) {
                flushed_stderr = true
            } else {
                if (code === 10) {
                    if (flushed_stderr) {
                        flushed_stderr = false
                        return
                    }
                    buffer_stderr += "\r\n";
                    flush = true
                }
                flushed_stderr = false
            }

            if (buffer_stderr != "") {
                if (flush) {
                    console.log(buffer_stderr);
                    VM.vt.xterm.write(buffer_stderr)
                    buffer_stderr = ""
                    return
                }
            }
            if (!flush)
                buffer_stderr += String.fromCharCode(code);
        }

        if (!modularized) {
            VM.FS = FS
        }

        VM.FS.init(stdin, stdout, stderr);

        var argv = window.location.href.split('?',2)
        var e;

        VM.PyConfig = JSON.parse(`{"executable" : "${argv.shift()}"}`)
        while (e=argv.shift())
            VM.arguments.push(e)

        argv = VM.arguments.pop()

        if (argv) {
            argv = argv.split('&')
            while (e=argv.shift())
                VM.arguments.push(e)
        }

        if (VM.arguments.length) {
            VM.APK = VM.arguments[0]
            console.log(__FILE__,"preRun1",VM.arguments)
        } else {
            if (autorun) {
                VM.APK = autorun
                console.log("AUTORUN", VM.APK )
            } else {
                console.log("no source given, interactive prompt requested")
                VM.APK = "org.python"
            }
            VM.arguments.push(VM.APK)
        }

    }

    var preRun = [ pre1 ]
    var postRun = [ function (VM) { window.python = VM } ]

    if (window.custom_prerun)
        preRun.push(custom_prerun)


    if (window.custom_postrun)
        preRun.push(custom_postrun)


    const Module = {
        arguments : [],

        readline : readline,

        canvas: (() => document.getElementById('canvas'))(),

        vt : vterm,

        PyRun_SimpleString : function(code) {
            if (window.worker) {
                window.worker.postMessage({ target: 'custom', userData: code });
            } else {
                this.postMessage(code);
            }
        },

        locateFile : function(path, prefix) {
            if (path == "main.data") {
                const url = (config.cdn || "" )+`python311/${path}`
                console.log(__FILE__,"locateData: "+path+' '+prefix, "->", url);
                return url;
            } else {
                console.log(__FILE__,"locateFile: "+path+' '+prefix);
            }
            return prefix + path;
        },

        printErr : function(){},
        print : function(){},

        setStatus : function(text) {
            if (text == "hide") {
                progressElement.value = null;
                progressElement.max = null;
                progressElement.hidden = true;
                spinnerElement.style.display = 'none';
                statusElement.innerHTML = "";
                return ;
            }

            if (!this.setStatus.last)
                this.setStatus.last = { time: Date.now(), text: '' };

            if (text === this.setStatus.last.text)
                return;

            var m = text.match(/([^(]+)\((\d+(\.\d+)?)\/(\d+)\)/);
            var now = Date.now();
            if (m && now - this.setStatus.last.time < 30)
                return; // if this is a progress update, skip it if too soon
            this.setStatus.last.time = now;
            this.setStatus.last.text = text;
            if (m) {
                text = m[1];
                progressElement.value = parseInt(m[2])*100;
                progressElement.max = parseInt(m[4])*100;
                progressElement.hidden = false;
                spinnerElement.hidden = false;
            } else {
                progressElement.value = null;
                progressElement.max = null;
                progressElement.hidden = true;
                if (!text)
                    spinnerElement.style.display = 'none';
            }
            statusElement.innerHTML = text;
        },

        totalDependencies: 0,

        monitorRunDependencies: function(left) {
            this.totalDependencies = Math.max(this.totalDependencies, left);
            this.setStatus(left ? 'Preparing... (' + (this.totalDependencies-left) + '/' + this.totalDependencies + ')' : 'All downloads complete.');
        },

        preRun: preRun,
        postRun: postRun
    }


    if (modularized) {
        python311(Module).then( async (vm) => {
                VM = vm
                await _until(defined, "APK", VM)
                await fshandler(VM)
                await _until(defined, "main_chook")
                console.log(__FILE__,"custom_site End")
            }
        );
    } else {
        VM = Module
        window.Module = Module
        const jswasmloader=document.createElement('script')
        jswasmloader.setAttribute("type","text/javascript")
        jswasmloader.setAttribute("src", (config.cdn || "")+ "python311/main.js")
        jswasmloader.setAttribute('async', true);
        document.getElementsByTagName("head")[0].appendChild(jswasmloader)

    }
}
register(pythonvm)


console.log(__FILE__,"waiting  python")

await _until(defined,"python")

console.log(__FILE__,"waiting vfs")

if (!modularized) {
    await _until(defined, "Module")

    await _until(defined, "APK", Module)

    await fshandler(Module)

    await _until(defined, "main_chook")

    if (window.main_chook) {
        if (window.custom_site)
            await window.custom_site(VM)
        else
            console.warn("custom_site(VM) not found")
        console.log(__FILE__,"custom_site End")
    } else {
        const msg="FATAL: python-wasm startup failure in main()\r\n"
        console.error(msg)
        Module.vt.print(msg)
    }
}

