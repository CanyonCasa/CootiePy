/*************************************************************
// Extensions to Client Side JavaScript ES5/ES6 compatible...
// First set of definitions modify the respective JS primitives
// exports (default) helper functions object
*************************************************************/

/// ************************************************************
/// Array Object Extensions...
/// ************************************************************
// function to generate page base path add-on to location variable...
if (!(Array.includes||Array.prototype.includes)) 
    Object.defineProperty(Array.prototype,'includes', {
    value: function(item) { return (this.indexOf(item)!==-1); },
    enumerable: false
    });


/// *************************************************************
/// Date Style Extension ...
const STYLE_DAYS = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
const STYLE_MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const STYLE_RE = /Y(?:YYY|Y)?|[SX][MDZ]|0?([MDNhms])\1?|[aefxz]|(['"])(.*?)\2/g;  // Date.prototpye.style parsing pattern
if (!Date.prototype.style)
/**
 * @lends Date#
 * @function style extends Date object defining a function for creating formated date strings
 * @param {string|'iso'|'form'} format - output format
 *  format string meta-characters...
 *  Y:          4 digit year, i.e. 2016
 *  M:          month, i.e. 2
 *  D:          day of month, i.e. 4
 *  N:          day of the week, i.e. 0-6
 *  SM:         long month name string, i.e. February
 *  SD:         long day name string, i.e. Sunday
 *  SZ:         long time zone name string, i.e. Mountain Standard Time
 *  LY:         leap year flag, true/false (not usable in format)
 *  h:          hour of the day, 12 hour format, unpadded, i.e. 9
 *  hh:         hour of the day, 24 hour format, padded, i.e. 09
 *  m:          minutes part hour, i.e. 7
 *  s:          seconds past minute, i.e. 5
 *  x:          milliseconds, i.e. 234
 *  a:          short meridiem flag, i.e. A or P
 *  z:          short time zone, i.e. MST
 *  e:          Unix epoch, seconds past midnight Jan 1, 1970
 *  f:          fractionalseconds past midnight Jan 1, 1970, i.e. with milliseconds
 *  dst:        Daylight Savings Time flag, true/false (not usable in format)
 *  ofs:        Local time offset (not usable in format)
 *  'text':     quoted text preserved, as well as non-meta characters such as spaces
 *  defined format keywords ...
 *    'form':   ["YYYY-MM-DD","hh:mm:ss"], needed by form inputs for date and time (defaults to local realm)
 *    'http':   HTTP Date header format, per RFC7231
 *    'iso':    "YYYY-MM-DD'T'hh:mm:ssZ", JavaScript standard
 *    'stamp:   filespec safe timestamp string, '20161207T212211Z'
 *  notes:
 *    1. Add a leading 0 or duplicate field character to pad result as 2 character field [MDNhms], i.e. 0M or MM
 *    2. Use Y or YYYY for 4 year or YY for 2 year
 *    3. An undefined or empty format returns an object of all fields
 * @param {'local'|'utc'} realm - flag to adjust input time to local or UTC time before styling
 *    'local':  treats input as UTC time and adjusts to local time before styling (default)
 *    'utc':    treats input as local time and adjusts to UTC before styling
 *    undefined:    leaves time unchanged, unless frmt = 'form', which assumes local
 * @return {string} - date string formatted as specified
 * 
 * @example...
 *    d = new Date();      // 2016-12-07T21:22:11.262Z
 *    d.style();           // { Y: 2016, M: 12, D: 7, h: 21, m: 22, s: 11, x: 262, z: 'MST', e:1481145731, f:1481145731.262, 
 *                              a:'PM', N:3, SM: 'December', SD: 'Wednesday', SZ: 'Mountain Daylight Time', LY:true, 
 *								dst:false, ofs: -420 }
 *    d.style().e;         // 1481145731
 *    d.style().f;         // 1481145731.262
 *    d.style("MM/DD/YY"); // '12/07/16'
 *    d.style('hh:mm:ss','local')  // '14:22:11', adjusts UTC input time (d) to local time (e.g. h = 22 - 7 = 14 )
 *    d.style('hh:mm:ss','utc')    // '04:22:11', treats input time as local and adjusts to UTC (e.g. h = 21+7 % 24 = 4)
 *    d.style('SD, DD SM YYYY hh:mm:ss "GMT"').replace(/[a-z]{4,}/gi,($0)=>$0.slice(0,3))   
 *      // HTTP header date, RFC7231: 'Wed, 07 Dec 2016 21:22:11 GMT'
 *          
 */
if (!Date.prototype.style) Date.prototype.style = function(frmt,realm) {
    var sign = (realm || frmt=='form') ? (String(realm).toLowerCase()=='utc' ? -1 : 1) : 0; // to utc, to local, or no change
    var dx = sign ? new Date(this-sign*this.getTimezoneOffset()*60*1000) : this;
    var zone = dx.toString().split('(')[1].replace(')','');
    var zx = zone.replace(/[a-z ]/g,'');
    var base = dx.toISOString();
    switch (frmt||'') {
        case 'form': return dx.style('YYYY-MM-DD hh:mm').split(' ');            // values for form inputs
        case 'http': return dx.style(`SD, DD SM YYYY hh:mm:ss "${sign==1?zx:'GMT'}"`).replace(/([a-z]{3})[a-z]+/gi,'$1');
        case 'iso': return (realm && sign==1) ? base.replace(/z/i,zx) : base;   // ISO (Zulu time) or ISO-like localtime
        case 'stamp': return dx.style(`YMMDDThhmmss${(realm && sign==1)?'z':'Z'}`);   // filespec safe timestamp
        case '':  // object of date field values
            var [Y,M,D,h,m,s,ms] = base.split(/[\-:\.TZ]/);
            var f = +dx*0.001;
            return { Y:+Y, M:+M, D:+D, h:+h, m:+m, s:+s, x:+ms, z:zx, e:Math.floor(f), f:f, a:h<12 ?"AM":"PM", N:dx.getDay(),
                SM: STYLE_MONTHS[M-1], XM: STYLE_MONTHS[M-1].substring(0,3), SD: STYLE_DAYS[dx.getDay()], XD: STYLE_DAYS[dx.getDay()].substring(0,3), 
                SZ:zone, XZ: zx, LY: Y%4==0&&(Y%100==Y%400), ofs: -dx.getTimezoneOffset(),
                dst: !!(new Date(1970,1,1).getTimezoneOffset()-dx.getTimezoneOffset()), iso: dx.toISOString() };
        default:  // any format string
            function pad(s) { return ('0'+s).slice(-2); };
            var tkn = dx.style(); tkn['YYYY']=tkn.Y; tkn['hh']=('0'+tkn['h']).substr(-2); if (tkn['h']>12) tkn['h']%=12;
            return (frmt).replace(STYLE_RE,$0=>$0 in tkn ? tkn[$0] : $0.slice(1) in tkn ? pad(tkn[$0.slice(1)]) : $0.slice(1,-1));
    };
};


///*************************************************************
/// Object Extensions...
///*************************************************************
/**
 * @function filterByKey object equivalent of Array.prototype.filter - calls user function with value, key, and source object
 * @memberof Object
 * @param {function} f - function called for each object field
 * @return {{}} - Modified object (does not mutate input unless filterFunc does)
 * @info result will reference source object if value is an object
  */
 if (!Object.filterByKey) Object.defineProperty(Object.prototype,'filterByKey', {
    value: 
        function(f) {
            var obj = this; var tmp = {};
            for (var key in obj) if (f(obj[key],key,obj)) tmp[key] = obj[key];
            return tmp;
        },
    enumerable: false
});

/**
 * @function mapByKey object equivalent of Array.prototype.map - calls user function with value, key, and source object
 * @memberof Object
 * @param {function} f - function called for each object field
 * @return {{}} - Modified object (does not mutate input unless mapFunc does)
 * @info result will reference source object if value is an object
  */
if (!Object.mapByKey) Object.defineProperty(Object.prototype,'mapByKey', {
    value: 
        function(f) {
            var obj = this; var tmp = {};
            for (var key in obj) tmp[key] = f(obj[key],key,obj);
            return tmp;
        },
    enumerable: false
});

/**
 * @function mergekeys recursively merge keys of an object into an existing object with merged object having precedence
 * @param {{}} merged - object merged into source object, MUST NOT BE CIRCULAR!
 * @return {{}} - object representing merger of source and merged (mutates source, but has no reference to merged) 
 */ 
if (!Object.mergekeys) Object.defineProperty(Object.prototype,'mergekeys', {
    value:
        function(merged={},except=[]) {
            var isObj = function(obj) { return (typeof obj==='object') && (obj!==null) && !(obj instanceof RegExp); };
            if (isObj(merged)) {
                for (var key of Object.keys(merged).filter(function(k){ return !except.includes(k); })) {
                    if (isObj(merged[key])) {
                        this[key] = this[key] || (merged[key] instanceof Array ? [] : {}); // init new object if doesn't exist
                        this[key].mergekeys(merged[key]); // new object so recursively merge keys
                    } else {
                        this[key] = merged[key];          // just replace with or insert merged key, even if null
                    };
                };
            };
            return this; 
        },
    enumerable: false
});


///*************************************************************
/// String Extensions...
///*************************************************************
// Title Case Conversion...
if (!String.prototype.toTitleCase) 
  String.prototype.toTitleCase = function () { return this.toLowerCase().replace(/(\b[a-z])/g,(m)=>m.toUpperCase()); };


///*************************************************************
/// General Extensions...
///*************************************************************
// function to generate page base path add-on to location variable...
if ((typeof location!=='undefined')&&!location.base)
  location.base = location.origin + location.pathname.replace('/'+location.pathname.split('/').pop(),'');


///*************************************************************
/// Helper Functions...
///*************************************************************

// CSV helper functions
// quote string, if not a number
var csvQuoteIf = x => x===null ? 'null' : x==='' || x===undefined || typeof x==='object' ? '' :
  typeof x==='string' && (x.includes(',') || x.includes('"') || !isNaN(x)) ? '"'+x.replaceAll('"','""')+'"': x;
// quote strings or elements of an array
var csvQuote = v => v instanceof Array ? v.map(x=>csvQuoteIf(x)) : csvQuoteIf(v);
// convert an array of data into a CSV line
var csvLineStringify = (a,eol) => a.length ? eol + csvQuote(a).join(',') : '';
// remove quotes warpping string and unescape ""
let csvUnquote = s => s.startsWith('"')&&s.endsWith('"') ? s.substring(1,s.length-1).replaceAll('""','"') : s;
let csvParseRegex = /(?:,|\n|^)("(?:(?:"")*[^"]*)*"|[^",\n]*|(?:\n|$))/g;
let csvLineParse = line =>(line.match(csvParseRegex)||[]).map(m=>m[0]===',' ? m.slice(1) : m)
    .map(x=> x===''||isNaN(x) ? csvUnquote(x) : Number(x));

