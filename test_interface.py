import os
import xml.etree.ElementTree as ET

import pytest

import opusrepository
import xml_parser

@pytest.fixture
def client():
    opusrepository.app.config['TESTING'] = True
    client = opusrepository.app.test_client()

    yield client

def login(client, username, password):
    return client.post('/login/', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

def test_login_logout(client):
    rv = login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    assert b'You are now logged in' in rv.data
    rv = logout(client)
    assert b'You have been logged out!' in rv.data
    rv = login(client, os.environ["TESTUSER"], "wrongpassword")
    assert b'Invalid credentials, try again.' in rv.data
    rv = login(client, "wrongusername", os.environ["TESTPW"])
    assert b'Invalid credentials, try again.' in rv.data

def test_registering(client):
    rv = client.get('/register/')
    assert b'Register' in rv.data

    rv = client.post('/register/', data=dict(
        username = "",
        email = "123test456user789",
        password = "123test456user789",
        confirm = "123test456user789"
    ), follow_redirects=True)
    assert b'Field must be between 4 and 20 characters long.' in rv.data

    rv = client.post('/register/', data=dict(
        username = "123test456user789",
        email = "",
        password = "123test456user789",
        confirm = "123test456user789"
    ), follow_redirects=True)
    assert b'Field must be between 6 and 50 characters long.' in rv.data

    rv = client.post('/register/', data=dict(
        username = "123test456user789",
        email = "123test456user789",
        password = "123test456user789",
        confirm = ""
    ), follow_redirects=True)
    assert b'Passwords must match' in rv.data

    rv = client.post('/register/', data=dict(
        username = "123test456user789",
        email = "123test456user789",
        password = "123test456user789",
        confirm = "123test456user789"
    ), follow_redirects=True)
    assert b'Thanks for registering!' in rv.data

    c, conn = opusrepository.connection()
    c.execute("DELETE FROM users WHERE username = (%s)", "123test456user789")
    conn.commit()
    c.close()
    conn.close()

def test_access_frontpage(client):
    rv = client.get('/', follow_redirects=True)
    assert b'You need to login first' in rv.data 
    assert b'type="submit" value="Login"' in rv.data
    login(client, os.environ["TESTUSER"], os.environ["TESTPW"])
    rv = client.get('/', follow_redirects=True)
    assert b'My corpora' in rv.data 
    assert b'My groups' in rv.data
    
def test_allowed_file():
    extensions = ['pdf', 'doc', 'txt', 'xml', 'html', 'tar', 'gz']
    for extension in extensions:
        print(opusrepository.allowed_file("ajokielto."+extension))
        assert opusrepository.allowed_file("ajokielto."+extension)
    invalid = ["ajokielto.exe", "ajokieltopdf"]
    for i in invalid:
        assert not opusrepository.allowed_file(i)

def test_parseLine():
    parser = xml_parser.XmlParser([])
    result = parser.parseLine('<div test="attribute">hello</div>')
    assert result == ('"div"', '"hello"', '"div"', {'test': 'attribute'})

def test_recursiveGroups():
    parser = xml_parser.XmlParser([])
    parser.recursiveGroups(ET.fromstring(
        '<entry id="mikkotest" kind="user info">\
            <member>mikkotest</member>\
            <my_group>mikkotest</my_group>\
    </entry>'
    ))

    assert len(parser.elementList) == 0
    parser.recursiveGroups(ET.fromstring(
        '<entry id="mikkotest" kind="user info">\
            <member>mikkotest</member>\
            <member_of>mikkotest,public</member_of>\
            <my_group>mikkotest</my_group>\
        </entry>'
    ))
    assert parser.elementList[0] == "mikkotest" 
    assert parser.elementList[1] == "public"

def test_groupsForUser():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="group/mikkotest">',
                '<entry id="mikkotest" kind="user info">',
                    '<member>mikkotest</member>',
                    '<member_of>mikkotest,public</member_of>',
                    '<my_group>mikkotest</my_group>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/mikkotest/" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    groups = parser.groupsForUser()
    assert groups[0] == "mikkotest" 
    assert groups[1] == "public"

def test_recursiveCorpora():
    parser = xml_parser.XmlParser([])

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry directory="mikkocorpus2/mikkotest" />'\
        '</list>'
    ))
    assert len(parser.elementList) == 0

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry path="mikkocorpus/mikkotest" />'\
            '<entry path="mikkocorpus2/mikkotest" />'\
        '</list>'
    ))
    assert parser.elementList[0] == "mikkocorpus" 
    assert parser.elementList[1] == "mikkocorpus2"

    parser.recursiveCorpora(ET.fromstring(
        '<list path="">'\
            '<entry path="mikkocorpus/mikkotest" />'\
            '<entry path="mikkocorpus2/mikkotest" />'\
        '</list>'
    ))
    assert len(parser.elementList) == 2 
    assert parser.elementList[0] == "mikkocorpus" 
    assert parser.elementList[1] == "mikkocorpus2"
      
