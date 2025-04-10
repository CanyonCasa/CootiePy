# CootiePy Broker

#### *Keywords*
Raspberry Pi, QTPy, CircuitPython, node-red, broker, cootie

#### *Abstract*

*CootiePy Broker implements a queued JSON interface over USB serial intended for use between Node-red and an RP2040 based QTPy board for offloading sensor measurements and actuator actions from a host such as a Raspberry Pi.*

## Hardware

The broker communicates using an QTPyRP2040 based board. It performs direct communications with sensors and other devices via the builtin QWIIC interface, as well as incorporates additional hardware for communicating with OneWire devices and other interfaces.

The broker communicates over the QTPy host USB based serial data interface. This interface must be enabled for use. See *boot.py* notes below.

**NOTE**: *Messages greater than 256 bytes length, including \n termination may cause blocking until whole message is received. Messages >16K has passed successfully, but are not recommended, nor likely necessary.

## Files

#### *boot.py*

The standard *boot.py* file initializes QTPy hardware and operations before running user code. The broker requires enabling the USB data serial port, disabled by default. Place the following code in *boot.py*: 

``` python
import usb_cdc
usb_cdc.enable(console=True, data=True)
print("USB data port enabled sucessfully!")
```
The print statement will output to the *boot_out.txt* file after a boot cycle.

*boot.py* includes some other code to provide a bit of diagnostics

#### *code.py*

This implements the broker functionallity.

#### *cfg.json*

#### *def.json*

## Protocol

The broker uses a simple but flexible JSON protocol similar to Node-red. Each "message" sent to and received from the broker consists of a single line of JSON terminated by a newline (i.e. \n, 0xA) character. Each broker message includes a **tag** field to identify the return destination, which enables multiple source and destination points for each broker.

#### *Message Types*

The protocol implements two message types:

* **Command Messages**: These messages instruct the broker to perform some internal configuration or operational action and always include a **cmd** field.
* **Action Messages**: These messages define sensor or actuator actions and always include an **id**
field representing the interface.

A message may be a _command message_ (precedence) or an _action message_, not both. See the respective *Command Messages or Action Messages* sections below for message specific details. The broker treats a message without either a **cmd** or **id** field as an error.

#### *Reserved fields*

The protocol defines a few reserved fields for internal message use:

* **cmd**: Used to denote and pass commands to the broker, where the value of *cmd* indicates the action to be taken. Other command specific parameters may be required.
* **ack**: Used to tell the broker to acknowledge a message by retuning a receipt. If defined as a property of a message it only applies to the specific message. Alternately, it can be set in global configuration. If defined with the value "echo", the broker acknowledges receipt by returning the entire message as received, with msg.ack='echo'. If simply True, the broker returns a message of the form _{tag: 'ack', ack: msg.tag, err: null}_. If defined as "log", the message will be logged to the local QtPy console.
* **id**: Specifies an I/O request sensor/actuator or local IO ID.   
* **tag**: Identifies the publishing event/topic for the return message, generally preserved from the imcoming message.
  A tag property is recommended, but if no tag is specifically provided, return messages will be routed by **<id>** (value) or **'cmd'** in the case of commands.
* **err**: Text description of internal error or None, appended to outgoing messages.

### Command Messages

Command messages perform a specific local command, including...

```json
// NOTE: tag field omitted for breity
// return current in-memory definition
{"cmd": "def"}
// load a definition file from "disk" (null -> default); returns the current definition
{"cmd": "def", "def":"<definition_filname>|null"}
// edit configuration parameter of in-memory definition
{"cmd": "cfg", "cfg":{"<param1>": <value1>, ...}}
// edit or define 1 or more IO objects; allows dynamically adding IO, assuming hardware support
{"cmd": "io", "io":[{"<param1>": <value1>, ...}]}  
// define a cronjob(s), see Cron class for details...
{"cmd": "cron", "jobs": [
    { "id": "<job_id>", "at": "<time_string>", "evt": "<cmd_or_action>", "n": <#_of_times_run>} }]
// set local time (should be sent immediately after boot)
{"cmd": "time", "time":{"epoch":<epoch>, "zone": ["<zone_string>", <UTC_offset>], "dst":0|1}}
// return status message...
{"cmd": "status", "prompt": "<optional_console_message>"}
// interrupt code.py execution... action =? 'reset', 'reload', 'exit'
{"cmd": "ctrl", "ctrl": "<action>"}
// returns device info...
{"cmd": "info"}

```

**NOTES**: 
1. *It is not possible to permanently save the configuration and definition changes at this time. A hard reset or power cycle returns all configuration settings to defaults.*
2. *msgs generally not checked for valid content.*
3. if no message tag is provided, return messages will have tag="cmd"

### Action Messages

Action messages perform loacl I/O, sensor measurements, or actuator state changes. They follow the form: 

```json
{"tag": "<tag>", "id": <id>, "action":<action>, "<param1>": <value1>, ...}
```

The *tag* property specifies the return destination. The *id* parameter identifies the specific sensor, I/O, or actuator and may represent any unique sensor "id", "name", "addr" or "sn" property. This gives flexibility in referencing devices.

If no action is specified, the object's default action will occur, such as reading a temperature. This means the payload for reading a particular sensor may be as simple as sending the ID (with a return tag). Parameters for a given device are specific to the device type.

### *Errors*
The broker attaches an *err* property, default null, to all return messages containing a description for any error detected. If it receives an unrecoverable garbled message, assuming not in quiet mode, it replies with the follwoing error message:

    ```json
    {"tag": "err", "err": "<error description>", "line":"<received_line>" }
    ```

### *Configuration Parameters*
* **ack**: Default *false*. When *true* causes all received messages to be acknowledged by a receipt as:

     ```json
    {"tag": "ack", "ack": "<ack>", "err": null}
    ```

    When defined as "echo", the broker returns the complete input message as acknowledgement. 
    If the incoming message did not include an *ack* property, the broker appends the *ack* property to the 
    acknowledged message to enable backend filtering.

* **quiet**: Default *false*. When *true*, acknowledgements and error messages are not returned

### Transports

The Cootie Broker supports multiple transports to passing data to and from Cooties.

  - **Serial (USB)**: A direct USB connection to pass data serially. Data passes as a JSON string.
  - **UDP**: A wireless connection with little overhead and support for one in many out messages. Data passes as a JSON string.
  - **HTTP**: A wireless connection with greater overhead but more reliability. GET requests must pass data as a Base64URL encoded query parameter q, i.e. /url?q=<Base64URL_encoded_JSON>. This ensures the ability to pass JSON without causing URL conflicts or the need to define multiple parameters or have to change a URL in the event the JSON contents changes. GET responses return directly as JSON content. A POST request must define a body representing the JSON data and handle the response content. Both request types must provide properContent-Type and Content-length headers
  - **Cootie**: The Cootie transport allows two Cootie Brokers to talk/listen as client/server pairs across a Node-red application.

Note: The Cootie Broker takes care of preparing JavaScript object data as JSON for the various modes. Individual Cootie endpoints need only implement individual protocols as needed. For example, a serial device only needs to support the Serial interface, not the others, but it must follow the broker protocols to communicate and play nicely.