from flask import json
import os
import pexpect

os.environ['PBXD_INTERNAL_V3_URL'] = 'http://localhost:5000/v3'
pbx_name = 'n1'
os.environ['PBXD_CONF'] = 'tests/pbxd_test_conf.json'
os.environ['PBX_COMMAND_TIMEOUT'] = '30'
os.environ['PBX_NAME'] = pbx_name
import pbxd.app  # noqa: E402
from pbxd.app import pbx  # noqa: E402


app = pbxd.app.load()


def test_health_check():
    with app.test_client() as c:
        rv = c.get('/healthz')
        assert rv.status_code == 200
        assert b'ossi_objects' in rv.data


def test_index_page_404():
    with app.test_client() as c:
        rv = c.get('/')
        assert rv.status_code == 404


def test_v3_pbx_name_check():
    app.testing = True
    with app.test_client() as c:
        rv = c.post('/v3/wrong-pbx', data='')
        assert rv.status_code == 500


def test_v2_pbx_name_check():
    app.testing = True
    with app.test_client() as c:
        rv = c.post('/v2/wrong-pbx', data={"request": '<command pbxName="wrong-pbx" cmdType="ossi" cmd="display time"/>'})
        assert rv.status_code == 500


def test_bad_v3_request():
    app.testing = True
    with app.test_client() as c:
        rv = c.post('/v3/{}'.format(pbx_name), data='')
        assert rv.status_code == 400


def test_bad_v2_request():
    app.testing = True
    with app.test_client() as c:
        rv = c.post('/v2/{}'.format(pbx_name), data='')
        assert rv.status_code == 400


def test_pbx_disconnect():
    pbx.session = pexpect.spawn("sh -c \"printf 'Proceed With Logoff' && sleep 1\"", timeout=5)
    pbx.disconnect()
    assert pbx.connected_termtype is None


def test_pbx_termtype_select():
    expect_stream = "sh -c \"stty -echo && printf 'Terminal Type (test): [test]\nt\n' && cat -\""
    pbx.session = pexpect.spawn(expect_stream, timeout=2)
    pbx._select_termtype(pbx.Termtype.ossi)
    assert True


def assert_in_v2_response(termtype, expected_texts, v2_post, expect_stream):
    pbx.connected_termtype = pbx.Termtype(termtype)  # use a known starting value
    pbx.pbx_command_timeout = 2
    pbx.session = pexpect.spawn(expect_stream, timeout=2)
    app.testing = True
    with app.test_client() as c:
        resp = c.post('/v2/{}'.format(pbx_name), data={"request": v2_post})
        for txt in expected_texts:
            assert txt in resp.data.decode('utf-8')
    pbx.session.close()


def assert_in_v3_response(termtype, expected_texts, v3_post, expect_stream):
    pbx.connected_termtype = pbx.Termtype(termtype)  # use a known starting value
    pbx.pbx_command_timeout = 2
    pbx.session = pexpect.spawn(expect_stream, timeout=2)
    app.testing = True
    with app.test_client() as c:
        resp = c.post('/v3/{}'.format(pbx_name), json=v3_post)
        data = json.loads(resp.data)
        assert isinstance(data, dict) is True
        for txt in expected_texts:
            assert txt in resp.data.decode('utf-8')
    pbx.session.close()