def test_corporaForUser():
    xml_data = [
        '<letsmt-ws version="56">'\
            '<list path="">'\
                '<entry path="mikkocorpus2/mikkotest" />'\
                '<entry path="mikkocorpus/mikkotest" />'\
            '</list>'\
            '<status code="0" location="/metadata" operation="GET" type="ok">Found 2 matching entries</status>'\
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    corpora = parser.corporaForUser()

    assert corpora[0] == "mikkocorpus2" 
    assert corpora[1] == "mikkocorpus"

def test_recursiveCollect():
    element = ET.fromstring(
        '<list path="/mikkocorpus">'\
            '<entry kind="branch" path="/mikkocorpus/mikkotest">'\
                '<name>mikkotest</name>'\
                '<group>public</group>'\
                '<owner>mikkotest</owner>'\
            '</entry>'\
        '</list>'
    )
    parser = xml_parser.XmlParser([])
    parser.recursiveCollect(element, "name")
    assert parser.elementList[-1] == "mikkotest"
    parser.recursiveCollect(element, "group")
    assert parser.elementList[-1] == "public"

def test_collectToList():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus">',
                '<entry kind="branch" path="/mikkocorpus/mikkotest">',
                    '<name>mikkotest</name>',
                    '<group>public</group>',
                    '<owner>mikkotest</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ] 

    parser = xml_parser.XmlParser(xml_data)
    elementlist = parser.collectToList("group")
    assert len(elementlist) == 1 
    assert elementlist[0] == "public"

def test_branchesForCorpus():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus">',
                '<entry kind="branch" path="/mikkocorpus/mikkotest">',
                    '<name>mikkotest</name>',
                    '<group>public</group>',
                    '<owner>mikkotest</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ] 

    parser = xml_parser.XmlParser(xml_data)
    branches = parser.branchesForCorpus()
    assert len(branches) == 1 
    assert branches[0] == "mikkotest"

def test_getUsers():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/group/">',
                '<entry id="public" kind="group" owner="admin">',
                    '<user>user1</user>',
                    '<user>user2</user>',
                    '<user>user3</user>',
                    '<user>user4</user>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/public" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    
    parser = xml_parser.XmlParser(xml_data)
    users = parser.getUsers()
    assert len(users) == 4 
    assert users[0] == "user1" 
    assert users[3] == "user4"

def test_navigateDirectory():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus/mikkotest/uploads">',
                '<entry kind="file">',
                    '<name>html.tar.gz</name>',
                    '<commit revision="HEAD">',
                        '<author>mikkotest</author>',
                        '<date>unknown</date>',
                    '</commit>',
                    '<group>public</group>',
                    '<owner>mikkotest</owner>',
                    '<size>14210</size>',
                '</entry>',
                '<entry kind="dir">',
                      '<name>html</name>',
                      '<commit revision="HEAD">',
                          '<author>mikkotest</author>',
                          '<date>unknown</date>',
                      '</commit>',
                      '<group>public</group>',
                      '<owner>mikkotest</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus/mikkotest/uploads" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    dirs = parser.navigateDirectory()

    assert len(dirs) == 2
    assert dirs[0][0] == "html.tar.gz"
    assert dirs[0][1] == "file"
    assert dirs[1][0] == "html"
    assert dirs[1][1] == "dir"

def test_getMonolingualAndParallel():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="">',
                '<entry path="mikkocorpus/mikkotest">',
                    '<name>mikkotest</name>',
                    '<gid>public</gid>',
                    '<import_queue></import_queue>',
                    '<langs>fi,en,sv</langs>',
                    '<modif>2018-11-27 14:05:14</modif>',
                    '<origin></origin>',
                    '<owner>mikkotest</owner>',
                    '<parallel-langs>fi-sv,en-fi,en-sv</parallel-langs>',
                '</entry>',
            '</list>',
            '<status code="0" location="/metadata/mikkocorpus/mikkotest" operation="GET" type="ok">Found matching path ID. Listing all of its properties</status>',
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    mopa = parser.getMonolingualAndParallel()
    assert len(mopa[0]) == 3
    assert len(mopa[1]) == 3
    for lan in [["fi", "dir"], ["sv", "dir"], ["en", "dir"]]:
        assert lan in mopa[0]
    for lan in [["fi-sv", "dir"], ["en-sv", "dir"], ["en-fi", "dir"]]:
        assert lan in mopa[1]

def test_recursiveMetadata():
    element = ET.fromstring(
        '<entry path="mikkocorpus/mikkotest/uploads/html.tar.gz">'\
              '<description>test</description>'\
              '<direction>unknown</direction>'\
              '<gid>public</gid>'\
              '<owner>mikkotest</owner>'\
              '<status>job canceled</status>'\
        '</entry>'
    )

    parser = xml_parser.XmlParser([])
    parser.recursiveMetadata(element)
    correct = {
        "description": "test",
        "direction": "unknown",
        "gid": "public",
        "owner": "mikkotest",
        "status": "job canceled"
    }
    for key in correct.keys():
        assert parser.elementDict[key] == correct[key]

def test_getMetadata():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="">',
            '<entry path="mikkocorpus/mikkotest/uploads/html.tar.gz">',
                  '<description>test</description>',
                  '<direction>unknown</direction>',
                  '<gid>public</gid>',
                  '<owner>mikkotest</owner>',
                  '<status>job canceled</status>',
            '</entry>',
            '</list>',
            '<status code="0" location="/metadata/mikkocorpus/mikkotest/uploads/html.tar.gz" operation="GET" type="ok">Found matching path ID. Listing all of its properties</status>',
        '</letsmt-ws>'
    ]

    parser = xml_parser.XmlParser(xml_data)
    metadata = parser.getMetadata()
    correct = {
        "description": "test",
        "direction": "unknown",
        "gid": "public",
        "owner": "mikkotest",
        "status": "job canceled"
    }
    for key in correct.keys():
        assert metadata[key] == correct[key]

