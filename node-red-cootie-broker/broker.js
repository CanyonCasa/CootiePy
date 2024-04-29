// version...
let {name, version} = require('./package.json');
console.log(`Loading ${name}, version: ${version}`);

// Load user defined node color palette, array of {ref:..., fill:...} values; must contain default as first entry
let palette = require('./color-palette');
if (palette[0].ref !== 'Default') palette.unshift({ ref: "Default", fill: "sienna" });

module.exports = function(RED) {
    "use strict";
    var events = require("events");
    const { SerialPort } = require('serialport');

    // Cootie-broker connection configuration Node...
    function CootieBrokerConnectionConfigNode(ncfg) {
        RED.nodes.createNode(this,ncfg);
        this.config = ncfg.config || {};
        this.debug = ncfg.debug || false;
        this.transport = ncfg.transport || 'cootie';
    }

    RED.nodes.registerType("cootie-connection-config",CootieBrokerConnectionConfigNode);

    // Node-red palette Cootie-broker node
    // receives msgs and sends them to the connection object; watches for "matching" return events
    function CootieBrokerNode(ncfg) {
        RED.nodes.createNode(this,ncfg);
        this.connection = ncfg.connection;  // connection cfg node id
        this.cfgConnection = RED.nodes.getNode(ncfg.connection);
        this.colorRef = ncfg.colorRef;      // node-specific color reference per colorPalette
        this.name = ncfg.name;
        this.mode = ncfg.mode;
        this.tag = ncfg.tag;
        this.handle = ncfg.tag || ncfg.id;  // node id property, not the msg defined id
        this.topic = ncfg.topic;
        this.ceid = ncfg.ceid;              // cootie endpoint ID; ceid avoids conflict with reserved ncfg.id (node.id)
        this.field = ncfg.field;
        this.out = ncfg.out;
        this.stat = ncfg.stat;
        this.ack = ncfg.ack;
        this.custom = ncfg.custom
        this.customType = ncfg.customType
        // node methods...
        this.parser = (template, obj)=>{
            try { return Function(...Object.keys(obj), `return \`${template}\``)(...Object.values(obj)); }
            catch(e) { return '???'; }
        };
        this.report = (function(node) { // wrapper for status to allow updating individual fields
            var rpt = { fill: 'grey', shape: "ring", text: "" };
            return (status) => {
                if (status===undefined) return rpt;
                if (typeof(status)==='object') {rpt = Object.assign(rpt,status)} else {rpt.text=String(status)};
                node.status(rpt);
                return rpt;
            }
        })(this);
        var node = this;
        // functional definition...
        if (node.cfgConnection) {
            // establish transport for this node
            node.cntn = cntnPool.get(this.cfgConnection,node.handle); // --> node.cntn.handle
            // process msg payloads...
            node.on("input", async function(msg) {
                if (!msg.hasOwnProperty("payload")) return;
                async function jsonataParse(node,template,msg) {
                    var expr = RED.util.prepareJSONataExpression(template,node);
                    return new Promise(resolve=>{ 
                        RED.util.evaluateJSONataExpression(expr,msg,(err,result)=>{ return resolve(result)});
                    });
                };
                node.msgTopic = msg.topic;
                //node.cntn.debug("incoming msg: "+JSON.stringify(msg));
                node.cntn.debug('');
                node.cntn.debug(`incoming broker msg: ${msg.topic}, ${msg._msgid}`);
                try {
                    if (node.mode==='custom') { // resolve custom payload if defined...
                        var custom = !node.custom ? '' : node.customType==='json' ? JSON.parse(node.custom) : 
                            await jsonataParse(node,node.custom,msg);
                        node.cntn.debug(`custom packet eval: ${JSON.stringify(custom)}`);
                    };
                    // define root output packet; precedence: msg.payload if object, id only if defined, custom or empty...
                    var [src,packet] = (node.mode==='bypass') ? ['msg',msg] :
                        node.mode==='custom' ? ['custom',custom] :
                        ((node.mode==='payload') && (typeof(msg.payload)==='object')) ? ['payload',msg.payload] :
                        node.mode==='simple' ? ['simple',{id: node.ceid}] : ['default',{}];
                    node.cntn.debug(`request packet[${node.mode},${src}]: ${JSON.stringify(packet)}`);
                    //node.cntn.debug(`node[${node.handle}]: ${node.mode}`);
                    if (node.mode!=='bypass') {
                        // optionally assign scalar payload to packet.field
                        if (typeof(msg.payload!=='object') && node.field) packet[node.field] = msg.payload;
                        if (!packet.tag) {
                            if (node.tag) packet.tag = node.tag;
                            if (!packet.tag && packet.id) // id but no tag so create a route alias
                                if (!node.cntn.alias(packet.id,node.handle))    // null means route exists to different return point
                                    node.warn(`Different existing route for ID[${packet.id}] --> ${node.cntn.alias(packet.id)}`)  
                        };
                        if (packet.tag && node.handle!==packet.tag) node.cntn.alias(packet.tag,node.handle);
                        if (!packet.ack && node.ack) packet.ack = node.ack;
                    } else {
                        node.cntn.alias(msg._msgid,node.handle);
                    };
                    //node.cntn.debug(`${node.handle} routes: ${JSON.stringify(node.cntn.alias())}`)
                    node.cntn.talk(packet,(rpt)=>node.report(rpt));
                } catch (e) {
                    node.error(RED._("broker.errors.processing",{error: e.toString()}));
                }
            });

            // add listener for this node on its connection to capture return messages...
            // !!! for some reason listener needs to be refreshed or it doesn't work after redeploy
            //   remove listeners, then add a new one for each redeploy, otherwise leaves dead listeners
            //   putting inside 'if' statement to only add once, doesn't work after redeploy either???
            //if (events.getEventListeners(node.cntn.tasker,node.handle).length===0) {
                node.cntn.tasker.removeAllListeners(node.handle);
                node.cntn.on(node.handle, function(obj) {
                    node.cntn.debug(`heard[${node.handle},${node.mode}]: ${JSON.stringify(obj)}`);
                    let msg = node.mode==='bypass' ? obj : 
                        {topic: node.topic||node.msgTopic, payload: node.out?node.parser(node.out,obj):obj};
                    node.send(msg);
                    node.cntn.debug(`sent: ${JSON.stringify(msg)}`);
                    node.report(node.stat?node.parser(node.stat,obj):[node.report().text,'Ok'].join(' -> '));
                });
                node.cntn.debug(`listening on tag: ${node.handle}`)
            //};
            // status events capture...
            if (events.getEventListeners(node.cntn.tasker,'cntn-ready').length===0) {
                node.cntn.on('cntn-ready', function() {
                    node.report({fill:"green",shape:"dot",text:node.cntn.label});
                });
                node.cntn.on('cntn-closed', function() {
                    node.report({fill:"red",shape:"ring",text:node.cntn.label});
                });
            };
        }
        else {
            this.error(RED._("broker.errors.missing-conf"), {});
        }
        node.on("close", function(done) { cntnPool.close(node.id,done); });
    }

    RED.nodes.registerType("cootie-broker",CootieBrokerNode);

    var cntnPool = (function() {
        var sharedTaskers = {};
        var connections = {};
        return {
            getAll: function() { return connections; },
            get:function(ccfg,nodeHandle) {
                // just return the connection object if already defined
                if (connections[ccfg.id]) { return connections[ccfg.id]; }
                // create a new connection object...
                connections[ccfg.id] = (function() {
                    var cntn = {
                        alias: function alias(key,value) {    // i.e. alias, listener
                            if (key && value===null) { delete this.aliasRoutes[key]; return null; };
                            if (value!==undefined) {
                                if (this.aliasRoutes[key] && this.aliasRoutes[key]!==value) return null;
                                this.aliasRoutes[key] = value;
                            };
                            if (key!==undefined) return this.aliasRoutes[key];
                            return this.aliasRoutes;
                        },
                        aliasRoutes: {},   // alternate node routing events
                        close: function(cb) { this.serial.close(cb) },
                        closing: false,
                        config: ccfg.config,
                        debug: ccfg.debug ? RED.log.info : ()=>{},
                        id: ccfg.id,
                        label: ccfg.config.label,
                        max: parseInt(ccfg.config.max) || 10,
                        handle: nodeHandle,
                        on: function(a,b) { this.tasker.on(a,b); },
                        serial: null,
                        talk: null,
                        tasker: new events.EventEmitter(),
                        timex: null,
                        transport: ccfg.transport
                    };
                    // setup shared connection event channel and listeners between cootie client/server pair...
                    if (cntn.transport==='cootie') {
                        sharedTaskers[cntn.config.reference] = sharedTaskers[cntn.config.reference] || new events.EventEmitter();
                        cntn.tasker = sharedTaskers[cntn.config.reference];
                        var tt = cntn.config.agent==='server'?'cntn-request':'cntn-response';
                        cntn.debug(`cootie listen[${cntn.id}]: ${cntn.config.agent}-->${tt}`);
                        cntn.tasker.on(tt,(px)=>cntn.parseAndRoute(px));
                        cntn.debug(`cntn-request listeners: ${events.getEventListeners(cntn.tasker,'cntn-request')}`);
                        cntn.debug(`cntn-response listeners: ${events.getEventListeners(cntn.tasker,'cntn-response')}`);
                        if (cntn.max>cntn.tasker.getMaxListeners()) cntn.tasker.setMaxListeners(cntn.max);
                    } else {
                        cntn.tasker.setMaxListeners(cntn.max);
                    };
                    // parses JSON messages from all transports to recover routing info...
                    cntn.parseAndRoute = function(response) {
                        var replied = false;
                        var reply = (e,o) => { if (e) { replied=true; cntn.tasker.emit(e,o); } };
                        cntn.debug(`cntn listen[${cntn.id}]: (${response.length}) ${response.trim()}`);
                        var robj = {};  // response object
                        try {
                            robj = JSON.parse(response);
                        } catch(e) {
                            RED.log.error(RED._("broker.errors.parse")+": "+e.toString());
                            cntn.debug(`cntn listen error: ${RED._("broker.errors.parse")}`);
                            robj = {err: true, msg: e.toString(), detail: response};
                        }
                        // cntn.debug(`cntn listen routes: ${JSON.stringify(cntn.alias())}`);
                        cntn.debug(`cntn parse route: tag/alias:${robj.tag}/${robj.tag?cntn.alias(robj.tag):undefined}, ` +
                            `id/alias:${robj.id}/${robj.id?cntn.alias(robj.id):undefined}, ` +
                            `transport: ${cntn.transport}${cntn.config.agent ? ', cootie agent: '+cntn.config.agent:''}`); 
                        cntn.debug(`cntn parse msg info: cmd:${robj.cmd}, _msgid:${robj._msgid}`);
                        if (cntn.transport==='cootie') {    // cootie client/server special case
                            if (cntn.config.agent==='server') {
                                cntn.debug(`cootie server[${cntn.id}]: ${cntn.handle}}`);
                                return reply(cntn.handle,robj);
                            } else {
                                if (robj._msgid) { // client bypass mode...
                                    reply(cntn.alias(robj._msgid),robj);
                                    cntn.debug(`bypass emit[${robj._msgid}]: ${cntn.alias(robj._msgid)}`)
                                    if (replied) return cntn.alias(robj._msgid,null); // remove _msgid alias, not used again
                                };
                            };
                        };
                        // note: data may be returned to multiple destinations, such as 'err' and '*'
                        if (robj.tag) reply(cntn.alias(robj.tag)||robj.tag, robj);    // defined tag, which may be an alias
                        if (!replied && cntn.alias(robj.id)) reply(cntn.alias(robj.id), robj); // infers no tag, check id alias
                        // possible copies to special endpoints
                        if (robj.tag!=='cmd' && robj.cmd) reply('cmd',robj);  // commands, but don't duplicate if tag==='cmd'
                        if (robj.tag!=='err' && robj.err) reply('err',robj);  // errors, don't duplicate
                        if (robj.tag!=='ack' && robj.ack) reply('ack',robj);  // ack, don't duplicate
                        // untagged + system messages catch-all '*' event...
                        if (!replied || ['cmd','err','ack'].some(f=>robj[f])) cntn.tasker.emit('*', robj);
                    };
                    cntn.talk = function(packet,callback) {
                        // format packet as JSON with newline termination and send it on its way to broker...
                        var px = JSON.stringify(packet)+'\n';
                        cntn.debug(`cntn talk[${cntn.id}@${cntn.transport}]: (${px.length}) ${px.trim()}`);
                        if (cntn.transport==='serial') {
                            cntn.serial.write(px,(err,res)=>{
                                if (err) RED.log.error(err)
                                callback(err ? {fill:'red',text:RED._('broker.errors.log')} : {fill:'green',text:`sent: ${px.length}`});
                            });
                        } else if (cntn.transport==='cootie') {
                            var task = cntn.config.agent==='server'?'cntn-response':'cntn-request'
                            cntn.debug(`cntn talk emit[${cntn.id}]: ${cntn.config.agent}-->${task}`);
                            cntn.tasker.emit(task,px);
                            callback(`sent: ${px.length}`);
                        } else {
                            RED.log.error(RED._("broker.errors.transport",{transport: cntn.transport}));
                            callback({fill:'red',text:RED._('broker.errors.log')});
                        }
                    };
                    // 
                    if (cntn.transport==='serial') {
                        var olderr = '';
                        var { serialport, baud, databits, label, parity, stopbits, timeout } = cntn.config;
                        var [baudRate,dataBits,stopBits,timeout] = [baud,databits,stopbits,timeout].map(v=>parseInt(v));
                        var portSettings = { path:serialport, baudRate, dataBits, parity, stopBits, autoOpen: true}
                        var setupSerial = function() {
                            cntn.serial = new SerialPort(portSettings, function(err) {
                                if (err) {
                                    if (err.toString() !== olderr) {
                                        olderr = err.toString();
                                        RED.log.error("[serial config:"+cntn.id+"] "+RED._("serial.errors.error",{port:label,error:olderr}), {});
                                    }
                                    cntn.timex = setTimeout(function() { setupSerial(); }, timeout);
                                };
                            });
                            if (!cntn.serial) return;
                            cntn.serial.on('error', function(err) {
                                RED.log.error("[serial config:"+cntn.id+"] "+RED._("serial.errors.error",{port:label,error:err.toString()}), {});
                                cntn.tasker.emit('closed');
                                if (cntn.timex) { clearTimeout(cntn.timex); }
                                cntn.timex = setTimeout(function() { setupSerial(); }, timeout);
                            });
                            cntn.serial.on('close', function() {
                                if (!cntn.closing) {
                                    if (olderr !== "unexpected") {
                                        olderr = "unexpected";
                                        RED.log.error("[serial config:"+cntn.id+"] "+
                                            RED._("serial.errors.unexpected-close",{port:cntn.label}), {});
                                    }
                                    cntn.tasker.emit('cntn-closed');
                                    if (cntn.timex) { clearTimeout(cntn.timex); }
                                    cntn.timex = setTimeout(function() { setupSerial(); }, timeout);
                                }
                            });
                            cntn.serial.on('open',function() {
                                olderr = "";
                                RED.log.info(`[setupSerial:${cntn.id}] ${RED._("serial.onopen",{config: cntn.label})}`);
                                if (cntn.timex) { clearTimeout(cntn.timex); cntn.timex = null; }
                                cntn.tasker.emit('cntn-ready');
                            });
                            // processes ALL serial responses of all nodes for this connection line-by-line
                            var buf = "";   // return message buffer, UTF8 ASCII
                            cntn.serial.on('data',function(d) {
                                cntn.debug(`${cntn.config.serialport}.onData: ${d.length}`);
                                buf += d;   // aggregate lines or partial lines
                                do {
                                    var line = "";      // current broker response
                                    var index = buf.indexOf('\n');  // look for newline termination
                                    if (index!=-1) {    // extract complete line from buffer
                                        line = buf.substring(0,index);
                                        buf = buf.substring(index+1);   
                                    };
                                    if (line) {         // ignore empty lines
                                        cntn.debug(`serial-in line[${line.length}]: ${line}`);
                                        cntn.parseAndRoute(line);
                                    };
                                } while (buf.length>0 && index!=-1);    // process all lines
                            });
                        }
                        setupSerial();
                    };

                    return cntn;
                })();
                return connections[ccfg.id];
            },
            close: function(id,done) {
                if (!connections[id]) return done();
                if (connections[id].transport!=='serial') {
                    delete connections[id];
                    return done();
                };
                if (connections[id].timex != null) clearTimeout(connections[id].timex);
                connections[id].closing = true;
                try {
                    connections[id].close(function() {
                        RED.log.info(RED._("serial.errors.closed",{port:connections[id].config.serialport}));
                        delete connections[id];
                        done();
                    });
                } catch(err) {}
            }            
        };
    })();

    RED.httpAdmin.get("/serialports", RED.auth.needsPermission('serial.read'), function(req,res) {
        SerialPort.list().then(
            ports => res.json(ports.map(p => p.path)),
            err => res.json([RED._("serial.errors.list")])
        )
    });
    RED.httpAdmin.get("/cootie-broker-colors", RED.auth.needsPermission('cootie-broker.read'), function(req,res) {
        res.json(palette);
    });
}
