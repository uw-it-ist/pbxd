# pbxd

pbxd is a web service that provides an API to an Avaya PBX.

It logs in to the SAT terminal of the PBX, then runs commands on the PBX and
returns the results to the client.

The number of gunicorn workers determines how many simultaneus logins are made
to the PBX system.


## Configuration

Environment variables:

    PBX_NAME=uw01
    PBX_COMMAND_TIMEOUT=300
    PBXD_CONF=pbxd_conf/pbxd_uw01_conf.json

Secrets are loaded from a JSON config file like this:

    {
        "connection_command": "/usr/bin/ssh -o 'StrictHostKeyChecking no' -o 'ServerAliveInterval -p 5022 -l username
        ip_address_of_pbx",
        "pbx_username": "username",
        "pbx_password": "password"
    }

## Access control

Restricting access to authorized users must be done by a proxy server like Nginx. Typically this will require X.509 certificates or host IP addresses.


## Dependencies

There are some python packages required for pbxd in the setup.py file and
it is good to keep them updated. pip-tools is used here to update the
requirements.txt file and help ensure predictable builds.

    deactivate; rm -rf venv
    python3 -m venv venv && . venv/bin/activate
    pip install pip-tools
    pip-compile


## Running

### Run in a virtual environment

    python3 -m venv venv && . venv/bin/activate
    pip install -r requirements.txt
    pip install -e .

    PBX_NAME=uw01 \
    PBX_COMMAND_TIMEOUT=300 \
    PBXD_CONF=pbxd_conf/pbxd_uw01_conf.json \
    gunicorn "pbxd.app:load()" -b localhost:8000 --access-logfile - --log-level INFO --reload

### Run in Docker container

    docker-compose build
    docker-compose up --abort-on-container-exit



## Client API

Clients use pbxd to run a command on the PBX and receive the results.

The PBX need to know what terminal type to use:
- `ossi` is the terminal type that returns fields with unique IDs. You can find the
IDs by doing a display command and use them in a change command.
- `vt220` is the terminal type that returns screen snapshots. You only use this
for display commands.

The `command` can be any command that the PBX understands. Typically these start
with the word `display`, `change`, `status`, or `monitor`.

With the `ossi` terminal type you can also provide a list of `fields` that are just
objects with OSSI field IDs and any value you want them changed to.
To clear a field you often have to set the value to a single space character.

One way to identify field IDs is to run a "display" command and then compare it
to the output from the same command in the vt220 terminal.

### v3

The v3 API uses JSON.
The JSON object has the following keys:
- `termtype` string: ossi or vt220
- `command` string: the command to run on the pbx
- `fields` array: the list of field IDs and values
    - field values should be a string, either an empty string '' or the
value that the field will be changed to.
- `debug` boolean: true or false to indicate if you want the raw PBX OSSI response.

Examples:

    curl -X POST -H "Content-Type: application/json" \
    -d '{"termtype": "ossi","command": "display time"}' \
    http://localhost:8000/v3/uw01

    curl -X POST -H "Content-Type: application/json" \
    -d '{"termtype": "ossi",
        "command": "display station 12345",
        "fields": {"8003ff00": "12345 Test", "8005ff00": ""}}' \
    http://localhost:8000/v3/uw01

    curl -X POST -H "Content-Type: application/json" \
    -d '{"termtype": "ossi",
        "command": "list extension count 10",
        "fields": {"0001ff00": "", "0002ff00": ""}}' \
    http://localhost:8000/v3/uw01

The v3 API will return a JSON object with one or more of these keys:
- ossi_objects: array with each OSSI object returned by the PBX
- screens: an array containing the vt220 screens
- error: a string with any error message from the PBX
- debug: an array with each raw line from the PBX OSSI response


### v2

The v2 API uses XML.

The `<command>` element has 3 attributes:
1. pbxName: the name of the pbx that should match the name in the URL
2. cmdType: ossi or vt220
3. cmd: the command to run on the pbx

The `<command>` element may have multiple child `<field>` elements. If the field has a text node then that text will be use for change commands.

`<field>` elements have 1 attribute:
1. fid: the OSSI field id


Examples:

    curl -d 'request=<command pbxName="uw01" cmdType="ossi" cmd="display time"/>' \
    http://localhost:8000/v2/uw01


    curl -d 'request=<command pbxName="uw01" cmdType="ossi" cmd="display station 12345">
       <field fid="8005ff00"/>
       <field fid="8003ff00">12345 Test</field>
    </command>' \
    http://localhost:8000/v2/uw01

    curl -d 'request=<command pbxName="uw01" cmdType="ossi" cmd="list extension count 10">
       <field fid="0001ff00"/>
       <field fid="0002ff00"/>
    </command>' \
    http://localhost:8000/v2/uw01

The v2 API will return a XML document with the `<command>` element and one or more of these child elements:
- `<ossi_object>`
- `<screen>`
- `<error>`


## Using pbx.definity in your own python code

You can import pbxd.pbx.definity in your own python code if you want to have more
control or don't need the pbxd web service.

    python3 -m venv venv && . venv/bin/activate
    pip install -r requirements.txt
    pip install -e .

Example script:

    import pbxd.pbx.definity as definity
    import json
    import logging
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] - %(message)s'
    )

    with open('pbxd_conf/pbxd_uw01_conf.json') as json_file:
        config = json.load(json_file)

    pbx = definity.Terminal(
        config['connection_command'],
        config['pbx_username'],
        config['pbx_password']
    )
    pbx.connect()

    fields = {'0003ff00': ''}
    result = pbx.ossi_command('display time', fields)  # returns {"ossi_objects": [{"0003ff00": "2020"}]}
    ossi = result['ossi_objects'][0]
    print('The PBX says the year is {}'.format(ossi.get('0003ff00')))

    vt220 = pbx.vt220_command('display time')
    print('\n'.join(vt220['screens']))

    pbx.disconnect()

## Background

The development of pbxd originated with a Perl module developed to support
scripts for automating management of the Lucent G3r PBX in the earl 2000's.
As more scripts were written and run there was duplicate code and multiple
scripts accessing the PBX simultaneously. There were also more PBX systems at
remote sites. Pbxd was created to share connections to a PBX, and enable
multiple clients like web browsers to get bits of information from the PBX.

Written in Perl as a CGI script it worked well enough for many years but given
time everything changes. It is still a useful tool and the Avaya Communication
Manager still supports the OSSI protocol so pbxd has been rewritting in Python
with a JSON API.

You can see a dscription of the original version here:
http://tools.cac.washington.edu/2010/04/avaya-pbx-admin-web-service.html