//  obj2csv function converts an array of JS objects into a csv string.
//  cfg provides conversion configuration info
//    order: an array of label keys that determines the output order,
//      default labels for array of arrays; required for array of objects
//    labels: an array of names for column labels
//      required for array of arrays if useFirstRowAsLabels=false; 
//    useFirstRowAsLabels: boolean to use first row of array or arrays as labels; default true
//    eol: End Of Line sequence; default "\r\n"
function obj2csv(obj,cfg={}) {
    let csv = ''
    cfg.useFirstRowAsLabels = cfg.useFirstRowAsLabels!==false;
    cfg.eol = cfg.eol || "\r\n";
    if (!Array.isArray(obj)) return 'ERROR: requires an array input!'
    if (Array.isArray(obj[0])) {
        cfg.labels = cfg.labels || cfg.useFirstRowAsLabels ? obj[0] : undefined;
        let index = cfg.useFirstRowAsLabels ? 1 : 0;
        if (!cfg.labels) return "ERROR: no labels avaiable!";
        if (cfg.order) {    // first convert to array of objects then use order for output
            let objData = obj.slice(index).map(a=>a.reduce((obj,val,idx)=>{obj[cfg.labels[idx]]=val; return obj},{}));
            return obj2csv(objData,cfg);
        } else {
            csv = csvLineStringify(cfg.order||cfg.labels,'');
            obj.slice(index).map(row=>csv += csvLineStringify(row,cfg.eol));
            return csv;
        }
    } else if (typeof obj[0] == 'object') {
        if (!cfg.order) return "ERROR: Array of objects requires a cfg.order for labels"
        csv = csvLineStringify(cfg.order,'');
        obj.map(row=>csv += csvLineStringify(cfg.order.map(lbl=>row[lbl]),cfg.eol))
        return csv;
    } else {
        return 'ERROR: input must be an array of arrays or objects'
    }
}