def test_getAlignmentCandidates():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="mikkocorpus/mikkotest/">',
                '<entry path="mikkocorpus/mikkotest/xml/en/html/ajokielto.xml">',
                    '<align-candidates>xml/fi/html/ajokielto.xml</align-candidates>',
                    '<aligned_with>xml/fi/html/ajokielto.xml,xml/sv/html/ajokielto.xml</aligned_with>',
                    '<gid>public</gid>',
                    '<imported_from>uploads/html.tar.gz:html/en/ajokielto.html</imported_from>',
                    '<language>en</language>',
                    '<owner>mikkotest</owner>',
                    '<parsed>ud/en/html/ajokielto.xml</parsed>',
                    '<resource-type>corpusfile</resource-type>',
                    '<size>38</size>',
                    '<status>successfully aligned with mikkocorpus/mikkotest/xml/sv/html/ajokielto.xml</status>',
                '</entry>',
            '</list>',
            '<status code="0" location="/metadata/mikkocorpus/mikkotest" operation="GET" type="ok">Found 1 matching entries</status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    candidates = parser.getAlignCandidates()
    correct = {'en/html/ajokielto.xml': ['fi/html/ajokielto.xml']}

    for key in correct.keys():
        for item in correct[key]:
            assert item in candidates[key]

def test_recursiveAttrTag():
    element = ET.fromstring(
        '<list path="/group/">'\
            '<entry id="mikkotest" kind="group" owner="mikkotest" testattr="testvalue">'\
                '<user>mikkotest</user>'\
            '</entry>'\
        '</list>'
    )
    parser = xml_parser.XmlParser([])
    parser.recursiveAttrTag(element, "entry", "testattr")
    
    assert parser.elementString == "testvalue"