def test_ossi_display_1_field():
    v3_post = {"termtype": "ossi", "command": "display time", "fields": {"0007ff00": ""}}
    v2_post = """<command pbxName="{}" cmdType="ossi" cmd="display time">
                        <field fid="0007ff00"/>
            </command>""".format(pbx_name)
    expect_stream = "sh -c \"stty -echo && printf 'f0005ff00	0006ff00	0007ff00\nd12	34	56\nt\n' && cat -\""
    expected_texts = ['0007ff00']
    assert_in_v3_response('ossi4', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('ossi4', expected_texts, v2_post, expect_stream)


def test_ossi_display_multiple_fields():
    v3_post = {"termtype": "ossi", "command": "display time", "fields": {"0005ff00": "", "0006ff00": "", "0007ff00": ""}}
    v2_post = """<command pbxName="{}" cmdType="ossi" cmd="display time">
                    <field fid="0005ff00"/>
                    <field fid="0006ff00"/>
                    <field fid="0007ff00"/>
        </command>""".format(pbx_name)
    expect_stream = "sh -c \"stty -echo && printf 'f0005ff00	0006ff00	0007ff00\nd12	34	56\nt\n' && cat -\""
    expected_texts = ['0005ff00', '0006ff00', '0007ff00']
    assert_in_v3_response('ossi4', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('ossi4', expected_texts, v2_post, expect_stream)


def test_ossi_display_all_fields():
    v3_post = {"termtype": "ossi", "command": "display time", "fields": {}}
    v2_post = '<command pbxName="{}" cmdType="ossi" cmd="display time"/>'.format(pbx_name)
    expect_stream = "sh -c \"stty -echo && printf 'f0005ff00	0006ff00	0007ff00\nd12	34	56\nt\n' && cat -\""
    expected_texts = ['0007ff00']
    assert_in_v3_response('ossi4', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('ossi4', expected_texts, v2_post, expect_stream)


def test_pbx_timeout():
    v3_post = {"termtype": "ossi", "command": "timeout test", "fields": {}}
    v2_post = '<command pbxName="{}" cmdType="ossi" cmd="timeout test"/>'.format(pbx_name)
    expect_stream = "sh -c \"stty -echo && sleep 10\""
    expected_texts = ['PBX timeout']
    assert_in_v3_response('ossi4', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('ossi4', expected_texts, v2_post, expect_stream)


def test_pbx_disconnectio_eof():
    v3_post = {"termtype": "ossi", "command": "disconnect EOF test", "fields": {}}
    v2_post = '<command pbxName="{}" cmdType="ossi" cmd="disconnect EOF test"/>'.format(pbx_name)
    expect_stream = "sh -c \"stty -echo && sleep 1\""
    expected_texts = ['PBX connection failed with EOF']
    assert_in_v3_response('ossi4', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('ossi4', expected_texts, v2_post, expect_stream)


def test_ossi_list_multiple_ossi_objects():
    v3_post = {"termtype": "ossi", "command": "list extension count 3", "fields": {}}
    v2_post = '<command pbxName="{}" cmdType="ossi" cmd="list extension count 3"/>'.format(pbx_name)
    expect_stream = "sh -c \"stty -echo && printf 'f0001ff00\nd12345\nn\nd21000\nn\nd31000\nt\n' && cat -\""
    expected_texts = ['0001ff00', '31000']
    assert_in_v3_response('ossi4', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('ossi4', expected_texts, v2_post, expect_stream)


def test_ossi_list_with_no_results():
    v3_post = {"termtype": "ossi", "command": "list extension 9999999999 count 1", "fields": {}}
    v2_post = '<command pbxName="{}" cmdType="ossi" cmd="list extension 9999999999 count 1"/>'.format(pbx_name)
    expect_stream = "sh -c \"stty -echo && printf 'f0001ff00\nt\n' && cat -\""
    expected_texts = ['ossi_obj']
    assert_in_v3_response('ossi4', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('ossi4', expected_texts, v2_post, expect_stream)


def test_ossi_error():
    v3_post = {"termtype": "ossi", "command": "display unknown object"}
    v2_post = '<command pbxName="{}" cmdType="ossi" cmd="display unknown object"/>'.format(pbx_name)
    expect_stream = "sh -c \"printf 'eERROR 00000000 nnn unknown is an invalid entry; please press HELP\nt\n' && cat -\""
    expected_texts = ['invalid entry']
    assert_in_v3_response('ossi4', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('ossi4', expected_texts, v2_post, expect_stream)


def test_vt220_error():
    v3_post = {"termtype": "vt220", "command": "display unknown object"}
    v2_post = '<command pbxName="{}" cmdType="vt220" cmd="display unknown object"/>'.format(pbx_name)
    expect_stream = "sh -c \"printf 'display unknown object\x1b7\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[23;0H\x1b[0;7m\x1b[0;7munknown is an invalid entry; please press HELP\x1b[0m\x1b8\x1b[24;1H\x1b[KCommand: display \n[KCommand:' && cat -\""  # noqa: E501
    expected_texts = ['invalid entry']
    assert_in_v3_response('vt220', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('vt220', expected_texts, v2_post, expect_stream)


def test_vt220_single_page():
    v3_post = {"termtype": "vt220", "command": "display time"}
    v2_post = '<command pbxName="{}" cmdType="vt220" cmd="display time"/>'.format(pbx_name)
    expect_stream = "sh -c \"printf 'display time\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[24;0H\x1b[K\x1b[1;0H\x1b[0;7m                                                                                \x1b[0m\x1b[1;0H\x1b7\x1b[1;1H\x1b[0;7mdisplay time \x1b[0m\x1b8\x1b[1;65H\x1b[0;7mPage   1 of   1\x1b[0m\x1b[2;32HDATE AND TIME\x1b[4;9HDATE\x1b[6;13HDay of the Week: \x1b[16;28H\x1b7\x1b[1;65H\x1b[0;7m                \x1b[0m\x1b8\x1b[24;1H\x1b[KCommand: \n[KCommand: \n' && cat -\""  # noqa: E501
    expected_texts = ['DATE AND TIME']
    assert_in_v3_response('vt220', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('vt220', expected_texts, v2_post, expect_stream)


def test_vt220_multipage_display():
    v3_post = {"termtype": "vt220", "command": "list extension count 10"}
    v2_post = '<command pbxName="{}" cmdType="vt220" cmd="list extension count 10"/>'.format(pbx_name)
    expect_stream = "sh -c \"printf 'list extension count 10\x1b[1;1H\x1b[24;0H\x1b[K\x1b7\x1b[1;1H\x1b[0;7mlist extension-type count 10 \x1b[0m\x1b8\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[2;1H\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b7\x1b[1;65H\x1b[0;7m       Page   1\x1b[0m\x1b8\x1b[3;1H\x1b[3;29HEXTENSION TYPE\n\r\n\r\x1b[5;6H                                                    COR/      Cv1/\n\r\x1b[6;6HExt               Type/Name                         COS  TN   Cv2\n\r\x1b[7;6H---               ---------                         ---  --   ----\n\r\x1b[8;6H  \x1b[21;68H    \n\r\x1b7\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[23;0H\x1b[0;7m\x1b[0;7m\t\tpress CANCEL to quit --  press NEXT PAGE to continue\x1b[0m\x1b8\x1b[22;0H\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[2;1H\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b7\x1b[1;65H\x1b[0;7m       Page   2\x1b[0m\x1b8\x1b[3;1H\x1b[3;29HEXTENSION TYPE\n\r\n\r\x1b[5;6H                                                    COR/      Cv1/\n\r\x1b[6;6HExt               Type/Name                         COS  TN   Cv2\n\r\x1b[7;6H---               ---------                         ---  --   ----\n\r\x1b[8;6H     \x1b[13;68H    \n\r\x1b7\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[23;0H\x1b[0;7m\x1b[0;7mCommand successfully completed\x1b[0m\x1b8\x1b7\x1b[1;65H\x1b[0;7m                \x1b[0m\x1b8\x1b[24;1H\x1b[KCommand: \n [KCommand: \n' && cat -\""  # noqa: E501
    expected_texts = ['EXTENSION TYPE']
    assert_in_v3_response('vt220', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('vt220', expected_texts, v2_post, expect_stream)


def test_vt220_paging():
    v3_post = {"termtype": "vt220", "command": "status station 55555"}
    v2_post = '<command pbxName="{}" cmdType="vt220" cmd="status station 55555"/>'.format(pbx_name)
    expect_stream = "sh -c \"printf ' status station 55555\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[24;0H\x1b[K\x1b[1;0H\x1b[0;7m                                                                                \x1b[0m\x1b[1;0H\x1b[2;1H\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b7\x1b[1;1H\x1b[0;7mstatus station 55555 \x1b[0m\x1b8\x1b[1;65H\x1b[0;7mPage   1 of   3\x1b[0m\x1b[2;31HGENERAL STATUS\x1b[3;6HAdministered Type: \x1b[3;25H9611SIP\x1b[4;9HConnected Type: \x1b[4;25HN/A            \x1b[5;14HExtension: \x1b[5;25H55555           \x1b[6;19HPort: \x1b[6;25HS001234   \x1b[3;44HService State: \x1b[3;59Hout-of-service        \x1b[4;44HSignal Status: \x1b[4;59Hnot connected         \x1b[5;43HNetwork Region: \x1b[5;59HNot Assigned\x1b[6;39HParameter Download: \x1b[6;59Hpending              \x1b[2;45H\x1b[0m\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[24;0H\x1b[K\x1b[1;0H\x1b[0;7m                                                                                \x1b[0m\x1b[1;0H\x1b[2;1H\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b7\x1b[1;1H\x1b[0;7mstatus station 55555 \x1b[0m\x1b8\x1b[1;65H\x1b[0;7mPage   2 of   3\x1b[0m\x1b[2;33HGENERAL STATUS\x1b[4;1HCONNECTED STATION INFORMATION\x1b[5;16HPart ID Number: \x1b[5;32Hunavailable\x1b[6;17HSerial Number: \x1b[6;32Hunavailable \x1b[2;47H\x1b[0m\x1b[23;0H\x1b[0;7m                                                                                \x1b[0m\x1b[23;0H\x1b[24;0H\x1b[K\x1b[1;0H\x1b[0;7m                                                                                \x1b[0m\x1b[1;0H\x1b[2;1H\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b[K\x1b[B\x1b7\x1b[1;1H\x1b[0;7mstatus station 55555 \x1b[0m\x1b8\x1b[1;65H\x1b[0;7mPage   3 of   3\x1b[0m\x1b[2;36HFINAL TEST PAGE \x1b[2;46H\x1b[0m\x1b[KCommand: \n [KCommand: \n' && cat -\""  # noqa: E501
    expected_texts = ['FINAL TEST PAGE']
    assert_in_v3_response('vt220', expected_texts, v3_post, expect_stream)
    assert_in_v2_response('vt220', expected_texts, v2_post, expect_stream)


def test_setup_session_for_disconnect():
    # this sets the session so the flask atexit can exit cleanly
    pbx.session = pexpect.spawn("sh -c \"printf 'Proceed With Logoff' && sleep 1\"", timeout=5)
    assert True