// converts a CSV line demitted string or array of lines to JS object
//  cfg provides conversion configuration info
//    labels: an array of names for column labels
//      required if useFirstRowAsLabels=false; 
//    useFirstRowAsLabels: boolean to use first row of array as labels; default true
//    includeLabels: boolean to specify if output should include labels; default true
function csv2obj(csv,cfg={}) {
    let obj = [];
    cfg.useFirstRowAsLabels = cfg.useFirstRowAsLabels!==false;
    cfg.includeLabels = cfg.includeLabels!==false;
    let lines = (typeof csv === 'string') ? csv.split(/\r\n|\r|\n/) : csv;
    cfg.labels = cfg.useFirstRowAsLabels ? csvLineParse(lines[0]) : cfg.labels;
    if (cfg.includeLabels) obj.push(cfg.labels);
    lines.slice(cfg.useFirstRowAsLabels ? 1:0).forEach(line=>line ? obj.push(csvLineParse(line)):undefined);
    return obj;
}


const helpers = {

    // convert a comma (or other) delimited string into an array
    asList: (x,delim=/,\s*/) => x instanceof Array ? x : (x||'').split(delim),

    // display a value as US dollars
    as$: (c) => '$' + Number(c).toFixed(2),

    // convert a B, KB, MB, GB, or TB string to number of bytes 
    asBytes: s => parseInt(s.replace(/([0-9.]+)([^0-9]?)b?/i,(m,i,x)=>i*Math.pow(1024,'BKMGT'.indexOf(x.toUpperCase())))),

    // convert number of bytes to a K, M, G, or T suffixed string
    asByteStr: (b,d=0) => String(Math.log(b)/Math.log(1024)).split('.').reduce((s,p,i)=>(i?Math.pow(1024,'0.'+p).toFixed(d):'BKMGT'[Number(p)])+s,''),

    // bounds a value between min and max...
    bound: (min,val,max) => {
        [m,v,mx] = [min,val,max].map(x=>x===null ? NaN : Number(x));
        return (isNaN(v)) ? NaN : !isNaN(m)&&(v<m) ? m : !isNaN(mx)&&(v>mx) ? mx : v
    },

    // convert a JS object (i.e. array of arrays or objects) to CSV data, vice versa, see details above 
    csv2obj: csv2obj,
    obj2csv: obj2csv,

    // filters an array for distinct values
    distinct: a => a.filter((v,i,a)=>a.indexOf(v)===i),

    // make a full copy of an object w/o reference to original using JSON functions...; 
    // circular references will log error and return null.
    jsonCopy: obj => { try { return JSON.parse(JSON.stringify(obj)); } 
        catch(e) { console.error(e,obj); return null; } },

    // formats JSON as HTML for pretty printing in color... 
    //   requires css class definitions for colors: 
    //      .json (wrap everything), .json-key, .json-value, .json-string, .json-boolean
    // original code source: Dem Pilafian
    //   fixed problems: spaces in keys, empty objects, changed quoted strings styling, added boolean styling
    //   https://blog.centerkey.com/2013/05/javascript-colorized-pretty-print-json.html
    jsonPrettyHTML: (obj,spaces=1) => {
        var pattern = /^( *)("[$\w ]+":)? ?("[^"]*"|[\w.+-]*)?([,[{}\]]+)?$/mg;
        function replacer(match, indent, key, val, term) {
            var tag = function(style,content,quote) { 
                quote = quote || '';
                return quote+"<span class='json-"+style+"'>"+content+'</span>'+quote; 
            };
            var line = indent || '';  // build the line piecewise from wrapped fields
                line += (key) ? tag('key',key.replace(/[":]/g, '')) + ': ' : '';
            line += (val) ? (val.startsWith('"') ? tag('string',val.replace(/"/g, ''),'"') : 
                ((val=='false'||val=='true') ? tag('boolean',val) : tag('value',val))) : '';
            return line + (term || '');
        };
        return JSON.stringify(obj, null, spaces)
        .replace(/\\"/g, '&quot;')                    // escaped quotes inside JSON string values
        .replace(/</g, '&lt;').replace(/>/g, '&gt;')  // html tag escapes, current browsers seem ok with quotes and ampersands
        .replace(pattern, replacer);                  // parse and wrap fields with tags
    },

    // JWT payload extraction: convert base64url tokens to b64 then to js object
    jwtDecode: jwt => {
        return jwt.split('.').map(t=>t.replace(/-/g,'+').replace(/_/g,'/'))
          .map(t=>t+('='.repeat(t.length%4 ? 4-t.length%4 : 0))).map((a,i)=>i<2?JSON.parse(atob(a)):a)
    },

    // function to create and populate an array of given size and values, note value can even be a function
    // makeArrayOf(10,((v,i)=>i)) will fill an array of 10 with indexes, i.e. equivalent to Python range(10)
    makeArrayOf: (size,value) => { return Array.apply(null, Array(size))
        .map(function(v,i,a){ return (typeof value=='function') ? value(v,i,a) : value }); },

    // function to correctly join an array of path parts, excluding "empty, null, or undefined parts", into a valid path...
    makePath: () => { return Array.from(arguments).filter(function(e){ return e; })
        .join('/').replace(/\/{2,}/g,'/').replace(/:\//,'://'); },

    // define a new Object of Type provided
    newType: (obj) => obj instanceof Array ? [] : {},

    /**
    * @function pluralize returns the correct word form for number given
    * @param {integer} num - item count
    * @param {string} singular - singular noun form
    * @param {string} [plural] - optional plural noun form, assumes singular + 's'
    */
    pluralize: (num,singular,plural) => num==1 ? singular : (plural || singular+'s'),
    
    // recursively search an ojbect to look for a contained object matching specified properties...
    scanForMatchTo: (object, match={},dflt={}) => {
        const isObj = (x) => (typeof x==='object') && (x!==null);
        const matches = (obj,x) => Object.keys(x).every(k=>(k in obj)&&(obj[k]===x[k]));
        if (!isObj(match)) return dflt;       // match is not an object
        if (matches(object,match)) return object; // check the object itself for match
        for (var k of Object.keys(object)) {    // check any objects it contains recursively
            if (isObj(object[k])) { var m=helpers.scanForMatchTo(object[k],match,null); if (m) return m; };
        };
        return dflt;  // default
    },

    // generates an n(=8) character unique ID of base (b=36, alphanumeric) ...
    uniqueID: (n=8,b=36) => { var u=''; while(u.length<n) u+=Math.random().toString(b).slice(2); return u.slice(-n); },

    // function to determine a number of complex variable types...
    verifyThat: (variable,isType) => {
        switch (isType) {
            case 'isTrueObject': return (typeof variable=='object') && (variable!==null)  && !(variable instanceof Array);
            case 'isArray': return (variable instanceof Array);
            case 'isArrayOfTrueObjects': return (variable instanceof Array) && helpers.verifyThat(variable[0],'isTrueObject');
            case 'isArrayOfAnyObjects': return (variable instanceof Array) && (typeof variable[0]==='object');
            case 'isArrayOfArrays': return (variable instanceof Array) && (variable[0] instanceof Array);
            case 'isEmptyObject': return Object.keys(variable).length==0;
            case 'isScalar': return (typeof variable=='string') || (typeof variable=='number');
            case 'isNotEmpty': return (typeof variable=='object') && (variable!==null) && (Object.keys(variable).length>0);
            case 'isEmpty': return (variable===undefined) || (variable==='') || !helpers.verifyThat(variable,'isNotEmpty');
            case 'isDefined' : return (variable!==undefined) && (variable!==null);
            case 'isNotDefined' : return (variable===undefined) || (variable===null);
            default: throw `verifyThat: Unknown type '${isType}' specified`;
        };
    }
}

//export default helpers;
window.helpers = helpers;

console.log('ClientLib.js loaded...');