def test_getAttrFromTag():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/group/">',
                '<entry id="mikkotest" kind="group" owner="mikkotest" testattr="testvalue">',
                    '<user>mikkotest</user>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/mikkotest" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    assert parser.getAttrFromTag("entry", "testattr") == "testvalue"

def test_getGroupOwner():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/group/">',
                '<entry id="mikkotest" kind="group" owner="mikkotest" testattr="testvalue">',
                    '<user>mikkotest</user>',
                '</entry>',
            '</list>',
            '<status code="0" location="/group/mikkotest" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    assert parser.getGroupOwner() == "mikkotest"

def test_getJobs():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="jobs">',
                '<entry name="job_1543831841_642742498" file="mikkocorpus/mikkotest/uploads/html.tar.gz" id="890" job="mikkocorpus/mikkotest/jobs/import/uploads/html.tar.gz.xml" status="RUNNING" />',
            '</list>',
            '<status code="0" location="job" operation="GET" type="ok" />',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    jobs = parser.getJobs()
    assert jobs[0][0] == "mikkocorpus/mikkotest/uploads/html.tar.gz"
    assert jobs[0][1] == "RUNNING"
    
def test_getFileContent():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml">',
                '<entry><?xml version="1.0" encoding="utf-8"?>',
                '<letsmt version="1.0">',
                '<p id="1">',
                '<s id="1">If a person is sentenced to a punishment for causing a serious traffic hazard, driving while intoxicated or driving while seriously intoxicated, the court also imposes a driving ban for at most five years.</s>',
                '</p>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus/mikkotest/xml/en/html/ajokielto.xml" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    content = parser.getFileContent()

    correct = '<?xml version="1.0" encoding="utf-8"?>\n'\
    '<letsmt version="1.0">\n'\
    '<p id="1">\n'\
    '<s id="1">If a person is sentenced to a punishment for causing a serious traffic hazard, driving while intoxicated or driving while seriously intoxicated, the court also imposes a driving ban for at most five years.</s>\n'\
    '</p>\n'

    assert content == correct

def test_itemExists():
    xml_data = [
        '<letsmt-ws version="56">',
            '<list path="/mikkocorpus">',
                '<entry kind="branch" path="/mikkocorpus/mikkotest">',
                    '<name>mikkotest</name>',
                    '<group>public</group>',
                    '<owner>mikkotest</owner>',
                '</entry>',
            '</list>',
            '<status code="0" location="/storage/mikkocorpus" operation="GET" type="ok"></status>',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)
    
    assert parser.itemExists() == True
        
    xml_data = [
        '<letsmt-ws version="56">',
            '''<status code="6" location="/storage/mikkocorpusdoesnotexist" operation="GET" type="error">Cannot find/read slot 'mikkocorpusdoesnotexist'</status>''',
        '</letsmt-ws>'
    ]
    parser = xml_parser.XmlParser(xml_data)

    assert parser.itemExists() == False
    
def test_rh_get():
    assert True

def test_rh_put():
    assert True

def test_rh_post():
    assert True

def test_rh_upload():
    assert True

def test_rh_delete():
    assert True

